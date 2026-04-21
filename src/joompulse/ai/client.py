"""Anthropic async client with prompt caching. Implementation in §2 roadmap."""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic

from joompulse.config import get_settings


@lru_cache(maxsize=1)
def get_anthropic() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key.get_secret_value())
