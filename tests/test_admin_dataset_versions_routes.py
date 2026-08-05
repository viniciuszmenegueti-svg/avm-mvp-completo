from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}
REVIEWER_HEADERS = {"X-Admin-API-Key": "avm-test-reviewer-key"}


def create_source(name: str = "Fonte Versões") -> dict:
    response = client.post(
        "/admin/data-sources",
        json={
            "name": name,
            "source_type": "CSV",
            "responsible": "Dados",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def create_dataset(name: str = "Base Versões") -> dict:
    source = create_source(f"Fonte {name}")
    response = client.post(
        "/admin/datasets",
        json={
            "data_source_id": source["data_source_id"],
            "name": name,
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def payload(dataset_id: str, checksum: str = "a" * 64) -> dict:
    return {
        "dataset_id": dataset_id,
        "file_name": "imoveis-2026-01.csv",
        "storage_path": "datasets/imoveis/2026/01.csv",
        "checksum_sha256": checksum,
        "file_size_bytes": 2048,
        "mime_type": "text/csv",
        "reference_start": "2026-01-01",
        "reference_end": "2026-01-31",
        "metadata": {"delimiter": ";"},
    }


def create_version(checksum: str = "a" * 64) -> dict:
    dataset = create_dataset()
    response = client.post(
        "/admin/dataset-versions",
        json=payload(dataset["dataset_id"], checksum),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def test_create_dataset_version() -> None:
    dataset = create_dataset()
    response = client.post(
        "/admin/dataset-versions",
        json=payload(dataset["dataset_id"]),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == 1
    assert data["status"] == "REGISTERED"
    assert data["created_by"] == "avm-test-admin"
    assert data["metadata"] == {"delimiter": ";"}


def test_version_numbers_are_sequential_per_dataset() -> None:
    dataset = create_dataset()
    numbers = []
    for checksum in ("b" * 64, "c" * 64):
        response = client.post(
            "/admin/dataset-versions",
            json=payload(dataset["dataset_id"], checksum),
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 201
        numbers.append(response.json()["version_number"])
    assert numbers == [1, 2]


def test_create_requires_existing_active_dataset() -> None:
    response = client.post(
        "/admin/dataset-versions",
        json=payload("00000000-0000-0000-0000-000000000000"),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_VERSION_DATASET_INVALID"

    dataset = create_dataset("Base Inativa")
    client.post(
        f"/admin/datasets/{dataset['dataset_id']}/deactivate",
        headers=ADMIN_HEADERS,
    )
    response = client.post(
        "/admin/dataset-versions",
        json=payload(dataset["dataset_id"], "d" * 64),
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422


def test_duplicate_checksum_is_rejected_within_dataset() -> None:
    dataset = create_dataset()
    body = payload(dataset["dataset_id"], "e" * 64)
    assert client.post(
        "/admin/dataset-versions", json=body, headers=ADMIN_HEADERS
    ).status_code == 201
    duplicate = client.post(
        "/admin/dataset-versions", json=body, headers=ADMIN_HEADERS
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DATASET_VERSION_CHECKSUM_CONFLICT"


def test_same_checksum_is_allowed_for_different_datasets() -> None:
    first = create_dataset("Base A")
    second = create_dataset("Base B")
    for dataset in (first, second):
        response = client.post(
            "/admin/dataset-versions",
            json=payload(dataset["dataset_id"], "f" * 64),
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 201


def test_get_and_unknown_version() -> None:
    created = create_version("1" * 64)
    response = client.get(
        f"/admin/dataset-versions/{created['dataset_version_id']}",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["dataset_version_id"] == created["dataset_version_id"]
    response = client.get(
        "/admin/dataset-versions/00000000-0000-0000-0000-000000000000",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


def test_list_filters_and_paginates() -> None:
    dataset = create_dataset("Base Filtros")
    first = client.post(
        "/admin/dataset-versions",
        json=payload(dataset["dataset_id"], "2" * 64),
        headers=ADMIN_HEADERS,
    ).json()
    second = client.post(
        "/admin/dataset-versions",
        json=payload(dataset["dataset_id"], "3" * 64),
        headers=REVIEWER_HEADERS,
    ).json()
    client.post(
        f"/admin/dataset-versions/{second['dataset_version_id']}/processing",
        headers=REVIEWER_HEADERS,
    )
    response = client.get(
        f"/admin/dataset-versions?dataset_id={dataset['dataset_id']}&status=PROCESSING&created_by=avm-test-reviewer&limit=1",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["dataset_version_id"] == second["dataset_version_id"]
    assert first["dataset_version_id"] != second["dataset_version_id"]


def test_invalid_list_period_returns_422() -> None:
    response = client.get(
        "/admin/dataset-versions?reference_from=2026-12-31&reference_until=2026-01-01",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_VERSION_PERIOD_INVALID"


def test_processing_and_completion_flow() -> None:
    created = create_version("4" * 64)
    version_id = created["dataset_version_id"]
    processing = client.post(
        f"/admin/dataset-versions/{version_id}/processing",
        headers=REVIEWER_HEADERS,
    )
    assert processing.status_code == 200
    assert processing.json()["status"] == "PROCESSING"
    assert processing.json()["processing_started_at"] is not None
    completed = client.post(
        f"/admin/dataset-versions/{version_id}/complete",
        json={"record_count": 250, "metadata": {"validated": True}},
        headers=REVIEWER_HEADERS,
    )
    assert completed.status_code == 200
    data = completed.json()
    assert data["status"] == "COMPLETED"
    assert data["record_count"] == 250
    assert data["metadata"] == {"validated": True}
    assert data["updated_by"] == "avm-test-reviewer"
    assert data["completed_at"] is not None


def test_processing_failure_flow() -> None:
    created = create_version("5" * 64)
    version_id = created["dataset_version_id"]
    client.post(
        f"/admin/dataset-versions/{version_id}/processing",
        headers=ADMIN_HEADERS,
    )
    failed = client.post(
        f"/admin/dataset-versions/{version_id}/fail",
        json={"error_message": "Cabeçalho inválido"},
        headers=ADMIN_HEADERS,
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "FAILED"
    assert failed.json()["error_message"] == "Cabeçalho inválido"


def test_invalid_status_transitions_return_409() -> None:
    created = create_version("6" * 64)
    version_id = created["dataset_version_id"]
    response = client.post(
        f"/admin/dataset-versions/{version_id}/complete",
        json={"record_count": 1},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409
    client.post(
        f"/admin/dataset-versions/{version_id}/processing",
        headers=ADMIN_HEADERS,
    )
    repeated = client.post(
        f"/admin/dataset-versions/{version_id}/processing",
        headers=ADMIN_HEADERS,
    )
    assert repeated.status_code == 409


def test_create_validation_rejects_invalid_checksum_and_period() -> None:
    dataset = create_dataset("Base Validação")
    invalid_checksum = payload(dataset["dataset_id"], "not-a-checksum")
    assert client.post(
        "/admin/dataset-versions",
        json=invalid_checksum,
        headers=ADMIN_HEADERS,
    ).status_code == 422
    invalid_period = payload(dataset["dataset_id"], "7" * 64)
    invalid_period["reference_start"] = "2026-12-31"
    invalid_period["reference_end"] = "2026-01-01"
    assert client.post(
        "/admin/dataset-versions",
        json=invalid_period,
        headers=ADMIN_HEADERS,
    ).status_code == 422


def test_admin_auth_is_required_and_invalid_key_rejected() -> None:
    assert client.get("/admin/dataset-versions").status_code == 401
    response = client.get(
        "/admin/dataset-versions",
        headers={"X-Admin-API-Key": "invalid"},
    )
    assert response.status_code == 403


def test_openapi_exposes_routes_and_security() -> None:
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/admin/dataset-versions"]["get"]
    assert operation["security"] == [{"AdminApiKey": []}]
    assert (
        "/admin/dataset-versions/{dataset_version_id}/complete"
        in document["paths"]
    )
