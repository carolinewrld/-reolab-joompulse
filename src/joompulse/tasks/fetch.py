from __future__ import annotations

from joompulse.logging import get_logger
from joompulse.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="joompulse.tasks.fetch.fetch_all_accounts")
def fetch_all_accounts() -> dict[str, int]:
    """Scheduled entrypoint: enqueue per-account fetch tasks."""
    log.info("fetch_all_accounts.stub")
    return {"enqueued": 0}


@celery_app.task(name="joompulse.tasks.fetch.fetch_account")
def fetch_account(ad_account_id: str) -> dict[str, int]:
    """Incremental Meta ingest for a single ad account."""
    log.info("fetch_account.stub", ad_account_id=ad_account_id)
    return {"creatives_upserted": 0, "insights_upserted": 0}
