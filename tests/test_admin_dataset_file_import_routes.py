import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}


def create_version(content: bytes, *, checksum: str | None = None, size: int | None = None) -> dict:
    source = client.post(
        "/admin/data-sources",
        json={
            "name": f"Fonte {hashlib.sha1(content).hexdigest()}",
            "source_type": "CSV",
            "responsible": "Dados",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    ).json()
    dataset = client.post(
        "/admin/datasets",
        json={
            "data_source_id": source["data_source_id"],
            "name": "Base de importação",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    ).json()
    response = client.post(
        "/admin/dataset-versions",
        json={
            "dataset_id": dataset["dataset_id"],
            "file_name": "dados.csv",
            "storage_path": "pending/dados.csv",
            "checksum_sha256": checksum or hashlib.sha256(content).hexdigest(),
            "file_size_bytes": len(content) if size is None else size,
            "mime_type": "text/csv",
            "metadata": {},
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 201
    return response.json()


def upload(version_id: str, content: bytes, name: str = "dados.csv", mime: str = "text/csv"):
    return client.post(
        f"/admin/dataset-versions/{version_id}/file",
        files={"file": (name, content, mime)},
        headers=ADMIN_HEADERS,
    )


def test_upload_and_process_csv(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"id;valor\n1;100\n2;200\n"
    version = create_version(content)

    uploaded = upload(version["dataset_version_id"], content)
    assert uploaded.status_code == 201
    data = uploaded.json()
    assert data["checksum_sha256"] == hashlib.sha256(content).hexdigest()
    assert data["file_size_bytes"] == len(content)
    assert (tmp_path / data["storage_path"]).is_file()

    processed = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/process-file",
        headers=ADMIN_HEADERS,
    )
    assert processed.status_code == 200
    result = processed.json()
    assert result["status"] == "COMPLETED"
    assert result["record_count"] == 2
    assert result["columns"] == ["id", "valor"]
    assert result["delimiter"] == ";"
    assert result["encoding"] == "utf-8"


def test_import_result_endpoint(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a,b\nx,y\n"
    version = create_version(content)
    assert upload(version["dataset_version_id"], content).status_code == 201
    assert client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/process-file",
        headers=ADMIN_HEADERS,
    ).status_code == 200

    response = client.get(
        f"/admin/dataset-versions/{version['dataset_version_id']}/import-result",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["columns"] == ["a", "b"]


def test_upload_requires_authentication(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    response = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/file",
        files={"file": ("dados.csv", content, "text/csv")},
    )
    assert response.status_code == 401


def test_rejects_non_csv_extension(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    response = upload(version["dataset_version_id"], content, name="dados.txt")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_FILE_INVALID"


def test_rejects_unsupported_mime_type(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    response = upload(
        version["dataset_version_id"],
        content,
        mime="application/pdf",
    )
    assert response.status_code == 422


def test_rejects_checksum_mismatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content, checksum="0" * 64)
    response = upload(version["dataset_version_id"], content)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_FILE_CHECKSUM_MISMATCH"
    assert not list(tmp_path.rglob("*.csv"))


def test_rejects_size_mismatch(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content, size=len(content) + 1)
    response = upload(version["dataset_version_id"], content)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DATASET_FILE_SIZE_MISMATCH"


def test_rejects_file_above_limit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DATASET_MAX_UPLOAD_BYTES", "4")
    content = b"a\n123\n"
    version = create_version(content)
    response = upload(version["dataset_version_id"], content)
    assert response.status_code == 422
    assert "limite" in response.json()["detail"]["message"]


def test_duplicate_upload_is_rejected(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    assert upload(version["dataset_version_id"], content).status_code == 201
    duplicate = upload(version["dataset_version_id"], content)
    assert duplicate.status_code == 409


def test_processing_without_uploaded_file_marks_failed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    response = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/process-file",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    result = client.get(
        f"/admin/dataset-versions/{version['dataset_version_id']}/import-result",
        headers=ADMIN_HEADERS,
    ).json()
    assert result["status"] == "FAILED"
    assert "não foi encontrado" in result["error_message"]


def test_invalid_csv_marks_version_failed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a,a\n1,2\n"
    version = create_version(content)
    assert upload(version["dataset_version_id"], content).status_code == 201
    response = client.post(
        f"/admin/dataset-versions/{version['dataset_version_id']}/process-file",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    result = client.get(
        f"/admin/dataset-versions/{version['dataset_version_id']}/import-result",
        headers=ADMIN_HEADERS,
    ).json()
    assert result["status"] == "FAILED"
    assert "duplicados" in result["error_message"]


def test_processing_cannot_run_twice(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATASET_UPLOAD_DIR", str(tmp_path))
    content = b"a\n1\n"
    version = create_version(content)
    assert upload(version["dataset_version_id"], content).status_code == 201
    endpoint = f"/admin/dataset-versions/{version['dataset_version_id']}/process-file"
    assert client.post(endpoint, headers=ADMIN_HEADERS).status_code == 200
    second = client.post(endpoint, headers=ADMIN_HEADERS)
    assert second.status_code == 409
