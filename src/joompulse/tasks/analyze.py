from __future__ import annotations

from joompulse.logging import get_logger
from joompulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="joompulse.tasks.analyze.decompose_creative")
def decompose_creative(creative_id: str) -> dict[str, str]:
    log.info("decompose_creative.stub", creative_id=creative_id)
    return {"status": "stub"}


@celery_app.task(name="joompulse.tasks.analyze.analyze_performance")
def analyze_performance(ad_id: str) -> dict[str, str]:
    log.info("analyze_performance.stub", ad_id=ad_id)
    return {"status": "stub"}


@celery_app.task(name="joompulse.tasks.analyze.recompute_benchmarks")
def recompute_benchmarks() -> dict[str, int]:
    log.info("recompute_benchmarks.stub")
    return {"accounts_updated": 0}
