"""Thin, typed wrapper over `facebook_business`.

The SDK is synchronous; our callers invoke these helpers inside
`asyncio.to_thread(...)` or directly from Celery workers.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount as FBAdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.api import FacebookAdsApi

from joompulse.config import get_settings

AD_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "status",
    "effective_status",
    "adset_id",
    "campaign_id",
    "creative{id}",
    "updated_time",
)

CREATIVE_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "title",
    "body",
    "call_to_action_type",
    "image_url",
    "thumbnail_url",
    "video_id",
    "object_story_spec",
    "effective_object_story_id",
)

INSIGHT_FIELDS: tuple[str, ...] = (
    "impressions",
    "clicks",
    "spend",
    "ctr",
    "cpm",
    "cpp",
    "actions",
    "action_values",
)


@dataclass(slots=True)
class AdRow:
    meta_ad_id: str
    name: str | None
    status: str
    ad_set_id: str
    campaign_id: str
    creative_id: str
    updated_time: datetime | None
    raw: dict[str, Any]


@dataclass(slots=True)
class CreativeRow:
    meta_creative_id: str
    title: str | None
    body: str | None
    cta_type: str | None
    image_url: str | None
    video_id: str | None
    raw: dict[str, Any]


@dataclass(slots=True)
class InsightRow:
    impressions: int
    clicks: int
    spend: float
    ctr: float | None
    cpm: float | None
    conversions: int
    raw: dict[str, Any]


def init_api(access_token: str) -> FacebookAdsApi:
    settings = get_settings()
    return FacebookAdsApi.init(
        app_id=settings.meta_app_id.get_secret_value() or None,
        app_secret=settings.meta_app_secret.get_secret_value() or None,
        access_token=access_token,
        api_version=settings.meta_api_version,
    )


def iter_ads(
    meta_account_id: str,
    since: datetime | None = None,
    page_size: int = 100,
) -> Iterator[AdRow]:
    account = FBAdAccount(meta_account_id)
    params: dict[str, Any] = {"limit": page_size}
    if since is not None:
        params["filtering"] = [
            {
                "field": "ad.updated_time",
                "operator": "GREATER_THAN",
                "value": int(since.timestamp()),
            }
        ]
    for ad in account.get_ads(fields=list(AD_FIELDS), params=params):
        data = ad.export_all_data()
        creative = data.get("creative") or {}
        updated = data.get("updated_time")
        yield AdRow(
            meta_ad_id=str(data["id"]),
            name=data.get("name"),
            status=str(data.get("effective_status") or data.get("status") or "UNKNOWN"),
            ad_set_id=str(data.get("adset_id") or ""),
            campaign_id=str(data.get("campaign_id") or ""),
            creative_id=str(creative.get("id") or ""),
            updated_time=_parse_dt(updated),
            raw=data,
        )


def get_creative(meta_creative_id: str) -> CreativeRow:
    creative = AdCreative(meta_creative_id).api_get(fields=list(CREATIVE_FIELDS))
    data = creative.export_all_data()
    return CreativeRow(
        meta_creative_id=str(data["id"]),
        title=data.get("title"),
        body=data.get("body"),
        cta_type=data.get("call_to_action_type"),
        image_url=data.get("image_url") or data.get("thumbnail_url"),
        video_id=str(data["video_id"]) if data.get("video_id") else None,
        raw=data,
    )


def get_video_source(video_id: str) -> str | None:
    video = AdVideo(video_id).api_get(fields=["source"])
    return video.export_all_data().get("source")  # type: ignore[no-any-return]


def get_insights(meta_ad_id: str, date_preset: str = "last_7d") -> InsightRow | None:
    insights = list(
        Ad(meta_ad_id).get_insights(
            fields=list(INSIGHT_FIELDS),
            params={"date_preset": date_preset},
        )
    )
    if not insights:
        return None
    data = insights[0].export_all_data()
    return InsightRow(
        impressions=int(data.get("impressions") or 0),
        clicks=int(data.get("clicks") or 0),
        spend=float(data.get("spend") or 0),
        ctr=_to_float(data.get("ctr")),
        cpm=_to_float(data.get("cpm")),
        conversions=_sum_conversions(data.get("actions") or []),
        raw=data,
    )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_conversions(actions: Iterable[dict[str, Any]]) -> int:
    total = 0
    for a in actions:
        t = a.get("action_type", "")
        if t.startswith("offsite_conversion") or t == "purchase":
            try:
                total += int(a.get("value", 0))
            except (TypeError, ValueError):
                continue
    return total
