from __future__ import annotations

import pytest
from fakeredis import aioredis as fake_aioredis

from joompulse.meta import rate_limit


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> rate_limit.TokenBucket:
    server = fake_aioredis.FakeServer()

    async def _conn(self: rate_limit.TokenBucket) -> fake_aioredis.FakeRedis:  # type: ignore[name-defined]
        if self._client is None:  # type: ignore[attr-defined]
            self._client = fake_aioredis.FakeRedis(server=server, decode_responses=False)  # type: ignore[attr-defined]
        return self._client  # type: ignore[attr-defined,return-value]

    monkeypatch.setattr(rate_limit.TokenBucket, "_conn", _conn)
    return rate_limit.TokenBucket(capacity=3, rate=3, period_s=60)


async def test_allows_within_capacity(bucket: rate_limit.TokenBucket) -> None:
    assert await bucket.acquire("test") == 0.0
    assert await bucket.acquire("test") == 0.0
    assert await bucket.acquire("test") == 0.0
    await bucket.close()


async def test_throttles_beyond_capacity(bucket: rate_limit.TokenBucket) -> None:
    for _ in range(3):
        await bucket.acquire("test")
    wait_s = await bucket.acquire("test")
    assert wait_s > 0
    await bucket.close()


async def test_isolated_buckets(bucket: rate_limit.TokenBucket) -> None:
    for _ in range(3):
        await bucket.acquire("a")
    assert await bucket.acquire("b") == 0.0
    await bucket.close()
