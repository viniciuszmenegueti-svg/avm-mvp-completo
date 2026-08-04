"""Run an exploratory batch backtest against a frozen model artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from app.services.backtest_report_service import build_backtest_report_pdf
from engine.validation.backtest import (
    BacktestResult,
    BacktestStatus,
    run_exploratory_backtest,
)
from engine.validation.importer import load_validation_csv


def build_limitations(observation_count: int) -> tuple[str, ...]:
    """Describe exploratory limitations without hard-coding the sample size."""
    return (
        (
            f"A base possui {observation_count} observacoes; a suficiencia amostral "
            "depende da politica de aceite aprovada pelo RT."
        ),
        "A independencia em relacao ao treino ainda nao foi aprovada pelo RT.",
        (
            "Os valores de referencia sao precos pedidos, nao valores de mercado "
            "confirmados."
        ),
        "Alguns enderecos, coordenadas ou precisoes locacionais podem estar ausentes.",
        "A politica de aceite e a identificacao do RT permanecem pendentes.",
        "O resultado serve somente para testar importacao, calculo e relatorio.",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa backtest em lote sem retreinar o modelo congelado."
    )
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--validation-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def segment_summary(results: list[BacktestResult]) -> list[dict[str, object]]:
    grouped: dict[str, list[BacktestResult]] = defaultdict(list)
    for result in results:
        grouped[f"Bairro: {result.neighborhood}"].append(result)
    rows: list[dict[str, object]] = []
    for segment, group in sorted(grouped.items()):
        conclusive = [row for row in group if row.absolute_error_brl is not None]
        if not conclusive:
            continue
        rows.append(
            {
                "segment": segment,
                "count": len(conclusive),
                "mae_brl": mean(float(row.absolute_error_brl) for row in conclusive),
                "median_ape": median(
                    float(row.absolute_percentage_error) for row in conclusive
                ),
                "ic80_coverage": mean(
                    bool(row.reference_inside_ic80) for row in conclusive
                ),
                "approval_rate": mean(
                    row.status == BacktestStatus.APPROVED_EXPLORATORY
                    for row in conclusive
                ),
            }
        )
    return rows


def main() -> int:
    arguments = parse_arguments()
    model_path = arguments.model_artifact.resolve()
    validation_path = arguments.validation_csv.resolve()
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    model: dict[str, Any] = json.loads(model_path.read_text(encoding="utf-8"))
    feature_names = tuple(model["feature_names"])
    observations, _ = load_validation_csv(
        validation_path,
        feature_names=feature_names,
        expected_city_ibge_code=str(model["city_ibge_code"]),
        expected_property_type=str(model["property_type"]),
    )
    results, summary = run_exploratory_backtest(
        observations=observations,
        feature_names=feature_names,
        coefficients=tuple(model["coefficients"]),
        residual_variance=float(model["residual_variance"]),
        design_inverse=tuple(tuple(row) for row in model["design_inverse"]),
        degrees_of_freedom=int(model["degrees_of_freedom"]),
        feature_ranges=tuple(tuple(row) for row in model["feature_ranges"]),
        allowed_neighborhoods=tuple(model.get("training_neighborhoods", ())),
    )
    results_path = output_dir / "backtest-results.csv"
    summary_path = output_dir / "backtest-summary.json"
    pdf_path = output_dir / "RELATORIO-BACKTEST-EXPLORATORIO.pdf"
    manifest_path = output_dir / "SHA256-MANIFEST.json"
    write_csv(results_path, [result.as_dict() for result in results])
    segments = segment_summary(results)
    summary_path.write_text(
        json.dumps(
            {
                "classification": "EXPLORATORY_EXTERNAL_BASE_CANDIDATE",
                "formal_homologation": False,
                "summary": summary.as_dict(),
                "segments": segments,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "classification": "EXPLORATORY_EXTERNAL_BASE_CANDIDATE",
        "warning": (
            "BASE EXTERNA CANDIDATA - INDEPENDENCIA NAO APROVADA - "
            "SEM VALIDADE CONTRATUAL"
        ),
        "introductory_notice": (
            "Este documento executa o modelo congelado contra uma base fornecida "
            "separadamente. A independencia, a representatividade e os valores de "
            "referencia ainda nao foram aprovados pelo Responsavel Tecnico. O "
            "resultado e exploratorio e nao constitui homologacao."
        ),
        "source": "Base CSV externa candidata com evidencias SHA-256",
        "subject": "Validacao exploratoria em base externa candidata",
        "overlap_count": "NAO VERIFICADO - RT PENDENTE",
        "limitations": build_limitations(len(observations)),
        "scope": f"IBGE {model['city_ibge_code']} - {model['property_type']}",
        "training_count": "MODELO_CONGELADO",
        "validation_count": len(observations),
        "split_seed": "NAO_APLICAVEL_BASE_FORNECIDA",
        "source_audit_sha256": file_sha256(validation_path),
        "training_sha256": str(model["training_sha256"]),
        "validation_sha256": file_sha256(validation_path),
    }
    pdf_path.write_bytes(
        build_backtest_report_pdf(
            summary=summary,
            results=results,
            metadata=metadata,
            segment_rows=segments,
        )
    )
    files = [model_path, validation_path, results_path, summary_path, pdf_path]
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "classification": "EXPLORATORY_EXTERNAL_BASE_CANDIDATE",
                "formal_homologation": False,
                "model_retrained": False,
                "files": [
                    {"path": str(path), "sha256": file_sha256(path)} for path in files
                ],
                "required_gate": "RT_APPROVED_POLICY_AND_INDEPENDENCE_REVIEW",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Backtest em lote concluido: {len(observations)} observacoes.")
    print("Homologacao formal: NAO")
    print(f"Evidencias: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
