from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    encryption_key: SecretStr = SecretStr("")

    # Postgres
    postgres_dsn: str
    postgres_dsn_sync: str

    # Redis
    redis_url: str

    # S3 / MinIO
    s3_endpoint: str
    s3_region: str = "us-east-1"
    s3_bucket: str
    s3_access_key: SecretStr
    s3_secret_key: SecretStr

    # Meta
    meta_app_id: SecretStr = SecretStr("")
    meta_app_secret: SecretStr = SecretStr("")
    meta_access_token: SecretStr = SecretStr("")
    meta_ad_account_ids: list[str] = Field(default_factory=list)
    meta_api_version: str = "v21.0"

    # Anthropic
    anthropic_api_key: SecretStr = SecretStr("")
    claude_model_decompose: str = "claude-opus-4-7"
    claude_model_analyze: str = "claude-sonnet-4-6"
    claude_model_fast: str = "claude-haiku-4-5"

    # Telegram
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_alert_chat_id: str | None = None
    telegram_digest_chat_id: str | None = None

    # Thresholds
    impressions_threshold: int = 1000
    reanalyze_cooldown_h: int = 48
    benchmark_window_days: int = 30
    video_sample_fps: int = 1
    video_frames_per_request: int = 15

    # Observability
    sentry_dsn: str | None = None

    @classmethod
    def parse_csv(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, list):
            return v
        return [s.strip() for s in v.split(",") if s.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
