"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-21

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    ad_status = postgresql.ENUM(
        "active", "paused", "archived", "deleted", "unknown",
        name="ad_status",
        create_type=True,
    )
    asset_kind = postgresql.ENUM(
        "image", "video", "carousel", name="asset_kind", create_type=True
    )
    verdict = postgresql.ENUM(
        "best_performer", "low_performer", "neutral", name="verdict", create_type=True
    )
    ad_status.create(op.get_bind(), checkfirst=True)
    asset_kind.create(op.get_bind(), checkfirst=True)
    verdict.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ad_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_account_id", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("encrypted_access_token", sa.LargeBinary, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "campaign",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_campaign_id", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "ad_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255)),
        sa.Column("objective", sa.String(64)),
        sa.Column("status", sa.Enum(name="ad_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ad_set",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_adset_id", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaign.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255)),
        sa.Column("status", sa.Enum(name="ad_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "creative",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_creative_id", sa.String(64), unique=True, nullable=False),
        sa.Column("fingerprint_hash", sa.String(64), nullable=False, index=True),
        sa.Column("title", sa.String(512)),
        sa.Column("body", sa.Text),
        sa.Column("cta_type", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "creative_asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Enum(name="asset_kind", create_type=False), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("duration_s", sa.Numeric(10, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ad",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meta_ad_id", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "ad_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_set.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "creative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255)),
        sa.Column("status", sa.Enum(name="ad_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "metric_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("clicks", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("spend", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Numeric(8, 6)),
        sa.Column("cpm", sa.Numeric(12, 4)),
        sa.Column("cpa", sa.Numeric(12, 4)),
        sa.Column("roas", sa.Numeric(10, 4)),
        sa.Column("conversions", sa.BigInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_metric_snapshot_ad_captured", "metric_snapshot", ["ad_id", "captured_at"])

    op.create_table(
        "taxonomy_term",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("label_ru", sa.String(255), nullable=False),
        sa.Column("label_en", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dimension", "code", name="uq_taxonomy_dimension_code"),
    )

    op.create_table(
        "creative_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("pain_codes", postgresql.ARRAY(sa.String(64)), nullable=False, server_default="{}"),
        sa.Column("concept_codes", postgresql.ARRAY(sa.String(64)), nullable=False, server_default="{}"),
        sa.Column("object_codes", postgresql.ARRAY(sa.String(64)), nullable=False, server_default="{}"),
        sa.Column("cta_codes", postgresql.ARRAY(sa.String(64)), nullable=False, server_default="{}"),
        sa.Column("other_suggestions", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
        sa.Column("raw_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(1024)),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "performance_verdict",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verdict", sa.Enum(name="verdict", create_type=False), nullable=False),
        sa.Column("score", sa.Numeric(6, 3), nullable=False),
        sa.Column("rationale_md", sa.Text, nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entity_type", "entity_id", "kind", name="uq_notification_dedup"),
    )


def downgrade() -> None:
    op.drop_table("notification_log")
    op.drop_table("performance_verdict")
    op.drop_table("creative_analysis")
    op.drop_table("taxonomy_term")
    op.drop_index("ix_metric_snapshot_ad_captured", table_name="metric_snapshot")
    op.drop_table("metric_snapshot")
    op.drop_table("ad")
    op.drop_table("creative_asset")
    op.drop_table("creative")
    op.drop_table("ad_set")
    op.drop_table("campaign")
    op.drop_table("ad_account")
    op.execute("DROP TYPE IF EXISTS verdict")
    op.execute("DROP TYPE IF EXISTS asset_kind")
    op.execute("DROP TYPE IF EXISTS ad_status")
