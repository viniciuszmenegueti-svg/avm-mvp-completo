from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import orders as orders_route
from app.main import app
from app.services import valuation_service


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}
REVIEWER_HEADERS = {"X-Admin-API-Key": "avm-test-reviewer-key"}


def training_payload(
    *,
    model_version: str = "2026.07-HOMOLOG-1",
    city_ibge_code: str = "3550308",
    expected_area_sign: int = 1,
) -> dict[str, object]:
    observations: list[list[float]] = []
    values: list[float] = []
    for index in range(36):
        area = 48.0 + index * 2.0
        bedrooms = float(1 + (index % 4))
        observations.append([area, bedrooms])
        noise = float((index % 5) - 2) * 350.0
        values.append(75_000.0 + 7_500.0 * area + 18_000.0 * bedrooms + noise)
    return {
        "city_ibge_code": city_ibge_code,
        "property_type": "APARTMENT",
        "dataset_version": "HOMOLOG-SYNTHETIC-SP-APT-2026-07",
        "source_reference": "MASSA-CONTROLADA-NAO-CONTRATUAL-001",
        "reference_date": "2026-07-31",
        "model_version": model_version,
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "dataset_metadata": {
            "classification": "SYNTHETIC_HOMOLOGATION_ONLY",
        },
        "dependent_variable": "usable_market_value_brl",
        "dependent_variable_unit": "BRL",
        "dependent_variable_transformation": "NONE",
        "feature_transformations": {},
        "feature_names": ["private_area_m2", "bedrooms"],
        "observations": observations,
        "values": values,
        "target": [85.0, 2.0],
        "expected_signs": {
            "private_area_m2": expected_area_sign,
            "bedrooms": 1,
        },
        "confidence_level": 0.8,
    }


def order_payload(external_order_id: str) -> dict[str, object]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Praça da Sé",
            "number": "100",
            "complement": "Apartamento 10",
            "private_area_m2": 85.0,
            "built_area_m2": 95.0,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 1,
            "parking_spaces": 1,
        },
        "location_confirmation": {
            "is_confirmed": True,
            "confirmation_method": "DOCUMENT_VALIDATION",
            "evidence_reference": "DOCUMENT-HOMOLOGATION-TEST",
            "verified_by": "HOMOLOGATION-TEST",
            "latitude": -23.55052,
            "longitude": -46.633308,
            "accuracy_meters": 20.0,
        },
    }


