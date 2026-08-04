import csv
from pathlib import Path

import pytest

from engine.validation.importer import ValidationImportError, load_validation_csv


HEADERS = [
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
]


def _write(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def _valid_row(identifier: str = "VAL-1") -> list[object]:
    return [
        identifier,
        "evidence://1",
        "a" * 64,
        "3304557",
        "APARTMENT",
        "Copacabana",
        1_000_000,
        "MARKET_VALUE_RT_REVIEWED",
        80,
        2,
        2,
        1,
    ]


def test_loads_an_auditable_independent_validation_csv(tmp_path: Path) -> None:
    source = tmp_path / "validation.csv"
    _write(source, [_valid_row()])

    observations, rows = load_validation_csv(
        source,
        feature_names=(
            "private_area_m2",
            "bedrooms",
            "bathrooms",
            "parking_spaces",
        ),
        expected_city_ibge_code="3304557",
        expected_property_type="APARTMENT",
    )

    assert len(rows) == 1
    assert observations[0].features == (80.0, 2.0, 2.0, 1.0)
    assert observations[0].reference_value_brl == 1_000_000


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row: row.__setitem__(0, "EXEMPLO-REMOVER"), "replace the example"),
        (lambda row: row.__setitem__(2, "invalid"), "64 hex"),
        (lambda row: row.__setitem__(3, "3550308"), "city scope"),
        (lambda row: row.__setitem__(4, "HOUSE"), "property type"),
        (lambda row: row.__setitem__(8, "not-a-number"), "must be numeric"),
    ],
)
def test_rejects_non_auditable_rows(
    tmp_path: Path, mutation: object, message: str
) -> None:
    row = _valid_row()
    mutation(row)  # type: ignore[operator]
    source = tmp_path / "validation.csv"
    _write(source, [row])

    with pytest.raises(ValidationImportError, match=message):
        load_validation_csv(
            source,
            feature_names=(
                "private_area_m2",
                "bedrooms",
                "bathrooms",
                "parking_spaces",
            ),
            expected_city_ibge_code="3304557",
            expected_property_type="APARTMENT",
        )


def test_rejects_duplicate_identifiers(tmp_path: Path) -> None:
    source = tmp_path / "validation.csv"
    _write(source, [_valid_row(), _valid_row()])

    with pytest.raises(ValidationImportError, match="duplicate validation_id"):
        load_validation_csv(
            source,
            feature_names=(
                "private_area_m2",
                "bedrooms",
                "bathrooms",
                "parking_spaces",
            ),
            expected_city_ibge_code="3304557",
            expected_property_type="APARTMENT",
        )
