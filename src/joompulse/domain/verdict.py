"""Verdict classification business logic. Implementation in §3 roadmap."""

from __future__ import annotations

from joompulse.db.models.enums import Verdict


def classify(score: float) -> Verdict:
    raise NotImplementedError
