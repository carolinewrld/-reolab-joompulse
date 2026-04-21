"""Controlled vocabulary loader and sync. See §6 README."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from joompulse.db.models import TaxonomyTerm

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


async def load_from_db(session: AsyncSession) -> list[Term]:
    rows = await session.execute(
        select(TaxonomyTerm).where(TaxonomyTerm.is_active.is_(True))
    )
    return [
        Term(
            dimension=r.dimension,
            code=r.code,
            label_ru=r.label_ru,
            label_en=r.label_en,
            description=r.description,
        )
        for r in rows.scalars().all()
    ]


def format_for_prompt(terms: Iterable[Term]) -> str:
    """Stable, cache-friendly block — one section per dimension, sorted by code."""
    by_dim: dict[str, list[Term]] = defaultdict(list)
    for t in terms:
        by_dim[t.dimension].append(t)
    for v in by_dim.values():
        v.sort(key=lambda t: t.code)

    lines: list[str] = []
    for dim in DIMENSIONS:
        lines.append(f"## {dim}")
        for t in by_dim.get(dim, []):
            desc = f" — {t.description}" if t.description else ""
            lines.append(f"- `{t.code}`: {t.label_ru}{desc}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_vocab(terms: Iterable[Term]) -> dict[str, set[str]]:
    vocab: dict[str, set[str]] = {d: set() for d in DIMENSIONS}
    for t in terms:
        vocab[t.dimension].add(t.code)
    return vocab
