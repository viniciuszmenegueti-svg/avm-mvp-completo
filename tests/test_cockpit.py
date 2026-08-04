from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_serves_self_contained_accessible_cockpit() -> None:
    response = client.get("/cockpit")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Cockpit AVM" in response.text
    assert "Geolocalização auditável" in response.text
    assert "Localizar pelo endereço" in response.text
    assert 'id="accuracy"' in response.text
    assert (
        'id="accuracy" type="number" required min="0" max="50" step="0.01" value="50"'
        not in response.text
    )
    assert "X-Client-API-Key" in response.text
    assert "https://" not in response.text
    assert '<script src="/cockpit-assets/cockpit.js"' in response.text
    assert "<label" in response.text


def test_cockpit_has_restrictive_browser_policy() -> None:
    response = client.get("/cockpit")

    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy
    assert "object-src 'none'" in policy
    permissions = response.headers["permissions-policy"]
    for blocked_capability in ("camera=()", "microphone=()", "geolocation=()"):
        assert blocked_capability in permissions
    assert response.headers["cache-control"] == "no-store"


def test_serves_local_cockpit_assets_without_embedded_secret() -> None:
    stylesheet = client.get("/cockpit-assets/cockpit.css")
    script = client.get("/cockpit-assets/cockpit.js")

    assert stylesheet.status_code == 200
    assert script.status_code == 200
    assert "sessionStorage" not in script.text
    assert "localStorage" not in script.text
    assert "change_this" not in script.text
    assert "replace_with" not in script.text
    assert "https://" not in script.text
    assert "/geocoding/resolve" in script.text
    assert "geocoding_audit_id" in script.text
    assert 'byId("latitude").value = ""' in script.text
    assert 'byId("longitude").value = ""' in script.text
    assert 'byId("accuracy").value = ""' in script.text
    assert "requires_accuracy_confirmation" not in script.text
    assert 'response.headers.get("Content-Disposition")' in script.text
    assert "anchor.download = reportFilename(response" in script.text
    assert 'actionButton("Processar", processOrder' in script.text
    assert "`/orders/${id}/process`" in script.text


def test_cockpit_is_not_added_to_openapi_contract() -> None:
    document = client.get("/openapi.json").json()

    assert "/cockpit" not in document["paths"]
    assert "/cockpit-assets/cockpit.js" not in document["paths"]
