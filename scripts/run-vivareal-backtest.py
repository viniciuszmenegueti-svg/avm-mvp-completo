"""Run a deterministic internal holdout backtest on the audited VivaReal base."""

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
from engine.models.linear_regression_nbr import fit_linear_model
from engine.validation.backtest import (
    BacktestObservation,
    BacktestResult,
    BacktestStatus,
    run_exploratory_backtest,
)


FEATURE_NAMES = (
    "private_area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
)
SPLIT_SEED = "AVM-VIVAREAL-RJ-HOLDOUT-V1"
VALIDATION_FRACTION = 0.20


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa backtest exploratorio com holdout interno deterministico."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=Path(".audit/market-data/vivareal-rj/vivareal-rj-auditado.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".audit/backtests/vivareal-rj"),
    )
    parser.add_argument(
        "--final-pdf",
        type=Path,
        default=Path("output/pdf/RELATORIO-BACKTEST-EXPLORATORIO-VIVAREAL-RJ.pdf"),
    )
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_eligible_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    eligible = [
        row for row in rows if row.get("training_eligible", "").lower() == "true"
    ]
    if len(eligible) < 30:
        raise ValueError("A base possui menos de 30 linhas elegiveis.")
    return eligible


def deterministic_holdout(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return exact 80/20 partitions ranked by a stable property fingerprint."""

    ranked = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"{SPLIT_SEED}|{row['physical_fingerprint']}".encode()
        ).hexdigest(),
    )
    validation_count = max(1, round(len(ranked) * VALIDATION_FRACTION))
    validation = ranked[:validation_count]
    training = ranked[validation_count:]
    training_ids = {row["physical_fingerprint"] for row in training}
    validation_ids = {row["physical_fingerprint"] for row in validation}
    if training_ids & validation_ids:
        raise RuntimeError("A divisao criou vazamento entre treino e validacao.")
    return training, validation


def numeric_features(row: dict[str, str]) -> list[float]:
    return [float(row[name]) for name in FEATURE_NAMES]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _segment_summary(
    results: list[BacktestResult], validation_rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    area_by_id = {
        row["observation_id"]: float(row["private_area_m2"]) for row in validation_rows
    }
    grouped: dict[str, list[BacktestResult]] = defaultdict(list)
    for result in results:
        grouped[f"Bairro: {result.neighborhood or 'NAO_INFORMADO'}"].append(result)
        area = area_by_id[result.validation_id]
        if area < 70:
            band = "Area: abaixo de 70 m2"
        elif area <= 120:
            band = "Area: 70 a 120 m2"
        else:
            band = "Area: acima de 120 m2"
        grouped[band].append(result)

    output: list[dict[str, object]] = []
    for segment, group in sorted(grouped.items()):
        conclusive = [row for row in group if row.absolute_error_brl is not None]
        if not conclusive:
            continue
        output.append(
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
    return output


def main() -> int:
    arguments = parse_arguments()
    audit_csv = arguments.audit_csv.resolve()
    if not audit_csv.is_file():
        raise FileNotFoundError(audit_csv)
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    final_pdf = arguments.final_pdf.resolve()
    final_pdf.parent.mkdir(parents=True, exist_ok=True)

    eligible = load_eligible_rows(audit_csv)
    training, validation = deterministic_holdout(eligible)
    observations = [numeric_features(row) for row in training]
    values = [float(row["asking_price_brl"]) for row in training]
    target = [median(column) for column in zip(*observations, strict=True)]
    diagnostics = fit_linear_model(
        feature_names=list(FEATURE_NAMES),
        observations=observations,
        values=values,
        target=target,
        expected_signs={name: 1 for name in FEATURE_NAMES},
    )
    validation_observations = [
        BacktestObservation(
            validation_id=row["observation_id"],
            features=tuple(numeric_features(row)),
            reference_value_brl=float(row["asking_price_brl"]),
            source_reference=row["source_url"],
            neighborhood=row["neighborhood"],
            reference_value_basis="ASKING_PRICE_RESEARCH_ONLY",
        )
        for row in validation
    ]
    results, summary = run_exploratory_backtest(
        observations=validation_observations,
        feature_names=diagnostics.feature_names,
        coefficients=diagnostics.coefficients,
        residual_variance=diagnostics.residual_variance,
        design_inverse=diagnostics.design_inverse,
        degrees_of_freedom=diagnostics.degrees_of_freedom,
        feature_ranges=diagnostics.feature_ranges,
    )

    training_payload = [
        {
            "observation_id": row["observation_id"],
            "physical_fingerprint": row["physical_fingerprint"],
            "features": numeric_features(row),
            "value": float(row["asking_price_brl"]),
        }
        for row in training
    ]
    validation_payload = [
        {
            "observation_id": row["observation_id"],
            "physical_fingerprint": row["physical_fingerprint"],
            "features": numeric_features(row),
            "reference_value_brl": float(row["asking_price_brl"]),
        }
        for row in validation
    ]
    training_hash = canonical_sha256(training_payload)
    validation_hash = canonical_sha256(validation_payload)

    validation_csv = output_dir / "validation-holdout.csv"
    results_csv = output_dir / "backtest-results.csv"
    summary_json = output_dir / "backtest-summary.json"
    model_artifact_json = output_dir / "backtest-model-artifact.json"
    manifest_json = output_dir / "SHA256-MANIFEST.json"
    write_csv(validation_csv, validation_payload)
    result_rows = []
    by_id = {row["observation_id"]: row for row in validation}
    for result in results:
        source = by_id[result.validation_id]
        result_rows.append(
            {
                **result.as_dict(),
                **{name: float(source[name]) for name in FEATURE_NAMES},
            }
        )
    write_csv(results_csv, result_rows)
    segments = _segment_summary(results, validation)
    summary_payload: dict[str, Any] = {
        "classification": "INTERNAL_HOLDOUT_EXPLORATORY",
        "external_independence": False,
        "formal_homologation": False,
        "summary": summary.as_dict(),
        "segments": segments,
        "model_diagnostics": {
            "feature_names": diagnostics.feature_names,
            "coefficients": diagnostics.coefficients,
            "adjusted_r_squared": diagnostics.adjusted_r_squared,
            "loocv_rmse_training": diagnostics.loocv_rmse,
            "economic_gates_passed": diagnostics.economic_gates_passed,
            "economic_gate_failures": diagnostics.economic_gate_failures,
            "feature_ranges": diagnostics.feature_ranges,
        },
    }
    summary_json.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    model_artifact = {
        "artifact_classification": "EXPLORATORY_FROZEN_LINEAR_MODEL",
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
        "dependent_variable": "asking_price_brl",
        "formal_homologation": False,
        "feature_names": diagnostics.feature_names,
        "coefficients": diagnostics.coefficients,
        "residual_variance": diagnostics.residual_variance,
        "design_inverse": diagnostics.design_inverse,
        "degrees_of_freedom": diagnostics.degrees_of_freedom,
        "feature_ranges": diagnostics.feature_ranges,
        "training_neighborhoods": sorted(
            {str(row["neighborhood"]) for row in training}
        ),
        "training_sha256": training_hash,
    }
    model_artifact_json.write_text(
        json.dumps(model_artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata = {
        "scope": "Rio de Janeiro/RJ - 3304557 - APARTMENT",
        "training_count": len(training),
        "validation_count": len(validation),
        "split_seed": SPLIT_SEED,
        "source_audit_sha256": file_sha256(audit_csv),
        "training_sha256": training_hash,
        "validation_sha256": validation_hash,
    }
    pdf = build_backtest_report_pdf(
        summary=summary,
        results=results,
        metadata=metadata,
        segment_rows=segments,
    )
    if not pdf.startswith(b"%PDF-"):
        raise RuntimeError("O relatorio gerado nao possui cabecalho PDF valido.")
    final_pdf.write_bytes(pdf)
    audit_pdf = output_dir / final_pdf.name
    audit_pdf.write_bytes(pdf)

    generated_files = [
        validation_csv,
        results_csv,
        summary_json,
        model_artifact_json,
        audit_pdf,
    ]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": "INTERNAL_HOLDOUT_EXPLORATORY",
        "external_independence": False,
        "formal_homologation": False,
        "source_audit_csv": str(audit_csv),
        "source_audit_sha256": metadata["source_audit_sha256"],
        "split": {
            "algorithm": "SHA256_RANK_EXACT_HOLDOUT_V1",
            "seed": SPLIT_SEED,
            "validation_fraction": VALIDATION_FRACTION,
            "training_count": len(training),
            "validation_count": len(validation),
            "overlap_count": 0,
            "training_sha256": training_hash,
            "validation_sha256": validation_hash,
        },
        "features": FEATURE_NAMES,
        "reference_value": "asking_price_brl",
        "reference_value_limit": "ASKING_PRICE_NOT_MARKET_VALUE",
        "decision_policy": summary.decision_basis,
        "formal_thresholds_configured": False,
        "required_next_gate": "EXTERNAL_INDEPENDENT_BASE_AND_RT_APPROVAL",
        "files": [
            {"path": str(path), "sha256": file_sha256(path)} for path in generated_files
        ],
    }
    manifest_json.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Backtest exploratorio concluido.")
    print(f"Treino: {len(training)}")
    print(f"Validacao interna: {len(validation)}")
    print(f"MAE: {summary.mean_absolute_error_brl:.2f}")
    print(f"RMSE: {summary.root_mean_squared_error_brl:.2f}")
    print(f"Cobertura IC80: {summary.ic80_empirical_coverage:.4f}")
    print("Homologacao formal: NAO")
    print(f"Evidencias: {output_dir}")
    print(f"PDF: {final_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
