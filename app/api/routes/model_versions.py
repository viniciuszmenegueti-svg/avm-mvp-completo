from fastapi import APIRouter

from app.schemas.model_version import (
    ModelVersionListResponse,
    ModelVersionResponse,
)
from engine.registry import (
    DEFAULT_MODEL_METHOD,
    get_active_model_versions,
)


router = APIRouter(
    prefix="/models",
    tags=["Modelos AVM"],
)


@router.get(
    "",
    response_model=ModelVersionListResponse,
    summary="Lista as versões ativas dos modelos AVM",
)
def list_active_model_versions() -> ModelVersionListResponse:
    active_models = get_active_model_versions()

    items = [
        ModelVersionResponse(
            method=model.method,
            version=model.version,
            status=model.status.value,
            description=model.description,
            is_default=model.method == DEFAULT_MODEL_METHOD,
        )
        for model in active_models
    ]

    return ModelVersionListResponse(
        total=len(items),
        items=items,
    )
