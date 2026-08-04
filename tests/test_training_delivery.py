from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from engine.training_delivery import (
    audit_training_collection,
    write_training_delivery,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path, *, collected: int = 3) -> Path:
    plan = root / "04-plano-nova-coleta"
    collection = root / "05-coleta-treinamento"
    plan.mkdir(parents=True)
    collection.mkdir(parents=True)
    _write_csv(
        plan / "PLANO-COLETA-TREINAMENTO-RJ.csv",
        [
            {
                "celula_id": "TREINO-RJ-001",
                "regiao": "Zona Sul",
                "bairro": "Copacabana",
                "faixa_area": "ATE_49_99_M2",
                "area_minima_m2": "12",
                "area_maxima_m2": "49.99",
                "meta_bruta": "3",
                "minimo_fontes_distintas": "3",
                "maximo_por_portal_na_celula": "1",
                "coletados": str(collected),
                "validos": "0",
                "pendentes": str(3 - collected),
                "status": "EM_COLETA",
                "classificacao": "TREINAMENTO_EXPLORATORIO",
            }
        ],
    )
    queue = []
    master = []
    for index in range(1, 4):
        observation_id = f"TREINO-RJ-001-OBS-{index:03d}"
        evidence_dir = collection / "TREINO-RJ-001" / "01-evidencias" / observation_id
        queue.append(
            {
                "observation_id": observation_id,
                "collection_cell_id": "TREINO-RJ-001",
                "preferred_portal": f"PORTAL-{index}",
                "status": (
                    "PENDING_DATA_COMPLETENESS"
                    if index <= collected
                    else "PREPARED_PENDING_COLLECTION"
                ),
            }
        )
        if index > collected:
            continue
        evidence_dir.mkdir(parents=True, exist_ok=True)
        pdf = evidence_dir / "evidencia-anuncio.pdf"
        pdf.write_bytes(b"%PDF-1.4\ntraining-test\n%%EOF")
        _write_csv(
            evidence_dir / "SHA256-MANIFEST.csv",
            [
                {
                    "arquivo": pdf.name,
                    "tamanho_bytes": pdf.stat().st_size,
                    "sha256": _hash(pdf),
                }
            ],
        )
        master.append(
            {
                "observation_id": observation_id,
                "collection_cell_id": "TREINO-RJ-001",
                "source_portal": f"PORTAL-{index}",
                "evidence_file": pdf.relative_to(collection).as_posix(),
                "evidence_sha256": _hash(pdf),
                "collection_status": "PENDING_DATA_COMPLETENESS",
                "latitude": "",
                "longitude": "",
                "location_accuracy_meters": "",
            }
        )
    queue_path = collection / "FILA-COLETA-360-OBS.json"
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    (collection / "FILA-COLETA-360-OBS.sha256.json").write_text(
        json.dumps({"row_count": len(queue), "sha256": _hash(queue_path)}),
        encoding="utf-8",
    )
    _write_csv(collection / "REGISTRO-MESTRE-COLETA.csv", master)
    return root


def test_audits_complete_evidence_without_claiming_training_readiness(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path / "model")

    result = audit_training_collection(root)

    assert result["planned_observations"] == 3
    assert result["collected_observations"] == 3
    assert result["valid_evidence_count"] == 3
    assert result["research_pipeline_smoke_ready"] is True
    assert result["training_dataset_ready"] is False
    assert "RT_VARIABLE_POLICY_PENDING" in result["blockers"]


def test_detects_tampered_evidence(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "model")
    evidence = next(root.rglob("evidencia-anuncio.pdf"))
    evidence.write_bytes(evidence.read_bytes() + b"tampered")

    result = audit_training_collection(root)

    assert result["valid_evidence_count"] == 2
    assert "EVIDENCE_INTEGRITY_FAILURE" in result["blockers"]


def test_rejects_a_queue_hash_mismatch(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "model")
    queue = root / "05-coleta-treinamento" / "FILA-COLETA-360-OBS.json"
    queue.write_text(queue.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="hash"):
        audit_training_collection(root)


def test_rejects_duplicate_observation_ids(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "model")
    collection = root / "05-coleta-treinamento"
    queue_path = collection / "FILA-COLETA-360-OBS.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue[1]["observation_id"] = queue[0]["observation_id"]
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    (collection / "FILA-COLETA-360-OBS.sha256.json").write_text(
        json.dumps({"row_count": len(queue), "sha256": _hash(queue_path)}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        audit_training_collection(root)


def test_writes_pdf_manifest_and_zip_package(tmp_path: Path) -> None:
    root = _fixture(tmp_path / "model")
    output = tmp_path / "delivery"

    result = write_training_delivery(model_root=root, output_dir=output)

    report = Path(result["report_pdf"])
    archive = Path(result["zip_path"])
    assert report.read_bytes().startswith(b"%PDF-")
    assert report.stat().st_size > 5_000
    assert zipfile.is_zipfile(archive)
    assert len(result["zip_sha256"]) == 64
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert any(row["path"] == report.name for row in manifest["files"])
