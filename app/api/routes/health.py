from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
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
    MODEL_EXECUTION_MODE,
)
from app.infrastructure.dependencies import DatabaseSession


router = APIRouter(
    prefix="/health",
    tags=["Sistema"],
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SECURE_ENVIRONMENTS = frozenset({"homologation", "staging", "production", "prod"})


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
        "execution_mode": MODEL_EXECUTION_MODE,
    }


def ready_response(
    session: Session,
) -> dict[str, str]:
    verify_database_connection(session)

    response = base_health_response()
    response["database"] = "ok"
    response["database_revision"] = verify_database_revision(session)

    return response


def verify_database_revision(session: Session) -> str:
    if APP_ENV.strip().lower() not in SECURE_ENVIRONMENTS:
        return "not_enforced_in_local_or_test"
    configuration = Config(str(PROJECT_ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    expected_heads = set(ScriptDirectory.from_config(configuration).get_heads())
    current_heads = set(
        MigrationContext.configure(session.connection()).get_current_heads()
    )
    if not current_heads or current_heads != expected_heads:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DATABASE_MIGRATION_NOT_CURRENT",
                "message": "O banco não está no único head Alembic esperado.",
                "expected_heads": sorted(expected_heads),
                "current_heads": sorted(current_heads),
            },
        )
    return next(iter(current_heads))


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
