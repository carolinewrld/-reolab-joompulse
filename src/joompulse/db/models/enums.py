from __future__ import annotations

import enum


class AdStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class AssetKind(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"


class Verdict(str, enum.Enum):
    BEST_PERFORMER = "best_performer"
    LOW_PERFORMER = "low_performer"
    NEUTRAL = "neutral"
