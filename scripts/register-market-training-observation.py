from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from urllib.parse import urlsplit


COLLECTION_FIELDS = (
    "observation_id",
    "collection_cell_id",
    "source_portal",
    "source_url",
    "source_listing_id",
    "captured_at",
    "source_reference_date",
    "evidence_file",
    "evidence_sha256",
    "property_type",
    "state",
    "city",
    "city_ibge_code",
    "postal_code",
    "neighborhood",
    "street",
    "number",
    "private_area_m2",
    "built_area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "asking_price_brl",
    "condo_fee_brl",
    "property_tax_brl",
    "latitude",
    "longitude",
    "location_source",
    "location_accuracy_meters",
    "physical_fingerprint",
    "validation_leakage_checked",
    "duplicate_checked",
    "collection_status",
    "exclusion_reason",
    "notes",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalize_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("A URL deve ser absoluta e usar HTTP ou HTTPS.")
    return f"{parsed.netloc.lower()}{parsed.path.rstrip('/').lower()}"


def normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", ascii_text).upper().split())


def canonical_hash(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest().upper()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: cabeçalho ausente.")
        return list(reader), list(reader.fieldnames)


def write_csv(
    path: Path,
    rows: Iterable[Mapping[str, object]],
    fields: Sequence[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def update_queue_registration(
    queue_row: dict[str, object],
    *,
    source_url: str,
    asking_price_brl: str,
    status: str,
) -> None:
    """Record collection progress without rewriting the planned portal."""
    queue_row.update(
        {
            "source_url": source_url,
            "asking_price_brl": asking_price_brl,
            "status": status,
        }
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--observation-id", required=True)
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--source-portal", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-listing-id", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--neighborhood", required=True)
    parser.add_argument("--street", required=True)
    parser.add_argument("--number", required=True)
    parser.add_argument("--private-area-m2", required=True)
    parser.add_argument("--bedrooms", required=True)
    parser.add_argument("--bathrooms", required=True)
    parser.add_argument("--parking-spaces", default="")
    parser.add_argument("--asking-price-brl", required=True)
    parser.add_argument("--condo-fee-brl", default="")
    parser.add_argument("--property-tax-brl", default="")
    parser.add_argument("--notes", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    root = args.model_root.resolve()
    evidence = args.evidence.resolve()
    if not evidence.is_file() or evidence.read_bytes()[:5] != b"%PDF-":
        raise ValueError("A evidência não é um PDF válido.")
    if not re.fullmatch(r"TREINO-RJ-\d{3}-OBS-\d{3}", args.observation_id):
        raise ValueError("Identificador da observação inválido.")
    if not re.fullmatch(r"TREINO-RJ-\d{3}", args.cell_id):
        raise ValueError("Identificador da célula inválido.")

    plan_dir = root / "04-plano-nova-coleta"
    collection_dir = root / "05-coleta-treinamento"
    cell_dir = collection_dir / args.cell_id
    evidence_dir = cell_dir / "01-evidencias" / args.observation_id
    records_dir = cell_dir / "02-registros"
    if evidence.parent != evidence_dir.resolve():
        raise ValueError("A evidência está fora da pasta da observação.")

    template = plan_dir / "TEMPLATE-NOVA-COLETA.csv"
    _, template_fields = read_csv(template)
    if tuple(template_fields) != COLLECTION_FIELDS:
        raise ValueError("O template de coleta possui cabeçalho inesperado.")

    url_key = normalize_url(args.source_url)
    blocklist_path = plan_dir / "URLS-BLOQUEADAS-NOVA-COLETA.csv"
    blocklist, block_fields = read_csv(blocklist_path)
    prior = [row for row in blocklist if row["chave_url"] == url_key]
    if prior:
        references = "|".join(row["referencias"] for row in prior)
        raise ValueError(f"URL já bloqueada por: {references}")

    evidence_hash = sha256(evidence)
    relative_evidence = evidence.relative_to(collection_dir).as_posix()
    fingerprint = canonical_hash(
        {
            "city_ibge_code": "3304557",
            "neighborhood": normalized_text(args.neighborhood),
            "street": normalized_text(args.street),
            "number": normalized_text(args.number),
            "private_area_m2": args.private_area_m2,
            "bedrooms": args.bedrooms,
            "bathrooms": args.bathrooms,
            "parking_spaces": args.parking_spaces,
        }
    )
    record = {
        "observation_id": args.observation_id,
        "collection_cell_id": args.cell_id,
        "source_portal": args.source_portal,
        "source_url": args.source_url,
        "source_listing_id": args.source_listing_id,
        "captured_at": args.captured_at,
        "source_reference_date": args.captured_at[:10],
        "evidence_file": relative_evidence,
        "evidence_sha256": evidence_hash,
        "property_type": "APARTMENT",
        "state": "RJ",
        "city": "Rio de Janeiro",
        "city_ibge_code": "3304557",
        "postal_code": "",
        "neighborhood": args.neighborhood,
        "street": args.street,
        "number": args.number,
        "private_area_m2": args.private_area_m2,
        "built_area_m2": "",
        "bedrooms": args.bedrooms,
        "bathrooms": args.bathrooms,
        "parking_spaces": args.parking_spaces,
        "asking_price_brl": args.asking_price_brl,
        "condo_fee_brl": args.condo_fee_brl,
        "property_tax_brl": args.property_tax_brl,
        "latitude": "",
        "longitude": "",
        "location_source": "PORTAL_MAP_NOT_VALIDATED",
        "location_accuracy_meters": "",
        "physical_fingerprint": fingerprint,
        "validation_leakage_checked": "TRUE",
        "duplicate_checked": "URL_AND_FINGERPRINT",
        "collection_status": "PENDING_DATA_COMPLETENESS",
        "exclusion_reason": "",
        "notes": args.notes,
    }

    master_path = collection_dir / "REGISTRO-MESTRE-COLETA.csv"
    master_rows: list[dict[str, str]] = []
    if master_path.exists():
        master_rows, master_fields = read_csv(master_path)
        if tuple(master_fields) != COLLECTION_FIELDS:
            raise ValueError("O registro mestre possui cabeçalho inesperado.")
    if any(row["observation_id"] == args.observation_id for row in master_rows):
        raise ValueError("Identificador da observação já registrado.")
    if any(normalize_url(row["source_url"]) == url_key for row in master_rows):
        raise ValueError("URL já registrada na nova coleta.")
    master_rows.append(record)
    write_csv(master_path, master_rows, list(COLLECTION_FIELDS))
    write_csv(
        records_dir / f"{args.observation_id}.csv",
        [record],
        list(COLLECTION_FIELDS),
    )

    metadata_path = evidence_dir / "registro-observacao.json"
    metadata_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    preparation_path = evidence_dir / "STATUS-PREPARACAO.json"
    preparation: dict[str, object] = {}
    if preparation_path.exists():
        try:
            preparation = json.loads(preparation_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            preparation = {}
    preparation.update(
        {
            "observation_id": args.observation_id,
            "status": "COLLECTION_RECORDED",
            "collection_status": record["collection_status"],
            "registered_at": args.captured_at,
            "source_portal": args.source_portal,
            "source_url": args.source_url,
            "evidence_sha256": evidence_hash,
        }
    )
    preparation_path.write_text(
        json.dumps(preparation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    evidence_record_path = evidence_dir / "registro-evidencia.txt"
    evidence_record_path.write_text(
        "\n".join(
            [
                f"OBSERVACAO: {args.observation_id}",
                "CLASSIFICACAO: TREINAMENTO EXPLORATORIO",
                "HOMOLOGACAO FORMAL: NAO",
                f"URL: {args.source_url}",
                f"CODIGO DO PORTAL: {args.source_listing_id}",
                f"CAPTURADO EM: {args.captured_at}",
                f"EVIDENCIA: {evidence.name}",
                f"SHA-256: {evidence_hash}",
                "BASE DO VALOR: ASKING_PRICE_EXPLORATORY",
                "LOCALIZACAO: NAO VALIDADA",
                "PRECISAO: NAO DECLARADA",
                "USO EM PRODUCAO: PROIBIDO",
                f"OBSERVACOES: {args.notes}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    plan_path = plan_dir / "PLANO-COLETA-TREINAMENTO-RJ.csv"
    plan_rows, plan_fields = read_csv(plan_path)
    matching_cells = [row for row in plan_rows if row["celula_id"] == args.cell_id]
    if len(matching_cells) != 1:
        raise ValueError("A célula não foi encontrada de forma única no plano.")
    cell = matching_cells[0]
    collected = int(cell["coletados"]) + 1
    target = int(cell["meta_bruta"])
    cell["coletados"] = str(collected)
    cell["pendentes"] = str(max(0, target - collected))
    cell["status"] = "EM_COLETA" if collected < target else "AGUARDANDO_AUDITORIA"
    write_csv(plan_path, plan_rows, plan_fields)

    blocklist.append(
        {
            "chave_url": url_key,
            "urls_originais": args.source_url,
            "origens": "NOVA_COLETA_TREINAMENTO",
            "referencias": args.observation_id,
            "uso_nova_coleta": "PROIBIDO_REUSO",
        }
    )
    write_csv(blocklist_path, blocklist, block_fields)
    block_hash_path = plan_dir / "SHA256-URLS-BLOQUEADAS.csv"
    write_csv(
        block_hash_path,
        [
            {
                "arquivo": blocklist_path.name,
                "quantidade_urls": len(blocklist),
                "sha256": sha256(blocklist_path),
                "gerado_em": args.captured_at,
            }
        ],
        ["arquivo", "quantidade_urls", "sha256", "gerado_em"],
    )

    queue_path = collection_dir / "FILA-COLETA-360-OBS.json"
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        matching_queue = [
            row for row in queue if row.get("observation_id") == args.observation_id
        ]
        if len(matching_queue) != 1:
            raise ValueError(
                "A observaÃ§Ã£o nÃ£o foi encontrada de forma Ãºnica na fila."
            )
        queue_row = matching_queue[0]
        update_queue_registration(
            queue_row,
            source_url=args.source_url,
            asking_price_brl=args.asking_price_brl,
            status=record["collection_status"],
        )
        queue_temporary = queue_path.with_suffix(queue_path.suffix + ".tmp")
        queue_temporary.write_text(
            json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        queue_temporary.replace(queue_path)
        queue_manifest_path = collection_dir / "FILA-COLETA-360-OBS.sha256.json"
        queue_manifest_path.write_text(
            json.dumps(
                {
                    "file": queue_path.name,
                    "row_count": len(queue),
                    "registered_count": len(master_rows),
                    "prepared_pending_count": len(queue) - len(master_rows),
                    "sha256": sha256(queue_path),
                    "generated_at": args.captured_at,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    manifest_files = sorted(
        path
        for path in evidence_dir.iterdir()
        if path.is_file() and path.name != "SHA256-MANIFEST.csv"
    )
    write_csv(
        evidence_dir / "SHA256-MANIFEST.csv",
        [
            {
                "arquivo": path.name,
                "tamanho_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in manifest_files
        ],
        ["arquivo", "tamanho_bytes", "sha256"],
    )

    print("OBSERVAÇÃO DE TREINAMENTO REGISTRADA")
    print(f"Observação: {args.observation_id}")
    print(f"Célula: {args.cell_id}")
    print(f"Coletados na célula: {collected}/{target}")
    print("Elegível para modelo: NÃO - dados e localização pendentes")
    print(f"SHA-256 da evidência: {evidence_hash}")
    print(f"Registro mestre: {master_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
