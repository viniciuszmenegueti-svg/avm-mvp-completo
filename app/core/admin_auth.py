import json
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import (
    ADMIN_ACTOR,
    ADMIN_API_KEY,
    ADMIN_CREDENTIALS_JSON,
)


def _load_admin_credentials() -> dict[str, str]:
    if ADMIN_CREDENTIALS_JSON:
        try:
            raw_credentials = json.loads(ADMIN_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ADMIN_CREDENTIALS_INVALID",
                    "message": (
                        "As credenciais administrativas configuradas são inválidas."
                    ),
                },
            ) from exc

        if not isinstance(raw_credentials, dict):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ADMIN_CREDENTIALS_INVALID",
                    "message": (
                        "As credenciais administrativas devem "
                        "ser configuradas como um objeto JSON."
                    ),
                },
            )

        credentials: dict[str, str] = {}

        for actor, api_key in raw_credentials.items():
            if (
                not isinstance(actor, str)
                or not actor.strip()
                or not isinstance(api_key, str)
                or not api_key
            ):
                raise HTTPException(
                    status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
                    detail={
                        "code": "ADMIN_CREDENTIALS_INVALID",
                        "message": (
                            "Cada credencial administrativa deve "
                            "possuir responsável e chave válidos."
                        ),
                    },
                )

            credentials[actor.strip()] = api_key

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ADMIN_CREDENTIALS_EMPTY",
                    "message": ("Nenhuma credencial administrativa foi configurada."),
                },
            )

        return credentials

    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ADMIN_API_KEY_NOT_CONFIGURED",
                "message": (
                    "A chave administrativa não está configurada "
                    "no ambiente da aplicação."
                ),
            },
        )

    if not ADMIN_ACTOR:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ADMIN_ACTOR_NOT_CONFIGURED",
                "message": (
                    "O responsável administrativo não está "
                    "configurado no ambiente da aplicação."
                ),
            },
        )

    return {
        ADMIN_ACTOR: ADMIN_API_KEY,
    }


def require_admin_api_key(
    x_admin_api_key: Annotated[
        str | None,
        Header(alias="X-Admin-API-Key"),
    ] = None,
) -> str:
    credentials = _load_admin_credentials()

    if x_admin_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "ADMIN_API_KEY_REQUIRED",
                "message": ("A chave administrativa deve ser informada."),
            },
        )

    for actor, configured_key in credentials.items():
        if secrets.compare_digest(
            x_admin_api_key,
            configured_key,
        ):
            return actor

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "INVALID_ADMIN_API_KEY",
            "message": ("A chave administrativa informada é inválida."),
        },
    )
