"""Strict import of a frozen independent validation CSV."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

from engine.validation.backtest import BacktestObservation


REQUIRED_COLUMNS = {
    "validation_id",
    "source_reference",
    "evidence_sha256",
    "city_ibge_code",
    "property_type",
    "neighborhood",
    "reference_value_brl",
    "reference_value_basis",
    "private_area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
}
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class ValidationImportError(ValueError):
    """Raised when the frozen validation base is not auditable."""


def _number(row: dict[str, str], field: str, row_number: int) -> float:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise ValidationImportError(
            f"Row {row_number}: {field} must be numeric."
        ) from error
    if not math.isfinite(value):
        raise ValidationImportError(f"Row {row_number}: {field} must be finite.")
    return value


def load_validation_csv(
    path: Path,
    *,
    feature_names: tuple[str, ...],
    expected_city_ibge_code: str,
    expected_property_type: str,
) -> tuple[list[BacktestObservation], list[dict[str, str]]]:
    """Load validated observations while preserving every original row."""

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        headers = set(reader.fieldnames or ())
        missing = sorted((REQUIRED_COLUMNS | set(feature_names)) - headers)
        if missing:
            raise ValidationImportError(
                f"Missing required columns: {', '.join(missing)}"
            )
        rows = list(reader)
    if not rows:
        raise ValidationImportError("Validation base is empty.")

    observations: list[BacktestObservation] = []
    identifiers: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        identifier = row["validation_id"].strip()
        if not identifier or identifier.upper().startswith("EXEMPLO"):
            raise ValidationImportError(
                f"Row {row_number}: replace the example with a real validation ID."
            )
        if identifier in identifiers:
            raise ValidationImportError(
                f"Row {row_number}: duplicate validation_id {identifier}."
            )
        identifiers.add(identifier)
        if row["city_ibge_code"].strip() != expected_city_ibge_code:
            raise ValidationImportError(
                f"Row {row_number}: city scope differs from the frozen model."
            )
        if row["property_type"].strip().upper() != expected_property_type.upper():
            raise ValidationImportError(
                f"Row {row_number}: property type differs from the frozen model."
            )
        if not row["source_reference"].strip():
            raise ValidationImportError(
                f"Row {row_number}: source_reference is required."
            )
        if not SHA256_PATTERN.fullmatch(row["evidence_sha256"].strip()):
            raise ValidationImportError(
                f"Row {row_number}: evidence_sha256 must contain 64 hex characters."
            )
        observations.append(
            BacktestObservation(
                validation_id=identifier,
                features=tuple(
                    _number(row, feature, row_number) for feature in feature_names
                ),
                reference_value_brl=_number(row, "reference_value_brl", row_number),
                source_reference=row["source_reference"].strip(),
                neighborhood=row["neighborhood"].strip() or "NAO_INFORMADO",
                reference_value_basis=row["reference_value_basis"].strip(),
            )
        )
    return observations, rows
