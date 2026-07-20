from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import APP_VERSION
from app.infrastructure.dependencies import (
    DatabaseSession,
)


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
                    "A API está em execução, mas o banco "
                    "de dados não está disponível."
                ),
            },
        ) from error


def ready_response(
    session: Session,
) -> dict[str, str]:
    verify_database_connection(session)

    return {
        "status": "ok",
        "service": "avm-api",
        "version": APP_VERSION,
        "database": "ok",
    }


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
    return {
        "status": "ok",
        "service": "avm-api",
        "version": APP_VERSION,
    }


@router.get(
    "/ready",
    summary="Verifica se a aplicação está pronta",
)
def readiness_check(
    session: DatabaseSession,
) -> dict[str, str]:
    return ready_response(session)
