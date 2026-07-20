from contextvars import ContextVar, Token
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


def get_request_id() -> str:
    return request_id_context.get()


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

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        token: Token[str] = request_id_context.set(
            request_id
        )

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

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )
        finally:
            request_id_context.reset(token)
