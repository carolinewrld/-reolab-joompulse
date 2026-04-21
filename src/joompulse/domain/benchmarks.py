"""Per-account rolling benchmarks (30-day window). Implementation in §3 roadmap."""

from __future__ import annotations


async def compute_percentiles(ad_account_id: str) -> dict[str, dict[str, float]]:
    raise NotImplementedError