def register_and_approve_model() -> dict:
    trained = client.post(
        "/statistical-models/train",
        json=training_payload(),
        headers=REVIEWER_HEADERS,
    )
    assert trained.status_code == 201, trained.text
    candidate = trained.json()
    approved = client.post(
        f"/statistical-models/{candidate['model_id']}/approve-homologation",
        json={"approval_reference": "HOMOLOGACAO-TECNICA-SEM-VALIDADE-001"},
        headers=ADMIN_HEADERS,
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_trains_versions_approves_and_uses_shadow_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved = register_and_approve_model()

    assert approved["status"] == "HOMOLOGATION_APPROVED"
    assert approved["dataset_status"] == "HOMOLOGATION_APPROVED"
    assert approved["contractual_validity"] is False
    assert len(approved["artifact_sha256"]) == 64
    assert approved["diagnostics"]["grades"]["overall"] is None
    assert approved["diagnostics"]["grades"]["automatic_fundamentation_gate"] in {
        "I",
        "II",
        "III",
    }

    listing = client.get("/statistical-models", headers=ADMIN_HEADERS)
    detail = client.get(
        f"/statistical-models/{approved['model_id']}", headers=ADMIN_HEADERS
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert detail.json()["artifact_sha256"] == approved["artifact_sha256"]

    monkeypatch.setattr(
        valuation_service, "MODEL_EXECUTION_MODE", "HOMOLOGATION_SHADOW"
    )
    created = client.post(
        "/orders",
        json=order_payload(f"SHADOW-{uuid4().hex}"),
    )
    assert created.status_code == 201
    order_id = created.json()["internal_order_id"]
    validated = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "VALIDATING_INPUT"},
    )
    assert validated.status_code == 200

    valuation = client.post(f"/orders/{order_id}/valuation")
    assert valuation.status_code == 201, valuation.text
    result = valuation.json()
    assert result["method"] == "LINEAR_REGRESSION_OLS"
    assert result["execution_mode"] == "HOMOLOGATION_SHADOW"
    assert result["statistical_model_id"] == approved["model_id"]
    assert result["model_artifact_sha256"] == approved["artifact_sha256"]
    assert result["dataset_sha256"] == approved["dataset_sha256"]
    assert result["contractual_validity"] is False
    assert float(result["estimated_value"]) > 0

    csv_report = client.get(f"/orders/{order_id}/valuation/report.csv")
    pdf_report = client.get(f"/orders/{order_id}/valuation/report.pdf")
    assert csv_report.headers["x-avm-execution-mode"] == "HOMOLOGATION_SHADOW"
    assert csv_report.headers["x-contractual-validity"] == "false"
    assert "HOMOLOGACAO-valuation" in csv_report.headers["content-disposition"]
    assert (
        "resultado.Modo de execução,HOMOLOGATION_SHADOW"
        in csv_report.content.decode("utf-8-sig")
    )
    assert pdf_report.content.startswith(b"%PDF-")
    assert pdf_report.headers["x-contractual-validity"] == "false"

    monkeypatch.setattr(orders_route, "MODEL_EXECUTION_MODE", "HOMOLOGATION_SHADOW")
    delivery = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "DELIVERING"},
    )
    assert delivery.status_code == 409
    assert delivery.json()["detail"]["code"] == "SHADOW_DELIVERY_BLOCKED"


def test_blocks_approval_when_economic_gate_fails() -> None:
    trained = client.post(
        "/statistical-models/train",
        json=training_payload(expected_area_sign=-1),
        headers=REVIEWER_HEADERS,
    )
    assert trained.status_code == 201
    approval = client.post(
        f"/statistical-models/{trained.json()['model_id']}/approve-homologation",
        json={"approval_reference": "GATE-ECONOMICO-REPROVADO"},
        headers=ADMIN_HEADERS,
    )
    assert approval.status_code == 409
    assert approval.json()["detail"]["code"] == "HOMOLOGATION_APPROVAL_BLOCKED"


def test_rejects_duplicate_version_and_unknown_city() -> None:
    first = client.post(
        "/statistical-models/train",
        json=training_payload(),
        headers=ADMIN_HEADERS,
    )
    duplicate = client.post(
        "/statistical-models/train",
        json=training_payload(),
        headers=ADMIN_HEADERS,
    )
    unknown_city = client.post(
        "/statistical-models/train",
        json=training_payload(model_version="2", city_ibge_code="9999999"),
        headers=ADMIN_HEADERS,
    )
    missing = client.get(
        "/statistical-models/00000000-0000-0000-0000-000000000000",
        headers=ADMIN_HEADERS,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 422
    assert unknown_city.status_code == 422
    assert unknown_city.json()["detail"]["code"] == "UNSUPPORTED_CITY"
    assert missing.status_code == 404


def test_shadow_refuses_when_no_approved_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        valuation_service, "MODEL_EXECUTION_MODE", "HOMOLOGATION_SHADOW"
    )
    created = client.post(
        "/orders",
        json=order_payload(f"SHADOW-NO-MODEL-{uuid4().hex}"),
    )
    order_id = created.json()["internal_order_id"]
    client.patch(f"/orders/{order_id}/status", json={"status": "VALIDATING_INPUT"})

    response = client.post(f"/orders/{order_id}/valuation")

    assert response.status_code == 409
    refusal = client.get(f"/orders/{order_id}/refusal")
    assert refusal.status_code == 200
    assert refusal.json()["reason_code"] == "TR_9_5_A"
    assert refusal.json()["evidence"]["condition"] == (
        "APPROVED_STATISTICAL_MODEL_UNAVAILABLE"
    )
