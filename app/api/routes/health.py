from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    APP_ENV,
    APP_NAME,
    APP_VERSION,
)
from app.infrastructure.dependencies import DatabaseSession


router = APIRouter(
    prefix="/health",
    tags=["Sistema"],
)


def verify_database_connection(
    session: Session,
) -> None:
    try:
        session.execute(text("SELECT 1"))

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": (
                    "A API está em execução, mas o banco de dados não está disponível."
                ),
            },
        ) from error


def base_health_response() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "avm-api",
        "name": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
    }


def ready_response(
    session: Session,
) -> dict[str, str]:
    verify_database_connection(session)

    response = base_health_response()
    response["database"] = "ok"

    return response


@router.get(
    "",
    summary="Verifica a saúde da API e do banco de dados",
)
def health_check(
    session: DatabaseSession,
) -> dict[str, str]:
    return ready_response(session)


@router.get(
    "/live",
    summary="Verifica se a aplicação está em execução",
)
def liveness_check() -> dict[str, str]:
    return base_health_response()


@router.get(
    "/ready",
    summary="Verifica se a aplicação está pronta",
)
def readiness_check(
    session: DatabaseSession,
) -> dict[str, str]:
    return ready_response(session)
