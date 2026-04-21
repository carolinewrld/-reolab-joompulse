from __future__ import annotations

import asyncio
import uuid

from joompulse.ai.decomposer import decompose_creative as run_decompose
from joompulse.db.base import get_sessionmaker
from joompulse.logging import get_logger
from joompulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(
    name="joompulse.tasks.analyze.decompose_creative",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_backoff_max=900,
    max_retries=4,
    retry_jitter=True,
)
def decompose_creative(self, creative_id: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    async def _run() -> dict[str, object]:
        async with get_sessionmaker()() as session:
            outcome = await run_decompose(session, uuid.UUID(creative_id))
            if outcome is None:
                return {"status": "skipped", "creative_id": creative_id}
            return {
                "status": "ok",
                "creative_id": creative_id,
                "analysis_id": str(outcome.analysis_id),
                "pain": outcome.result.pain_codes,
                "concept": outcome.result.concept_codes,
                "object": outcome.result.object_codes,
                "cta": outcome.result.cta_codes,
                "other_count": len(outcome.result.other_suggestions),
            }

    return asyncio.run(_run())


@celery_app.task(name="joompulse.tasks.analyze.analyze_performance")
def analyze_performance(ad_id: str) -> dict[str, str]:
    log.info("analyze_performance.stub", ad_id=ad_id)
    return {"status": "stub"}


@celery_app.task(name="joompulse.tasks.analyze.recompute_benchmarks")
def recompute_benchmarks() -> dict[str, int]:
    log.info("recompute_benchmarks.stub")
    return {"accounts_updated": 0}
