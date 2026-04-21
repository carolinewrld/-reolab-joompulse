"""Redis-backed token bucket for Meta Marketing API.

Meta tier-1 dev default is ~200 calls/hour per app, prod tier ~60k/hour.
We use a coarse bucket keyed by ad account — actual Meta headers
(X-Business-Use-Case-Usage) will tune this dynamically in a later iteration.
"""

from __future__ import annotations

import time

import redis.asyncio as aioredis

from joompulse.config import get_settings

# Atomic token bucket: refills `rate` tokens per `period` seconds up to
# `capacity`. Returns 1 if acquired, 0 if throttled (in which case caller
# should sleep for `retry_after` seconds).
_LUA_ACQUIRE = """
local tokens_key = KEYS[1]
local ts_key = KEYS[2]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local period = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local cost = tonumber(ARGV[5])

local tokens = tonumber(redis.call('get', tokens_key))
local last = tonumber(redis.call('get', ts_key))

if tokens == nil then
  tokens = capacity
  last = now
end

local elapsed = math.max(0, now - last)
local refill = elapsed * (rate / period)
tokens = math.min(capacity, tokens + refill)

local allowed = tokens >= cost
if allowed then
  tokens = tokens - cost
end

redis.call('set', tokens_key, tokens, 'EX', period * 2)
redis.call('set', ts_key, now, 'EX', period * 2)

local deficit = math.max(0, cost - tokens)
local retry_after = 0
if not allowed then
  retry_after = math.ceil(deficit / (rate / period))
end

return {allowed and 1 or 0, retry_after}
"""


class TokenBucket:
    def __init__(
        self,
        redis_url: str | None = None,
        capacity: int = 200,
        rate: int = 200,
        period_s: int = 3600,
    ) -> None:
        self._redis_url = redis_url or get_settings().redis_url
        self._capacity = capacity
        self._rate = rate
        self._period = period_s
        self._client: aioredis.Redis | None = None
        self._sha: str | None = None

    async def _conn(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=False)
        return self._client

    async def acquire(self, bucket: str, cost: int = 1) -> float:
        """Try to acquire `cost` tokens. Returns 0 if allowed, >0 seconds to wait."""
        r = await self._conn()
        if self._sha is None:
            self._sha = await r.script_load(_LUA_ACQUIRE)
        tokens_key = f"rl:{bucket}:tokens"
        ts_key = f"rl:{bucket}:ts"
        result = await r.evalsha(
            self._sha,
            2,
            tokens_key,
            ts_key,
            self._capacity,
            self._rate,
            self._period,
            int(time.time()),
            cost,
        )
        allowed, retry_after = int(result[0]), int(result[1])
        return 0.0 if allowed else float(retry_after)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
