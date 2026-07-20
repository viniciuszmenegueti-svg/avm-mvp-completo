import logging
from time import perf_counter

from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


logger = logging.getLogger("app.http")


class HttpLoggingMiddleware:
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        status_code = 500

        async def send_with_logging(
            message: Message,
        ) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_logging,
            )
        finally:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000

            method = scope.get("method", "-")
            path = scope.get("path", "-")

            logger.info(
                (
                    "method=%s path=%s "
                    "status_code=%s duration_ms=%.2f"
                ),
                method,
                path,
                status_code,
                duration_ms,
            )
