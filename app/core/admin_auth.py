import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import ADMIN_ACTOR, ADMIN_API_KEY


def require_admin_api_key(
    x_admin_api_key: Annotated[
        str | None,
        Header(alias="X-Admin-API-Key"),
    ] = None,
) -> str:
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

    if x_admin_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "ADMIN_API_KEY_REQUIRED",
                "message": ("A chave administrativa deve ser informada."),
            },
        )

    if not secrets.compare_digest(
        x_admin_api_key,
        ADMIN_API_KEY,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INVALID_ADMIN_API_KEY",
                "message": ("A chave administrativa informada é inválida."),
            },
        )

    return ADMIN_ACTOR
