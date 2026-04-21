from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from joompulse.db.base import Base
from joompulse.db.models.mixins import UUIDPkMixin


class MetricSnapshot(UUIDPkMixin, Base):
    __tablename__ = "metric_snapshot"

    ad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad.id", ondelete="CASCADE"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    impressions: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    spend: Mapped[float] = mapped_column(Numeric(18, 4), default=0, nullable=False)
    ctr: Mapped[float | None] = mapped_column(Numeric(8, 6))
    cpm: Mapped[float | None] = mapped_column(Numeric(12, 4))
    cpa: Mapped[float | None] = mapped_column(Numeric(12, 4))
    roas: Mapped[float | None] = mapped_column(Numeric(10, 4))
    conversions: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    __table_args__ = (
        Index("ix_metric_snapshot_ad_captured", "ad_id", "captured_at"),
    )
