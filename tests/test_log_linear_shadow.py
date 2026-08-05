import json
from pathlib import Path

import pytest

from engine.models.log_linear_shadow import (
    ShadowModelError,
    load_shadow_model,
    predict_shadow_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "shadow-model-rj.json"


def test_loads_active_shadow_model() -> None:
    model = load_shadow_model(
        CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    assert model.name == "RJ_FIXED_SPLIT_V3"
    assert model.version == "3"
    assert model.city_ibge_code == "3304557"
    assert model.property_type == "APARTMENT"
    assert set(model.supported_neighborhoods) == {
        "Botafogo",
        "Copacabana",
    }
    assert len(model.artifact_sha256) == 64


def test_predicts_copacabana_apartment() -> None:
    model = load_shadow_model(
        CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    result = predict_shadow_model(
        model,
        city_ibge_code="3304557",
        property_type="APARTMENT",
        neighborhood="Copacabana",
        private_area_m2=100.0,
        bedrooms=3,
        bathrooms=2,
        parking_spaces=1,
    )

    assert result.estimated_value_brl > 0
    assert result.confidence_lower_brl > 0
    assert (
        result.confidence_lower_brl
        < result.estimated_value_brl
        < result.confidence_upper_brl
    )
    assert result.confidence_level == pytest.approx(0.80)
    assert result.confidence_amplitude_percent == pytest.approx(
        66.8382993483374
    )
    assert result.execution_mode == "SHADOW"


def test_prediction_is_deterministic() -> None:
    model = load_shadow_model(
        CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    arguments = {
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
        "neighborhood": "Botafogo",
        "private_area_m2": 120.0,
        "bedrooms": 3,
        "bathrooms": 2,
        "parking_spaces": 1,
    }

    first = predict_shadow_model(model, **arguments)
    second = predict_shadow_model(model, **arguments)

    assert first == second


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("private_area_m2", 401.0),
        ("bedrooms", 7),
        ("bathrooms", 0),
        ("parking_spaces", 5),
    ],
)
def test_blocks_extrapolation(
    field: str,
    value: float,
) -> None:
    model = load_shadow_model(
        CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    arguments = {
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
        "neighborhood": "Copacabana",
        "private_area_m2": 80.0,
        "bedrooms": 2,
        "bathrooms": 2,
        "parking_spaces": 1,
    }

    arguments[field] = value

    with pytest.raises(
        ShadowModelError,
        match="Extrapolação bloqueada",
    ):
        predict_shadow_model(model, **arguments)


def test_blocks_unsupported_neighborhood() -> None:
    model = load_shadow_model(
        CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    with pytest.raises(
        ShadowModelError,
        match="Bairro fora do domínio",
    ):
        predict_shadow_model(
            model,
            city_ibge_code="3304557",
            property_type="APARTMENT",
            neighborhood="Ipanema",
            private_area_m2=100.0,
            bedrooms=3,
            bathrooms=2,
            parking_spaces=1,
        )


def test_rejects_disabled_configuration(
    tmp_path: Path,
) -> None:
    config = json.loads(
        CONFIG_PATH.read_text(
            encoding="utf-8-sig"
        )
    )
    config["enabled"] = False

    temporary_config = (
        tmp_path /
        "shadow-model-disabled.json"
    )

    temporary_config.write_text(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ShadowModelError,
        match="desabilitado",
    ):
        load_shadow_model(
            temporary_config,
            project_root=PROJECT_ROOT,
        )
