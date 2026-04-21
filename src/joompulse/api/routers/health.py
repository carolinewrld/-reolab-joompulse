from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from joompulse import __version__
from joompulse.config import get_settings
from joompulse.db.base import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready() -> dict[str, str]:
    settings = get_settings()

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"postgres_unavailable: {exc}",
        ) from exc

    try:
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"redis_unavailable: {exc}",
        ) from exc

    return {"status": "ready"}
