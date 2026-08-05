from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}
REVIEWER_HEADERS = {"X-Admin-API-Key": "avm-test-reviewer-key"}


def create_source(name: str = "Fonte Dataset") -> dict[str, object]:
    response = client.post(
        "/admin/data-sources",
        json={
            "name": name,
            "source_type": "CSV",
            "responsible": "Equipe de Dados",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def payload(source_id: str, name: str = "Imóveis RJ 2026") -> dict[str, object]:
    return {
        "data_source_id": source_id,
        "name": name,
        "description": "Amostra de imóveis",
        "reference_start": "2026-01-01",
        "reference_end": "2026-06-30",
        "metadata": {"rows": 100, "format": "csv"},
    }


def create_dataset(name: str = "Imóveis RJ 2026") -> dict[str, object]:
    source = create_source(f"Fonte {name}")
    response = client.post(
        "/admin/datasets",
        json=payload(str(source["data_source_id"]), name),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def test_create_dataset() -> None:
    source = create_source()
    response = client.post(
        "/admin/datasets",
        json=payload(str(source["data_source_id"])),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["created_by"] == "avm-test-admin"
    assert data["metadata"]["rows"] == 100


def test_create_requires_existing_active_source() -> None:
    response = client.post(
        "/admin/datasets",
        json=payload("00000000-0000-0000-0000-000000000000"),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_DATA_SOURCE_INVALID"

    source = create_source("Fonte Inativa")
    client.post(
        f"/admin/data-sources/{source['data_source_id']}/deactivate",
        headers=ADMIN_HEADERS,
    )
    response = client.post(
        "/admin/datasets",
        json=payload(str(source["data_source_id"])),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


def test_duplicate_name_is_scoped_to_source() -> None:
    source = create_source("Fonte Única")
    first = client.post(
        "/admin/datasets",
        json=payload(str(source["data_source_id"]), "Base A"),
        headers=ADMIN_HEADERS,
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/admin/datasets",
        json=payload(str(source["data_source_id"]), "  base   a "),
        headers=ADMIN_HEADERS,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DATASET_NAME_CONFLICT"


def test_same_name_allowed_for_different_sources() -> None:
    first = create_source("Fonte A")
    second = create_source("Fonte B")
    for source in (first, second):
        response = client.post(
            "/admin/datasets",
            json=payload(str(source["data_source_id"]), "Base Compartilhada"),
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 201


def test_get_and_unknown_dataset() -> None:
    created = create_dataset()
    response = client.get(
        f"/admin/datasets/{created['dataset_id']}", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["dataset_id"] == created["dataset_id"]

    response = client.get(
        "/admin/datasets/00000000-0000-0000-0000-000000000000",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


def test_list_filters_and_paginates() -> None:
    source = create_source("Fonte Filtros")
    for name in ("Base Janeiro", "Base Fevereiro"):
        response = client.post(
            "/admin/datasets",
            json=payload(str(source["data_source_id"]), name),
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 201
    response = client.get(
        f"/admin/datasets?data_source_id={source['data_source_id']}&name=fevereiro&limit=1",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Base Fevereiro"


def test_invalid_list_period_returns_422() -> None:
    response = client.get(
        "/admin/datasets?reference_from=2026-07-01&reference_until=2026-01-01",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_REFERENCE_PERIOD_INVALID"


def test_update_dataset_and_track_actor() -> None:
    created = create_dataset()
    response = client.patch(
        f"/admin/datasets/{created['dataset_id']}",
        json={
            "description": "Revisado",
            "reference_end": "2026-12-31",
            "metadata": {"reviewed": True},
        },
        headers=REVIEWER_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Revisado"
    assert data["updated_by"] == "avm-test-reviewer"
    assert data["metadata"] == {"reviewed": True}


def test_update_rejects_invalid_reference_period() -> None:
    created = create_dataset()
    response = client.patch(
        f"/admin/datasets/{created['dataset_id']}",
        json={"reference_start": "2027-01-01"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_REFERENCE_PERIOD_INVALID"


def test_deactivate_activate_and_archive_dataset() -> None:
    created = create_dataset()
    dataset_id = created["dataset_id"]
    response = client.post(
        f"/admin/datasets/{dataset_id}/deactivate", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    response = client.post(
        f"/admin/datasets/{dataset_id}/activate", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    response = client.post(
        f"/admin/datasets/{dataset_id}/archive", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ARCHIVED"


def test_archived_dataset_is_immutable() -> None:
    created = create_dataset()
    dataset_id = created["dataset_id"]
    client.post(f"/admin/datasets/{dataset_id}/archive", headers=ADMIN_HEADERS)
    response = client.patch(
        f"/admin/datasets/{dataset_id}",
        json={"description": "Não permitido"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409
    response = client.post(
        f"/admin/datasets/{dataset_id}/activate", headers=ADMIN_HEADERS
    )
    assert response.status_code == 409


def test_repeated_status_transition_returns_409() -> None:
    created = create_dataset()
    response = client.post(
        f"/admin/datasets/{created['dataset_id']}/activate",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409


def test_admin_auth_is_required_and_invalid_key_rejected() -> None:
    assert client.get("/admin/datasets").status_code == 401
    response = client.get(
        "/admin/datasets", headers={"X-Admin-API-Key": "invalid"}
    )
    assert response.status_code == 403


def test_create_validation_rejects_invalid_period() -> None:
    source = create_source("Fonte Período")
    invalid = payload(str(source["data_source_id"]))
    invalid["reference_start"] = "2026-12-31"
    invalid["reference_end"] = "2026-01-01"
    response = client.post(
        "/admin/datasets", json=invalid, headers=ADMIN_HEADERS
    )
    assert response.status_code == 422


def test_openapi_exposes_dataset_routes_and_security() -> None:
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/admin/datasets"]["get"]
    assert operation["security"] == [{"AdminApiKey": []}]
    assert "/admin/datasets/{dataset_id}/archive" in document["paths"]
