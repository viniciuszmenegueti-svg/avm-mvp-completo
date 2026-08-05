"""Generate adversarial order scenarios for all Annex III locations.

Every record produced here is synthetic and must remain outside statistical
model training and contractual valuation datasets.  The coordinates are only
stable test fixtures near each city centre; they are not geocoding evidence.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TargetCity:
    ibge_code: str
    name: str
    state: str
    latitude: float
    longitude: float
    postal_code: str


@dataclass(frozen=True, slots=True)
class OrderTestScenario:
    scenario_id: str
    city_ibge_code: str
    city: str
    state: str
    property_type: str
    category: str
    description: str
    expected_http_status: int
    expected_order_status: str | None
    expected_code: str | None
    payload: dict[str, Any]
    synthetic: bool = True
    contract_eligible: bool = False

    def as_row(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "city_ibge_code": self.city_ibge_code,
            "city": self.city,
            "state": self.state,
            "property_type": self.property_type,
            "category": self.category,
            "description": self.description,
            "expected_http_status": self.expected_http_status,
            "expected_order_status": self.expected_order_status or "",
            "expected_code": self.expected_code or "",
            "synthetic": self.synthetic,
            "contract_eligible": self.contract_eligible,
            "payload_json": json.dumps(
                self.payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        }


ANNEX_III_CITIES: tuple[TargetCity, ...] = (
    TargetCity("3304557", "Rio de Janeiro", "RJ", -22.9068, -43.1729, "20040-020"),
    TargetCity("3550308", "São Paulo", "SP", -23.5505, -46.6333, "01001-000"),
    TargetCity("5300108", "Brasília", "DF", -15.7939, -47.8828, "70040-010"),
    TargetCity("2927408", "Salvador", "BA", -12.9714, -38.5014, "40020-000"),
    TargetCity("3106200", "Belo Horizonte", "MG", -19.9167, -43.9345, "30110-002"),
    TargetCity("4106902", "Curitiba", "PR", -25.4284, -49.2733, "80020-000"),
    TargetCity("2611606", "Recife", "PE", -8.0476, -34.8770, "50030-230"),
    TargetCity("2304400", "Fortaleza", "CE", -3.7319, -38.5267, "60025-060"),
    TargetCity("5208707", "Goiânia", "GO", -16.6869, -49.2648, "74003-010"),
    TargetCity("4314902", "Porto Alegre", "RS", -30.0346, -51.2177, "90010-150"),
)

PROPERTY_TYPES = ("APARTMENT", "HOUSE", "LAND")
SCENARIOS_PER_SEGMENT = 24


def build_order_test_scenarios() -> tuple[OrderTestScenario, ...]:
    scenarios: list[OrderTestScenario] = []
    for city in ANNEX_III_CITIES:
        for property_type in PROPERTY_TYPES:
            scenarios.extend(_segment_scenarios(city, property_type))
    return tuple(scenarios)


def scenario_dataset_sha256(
    scenarios: tuple[OrderTestScenario, ...] | None = None,
) -> str:
    selected = scenarios or build_order_test_scenarios()
    canonical = [scenario.as_row() for scenario in selected]
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scenario_summary(
    scenarios: tuple[OrderTestScenario, ...] | None = None,
) -> dict[str, object]:
    selected = scenarios or build_order_test_scenarios()
    categories: dict[str, int] = {}
    outcomes: dict[str, int] = {}
    for scenario in selected:
        categories[scenario.category] = categories.get(scenario.category, 0) + 1
        key = str(scenario.expected_http_status)
        outcomes[key] = outcomes.get(key, 0) + 1
    return {
        "dataset_purpose": "SYSTEM_TEST_ONLY",
        "synthetic": True,
        "contract_eligible": False,
        "city_count": len(ANNEX_III_CITIES),
        "property_type_count": len(PROPERTY_TYPES),
        "scenario_count": len(selected),
        "scenarios_per_segment": SCENARIOS_PER_SEGMENT,
        "categories": categories,
        "expected_http_statuses": outcomes,
        "sha256": scenario_dataset_sha256(selected),
    }


def _segment_scenarios(
    city: TargetCity,
    property_type: str,
) -> list[OrderTestScenario]:
    scenarios: list[OrderTestScenario] = []
    accuracies = (
        5.0,
        10.0,
        15.0,
        20.0,
        25.0,
        30.0,
        35.0,
        40.0,
        45.0,
        49.0,
        49.99,
        50.0,
    )
    for index, accuracy in enumerate(accuracies, start=1):
        payload = _base_payload(city, property_type, index)
        payload["location_confirmation"]["accuracy_meters"] = accuracy
        scenarios.append(
            _scenario(
                city,
                property_type,
                index,
                "NOMINAL" if index <= 9 else "BOUNDARY",
                f"Entrada completa com imprecisão declarada de {accuracy:.2f} m.",
                201,
                "RECEIVED",
                None,
                payload,
            )
        )

    boundary_mutations: tuple[tuple[str, str, Any], ...] = (
        ("BOUNDARY", "Imprecisão mínima igual a zero.", ("accuracy_meters", 0.0)),
        ("BOUNDARY", "Contagens residenciais iguais a zero.", ("counts", 0)),
        ("BOUNDARY", "Contagens residenciais no limite máximo.", ("counts", 20)),
        ("UNICODE", "Texto Unicode e acentuação preservados.", ("unicode", True)),
        (
            "BOUNDARY",
            "Identificador e complemento próximos do limite.",
            ("long_text", True),
        ),
        (
            "BOUNDARY",
            "Número predial sem número, explicitamente declarado.",
            ("number", "S/N"),
        ),
    )
    for offset, (category, description, mutation) in enumerate(
        boundary_mutations,
        start=13,
    ):
        payload = _base_payload(city, property_type, offset)
        _apply_mutation(payload, mutation)
        scenarios.append(
            _scenario(
                city,
                property_type,
                offset,
                category,
                description,
                201,
                "RECEIVED",
                None,
                payload,
            )
        )

    adverse: tuple[tuple[str, str, int, str | None, str, str], ...] = (
        (
            "LOCATION_REFUSAL",
            "Imprecisão imediatamente acima do limite contratual.",
            201,
            "REFUSED",
            "TR_9_5_D",
            "accuracy_above_limit",
        ),
        (
            "LOCATION_REFUSAL",
            "Localização expressamente não confirmada.",
            201,
            "REFUSED",
            "TR_9_5_D",
            "unconfirmed_location",
        ),
        (
            "DATA_REFUSAL",
            "Cidade e UF incompatíveis com o código IBGE.",
            201,
            "REFUSED",
            "TR_9_5_B",
            "city_mismatch",
        ),
        (
            "CONFLICT_REFUSAL",
            "Conflito de interesse declarado com dossiê completo.",
            201,
            "REFUSED",
            "TR_9_5_C",
            "conflict",
        ),
        (
            "SCHEMA_ERROR",
            "Área de referência igual a zero.",
            422,
            None,
            "VALIDATION_ERROR",
            "zero_area",
        ),
        (
            "SCHEMA_ERROR",
            "Latitude fora do intervalo geográfico.",
            422,
            None,
            "VALIDATION_ERROR",
            "invalid_latitude",
        ),
    )
    for offset, item in enumerate(adverse, start=19):
        category, description, http, order_status, code, mutation = item
        payload = _base_payload(city, property_type, offset)
        _apply_adverse_mutation(payload, property_type, mutation)
        scenarios.append(
            _scenario(
                city,
                property_type,
                offset,
                category,
                description,
                http,
                order_status,
                code,
                payload,
            )
        )

    if len(scenarios) != SCENARIOS_PER_SEGMENT:
        raise AssertionError("Unexpected scenario count for segment.")
    return scenarios


def _base_payload(
    city: TargetCity,
    property_type: str,
    index: int,
) -> dict[str, Any]:
    prefix = f"TEST-{city.ibge_code}-{property_type[:3]}-{index:02d}"
    property_data: dict[str, Any] = {
        "property_type": property_type,
        "state": city.state,
        "city": city.name,
        "city_ibge_code": city.ibge_code,
        "postal_code": city.postal_code,
        "neighborhood": "Bairro Sintético de Teste",
        "street": "Logradouro Sintético AVM",
        "number": str(100 + index),
        "complement": f"Cenário {index:02d} — não contratual",
        "private_area_m2": None,
        "built_area_m2": None,
        "land_area_m2": None,
        "bedrooms": None,
        "bathrooms": None,
        "parking_spaces": None,
    }
    if property_type == "APARTMENT":
        property_data.update(
            private_area_m2=45.0 + index * 3.5,
            built_area_m2=55.0 + index * 4.0,
            bedrooms=index % 5,
            bathrooms=index % 4,
            parking_spaces=index % 3,
        )
    elif property_type == "HOUSE":
        property_data.update(
            built_area_m2=80.0 + index * 8.0,
            land_area_m2=140.0 + index * 15.0,
            bedrooms=1 + index % 6,
            bathrooms=1 + index % 5,
            parking_spaces=index % 5,
        )
    else:
        property_data.update(land_area_m2=180.0 + index * 25.0)

    return {
        "external_order_id": prefix,
        "property": property_data,
        "conflict_of_interest": {"has_conflict": False},
        "location_confirmation": {
            "is_confirmed": True,
            "confirmation_method": "SYNTHETIC_TEST_FIXTURE",
            "evidence_reference": f"EVIDENCIA-SINTETICA-{prefix}",
            "verified_by": "AUTOMATED_TEST_SUITE",
            "latitude": city.latitude + index * 0.00001,
            "longitude": city.longitude - index * 0.00001,
            "accuracy_meters": 25.0,
        },
    }


def _apply_mutation(payload: dict[str, Any], mutation: Any) -> None:
    kind, value = mutation
    property_data = payload["property"]
    location = payload["location_confirmation"]
    if kind == "accuracy_meters":
        location["accuracy_meters"] = value
    elif kind == "counts":
        if property_data["property_type"] != "LAND":
            property_data["bedrooms"] = value
            property_data["bathrooms"] = value
            property_data["parking_spaces"] = value
    elif kind == "unicode":
        property_data["neighborhood"] = "São José — Ação & Cidadania"
        property_data["complement"] = "Bloco Ç, unidade nº 10"
    elif kind == "long_text":
        property_data["complement"] = "X" * 100
    elif kind == "number":
        property_data["number"] = value


def _apply_adverse_mutation(
    payload: dict[str, Any],
    property_type: str,
    mutation: str,
) -> None:
    property_data = payload["property"]
    location = payload["location_confirmation"]
    if mutation == "accuracy_above_limit":
        location["accuracy_meters"] = 50.01
    elif mutation == "unconfirmed_location":
        payload["location_confirmation"] = {
            "is_confirmed": False,
            "confirmation_method": "DOCUMENT_VALIDATION",
            "evidence_reference": "DOCUMENTO-NAO-CONCLUSIVO",
            "failure_reason": "Endereço não confirmado pelas evidências disponíveis.",
            "verified_by": "AUTOMATED_TEST_SUITE",
        }
    elif mutation == "city_mismatch":
        property_data["city"] = "Cidade Incompatível"
        property_data["state"] = "ZZ"
    elif mutation == "conflict":
        payload["conflict_of_interest"] = {
            "has_conflict": True,
            "conflict_type": "RELATED_PARTY",
            "description": "Vínculo sintético declarado para testar a recusa.",
            "identified_by": "AUTOMATED_TEST_SUITE",
        }
    elif mutation == "zero_area":
        area_field = {
            "APARTMENT": "private_area_m2",
            "HOUSE": "built_area_m2",
            "LAND": "land_area_m2",
        }[property_type]
        property_data[area_field] = 0
    elif mutation == "invalid_latitude":
        location["latitude"] = 90.01


def _scenario(
    city: TargetCity,
    property_type: str,
    index: int,
    category: str,
    description: str,
    expected_http_status: int,
    expected_order_status: str | None,
    expected_code: str | None,
    payload: dict[str, Any],
) -> OrderTestScenario:
    return OrderTestScenario(
        scenario_id=f"SCN-{city.ibge_code}-{property_type[:3]}-{index:02d}",
        city_ibge_code=city.ibge_code,
        city=city.name,
        state=city.state,
        property_type=property_type,
        category=category,
        description=description,
        expected_http_status=expected_http_status,
        expected_order_status=expected_order_status,
        expected_code=expected_code,
        payload=deepcopy(payload),
    )
