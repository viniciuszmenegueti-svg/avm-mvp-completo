import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}


def completed_version(monkeypatch, tmp_path: Path, content: bytes) -> dict:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    suffix = hashlib.sha1(content).hexdigest()
    source_response = client.post(
        "/admin/data-sources",
        json={
            "name": f"Fonte staging {suffix}",
            "source_type": "CSV",
            "responsible": "Dados",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert source_response.status_code == 201
    dataset_response = client.post(
        "/admin/datasets",
        json={
            "data_source_id": source_response.json()["data_source_id"],
            "name": "Dataset staging",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert dataset_response.status_code == 201
    version_response = client.post(
        "/admin/dataset-versions",
        json={
            "dataset_id": dataset_response.json()["dataset_id"],
            "file_name": "dados.csv",
            "storage_path": "pending/dados.csv",
            "checksum_sha256": hashlib.sha256(content).hexdigest(),
            "file_size_bytes": len(content),
            "mime_type": "text/csv",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert version_response.status_code == 201
    version = version_response.json()
    uploaded = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/file",
        files={"file": ("dados.csv", content, "text/csv")},
        headers=ADMIN_HEADERS,
    )
    assert uploaded.status_code == 201
    processed = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/process-file",
        headers=ADMIN_HEADERS,
    )
    assert processed.status_code == 200
    return version


def test_stage_csv_valid_invalid_and_duplicate(monkeypatch, tmp_path: Path) -> None:
    content = (
        "id;nome;valor;data;ativo\n"
        "1;  Maria   Silva ;10,50;2026-08-01;sim\n"
        "2;;abc;2026-13-01;talvez\n"
        "1;Maria Silva;10,50;2026-08-01;sim\n"
    ).encode()
    version = completed_version(monkeypatch, tmp_path, content)
    response = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/stage-import",
        json={
            "required_fields": ["id", "nome"],
            "field_types": {
                "id": "INTEGER",
                "valor": "DECIMAL",
                "data": "DATE",
                "ativo": "BOOLEAN",
            },
            "batch_size": 1,
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 1
    assert data["invalid_rows"] == 1
    assert data["duplicate_rows"] == 1


def test_summary_and_rejected_rows(monkeypatch, tmp_path: Path) -> None:
    content = b"id;nome\n1;Ana\n2;\n1;Ana\n"
    version = completed_version(monkeypatch, tmp_path, content)
    version_id = version["dataset_version_id"]
    assert client.post(
        f"/admin/dataset-versions/{version_id}/stage-import",
        json={
            "required_fields": ["nome"],
            "field_types": {"id": "INTEGER"},
        },
        headers=ADMIN_HEADERS,
    ).status_code == 201

    summary = client.get(
        f"/admin/dataset-versions/{version_id}/staging-summary",
        headers=ADMIN_HEADERS,
    )
    assert summary.status_code == 200
    assert summary.json()["invalid_rows"] == 1

    rejected = client.get(
        f"/admin/dataset-versions/{version_id}/rejected-rows?limit=1&offset=0",
        headers=ADMIN_HEADERS,
    )
    assert rejected.status_code == 200
    assert rejected.json()["total"] == 2
    assert len(rejected.json()["items"]) == 1
    assert rejected.json()["items"][0]["line_number"] >= 2


def test_rejected_rows_can_filter_status(monkeypatch, tmp_path: Path) -> None:
    content = b"id;nome\n1;Ana\n2;\n1;Ana\n"
    version = completed_version(monkeypatch, tmp_path, content)
    version_id = version["dataset_version_id"]
    client.post(
        f"/admin/dataset-versions/{version_id}/stage-import",
        json={"required_fields": ["nome"], "field_types": {"id": "INTEGER"}},
        headers=ADMIN_HEADERS,
    )
    response = client.get(
        f"/admin/dataset-versions/{version_id}/rejected-rows?status=INVALID",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "INVALID"


def test_reprocessing_requires_force(monkeypatch, tmp_path: Path) -> None:
    version = completed_version(monkeypatch, tmp_path, b"id\n1\n")
    endpoint = f"/admin/dataset-versions/{version['dataset_version_id']}/stage-import"
    assert client.post(endpoint, json={}, headers=ADMIN_HEADERS).status_code == 201
    assert client.post(endpoint, json={}, headers=ADMIN_HEADERS).status_code == 409
    forced = client.post(
        endpoint,
        json={"force_reprocess": True},
        headers=ADMIN_HEADERS,
    )
    assert forced.status_code == 201
    assert forced.json()["total_rows"] == 1


def test_staging_requires_completed_version() -> None:
    response = client.post(
        "/admin/dataset-versions/00000000-0000-0000-0000-000000000000/stage-import",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


def test_staging_validates_configured_columns(monkeypatch, tmp_path: Path) -> None:
    version = completed_version(monkeypatch, tmp_path, b"id;nome\n1;Ana\n")
    response = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/stage-import",
        json={"required_fields": ["cidade"]},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    summary = client.get(
        f"/admin/dataset-versions/{version['dataset_version_id']}/staging-summary",
        headers=ADMIN_HEADERS,
    )
    assert summary.status_code == 200
    assert summary.json()["status"] == "FAILED"


def test_endpoints_require_admin_authentication(monkeypatch, tmp_path: Path) -> None:
    version = completed_version(monkeypatch, tmp_path, b"id\n1\n")
    version_id = version["dataset_version_id"]
    assert client.post(
        f"/admin/dataset-versions/{version_id}/stage-import", json={}
    ).status_code == 401
    assert client.get(
        f"/admin/dataset-versions/{version_id}/staging-summary"
    ).status_code == 401


def test_rejected_rows_rejects_valid_filter(monkeypatch, tmp_path: Path) -> None:
    version = completed_version(monkeypatch, tmp_path, b"id\n1\n")
    version_id = version["dataset_version_id"]
    client.post(
        f"/admin/dataset-versions/{version_id}/stage-import",
        json={},
        headers=ADMIN_HEADERS,
    )
    response = client.get(
        f"/admin/dataset-versions/{version_id}/rejected-rows?status=VALID",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
