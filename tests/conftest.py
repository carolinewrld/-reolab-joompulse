from __future__ import annotations

import base64
import os
from collections.abc import Iterator

import pytest

from joompulse.config import get_settings
from joompulse.security import crypto


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
        "ENCRYPTION_KEY": base64.urlsafe_b64encode(b"\x01" * 32).decode(),
    }
    for k, v in defaults.items():
        if os.environ.get(k) is None:
            monkeypatch.setenv(k, v)

    get_settings.cache_clear()
    crypto._fernet.cache_clear()
    yield
    get_settings.cache_clear()
    crypto._fernet.cache_clear()
