from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


PORTAL_SEQUENCE = (
    "ZAP_IMOVEIS",
    "QUINTOANDAR",
    "VIVAREAL",
    "IMOVELWEB",
    "OLX",
    "CHAVES_NA_MAO",
    "ZAP_IMOVEIS",
    "QUINTOANDAR",
    "VIVAREAL",
    "IMOVELWEB",
)


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
    parser.add_argument("--prepared-at", required=True)
    args = parser.parse_args()

    root = args.model_root.resolve()
    plan_path = root / "04-plano-nova-coleta" / "PLANO-COLETA-TREINAMENTO-RJ.csv"
    collection_root = root / "05-coleta-treinamento"
    master_path = collection_root / "REGISTRO-MESTRE-COLETA.csv"

    plan = read_csv(plan_path)
    master = read_csv(master_path) if master_path.exists() else []
    registered = {row["observation_id"]: row for row in master}
    queue: list[dict[str, object]] = []

    for cell in plan:
        cell_id = cell["celula_id"]
        target = int(cell["meta_bruta"])
        evidence_root = collection_root / cell_id / "01-evidencias"
        evidence_root.mkdir(parents=True, exist_ok=True)

        for sequence in range(1, target + 1):
            observation_id = f"{cell_id}-OBS-{sequence:03d}"
            observation_dir = evidence_root / observation_id
            observation_dir.mkdir(parents=True, exist_ok=True)
            existing = registered.get(observation_id)
            status = (
                existing["collection_status"]
                if existing is not None
                else "PREPARED_PENDING_COLLECTION"
            )
            source_url = existing["source_url"] if existing is not None else ""
            source_portal = (
                existing["source_portal"]
                if existing is not None
                else PORTAL_SEQUENCE[sequence - 1]
            )
            asking_price = existing["asking_price_brl"] if existing is not None else ""

            record = {
                "priority": len(queue) + 1,
                "observation_id": observation_id,
                "collection_cell_id": cell_id,
                "region": cell["regiao"],
                "neighborhood": cell["bairro"],
                "area_band": cell["faixa_area"],
                "area_min_m2": cell["area_minima_m2"],
                "area_max_m2": cell["area_maxima_m2"],
                "preferred_portal": source_portal,
                "source_url": source_url,
                "asking_price_brl": asking_price,
                "status": status,
                "evidence_directory": str(observation_dir),
                "requires_real_listing": True,
                "requires_pdf_evidence": True,
                "requires_sha256": True,
                "requires_duplicate_check": True,
                "requires_validation_leakage_check": True,
                "requires_location_validation": True,
                "formal_homologation": False,
                "prepared_at": args.prepared_at,
            }
            queue.append(record)

            if existing is None:
                instructions = "\n".join(
                    [
                        f"OBSERVACAO PREPARADA: {observation_id}",
                        "========================================",
                        "",
                        "Classificacao: TREINAMENTO EXPLORATORIO",
                        "Homologacao formal: NAO",
                        f"Celula: {cell_id}",
                        f"Regiao: {cell['regiao']}",
                        f"Bairro: {cell['bairro']}",
                        f"Faixa de area: {cell['faixa_area']}",
                        (
                            "Area permitida: "
                            f"{cell['area_minima_m2']} a "
                            f"{cell['area_maxima_m2']} m2"
                        ),
                        f"Portal preferencial: {source_portal}",
                        "",
                        "Antes de registrar:",
                        "1. Confirmar que o anuncio e de venda e esta ativo.",
                        (
                            "2. Conferir URL e impressao digital contra a lista "
                            "de bloqueio."
                        ),
                        "3. Preservar capturas e PDF do anuncio.",
                        "4. Registrar somente dados visiveis e auditaveis.",
                        "5. Nao presumir numero, CEP, coordenadas ou precisao.",
                        "6. Gerar manifesto SHA-256.",
                        "7. Manter como pendente se faltarem dados obrigatorios.",
                        "",
                        (
                            "Proibido reutilizar observacoes da validacao ou do "
                            "treinamento anterior."
                        ),
                        "Proibido classificar preco pedido como transacao confirmada.",
                        "",
                    ]
                )
                instruction_path = observation_dir / "INSTRUCOES-COLETA.txt"
                if not instruction_path.exists():
                    instruction_path.write_text(instructions, encoding="utf-8")
                preparation_path = observation_dir / "STATUS-PREPARACAO.json"
                if not preparation_path.exists():
                    preparation_path.write_text(
                        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )

    queue_path = collection_root / "FILA-COLETA-360-OBS.json"
    queue_path.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest_path = collection_root / "FILA-COLETA-360-OBS.sha256.json"
    manifest_path.write_text(
        json.dumps(
            {
                "file": queue_path.name,
                "row_count": len(queue),
                "registered_count": len(registered),
                "prepared_pending_count": len(queue) - len(registered),
                "sha256": sha256(queue_path),
                "generated_at": args.prepared_at,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("FILA COMPLETA DE OBSERVACOES PREPARADA")
    print(f"Observacoes totais: {len(queue)}")
    print(f"Preservadas: {len(registered)}")
    print(f"Preparadas e pendentes: {len(queue) - len(registered)}")
    print(f"Arquivo: {queue_path}")
    print(f"SHA-256: {sha256(queue_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
