"""S3 / MinIO async client. Business logic to be filled in §1 roadmap."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import aioboto3

from joompulse.config import get_settings


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
