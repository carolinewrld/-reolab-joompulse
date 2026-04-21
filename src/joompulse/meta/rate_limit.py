"""Token bucket via Redis for Meta API rate limits. To be implemented in §1."""

from __future__ import annotations


async def acquire(bucket: str, cost: int = 1) -> None:
    raise NotImplementedError
