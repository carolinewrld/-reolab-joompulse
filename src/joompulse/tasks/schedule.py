from __future__ import annotations

from celery.schedules import crontab

BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    "fetch-ads-every-15-min": {
        "task": "joompulse.tasks.fetch.fetch_all_accounts",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "fetch"},
    },
    "recompute-benchmarks-hourly": {
        "task": "joompulse.tasks.analyze.recompute_benchmarks",
        "schedule": crontab(minute=5),
        "options": {"queue": "ai"},
    },
    "daily-digest-10am": {
        "task": "joompulse.tasks.notify.daily_digest",
        "schedule": crontab(hour=10, minute=0),
        "options": {"queue": "notify"},
    },
}
