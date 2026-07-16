from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.orders import router as orders_router
from app.core.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

app.include_router(health_router)
app.include_router(orders_router)


@app.get(
    "/",
    tags=["Sistema"],
    summary="Informações básicas da aplicação",
)
def root() -> dict[str, str]:
    return {
        "message": "AVM Imóveis API em execução",
        "version": APP_VERSION,
        "documentation": "/docs",
        "health": "/health",
    }
