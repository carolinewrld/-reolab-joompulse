from __future__ import annotations

from joompulse.logging import get_logger
from joompulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="joompulse.tasks.notify.notify_verdict")
def notify_verdict(verdict_id: str) -> dict[str, str]:
    log.info("notify_verdict.stub", verdict_id=verdict_id)
    return {"status": "stub"}


@celery_app.task(name="joompulse.tasks.notify.daily_digest")
def daily_digest() -> dict[str, int]:
    log.info("daily_digest.stub")
    return {"items_sent": 0}
