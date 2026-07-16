from fastapi import APIRouter

router = APIRouter(tags=["Sistema"])


@router.get(
    "/health",
    summary="Verifica se a API está funcionando",
)
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "avm-api",
        "version": "0.1.0",
    }
