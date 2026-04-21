"""Thin wrapper over facebook_business SDK. Implementation arrives in §1 roadmap."""

from __future__ import annotations

from facebook_business.api import FacebookAdsApi

from joompulse.config import get_settings


def init_api(access_token: str | None = None) -> FacebookAdsApi:
    settings = get_settings()
    token = access_token or settings.meta_access_token.get_secret_value()
    return FacebookAdsApi.init(
        app_id=settings.meta_app_id.get_secret_value() or None,
        app_secret=settings.meta_app_secret.get_secret_value() or None,
        access_token=token,
        api_version=settings.meta_api_version,
    )
