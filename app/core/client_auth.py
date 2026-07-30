import json
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import APP_ENV, CLIENT_CREDENTIALS_JSON


def _authentication_required() -> bool:
    environment = APP_ENV.strip().lower()
    return environment not in {"development", "dev", "test"} or bool(
        CLIENT_CREDENTIALS_JSON
    )


def _load_client_credentials() -> dict[str, str]:
    try:
        raw_credentials = json.loads(CLIENT_CREDENTIALS_JSON)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CLIENT_CREDENTIALS_INVALID",
                "message": "As credenciais de integração configuradas são inválidas.",
            },
        ) from exc

    if not isinstance(raw_credentials, dict) or not raw_credentials:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CLIENT_CREDENTIALS_NOT_CONFIGURED",
                "message": "Nenhuma credencial de integração foi configurada.",
            },
        )

    credentials: dict[str, str] = {}
    for actor, api_key in raw_credentials.items():
        if (
            not isinstance(actor, str)
            or not actor.strip()
            or not isinstance(api_key, str)
            or len(api_key) < 24
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "CLIENT_CREDENTIALS_INVALID",
                    "message": (
                        "Cada credencial deve ter identidade e chave "
                        "com pelo menos 24 caracteres."
                    ),
                },
            )
        credentials[actor.strip()] = api_key
    return credentials


def require_client_api_key(
    x_client_api_key: Annotated[
        str | None,
        Header(alias="X-Client-API-Key"),
    ] = None,
) -> str:
    if not _authentication_required():
        return "development-anonymous"

    credentials = _load_client_credentials()
    if x_client_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "CLIENT_API_KEY_REQUIRED",
                "message": "A chave de integração deve ser informada.",
            },
        )
    for actor, configured_key in credentials.items():
        if secrets.compare_digest(x_client_api_key, configured_key):
            return actor
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "INVALID_CLIENT_API_KEY",
            "message": "A chave de integração informada é inválida.",
        },
    )
