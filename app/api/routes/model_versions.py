from fastapi import APIRouter, HTTPException, status

from app.schemas.model_version import (
    ModelVersionListResponse,
    ModelVersionResponse,
)
from app.schemas.valuation import ValuationMethod
from engine.registry import (
    DEFAULT_MODEL_METHOD,
    ModelVersion,
    get_active_model_versions,
    get_model_version,
)


router = APIRouter(
    prefix="/models",
    tags=["Modelos AVM"],
)


def model_version_to_response(
    model: ModelVersion,
) -> ModelVersionResponse:
    return ModelVersionResponse(
        method=model.method,
        version=model.version,
        status=model.status.value,
        description=model.description,
        is_default=model.method == DEFAULT_MODEL_METHOD,
    )


@router.get(
    "",
    response_model=ModelVersionListResponse,
    summary="Lista as versões ativas dos modelos AVM",
)
def list_active_model_versions() -> ModelVersionListResponse:
    active_models = get_active_model_versions()

    items = [model_version_to_response(model) for model in active_models]

    return ModelVersionListResponse(
        total=len(items),
        items=items,
    )


@router.get(
    "/{method}",
    response_model=ModelVersionResponse,
    summary="Consulta uma versão de modelo AVM",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Modelo AVM não encontrado",
        },
    },
)
def get_registered_model_version(
    method: str,
) -> ModelVersionResponse:
    try:
        valuation_method = ValuationMethod(method)
        model = get_model_version(valuation_method)
    except (ValueError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo AVM não encontrado.",
        ) from error

    return model_version_to_response(model)
