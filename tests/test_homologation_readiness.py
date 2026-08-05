from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}


def test_readiness_is_fail_closed_and_never_claims_contractual_approval() -> None:
    response = client.get(
        "/admin/homologation-readiness",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SETUP_REQUIRED"
    assert body["controlled_technical_testing_ready"] is False
    assert body["formal_caixa_homologation_ready"] is False
    assert body["contractual_operation_ready"] is False
    assert "EXPLICIT_CAIXA_AUTHORIZATION" in body["external_blockers"]
    assert body["requested_by"] == "avm-test-admin"
