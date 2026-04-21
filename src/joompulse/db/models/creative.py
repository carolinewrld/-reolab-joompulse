from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from joompulse.db.base import Base
from joompulse.db.models.enums import AssetKind
from joompulse.db.models.mixins import TimestampsMixin, UUIDPkMixin


class Creative(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "creative"

    meta_creative_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    body: Mapped[str | None] = mapped_column(Text)
    cta_type: Mapped[str | None] = mapped_column(String(64))


class CreativeAsset(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "creative_asset"

    creative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[AssetKind] = mapped_column(Enum(AssetKind, name="asset_kind"), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Numeric(10, 3))
