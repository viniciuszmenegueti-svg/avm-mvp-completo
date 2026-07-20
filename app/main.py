from fastapi import FastAPI

from app.api.routes.cities import router as cities_router
from app.api.routes.health import router as health_router
from app.api.routes.order_status_history import (
    router as order_status_history_router,
)
from app.api.routes.orders import router as orders_router
from app.core.exception_handlers import unexpected_error_handler
from app.core.http_logging import HttpLoggingMiddleware
from app.core.logging_config import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)


configure_logging()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

app.add_middleware(HttpLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.add_exception_handler(
    Exception,
    unexpected_error_handler,
)


@app.get(
    "/",
    tags=["Sistema"],
    summary="Informações básicas da API",
)
def root() -> dict[str, str]:
    return {
        "message": "AVM Imóveis API em execução",
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "documentation": "/docs",
    }


app.include_router(health_router)
app.include_router(orders_router)
app.include_router(order_status_history_router)
app.include_router(cities_router)




