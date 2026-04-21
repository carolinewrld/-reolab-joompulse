"""Prompt file loader (templates live under ./prompts)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=None)
def load(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def system_prompt() -> str:
    return load("system")


def decompose_prompt() -> str:
    return load("decompose")


def analyze_prompt() -> str:
    return load("analyze")
