from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def payload() -> dict[str, object]:
    return {
        "policy": {
            "city_ibge_code": "3550308",
            "city": "São Paulo",
            "state": "SP",
            "property_type": "APARTMENT",
            "reference_date": "2026-07-31",
            "variable_count": 7,
        },
        "observations": [
            {
                "observation_id": "WEB-TEST-001",
                "source_portal": "PORTAL-TESTE",
                "source_url": "https://example.com/listing/001",
                "source_listing_id": "001",
                "source_stable_url": True,
                "captured_at": "2026-07-31T10:00:00-03:00",
                "source_reference_date": "2026-07-30",
                "source_reference_date_precision": "EXACT",
                "evidence_type": "OFFER",
                "property_type": "APARTMENT",
                "state": "SP",
                "city": "São Paulo",
                "city_ibge_code": "3550308",
                "neighborhood": "Centro",
                "street": "Rua sem número",
                "number": "",
                "private_area_m2": 70,
                "bedrooms": 2,
                "bathrooms": 1,
                "parking_spaces": 1,
                "asking_price_brl": 500000,
                "market_value_basis": "ASKING_PRICE_ONLY",
            }
        ],
    }


def test_dataset_assessment_requires_administrative_authentication() -> None:
    response = client.post("/statistical-models/datasets/assess", json=payload())

    assert response.status_code == 401


def test_dataset_assessment_preserves_and_explains_rejected_offer() -> None:
    response = client.post(
        "/statistical-models/datasets/assess",
        json=payload(),
        headers={"X-Admin-API-Key": "avm-test-admin-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    assert body["collection_valid_count"] == 1
    assert body["model_eligible_count"] == 0
    assert body["model_ready"] is False
    reasons = body["assessments"][0]["reason_codes"]
    assert "USABLE_MARKET_VALUE_MISSING" in reasons
    assert "ADDRESS_NUMBER_MISSING" in reasons
    assert "COORDINATES_MISSING" in reasons
