"""S3 / MinIO async helpers for creative assets."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import aioboto3
import httpx

from joompulse.config import get_settings
from joompulse.logging import get_logger
from joompulse.storage.fingerprint import asset_key, sha256_bytes

log = get_logger(__name__)


@dataclass(slots=True)
class UploadedAsset:
    s3_key: str
    fingerprint: str
    size: int
    content_type: str | None


@asynccontextmanager
async def s3_client() -> AsyncIterator[Any]:
    settings = get_settings()
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
    ) as client:
        yield client


async def ensure_bucket() -> None:
    settings = get_settings()
    async with s3_client() as s3:
        try:
            await s3.head_bucket(Bucket=settings.s3_bucket)
        except Exception:  # noqa: BLE001
            await s3.create_bucket(Bucket=settings.s3_bucket)
            log.info("s3.bucket_created", bucket=settings.s3_bucket)


async def _object_exists(s3: Any, bucket: str, key: str) -> bool:
    try:
        await s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:  # noqa: BLE001
        return False


async def upload_from_url(url: str, *, http: httpx.AsyncClient | None = None) -> UploadedAsset:
    """Download `url` to memory, compute SHA-256, upload to S3 (idempotent by fingerprint)."""
    settings = get_settings()
    own_client = http is None
    client = http or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        body = resp.content
        content_type = resp.headers.get("content-type")
    finally:
        if own_client:
            await client.aclose()

    fingerprint = sha256_bytes(body)
    key = asset_key(fingerprint, content_type)

    async with s3_client() as s3:
        if not await _object_exists(s3, settings.s3_bucket, key):
            await s3.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType=content_type or "application/octet-stream",
            )
            log.info("s3.uploaded", key=key, size=len(body))
        else:
            log.debug("s3.exists", key=key)

    return UploadedAsset(
        s3_key=key,
        fingerprint=fingerprint,
        size=len(body),
        content_type=content_type,
    )


async def presign_get(key: str, expires_s: int = 900) -> str:
    settings = get_settings()
    async with s3_client() as s3:
        url: str = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires_s,
        )
        return url


async def get_object_bytes(key: str) -> bytes:
    settings = get_settings()
    async with s3_client() as s3:
        obj = await s3.get_object(Bucket=settings.s3_bucket, Key=key)
        return await obj["Body"].read()  # type: ignore[no-any-return]
