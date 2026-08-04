"""Export the deterministic Annex III order-test dataset."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from engine.testing.order_scenarios import (
    build_order_test_scenarios,
    scenario_summary,
)


CSV_FIELDS = (
    "scenario_id",
    "city_ibge_code",
    "city",
    "state",
    "property_type",
    "category",
    "description",
    "expected_http_status",
    "expected_order_status",
    "expected_code",
    "synthetic",
    "contract_eligible",
    "payload_json",
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Gera a massa sintética adversa das dez localidades do Anexo III.")
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/test_scenarios"),
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output_directory = arguments.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    scenarios = build_order_test_scenarios()
    rows = [scenario.as_row() for scenario in scenarios]
    summary = scenario_summary(scenarios)

    csv_path = output_directory / "avm-order-scenarios-annex-iii.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    jsonl_path = output_directory / "avm-order-scenarios-annex-iii.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as jsonl_file:
        for scenario in scenarios:
            jsonl_file.write(
                json.dumps(
                    scenario.as_row(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            jsonl_file.write("\n")

    manifest_path = output_directory / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Massa sintética de testes gerada com sucesso.")
    print(f"Cenários: {summary['scenario_count']}")
    print(f"SHA-256 canônico: {summary['sha256']}")
    print(f"CSV: {csv_path}")
    print(f"JSONL: {jsonl_path}")
    print(f"Manifesto: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
