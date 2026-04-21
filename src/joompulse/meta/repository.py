"""Idempotent upserts for Meta domain entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from joompulse.db.models import (
    Ad,
    AdSet,
    Campaign,
    Creative,
    CreativeAsset,
    MetricSnapshot,
)
from joompulse.db.models.enums import AdStatus, AssetKind
from joompulse.meta.client import AdRow, CreativeRow, InsightRow

_META_STATUS_MAP = {
    "ACTIVE": AdStatus.ACTIVE,
    "PAUSED": AdStatus.PAUSED,
    "ARCHIVED": AdStatus.ARCHIVED,
    "DELETED": AdStatus.DELETED,
}


def _map_status(raw: str | None) -> AdStatus:
    if not raw:
        return AdStatus.UNKNOWN
    return _META_STATUS_MAP.get(raw.upper(), AdStatus.UNKNOWN)


async def upsert_campaign(
    session: AsyncSession,
    *,
    meta_campaign_id: str,
    ad_account_id: uuid.UUID,
    name: str | None = None,
    objective: str | None = None,
    status: str | None = None,
) -> uuid.UUID:
    stmt = (
        insert(Campaign)
        .values(
            id=uuid.uuid4(),
            meta_campaign_id=meta_campaign_id,
            ad_account_id=ad_account_id,
            name=name,
            objective=objective,
            status=_map_status(status),
        )
        .on_conflict_do_update(
            index_elements=["meta_campaign_id"],
            set_={"name": name, "objective": objective, "status": _map_status(status)},
        )
        .returning(Campaign.id)
    )
    return (await session.execute(stmt)).scalar_one()


async def upsert_ad_set(
    session: AsyncSession,
    *,
    meta_adset_id: str,
    campaign_id: uuid.UUID,
    name: str | None = None,
    status: str | None = None,
) -> uuid.UUID:
    stmt = (
        insert(AdSet)
        .values(
            id=uuid.uuid4(),
            meta_adset_id=meta_adset_id,
            campaign_id=campaign_id,
            name=name,
            status=_map_status(status),
        )
        .on_conflict_do_update(
            index_elements=["meta_adset_id"],
            set_={"name": name, "status": _map_status(status)},
        )
        .returning(AdSet.id)
    )
    return (await session.execute(stmt)).scalar_one()


async def upsert_creative(
    session: AsyncSession,
    *,
    creative: CreativeRow,
    fingerprint_hash: str,
) -> tuple[uuid.UUID, bool]:
    """Returns (id, was_created)."""
    existing = await session.scalar(
        select(Creative.id).where(Creative.meta_creative_id == creative.meta_creative_id)
    )
    if existing is not None:
        await session.execute(
            insert(Creative)
            .values(
                id=existing,
                meta_creative_id=creative.meta_creative_id,
                fingerprint_hash=fingerprint_hash,
                title=creative.title,
                body=creative.body,
                cta_type=creative.cta_type,
            )
            .on_conflict_do_update(
                index_elements=["meta_creative_id"],
                set_={
                    "fingerprint_hash": fingerprint_hash,
                    "title": creative.title,
                    "body": creative.body,
                    "cta_type": creative.cta_type,
                },
            )
        )
        return existing, False

    new_id = uuid.uuid4()
    await session.execute(
        insert(Creative).values(
            id=new_id,
            meta_creative_id=creative.meta_creative_id,
            fingerprint_hash=fingerprint_hash,
            title=creative.title,
            body=creative.body,
            cta_type=creative.cta_type,
        )
    )
    return new_id, True


async def upsert_creative_asset(
    session: AsyncSession,
    *,
    creative_id: uuid.UUID,
    kind: AssetKind,
    s3_key: str,
    width: int | None = None,
    height: int | None = None,
    duration_s: float | None = None,
) -> uuid.UUID:
    existing = await session.scalar(
        select(CreativeAsset.id).where(
            CreativeAsset.creative_id == creative_id, CreativeAsset.s3_key == s3_key
        )
    )
    if existing is not None:
        return existing
    new_id = uuid.uuid4()
    await session.execute(
        insert(CreativeAsset).values(
            id=new_id,
            creative_id=creative_id,
            kind=kind,
            s3_key=s3_key,
            width=width,
            height=height,
            duration_s=duration_s,
        )
    )
    return new_id


async def upsert_ad(
    session: AsyncSession,
    *,
    row: AdRow,
    ad_set_id: uuid.UUID,
    creative_id: uuid.UUID,
) -> uuid.UUID:
    stmt = (
        insert(Ad)
        .values(
            id=uuid.uuid4(),
            meta_ad_id=row.meta_ad_id,
            ad_set_id=ad_set_id,
            creative_id=creative_id,
            name=row.name,
            status=_map_status(row.status),
        )
        .on_conflict_do_update(
            index_elements=["meta_ad_id"],
            set_={
                "ad_set_id": ad_set_id,
                "creative_id": creative_id,
                "name": row.name,
                "status": _map_status(row.status),
            },
        )
        .returning(Ad.id)
    )
    return (await session.execute(stmt)).scalar_one()


async def write_metric_snapshot(
    session: AsyncSession,
    *,
    ad_id: uuid.UUID,
    captured_at: datetime,
    insight: InsightRow,
) -> None:
    await session.execute(
        insert(MetricSnapshot).values(
            id=uuid.uuid4(),
            ad_id=ad_id,
            captured_at=captured_at,
            impressions=insight.impressions,
            clicks=insight.clicks,
            spend=insight.spend,
            ctr=insight.ctr,
            cpm=insight.cpm,
            conversions=insight.conversions,
        )
    )


async def latest_snapshot(session: AsyncSession, ad_id: uuid.UUID) -> MetricSnapshot | None:
    stmt = (
        select(MetricSnapshot)
        .where(MetricSnapshot.ad_id == ad_id)
        .order_by(MetricSnapshot.captured_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def already_analyzed(session: AsyncSession, creative_id: uuid.UUID) -> bool:
    from joompulse.db.models import CreativeAnalysis  # local import to avoid cycles

    stmt = select(CreativeAnalysis.id).where(CreativeAnalysis.creative_id == creative_id).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def recent_verdict_exists(
    session: AsyncSession, ad_id: uuid.UUID, since: datetime
) -> bool:
    from joompulse.db.models import PerformanceVerdict

    stmt = (
        select(PerformanceVerdict.id)
        .where(PerformanceVerdict.ad_id == ad_id, PerformanceVerdict.captured_at >= since)
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


def classify_asset_kind(creative: CreativeRow) -> AssetKind:
    if creative.video_id:
        return AssetKind.VIDEO
    if creative.image_url:
        return AssetKind.IMAGE
    return AssetKind.CAROUSEL


def pick_asset_url(creative: CreativeRow, video_source: str | None = None) -> str | None:
    if creative.video_id and video_source:
        return video_source
    return creative.image_url


def build_fingerprint_source(creative: CreativeRow) -> dict[str, Any]:
    """Deterministic payload used as fallback fingerprint when binary is not downloaded."""
    return {
        "id": creative.meta_creative_id,
        "title": creative.title,
        "body": creative.body,
        "cta": creative.cta_type,
        "image_url": creative.image_url,
        "video_id": creative.video_id,
    }
