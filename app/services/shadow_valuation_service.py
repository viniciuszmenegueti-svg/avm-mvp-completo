"""Serviço de aplicação para execução isolada do modelo sombra RJ v3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.schemas.property import PropertyInput
from engine.models.log_linear_shadow import (
    ShadowModel,
    ShadowModelError,
    ShadowPrediction,
    load_shadow_model,
    predict_shadow_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT /
    "config" /
    "shadow-model-rj.json"
)


class ShadowValuationServiceError(ValueError):
    """Erro controlado na execução do serviço de avaliação sombra."""


@dataclass(frozen=True, slots=True)
class ShadowValuationResult:
    prediction: ShadowPrediction
    model: ShadowModel


def _required_number(
    value: int | float | None,
    *,
    field_name: str,
) -> float:
    if value is None:
        raise ShadowValuationServiceError(
            f"O imóvel não informou o campo obrigatório: {field_name}."
        )

    return float(value)


def calculate_shadow_valuation(
    property_data: PropertyInput,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> ShadowValuationResult:
    """Calcula a estimativa sombra sem persistir ou substituir a avaliação oficial."""

    try:
        model = load_shadow_model(
            config_path,
            project_root=PROJECT_ROOT,
        )

        prediction = predict_shadow_model(
            model,
            city_ibge_code=property_data.city_ibge_code,
            property_type=property_data.property_type.value,
            neighborhood=property_data.neighborhood,
            private_area_m2=_required_number(
                property_data.private_area_m2,
                field_name="private_area_m2",
            ),
            bedrooms=_required_number(
                property_data.bedrooms,
                field_name="bedrooms",
            ),
            bathrooms=_required_number(
                property_data.bathrooms,
                field_name="bathrooms",
            ),
            parking_spaces=_required_number(
                property_data.parking_spaces,
                field_name="parking_spaces",
            ),
        )
    except ShadowModelError as error:
        raise ShadowValuationServiceError(
            str(error)
        ) from error

    return ShadowValuationResult(
        prediction=prediction,
        model=model,
    )
