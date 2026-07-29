from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.production_readiness import assert_safe_production_configuration
from app.infrastructure.database import engine


@asynccontextmanager
async def application_lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    assert_safe_production_configuration()
    yield

    engine.dispose()
