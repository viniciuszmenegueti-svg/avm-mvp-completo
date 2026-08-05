from app.main import app


SHADOW_PATH = (
    "/orders/{internal_order_id}/"
    "shadow-valuation-preview"
)


def test_shadow_preview_route_is_exposed() -> None:
    openapi = app.openapi()
    paths = openapi["paths"]

    assert SHADOW_PATH in paths
    assert "get" in paths[SHADOW_PATH]


def test_shadow_preview_route_has_expected_contract() -> None:
    operation = app.openapi()["paths"][SHADOW_PATH]["get"]

    assert operation["summary"] == (
        "Executa prévia não persistida do modelo sombra"
    )

    responses = operation["responses"]

    assert "200" in responses
    assert "404" in responses
    assert "422" in responses


def test_shadow_preview_response_schema_is_registered() -> None:
    schemas = app.openapi()["components"]["schemas"]

    assert "ShadowValuationPreviewResponse" in schemas

    schema = schemas["ShadowValuationPreviewResponse"]
    properties = schema["properties"]

    assert "estimated_value_brl" in properties
    assert "confidence_lower_brl" in properties
    assert "confidence_upper_brl" in properties
    assert "artifact_sha256" in properties
    assert "contractual_validity" in properties
    assert "formal_homologation" in properties
