from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.database import engine


@asynccontextmanager
async def application_lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    yield

    engine.dispose()
