from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Minimal env so `Settings()` validates in tests without a real .env
    defaults = {
        "POSTGRES_DSN": "postgresql+asyncpg://u:p@localhost/db",
        "POSTGRES_DSN_SYNC": "postgresql://u:p@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "S3_ENDPOINT": "http://localhost:9000",
        "S3_BUCKET": "test",
        "S3_ACCESS_KEY": "a",
        "S3_SECRET_KEY": "b",
        "ENCRYPTION_KEY": "x" * 44,
    }
    for k, v in defaults.items():
        if os.environ.get(k) is None:
            monkeypatch.setenv(k, v)
    yield
