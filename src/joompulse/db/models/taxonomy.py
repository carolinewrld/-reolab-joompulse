from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from joompulse.db.base import Base
from joompulse.db.models.mixins import TimestampsMixin, UUIDPkMixin


class TaxonomyTerm(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "taxonomy_term"

    dimension: Mapped[str] = mapped_column(String(32), nullable=False)  # pain|concept|object|cta
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    label_en: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("dimension", "code", name="uq_taxonomy_dimension_code"),
    )


class CreativeAnalysis(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "creative_analysis"

    creative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pain_codes: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)
    concept_codes: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)
    object_codes: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)
    cta_codes: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, nullable=False)
    other_suggestions: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)), default=list, nullable=False
    )
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
