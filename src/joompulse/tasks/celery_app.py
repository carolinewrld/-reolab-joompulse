from __future__ import annotations

from celery import Celery
from kombu import Queue

from joompulse.config import get_settings
from joompulse.tasks.schedule import BEAT_SCHEDULE

settings = get_settings()

celery_app = Celery(
    "joompulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "joompulse.tasks.fetch",
        "joompulse.tasks.analyze",
        "joompulse.tasks.notify",
    ],
)

celery_app.conf.update(
    task_queues=(
        Queue("fetch"),
        Queue("ai"),
        Queue("notify"),
    ),
    task_routes={
        "joompulse.tasks.fetch.*": {"queue": "fetch"},
        "joompulse.tasks.analyze.*": {"queue": "ai"},
        "joompulse.tasks.notify.*": {"queue": "notify"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    beat_schedule=BEAT_SCHEDULE,
)
