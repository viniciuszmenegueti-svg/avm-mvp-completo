import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_id import request_id_context


logger = logging.getLogger("app.errors")


def get_request_id_from_request(
    request: Request,
) -> str:
    return getattr(
        request.state,
        "request_id",
        request.headers.get("X-Request-ID", "-"),
    )


def serialize_validation_errors(
    error: RequestValidationError,
) -> list[dict[str, Any]]:
    serialized_errors: list[dict[str, Any]] = []

    for validation_error in error.errors():
        serialized_errors.append(
            {
                "type": validation_error.get("type"),
                "location": list(validation_error.get("loc", ())),
                "message": validation_error.get("msg"),
                "input": validation_error.get("input"),
            }
        )

    return serialized_errors


async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    request_id = get_request_id_from_request(request)

    logger.warning(
        ("validation_error method=%s path=%s error_count=%s"),
        request.method,
        request.url.path,
        len(error.errors()),
    )

    return JSONResponse(
        status_code=422,
        headers={
            "X-Request-ID": request_id,
        },
        content={
            "detail": {
                "code": "VALIDATION_ERROR",
                "message": ("Os dados enviados são inválidos."),
                "request_id": request_id,
                "errors": serialize_validation_errors(error),
            }
        },
    )


async def unexpected_error_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    request_id = get_request_id_from_request(request)

    token = request_id_context.set(request_id)

    try:
        logger.exception(
            ("unexpected_error method=%s path=%s error_type=%s"),
            request.method,
            request.url.path,
            type(error).__name__,
            exc_info=error,
        )
    finally:
        request_id_context.reset(token)

    return JSONResponse(
        status_code=500,
        headers={
            "X-Request-ID": request_id,
        },
        content={
            "detail": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": ("Ocorreu um erro interno inesperado."),
                "request_id": request_id,
            }
        },
    )
