from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


class RequestIdMiddleware:
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

        request_headers = dict(
            scope.get("headers", [])
        )

        provided_request_id = request_headers.get(
            b"x-request-id"
        )

        if provided_request_id:
            request_id = provided_request_id.decode(
                "utf-8",
                errors="replace",
            )
        else:
            request_id = str(uuid4())

        async def send_with_request_id(
            message: Message,
        ) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(
                    scope=message
                )
                response_headers["X-Request-ID"] = (
                    request_id
                )

            await send(message)

        await self.app(
            scope,
            receive,
            send_with_request_id,
        )
