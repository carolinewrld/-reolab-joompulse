from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from joompulse.db.base import Base
from joompulse.db.models.enums import AdStatus
from joompulse.db.models.mixins import TimestampsMixin, UUIDPkMixin


class Campaign(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "campaign"

    meta_campaign_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ad_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_account.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    objective: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[AdStatus] = mapped_column(
        Enum(AdStatus, name="ad_status"), default=AdStatus.UNKNOWN, nullable=False
    )


class AdSet(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "ad_set"

    meta_adset_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[AdStatus] = mapped_column(
        Enum(AdStatus, name="ad_status"), default=AdStatus.UNKNOWN, nullable=False
    )


class Ad(UUIDPkMixin, TimestampsMixin, Base):
    __tablename__ = "ad"

    meta_ad_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ad_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_set.id", ondelete="CASCADE"),
        nullable=False,
    )
    creative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[AdStatus] = mapped_column(
        Enum(AdStatus, name="ad_status"), default=AdStatus.UNKNOWN, nullable=False
    )
