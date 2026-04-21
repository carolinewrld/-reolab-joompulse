from __future__ import annotations

from joompulse.db.models.enums import AdStatus, AssetKind
from joompulse.meta.client import CreativeRow
from joompulse.meta.repository import (
    _map_status,
    build_fingerprint_source,
    classify_asset_kind,
    pick_asset_url,
)


def _creative(**overrides: object) -> CreativeRow:
    defaults: dict[str, object] = {
        "meta_creative_id": "c1",
        "title": "t",
        "body": "b",
        "cta_type": "SHOP_NOW",
        "image_url": None,
        "video_id": None,
        "raw": {},
    }
    defaults.update(overrides)
    return CreativeRow(**defaults)  # type: ignore[arg-type]


def test_map_status() -> None:
    assert _map_status("ACTIVE") is AdStatus.ACTIVE
    assert _map_status("paused") is AdStatus.PAUSED
    assert _map_status(None) is AdStatus.UNKNOWN
    assert _map_status("???") is AdStatus.UNKNOWN


def test_classify_asset_kind() -> None:
    assert classify_asset_kind(_creative(video_id="v1")) is AssetKind.VIDEO
    assert classify_asset_kind(_creative(image_url="http://x")) is AssetKind.IMAGE
    assert classify_asset_kind(_creative()) is AssetKind.CAROUSEL


def test_pick_asset_url_prefers_video_source() -> None:
    c = _creative(video_id="v1", image_url="http://thumb")
    assert pick_asset_url(c, video_source="http://video.mp4") == "http://video.mp4"
    assert pick_asset_url(c, video_source=None) == "http://thumb"


def test_fingerprint_source_is_stable() -> None:
    c = _creative(title="hello", body="world")
    out = build_fingerprint_source(c)
    assert out["id"] == "c1"
    assert out["title"] == "hello"
    assert set(out) == {"id", "title", "body", "cta", "image_url", "video_id"}
