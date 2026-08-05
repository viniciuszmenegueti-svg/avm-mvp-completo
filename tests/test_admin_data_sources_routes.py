from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}
REVIEWER_HEADERS = {"X-Admin-API-Key": "avm-test-reviewer-key"}


def payload(name: str = "Viva Real RJ") -> dict[str, object]:
    return {
        "name": name,
        "source_type": "PORTAL_IMOBILIARIO",
        "responsible": "Equipe de Dados",
        "description": "Anúncios de apartamentos no Rio de Janeiro",
        "reference_date": "2026-08-01",
        "metadata": {"city_ibge_code": "3304557", "licensed": True},
    }


def create_source(name: str = "Viva Real RJ") -> dict[str, object]:
    response = client.post("/admin/data-sources", json=payload(name), headers=ADMIN_HEADERS)
    assert response.status_code == 201
    return response.json()


def test_create_data_source() -> None:
    data = create_source()
    assert data["name"] == "Viva Real RJ"
    assert data["source_type"] == "PORTAL_IMOBILIARIO"
    assert data["status"] == "ACTIVE"
    assert data["created_by"] == "avm-test-admin"
    assert data["metadata"]["licensed"] is True


def test_create_rejects_duplicate_name_case_insensitively() -> None:
    create_source("Viva Real RJ")
    response = client.post(
        "/admin/data-sources",
        json=payload("  viva   real rj "),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DATA_SOURCE_NAME_CONFLICT"


def test_get_data_source() -> None:
    created = create_source()
    response = client.get(
        f"/admin/data-sources/{created['data_source_id']}", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["data_source_id"] == created["data_source_id"]


def test_get_unknown_data_source_returns_404() -> None:
    response = client.get(
        "/admin/data-sources/00000000-0000-0000-0000-000000000000",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DATA_SOURCE_NOT_FOUND"


def test_list_and_filter_data_sources() -> None:
    create_source("Viva Real RJ")
    second = payload("CNEFE RJ")
    second["source_type"] = "CADASTRO_PUBLICO"
    second["responsible"] = "Geocodificação"
    response = client.post("/admin/data-sources", json=second, headers=ADMIN_HEADERS)
    assert response.status_code == 201

    response = client.get(
        "/admin/data-sources?source_type=cadastro_publico&name=cnefe",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "CNEFE RJ"


def test_list_paginates_data_sources() -> None:
    create_source("Fonte A")
    create_source("Fonte B")
    response = client.get(
        "/admin/data-sources?limit=1&offset=1", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


def test_update_data_source_and_tracks_actor() -> None:
    created = create_source()
    response = client.patch(
        f"/admin/data-sources/{created['data_source_id']}",
        json={
            "responsible": "Revisão Técnica",
            "description": "Descrição atualizada",
            "metadata": {"reviewed": True},
        },
        headers=REVIEWER_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["responsible"] == "Revisão Técnica"
    assert data["metadata"] == {"reviewed": True}
    assert data["updated_by"] == "avm-test-reviewer"


def test_update_rejects_name_used_by_another_source() -> None:
    first = create_source("Fonte A")
    create_source("Fonte B")
    response = client.patch(
        f"/admin/data-sources/{first['data_source_id']}",
        json={"name": "fonte b"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409


def test_deactivate_and_activate_data_source() -> None:
    created = create_source()
    source_id = created["data_source_id"]
    response = client.post(
        f"/admin/data-sources/{source_id}/deactivate", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    filtered = client.get(
        "/admin/data-sources?status=INACTIVE", headers=ADMIN_HEADERS
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    response = client.post(
        f"/admin/data-sources/{source_id}/activate", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_repeated_status_transition_returns_409() -> None:
    created = create_source()
    response = client.post(
        f"/admin/data-sources/{created['data_source_id']}/activate",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DATA_SOURCE_STATUS_CONFLICT"


def test_admin_auth_is_required() -> None:
    response = client.get("/admin/data-sources")
    assert response.status_code == 401


def test_invalid_admin_key_is_rejected() -> None:
    response = client.get(
        "/admin/data-sources", headers={"X-Admin-API-Key": "invalid"}
    )
    assert response.status_code == 403


def test_create_validation_rejects_blank_name() -> None:
    invalid = payload()
    invalid["name"] = "  "
    response = client.post(
        "/admin/data-sources", json=invalid, headers=ADMIN_HEADERS
    )
    assert response.status_code == 422


def test_openapi_exposes_data_source_routes_and_security() -> None:
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/admin/data-sources"]["get"]
    assert operation["security"] == [{"AdminApiKey": []}]
    assert "/admin/data-sources/{data_source_id}/deactivate" in document["paths"]
