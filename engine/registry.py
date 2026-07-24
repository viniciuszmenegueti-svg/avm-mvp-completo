from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.schemas.property import PropertyInput
from app.schemas.valuation import ValuationMethod
from engine.models.rule_based_v1 import (
    ValuationCalculation,
    calculate_valuation,
)


class ModelStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


class ModelVersionNotFoundError(LookupError):
    def __init__(
        self,
        method: object,
    ) -> None:
        self.method = method

        super().__init__(
            f"Modelo AVM não registrado: {method}",
        )


class ModelVersionNotActiveError(RuntimeError):
    def __init__(
        self,
        method: ValuationMethod,
        model_status: ModelStatus,
    ) -> None:
        self.method = method
        self.model_status = model_status

        super().__init__(
            (
                f"Modelo AVM não está ativo: {method.value}. "
                f"Status atual: {model_status.value}."
            )
        )


ValuationCalculator = Callable[
    [PropertyInput, Decimal],
    ValuationCalculation,
]


@dataclass(frozen=True, slots=True)
class ModelVersion:
    method: ValuationMethod
    version: str
    status: ModelStatus
    calculator: ValuationCalculator
    description: str


MODEL_VERSIONS: dict[ValuationMethod, ModelVersion] = {
    ValuationMethod.RULE_BASED_V1: ModelVersion(
        method=ValuationMethod.RULE_BASED_V1,
        version="1.0.0",
        status=ModelStatus.ACTIVE,
        calculator=calculate_valuation,
        description=(
            "Modelo determinístico baseado em preço por metro quadrado "
            "e características do imóvel."
        ),
    ),
}


DEFAULT_MODEL_METHOD = ValuationMethod.RULE_BASED_V1


def get_model_version(
    method: ValuationMethod,
) -> ModelVersion:
    try:
        return MODEL_VERSIONS[method]
    except KeyError as error:
        raise ModelVersionNotFoundError(method) from error


def get_default_model_version() -> ModelVersion:
    return get_model_version(DEFAULT_MODEL_METHOD)


def get_active_model_version(
    method: ValuationMethod,
) -> ModelVersion:
    model = get_model_version(method)

    if model.status != ModelStatus.ACTIVE:
        raise ModelVersionNotActiveError(
            method=model.method,
            model_status=model.status,
        )

    return model


def get_active_model_versions() -> list[ModelVersion]:
    return [
        model for model in MODEL_VERSIONS.values() if model.status == ModelStatus.ACTIVE
    ]
