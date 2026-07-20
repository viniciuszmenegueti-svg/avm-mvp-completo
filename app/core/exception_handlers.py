import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.request_id import request_id_context


logger = logging.getLogger("app.errors")


async def unexpected_error_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    request_id = getattr(
        request.state,
        "request_id",
        request.headers.get("X-Request-ID", "-"),
    )

    token = request_id_context.set(request_id)

    try:
        logger.exception(
            (
                "unexpected_error method=%s "
                "path=%s error_type=%s"
            ),
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
                "message": (
                    "Ocorreu um erro interno inesperado."
                ),
                "request_id": request_id,
            }
        },
    )
