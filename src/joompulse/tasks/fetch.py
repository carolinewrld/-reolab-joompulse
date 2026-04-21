from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from joompulse.db.base import get_sessionmaker
from joompulse.db.models import AdAccount
from joompulse.logging import get_logger
from joompulse.meta.fetcher import sync_account
from joompulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="joompulse.tasks.fetch.fetch_all_accounts")
def fetch_all_accounts() -> dict[str, int]:
    """Scheduled entrypoint: enqueue one fetch_account task per active account."""

    async def _enumerate() -> list[str]:
        async with get_sessionmaker()() as session:
            rows = await session.execute(
                select(AdAccount.meta_account_id).where(AdAccount.status == "active")
            )
            return [r[0] for r in rows.all()]

    accounts = asyncio.run(_enumerate())
    for meta_id in accounts:
        fetch_account.apply_async(args=[meta_id], queue="fetch")
    log.info("fetch.enumerate", count=len(accounts))
    return {"enqueued": len(accounts)}


@celery_app.task(
    name="joompulse.tasks.fetch.fetch_account",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=1800,
    max_retries=5,
    retry_jitter=True,
)
def fetch_account(self, meta_account_id: str) -> dict[str, int | list[str]]:  # type: ignore[no-untyped-def]
    async def _run() -> dict[str, int | list[str]]:
        async with get_sessionmaker()() as session:
            account = await session.scalar(
                select(AdAccount).where(AdAccount.meta_account_id == meta_account_id)
            )
            if account is None:
                log.warning("fetch.account.not_found", meta_account_id=meta_account_id)
                return {"ads_seen": 0, "snapshots_written": 0, "performance_triggers": []}

            stats = await sync_account(session, account)

        # Enqueue AI follow-ups outside the DB session.
        from joompulse.tasks.analyze import analyze_performance, decompose_creative

        for creative_uuid in stats.new_creatives:
            decompose_creative.apply_async(args=[creative_uuid], queue="ai")
        for ad_uuid in stats.performance_triggers:
            analyze_performance.apply_async(args=[ad_uuid], queue="ai")

        return {
            "ads_seen": stats.ads_seen,
            "snapshots_written": stats.snapshots_written,
            "new_creatives": stats.new_creatives,
            "performance_triggers": stats.performance_triggers,
        }

    return asyncio.run(_run())
