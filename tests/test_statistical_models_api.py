from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def fit_payload() -> dict[str, object]:
    observations = [[float(index), float(index % 2)] for index in range(1, 25)]
    values = [
        100_000.0 + 5_000.0 * row[0] + 10_000.0 * row[1] + (index % 3) * 500
        for index, row in enumerate(observations)
    ]
    return {
        "feature_names": ["area_index", "parking"],
        "observations": observations,
        "values": values,
        "target": [12.5, 1.0],
        "expected_signs": {"area_index": 1, "parking": 1},
        "confidence_level": 0.8,
    }


def test_requires_admin_authentication() -> None:
    response = client.post("/statistical-models/fit", json=fit_payload())
    assert response.status_code == 401


def test_returns_diagnostics_but_never_claims_homologation() -> None:
    response = client.post(
        "/statistical-models/fit",
        json=fit_payload(),
        headers={"X-Admin-API-Key": "avm-test-admin-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grades"]["sample"] == "III"
    assert body["press"] > 0
    assert body["homologated"] is False
    assert "Responsável Técnico" in body["review_notice"]
