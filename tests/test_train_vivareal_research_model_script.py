from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "train-vivareal-research-model.py"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "train_vivareal_research_model", SCRIPT_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rejects_known_placeholder_contamination() -> None:
    script = _load_script()
    rows = [
        {"publicationType": "143", "status": "143"},
        {"publicationType": "143", "status": "143"},
        {"publicationType": "STANDARD", "status": "ACTIVE"},
    ]

    with pytest.raises(ValueError, match="sentinela 143"):
        script._reject_placeholder_contamination(Path("contaminada.xlsx"), rows)


def test_accepts_real_textual_statuses() -> None:
    script = _load_script()
    rows = [
        {"publicationType": "STANDARD", "status": "ACTIVE"},
        {"publicationType": "PREMIUM", "status": "INACTIVE"},
    ]

    script._reject_placeholder_contamination(Path("original.xlsx"), rows)


def test_single_source_reconciliation_keeps_unique_rows() -> None:
    script = _load_script()
    source = Path("original.xlsx")
    rows = [
        {"url": "https://example.test/1", "id": "1"},
        {"url": "https://example.test/2", "id": "2"},
    ]

    reconciled, conflicts = script.reconcile_workbooks([(source, rows)])

    assert len(reconciled) == 2
    assert conflicts == {}
    assert {row["_source_files"] for row in reconciled} == {"original.xlsx"}


def test_implausible_sentinel_like_features_are_excluded() -> None:
    script = _load_script()
    rows = [
        {
            "url": "https://example.test/1",
            "id": "1",
            "listingType": "SALE",
            "propertyType": "UNIT",
            "city": "Rio de Janeiro",
            "state": "RJ",
            "currency": "BRL",
            "price": 500_000,
            "usableArea": 70,
            "bedrooms": 2,
            "bathrooms": 1,
            "parkingSpaces": 143,
            "street": "Rua A",
            "zipCode": "20000000",
            "neighborhood": "Centro",
            "lat": -22.9,
            "lng": -43.2,
            "updatedAt": "2026-08-01",
            "scrapedAt": "2026-08-02",
        }
    ]

    [audit] = script.prepare_audit_rows(rows)

    assert audit["training_eligible"] is False
    assert audit["exclusion_reasons"] == "IMPLAUSIBLE_TRAINING_FEATURE"
