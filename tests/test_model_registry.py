import pytest

from app.schemas.valuation import ValuationMethod
from engine.models.rule_based_v1 import calculate_valuation
from engine.registry import (
    DEFAULT_MODEL_METHOD,
    MODEL_VERSIONS,
    ModelStatus,
    ModelVersionNotFoundError,
    get_active_model_versions,
    get_default_model_version,
    get_model_version,
)


def test_registers_rule_based_v1() -> None:
    model = get_model_version(ValuationMethod.RULE_BASED_V1)

    assert model.method == ValuationMethod.RULE_BASED_V1
    assert model.version == "1.0.0"
    assert model.status == ModelStatus.ACTIVE
    assert model.calculator is calculate_valuation
    assert model.description


def test_uses_rule_based_v1_as_default() -> None:
    model = get_default_model_version()

    assert DEFAULT_MODEL_METHOD == ValuationMethod.RULE_BASED_V1
    assert model is MODEL_VERSIONS[ValuationMethod.RULE_BASED_V1]


def test_lists_active_model_versions() -> None:
    active_models = get_active_model_versions()

    assert len(active_models) == 1
    assert active_models[0].method == ValuationMethod.RULE_BASED_V1
    assert active_models[0].status == ModelStatus.ACTIVE


def test_rejects_unregistered_model_method() -> None:
    class UnknownMethod(str):
        pass

    unknown_method = UnknownMethod("UNKNOWN_MODEL")

    with pytest.raises(
        ModelVersionNotFoundError,
        match="Modelo AVM não registrado: UNKNOWN_MODEL",
    ) as exception_info:
        get_model_version(
            unknown_method,  # type: ignore[arg-type]
        )

    assert exception_info.value.method == unknown_method


def test_model_not_found_error_is_lookup_error() -> None:
    error = ModelVersionNotFoundError("UNKNOWN_MODEL")

    assert isinstance(error, LookupError)
    assert error.method == "UNKNOWN_MODEL"
