from collections import Counter

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.order import OrderCreate
from engine.testing.order_scenarios import (
    ANNEX_III_CITIES,
    PROPERTY_TYPES,
    SCENARIOS_PER_SEGMENT,
    build_order_test_scenarios,
    scenario_dataset_sha256,
    scenario_summary,
)


client = TestClient(app)


def test_annex_iii_catalog_is_exact_and_unambiguous() -> None:
    actual = [(city.name, city.state, city.ibge_code) for city in ANNEX_III_CITIES]

    assert actual == [
        ("Rio de Janeiro", "RJ", "3304557"),
        ("São Paulo", "SP", "3550308"),
        ("Brasília", "DF", "5300108"),
        ("Salvador", "BA", "2927408"),
        ("Belo Horizonte", "MG", "3106200"),
        ("Curitiba", "PR", "4106902"),
        ("Recife", "PE", "2611606"),
        ("Fortaleza", "CE", "2304400"),
        ("Goiânia", "GO", "5208707"),
        ("Porto Alegre", "RS", "4314902"),
    ]


def test_builds_large_balanced_non_contractual_dataset() -> None:
    scenarios = build_order_test_scenarios()
    segments = Counter(
        (scenario.city_ibge_code, scenario.property_type) for scenario in scenarios
    )

    assert len(scenarios) == 720
    assert len(segments) == 30
    assert set(segments.values()) == {SCENARIOS_PER_SEGMENT}
    assert all(scenario.synthetic for scenario in scenarios)
    assert not any(scenario.contract_eligible for scenario in scenarios)
    assert len({scenario.scenario_id for scenario in scenarios}) == len(scenarios)
    assert len(
        {scenario.payload["external_order_id"] for scenario in scenarios}
    ) == len(scenarios)


def test_scenario_contract_matches_schema_expectations() -> None:
    for scenario in build_order_test_scenarios():
        if scenario.expected_http_status == 422:
            with pytest.raises(ValidationError):
                OrderCreate.model_validate(scenario.payload)
        else:
            parsed = OrderCreate.model_validate(scenario.payload)
            assert parsed.external_order_id == scenario.payload["external_order_id"]


def test_summary_and_hash_are_deterministic() -> None:
    first = build_order_test_scenarios()
    second = build_order_test_scenarios()

    assert scenario_dataset_sha256(first) == scenario_dataset_sha256(second)
    assert scenario_summary(first) == scenario_summary(second)
    assert scenario_summary(first)["scenario_count"] == 720
    assert scenario_summary(first)["expected_http_statuses"] == {
        "201": 660,
        "422": 60,
    }


def test_nominal_order_creation_for_every_city_and_property_type() -> None:
    scenarios = build_order_test_scenarios()
    for city in ANNEX_III_CITIES:
        for property_type in PROPERTY_TYPES:
            scenario = next(
                item
                for item in scenarios
                if item.city_ibge_code == city.ibge_code
                and item.property_type == property_type
                and item.category == "NOMINAL"
            )
            response = client.post("/orders", json=scenario.payload)
            assert response.status_code == 201
            assert response.json()["status"] == "RECEIVED"


@pytest.mark.parametrize(
    ("category", "expected_status", "expected_code"),
    [
        ("LOCATION_REFUSAL", "REFUSED", "TR_9_5_D"),
        ("DATA_REFUSAL", "REFUSED", "TR_9_5_B"),
        ("CONFLICT_REFUSAL", "REFUSED", "TR_9_5_C"),
    ],
)
def test_adverse_scenarios_generate_taxative_refusals(
    category: str,
    expected_status: str,
    expected_code: str,
) -> None:
    scenario = next(
        item
        for item in build_order_test_scenarios()
        if item.city_ibge_code == "3550308"
        and item.property_type == "APARTMENT"
        and item.category == category
    )

    response = client.post("/orders", json=scenario.payload)
    assert response.status_code == 201
    order = response.json()
    assert order["status"] == expected_status

    refusal = client.get(f"/orders/{order['internal_order_id']}/refusal")
    assert refusal.status_code == 200
    assert refusal.json()["reason_code"] == expected_code
