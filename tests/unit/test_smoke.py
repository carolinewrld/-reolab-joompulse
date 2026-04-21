from __future__ import annotations

from pathlib import Path

import pytest

from joompulse import __version__
from joompulse.ai.taxonomy import DIMENSIONS, load_all
from joompulse.config import Settings, get_settings
from joompulse.tasks.schedule import BEAT_SCHEDULE


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_load() -> None:
    # clear cache because conftest may have set env after first call in another test
    get_settings.cache_clear()
    s = Settings()  # type: ignore[call-arg]
    assert s.impressions_threshold == 1000
    assert s.claude_model_decompose.startswith("claude-")


def test_beat_schedule_has_three_jobs() -> None:
    assert set(BEAT_SCHEDULE) == {
        "fetch-ads-every-15-min",
        "recompute-benchmarks-hourly",
        "daily-digest-10am",
    }


@pytest.mark.parametrize("dim", DIMENSIONS)
def test_taxonomy_seed_present(dim: str) -> None:
    terms = [t for t in load_all(Path("taxonomy")) if t.dimension == dim]
    assert len(terms) >= 15, f"{dim} must have ≥15 seed terms, got {len(terms)}"
    codes = [t.code for t in terms]
    assert len(codes) == len(set(codes)), f"duplicate codes in {dim}"
