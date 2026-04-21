"""Controlled vocabulary loader and sync. See §6 README."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


DIMENSIONS = ("pain", "concept", "object", "cta")


@dataclass(slots=True, frozen=True)
class Term:
    dimension: str
    code: str
    label_ru: str
    label_en: str | None
    description: str | None


def load_all(root: Path) -> list[Term]:
    terms: list[Term] = []
    for dim in DIMENSIONS:
        path = root / f"{dim}.yaml"
        if not path.exists():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for item in raw:
            terms.append(
                Term(
                    dimension=dim,
                    code=item["code"],
                    label_ru=item["label_ru"],
                    label_en=item.get("label_en"),
                    description=item.get("description"),
                )
            )
    return terms
