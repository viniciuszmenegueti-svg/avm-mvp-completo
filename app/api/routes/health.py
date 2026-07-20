from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import APP_VERSION
from app.infrastructure.database import SessionLocal


router = APIRouter(tags=["Sistema"])


@router.get(
    "/health",
    summary="Verifica a saúde da API e do banco de dados",
)
def health_check() -> dict[str, str]:
    try:
        with SessionLocal() as session:
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

    return {
        "status": "ok",
        "service": "avm-api",
        "version": APP_VERSION,
        "database": "ok",
    }
