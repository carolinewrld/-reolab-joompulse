from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from joompulse import __version__
from joompulse.api.routers import health
from joompulse.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    get_logger(__name__).info("api.startup", version=__version__)
    yield
    get_logger(__name__).info("api.shutdown")


app = FastAPI(
    title="JoomPulse Creative Intelligence",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(health.router)
