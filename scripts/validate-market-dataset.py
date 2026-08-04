import argparse
import csv
import json
from datetime import date
from pathlib import Path

from engine.datasets.market_observations import (
    DatasetPolicy,
    assess_market_dataset,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida uma coleta de dados imobiliários sem remover linhas e gera "
            "trilha de inclusão/exclusão para revisão do RT."
        )
    )
    parser.add_argument("input", type=Path, help="Arquivo CSV UTF-8 de entrada.")
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--city", default="São Paulo")
    parser.add_argument("--state", default="SP")
    parser.add_argument("--ibge-code", default="3550308")
    parser.add_argument("--property-type", default="APARTMENT")
    parser.add_argument("--reference-date", type=date.fromisoformat, required=True)
    parser.add_argument("--variable-count", type=int, default=7)
    parser.add_argument("--max-age-days", type=int, default=365)
    parser.add_argument("--max-source-share", type=float, default=0.50)
    parser.add_argument(
        "--require-model-ready",
        action="store_true",
        help="Retorna código 2 quando a base não estiver pronta para o modelo.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("O CSV não possui cabeçalho.")
        return list(reader), list(reader.fieldnames)


def write_assessed_rows(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    assessments: list[dict[str, object]],
) -> None:
    audit_fields = [
        "audit_collection_valid",
        "audit_model_eligible",
        "audit_reason_codes",
        "audit_duplicate_of",
        "audit_price_per_m2_brl",
        "audit_source_fingerprint",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=[*fieldnames, *audit_fields])
        writer.writeheader()
        for row, assessment in zip(rows, assessments, strict=True):
            output = dict(row)
            output.update(
                {
                    "audit_collection_valid": assessment["collection_valid"],
                    "audit_model_eligible": assessment["model_eligible"],
                    "audit_reason_codes": "|".join(assessment["reason_codes"]),
                    "audit_duplicate_of": assessment["duplicate_of"] or "",
                    "audit_price_per_m2_brl": (assessment["price_per_m2_brl"] or ""),
                    "audit_source_fingerprint": assessment["source_fingerprint"],
                }
            )
            writer.writerow(output)


def main() -> int:
    arguments = parse_arguments()
    rows, fieldnames = read_rows(arguments.input)
    policy = DatasetPolicy(
        city_ibge_code=arguments.ibge_code,
        city=arguments.city,
        state=arguments.state,
        property_type=arguments.property_type,
        reference_date=arguments.reference_date,
        variable_count=arguments.variable_count,
        max_age_days=arguments.max_age_days,
        max_source_share=arguments.max_source_share,
    )
    result = assess_market_dataset(rows, policy)
    manifest = result.as_dict()

    write_assessed_rows(
        arguments.output_csv,
        rows,
        fieldnames,
        list(manifest["assessments"]),
    )
    arguments.manifest.parent.mkdir(parents=True, exist_ok=True)
    arguments.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Observações preservadas: {result.total_count}")
    print(f"Coletas estruturalmente válidas: {result.collection_valid_count}")
    print(f"Elegíveis para modelo: {result.model_eligible_count}")
    print(f"Excluídas do modelo: {result.excluded_count}")
    print(f"Grau de amostra: {result.sample_grade or 'NÃO ATINGIDO'}")
    print(f"Distribuição por fonte: {result.source_distribution_passed}")
    print(f"Base pronta para modelo: {result.model_ready}")
    print(f"SHA-256 do dataset: {result.dataset_sha256}")
    print(f"CSV auditado: {arguments.output_csv.resolve()}")
    print(f"Manifesto: {arguments.manifest.resolve()}")

    if arguments.require_model_ready and not result.model_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
