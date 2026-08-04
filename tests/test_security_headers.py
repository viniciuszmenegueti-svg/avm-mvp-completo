from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_adds_browser_security_headers_to_success_and_error_responses() -> None:
    for path in ("/health/live", "/route-that-does-not-exist"):
        response = client.get(path)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["permissions-policy"].startswith("camera=()")
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.headers["x-permitted-cross-domain-policies"] == "none"


def test_hsts_is_only_emitted_when_transport_is_https() -> None:
    plain = client.get("/health/live")
    secure_client = TestClient(app, base_url="https://testserver")
    secure = secure_client.get("/health/live")

    assert "strict-transport-security" not in plain.headers
    assert secure.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )
