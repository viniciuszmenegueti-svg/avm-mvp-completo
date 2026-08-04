from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    args = parser.parse_args()

    root = args.model_root.resolve()
    collection_root = root / "05-coleta-treinamento"
    queue_path = collection_root / "FILA-COLETA-360-OBS.json"
    manifest_path = collection_root / "FILA-COLETA-360-OBS.sha256.json"
    master_path = collection_root / "REGISTRO-MESTRE-COLETA.csv"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    master = read_csv(master_path)
    registered_ids = {row["observation_id"] for row in master}
    issues: list[str] = []

    ids = [row["observation_id"] for row in queue]
    if len(queue) != 360:
        issues.append(f"QUEUE_COUNT={len(queue)}")
    if len(set(ids)) != 360:
        issues.append("DUPLICATE_OBSERVATION_ID")
    if manifest["sha256"] != sha256(queue_path):
        issues.append("QUEUE_HASH_MISMATCH")
    if manifest["row_count"] != 360:
        issues.append("MANIFEST_ROW_COUNT")

    by_cell: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in queue:
        by_cell[str(row["collection_cell_id"])].append(row)
        observation_dir = Path(str(row["evidence_directory"]))
        if not observation_dir.is_dir():
            issues.append(f"MISSING_DIRECTORY:{row['observation_id']}")
        if row["observation_id"] not in registered_ids:
            if not (observation_dir / "INSTRUCOES-COLETA.txt").is_file():
                issues.append(f"MISSING_INSTRUCTIONS:{row['observation_id']}")
            if not (observation_dir / "STATUS-PREPARACAO.json").is_file():
                issues.append(f"MISSING_PREPARATION_STATUS:{row['observation_id']}")

    if len(by_cell) != 36:
        issues.append(f"CELL_COUNT={len(by_cell)}")
    for cell_id, rows in by_cell.items():
        if len(rows) != 10:
            issues.append(f"CELL_TARGET:{cell_id}={len(rows)}")
        portal_counts = Counter(str(row["preferred_portal"]) for row in rows)
        if len(portal_counts) < 6:
            issues.append(f"PORTAL_DIVERSITY:{cell_id}={len(portal_counts)}")
        if max(portal_counts.values()) > 2:
            issues.append(f"PORTAL_CONCENTRATION:{cell_id}")

    workbook = args.workbook.resolve()
    if not workbook.is_file() or not zipfile.is_zipfile(workbook):
        issues.append("INVALID_XLSX")
    else:
        with zipfile.ZipFile(workbook) as archive:
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            if not required.issubset(archive.namelist()):
                issues.append("INCOMPLETE_XLSX")

    print("AUDITORIA DA PREPARACAO DAS OBS")
    print(f"Observacoes: {len(queue)}")
    print(f"Celulas: {len(by_cell)}")
    print(f"Registradas: {len(registered_ids)}")
    print(f"Preparadas e pendentes: {len(queue) - len(registered_ids)}")
    print(f"Problemas: {len(issues)}")
    for issue in issues:
        print(issue)
    if issues:
        return 1
    print("PREPARACAO VALIDADA COM SUCESSO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
