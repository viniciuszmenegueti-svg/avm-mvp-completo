from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.types import ExceptionHandler

from app.api.routes.admin_data_sources import router as admin_data_sources_router
from app.api.routes.admin_datasets import router as admin_datasets_router
from app.api.routes.admin_dataset_versions import router as admin_dataset_versions_router
from app.api.routes.admin_diagnostics import router as admin_diagnostics_router
from app.api.routes.admin_shadow_valuations import (
    router as admin_shadow_valuations_router,
)
from app.api.routes.cities import router as cities_router
from app.api.routes.cockpit import STATIC_DIRECTORY
from app.api.routes.cockpit import router as cockpit_router
from app.api.routes.health import router as health_router
from app.api.routes.geocoding import router as geocoding_router
from app.api.routes.model_versions import (
    router as model_versions_router,
)
from app.api.routes.order_refusals import (
    router as order_refusals_router,
)
from app.api.routes.order_status_history import (
    router as order_status_history_router,
)
from app.api.routes.orders import router as orders_router
from app.api.routes.property_assets import (
    router as property_assets_router,
)
from app.api.routes.statistical_models import router as statistical_models_router
from app.api.routes.valuations import router as valuations_router
from app.core.config import (
    APP_DEBUG,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)
from app.core.exception_handlers import (
    unexpected_error_handler,
    validation_error_handler,
)
from app.core.http_logging import HttpLoggingMiddleware
from app.core.lifespan import application_lifespan
from app.core.logging_config import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware


configure_logging()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    debug=APP_DEBUG,
    lifespan=application_lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HttpLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.add_exception_handler(
    RequestValidationError,
    cast(ExceptionHandler, validation_error_handler),
)
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
        "message": f"{APP_NAME} em execução",
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "documentation": "/docs",
        "cockpit": "/cockpit",
    }


app.include_router(health_router)
app.include_router(admin_diagnostics_router)
app.include_router(admin_data_sources_router)
app.include_router(admin_datasets_router)
app.include_router(admin_dataset_versions_router)
app.include_router(admin_shadow_valuations_router)
app.include_router(geocoding_router)
app.include_router(orders_router)
app.include_router(property_assets_router)
app.include_router(valuations_router)
app.include_router(order_refusals_router)
app.include_router(order_status_history_router)
app.include_router(cities_router)
app.include_router(model_versions_router)
app.include_router(statistical_models_router)
app.include_router(cockpit_router)
app.mount(
    "/cockpit-assets",
    StaticFiles(directory=STATIC_DIRECTORY),
    name="cockpit-assets",
)
