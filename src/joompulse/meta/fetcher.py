"""Per-account ingest orchestrator.

Pulls ads + creatives + insights, upserts domain tables, downloads new assets
to S3, and enqueues downstream AI jobs:

  * `decompose_creative(creative_id)` — for every newly seen creative
  * `analyze_performance(ad_id)`      — once impressions >= threshold and not
                                        already evaluated within cooldown
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from joompulse.config import get_settings
from joompulse.db.models import AdAccount
from joompulse.logging import get_logger
from joompulse.meta import client as meta_client
from joompulse.meta import repository as repo
from joompulse.meta.rate_limit import TokenBucket
from joompulse.security.crypto import decrypt
from joompulse.storage import s3 as s3store
from joompulse.storage.fingerprint import sha256_bytes

log = get_logger(__name__)


@dataclass(slots=True)
class SyncStats:
    ads_seen: int = 0
    creatives_upserted: int = 0
    new_creatives: list[str] = field(default_factory=list)          # creative UUIDs
    snapshots_written: int = 0
    performance_triggers: list[str] = field(default_factory=list)   # ad UUIDs


async def load_account(session: AsyncSession, meta_account_id: str) -> AdAccount | None:
    return await session.scalar(
        select(AdAccount).where(AdAccount.meta_account_id == meta_account_id)
    )


async def sync_account(
    session: AsyncSession,
    account: AdAccount,
    *,
    since_override: datetime | None = None,
) -> SyncStats:
    settings = get_settings()
    bucket = TokenBucket()
    stats = SyncStats()

    token = decrypt(account.encrypted_access_token)
    meta_client.init_api(token)

    since = since_override or account.last_synced_at
    bucket_key = f"meta:{account.meta_account_id}"

    log.info(
        "fetch.account.start",
        account=account.meta_account_id,
        since=since.isoformat() if since else None,
    )

    try:
        async for ad_row in _iter_ads_async(account.meta_account_id, since, bucket, bucket_key):
            stats.ads_seen += 1
            await _process_ad(session, account, ad_row, bucket, bucket_key, stats)
        await session.flush()
        account.last_synced_at = datetime.now(UTC)
        await session.commit()
    finally:
        await bucket.close()

    log.info(
        "fetch.account.done",
        account=account.meta_account_id,
        ads=stats.ads_seen,
        snapshots=stats.snapshots_written,
        new_creatives=len(stats.new_creatives),
        perf_triggers=len(stats.performance_triggers),
    )
    return stats


async def _iter_ads_async(
    meta_account_id: str,
    since: datetime | None,
    bucket: TokenBucket,
    bucket_key: str,
):
    await _throttle(bucket, bucket_key)
    rows = await asyncio.to_thread(
        lambda: list(meta_client.iter_ads(meta_account_id, since=since))
    )
    for row in rows:
        yield row


async def _process_ad(
    session: AsyncSession,
    account: AdAccount,
    ad_row: meta_client.AdRow,
    bucket: TokenBucket,
    bucket_key: str,
    stats: SyncStats,
) -> None:
    if not ad_row.creative_id or not ad_row.campaign_id or not ad_row.ad_set_id:
        log.warning("fetch.ad.skip_missing_fk", meta_ad_id=ad_row.meta_ad_id)
        return

    campaign_id = await repo.upsert_campaign(
        session,
        meta_campaign_id=ad_row.campaign_id,
        ad_account_id=account.id,
        name=None,
        objective=None,
        status=ad_row.status,
    )
    ad_set_id = await repo.upsert_ad_set(
        session,
        meta_adset_id=ad_row.ad_set_id,
        campaign_id=campaign_id,
        name=None,
        status=ad_row.status,
    )

    await _throttle(bucket, bucket_key)
    creative_row = await asyncio.to_thread(meta_client.get_creative, ad_row.creative_id)

    fingerprint, uploaded = await _materialize_asset(creative_row, bucket, bucket_key)

    creative_uuid, is_new = await repo.upsert_creative(
        session, creative=creative_row, fingerprint_hash=fingerprint
    )
    if is_new:
        stats.creatives_upserted += 1
        stats.new_creatives.append(str(creative_uuid))

    if uploaded is not None:
        await repo.upsert_creative_asset(
            session,
            creative_id=creative_uuid,
            kind=repo.classify_asset_kind(creative_row),
            s3_key=uploaded.s3_key,
        )

    ad_uuid = await repo.upsert_ad(
        session,
        row=ad_row,
        ad_set_id=ad_set_id,
        creative_id=creative_uuid,
    )

    await _throttle(bucket, bucket_key)
    insight = await asyncio.to_thread(meta_client.get_insights, ad_row.meta_ad_id)
    if insight is not None:
        await repo.write_metric_snapshot(
            session,
            ad_id=ad_uuid,
            captured_at=datetime.now(UTC),
            insight=insight,
        )
        stats.snapshots_written += 1

        if await _should_trigger_performance(session, ad_uuid, insight):
            stats.performance_triggers.append(str(ad_uuid))


async def _materialize_asset(
    creative: meta_client.CreativeRow,
    bucket: TokenBucket,
    bucket_key: str,
) -> tuple[str, s3store.UploadedAsset | None]:
    url: str | None = creative.image_url
    if creative.video_id and not url:
        await _throttle(bucket, bucket_key)
        video_source = await asyncio.to_thread(meta_client.get_video_source, creative.video_id)
        if video_source:
            url = video_source

    if not url:
        # Fall back to deterministic metadata fingerprint so dedup still works.
        payload = json.dumps(repo.build_fingerprint_source(creative), sort_keys=True).encode()
        return sha256_bytes(payload), None

    uploaded = await s3store.upload_from_url(url)
    return uploaded.fingerprint, uploaded


async def _should_trigger_performance(
    session: AsyncSession,
    ad_id: uuid.UUID,
    insight: meta_client.InsightRow,
) -> bool:
    settings = get_settings()
    if insight.impressions < settings.impressions_threshold:
        return False
    cooldown_start = datetime.now(UTC) - timedelta(hours=settings.reanalyze_cooldown_h)
    if await repo.recent_verdict_exists(session, ad_id, cooldown_start):
        return False
    return True


async def _throttle(bucket: TokenBucket, key: str) -> None:
    wait_s = await bucket.acquire(key)
    if wait_s > 0:
        log.info("fetch.rate_limited", key=key, sleep_s=wait_s)
        await asyncio.sleep(wait_s)
        # second try — guaranteed after refill
        wait_s2 = await bucket.acquire(key)
        if wait_s2 > 0:
            await asyncio.sleep(wait_s2)
