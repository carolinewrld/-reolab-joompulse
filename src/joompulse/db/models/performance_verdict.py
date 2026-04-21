from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from joompulse.db.base import Base
from joompulse.db.models.enums import Verdict
from joompulse.db.models.mixins import TimestampsMixin, UUIDPkMixin


class PerformanceVerdict(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "performance_verdict"

    creative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict: Mapped[Verdict] = mapped_column(Enum(Verdict, name="verdict"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    rationale_md: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
