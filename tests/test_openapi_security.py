from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_declares_api_key_security_schemes() -> None:
    document = client.get("/openapi.json").json()

    assert document["components"]["securitySchemes"] == {
        "AdminApiKey": {
            "type": "apiKey",
            "description": (
                "Chave administrativa vinculada a uma identidade autorizada."
            ),
            "in": "header",
            "name": "X-Admin-API-Key",
        },
        "ClientApiKey": {
            "type": "apiKey",
            "description": "Chave da integração cliente autorizada.",
            "in": "header",
            "name": "X-Client-API-Key",
        },
    }


def test_marks_client_and_admin_operations_as_protected() -> None:
    document = client.get("/openapi.json").json()

    assert document["paths"]["/orders"]["get"]["security"] == [{"ClientApiKey": []}]
    assert document["paths"]["/orders/{internal_order_id}/process"]["post"][
        "security"
    ] == [{"ClientApiKey": []}]
    assert document["paths"]["/geocoding/resolve"]["post"]["security"] == [
        {"ClientApiKey": []}
    ]
    assert document["paths"]["/admin/diagnostics"]["get"]["security"] == [
        {"AdminApiKey": []}
    ]


def test_does_not_expose_api_keys_as_optional_header_parameters() -> None:
    document = client.get("/openapi.json").json()

    order_parameters = document["paths"]["/orders"]["get"].get("parameters", [])
    diagnostic_parameters = document["paths"]["/admin/diagnostics"]["get"].get(
        "parameters",
        [],
    )

    assert all(
        parameter["name"] != "X-Client-API-Key" for parameter in order_parameters
    )
    assert all(
        parameter["name"] != "X-Admin-API-Key" for parameter in diagnostic_parameters
    )


def test_documents_idempotent_automatic_order_processing() -> None:
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/orders/{internal_order_id}/process"]["post"]

    assert "idempotente" in operation["summary"].lower()
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/OrderProcessResponse"
    }
    assert {"200", "404", "409", "422", "503"}.issubset(operation["responses"])
