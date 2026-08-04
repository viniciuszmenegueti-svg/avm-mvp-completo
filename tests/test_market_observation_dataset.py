from datetime import date

import pytest

from engine.datasets.market_observations import (
    DatasetPolicy,
    assess_market_dataset,
)


def policy(*, variable_count: int = 7) -> DatasetPolicy:
    return DatasetPolicy(
        city_ibge_code="3550308",
        city="São Paulo",
        state="SP",
        property_type="APARTMENT",
        reference_date=date(2026, 7, 31),
        variable_count=variable_count,
    )


def valid_transaction(index: int = 1, portal: str = "REGISTRY") -> dict[str, str]:
    return {
        "observation_id": f"OBS-{index:03d}",
        "source_portal": portal,
        "source_url": f"https://example.com/transactions/{index}",
        "source_listing_id": f"TX-{index:03d}",
        "source_stable_url": "true",
        "captured_at": "2026-07-31T10:00:00-03:00",
        "source_reference_date": "2026-07-15",
        "source_reference_date_precision": "EXACT",
        "evidence_type": "TRANSACTION",
        "property_type": "APARTMENT",
        "state": "SP",
        "city": "São Paulo",
        "city_ibge_code": "3550308",
        "postal_code": "01001-000",
        "neighborhood": "Centro",
        "street": "Rua de Teste",
        "number": str(100 + index),
        "private_area_m2": str(60 + index),
        "bedrooms": "2",
        "bathrooms": "2",
        "parking_spaces": "1",
        "asking_price_brl": "",
        "transaction_price_brl": str(500_000 + index * 1_000),
        "usable_market_value_brl": str(500_000 + index * 1_000),
        "market_value_basis": "CONFIRMED_TRANSACTION",
        "rt_review_reference": "RT-REVIEW-001",
        "latitude": "-23.550520",
        "longitude": "-46.633308",
        "location_accuracy_meters": "35",
        "geocoding_method": "CNEFE_MATCH",
        "geocoding_evidence_reference": "CNEFE-3550308-TESTE",
        "geocoding_verified_by": "PIPELINE-TESTE",
        "evidence_reference": "evidence/transaction-001.json",
        "evidence_sha256": "A" * 64,
    }


def internet_offer() -> dict[str, str]:
    row = valid_transaction()
    row.update(
        {
            "source_portal": "PORTAL-IMOBILIARIO",
            "source_url": "https://example.com/listing/001",
            "source_listing_id": "LISTING-001",
            "evidence_type": "OFFER",
            "asking_price_brl": "690000",
            "transaction_price_brl": "",
            "usable_market_value_brl": "",
            "market_value_basis": "ASKING_PRICE_ONLY",
            "market_adjustment_reference": "",
            "rt_review_reference": "",
            "number": "",
            "postal_code": "",
            "latitude": "",
            "longitude": "",
            "location_accuracy_meters": "",
            "geocoding_method": "",
            "geocoding_evidence_reference": "",
            "geocoding_verified_by": "",
            "evidence_reference": "",
            "evidence_sha256": "",
        }
    )
    return row


def test_accepts_a_fully_auditable_confirmed_transaction() -> None:
    result = assess_market_dataset([valid_transaction()], policy())
    assessment = result.assessments[0]

    assert assessment.collection_valid is True
    assert assessment.model_eligible is True
    assert assessment.reason_codes == ()
    assert assessment.price_per_m2_brl == 8213.11


def test_preserves_internet_offer_but_blocks_it_from_the_model() -> None:
    result = assess_market_dataset([internet_offer()], policy())
    assessment = result.assessments[0]

    assert result.total_count == 1
    assert assessment.collection_valid is True
    assert assessment.model_eligible is False
    assert "USABLE_MARKET_VALUE_MISSING" in assessment.reason_codes
    assert "OFFER_ADJUSTMENT_NOT_RT_APPROVED" in assessment.reason_codes
    assert "ADDRESS_NUMBER_MISSING" in assessment.reason_codes
    assert "COORDINATES_MISSING" in assessment.reason_codes
    assert "EVIDENCE_SHA256_MISSING_OR_INVALID" in assessment.reason_codes


def test_marks_potential_duplicate_without_deleting_the_row() -> None:
    first = valid_transaction(1, "PORTAL-A")
    second = dict(first)
    second.update(
        {
            "observation_id": "OBS-002",
            "source_portal": "PORTAL-B",
            "source_url": "https://example.org/listing/duplicate",
            "source_listing_id": "DUPLICATE-002",
        }
    )

    result = assess_market_dataset([first, second], policy())

    assert result.total_count == 2
    assert result.assessments[1].duplicate_of == "OBS-001"
    assert "POTENTIAL_DUPLICATE" in result.assessments[1].reason_codes
    assert result.model_eligible_count == 1


def test_rejects_location_accuracy_above_contract_limit() -> None:
    row = valid_transaction()
    row["location_accuracy_meters"] = "50.01"

    result = assess_market_dataset([row], policy())

    assert result.assessments[0].model_eligible is False
    assert "LOCATION_ACCURACY_ABOVE_LIMIT" in result.assessments[0].reason_codes


def test_rejects_stale_or_approximate_reference_dates() -> None:
    row = valid_transaction()
    row["source_reference_date"] = "2025-01-01"
    row["source_reference_date_precision"] = "CAPTURE_ONLY"

    result = assess_market_dataset([row], policy())

    assert "SOURCE_REFERENCE_DATE_STALE" in result.assessments[0].reason_codes
    assert "SOURCE_REFERENCE_DATE_NOT_EXACT" in result.assessments[0].reason_codes


def test_computes_sample_grade_and_source_concentration_gate() -> None:
    portals = ("SOURCE-A", "SOURCE-B", "SOURCE-C")
    rows = [valid_transaction(index, portals[index % 3]) for index in range(1, 13)]

    result = assess_market_dataset(rows, policy(variable_count=1))

    assert result.model_eligible_count == 12
    assert result.sample_grade == "III"
    assert result.maximum_source_share == 4 / 12
    assert result.source_distribution_passed is True
    assert result.model_ready is True


def test_source_concentration_normalizes_portal_spelling() -> None:
    rows = [
        valid_transaction(1, "OLX"),
        valid_transaction(2, " olx "),
        valid_transaction(3, "Olx"),
        valid_transaction(4, "OTHER"),
    ]

    result = assess_market_dataset(rows, policy(variable_count=1))

    assert result.source_counts == {"OLX": 3, "OTHER": 1}
    assert result.maximum_source_share == 0.75
    assert result.source_distribution_passed is False


@pytest.mark.parametrize(
    ("property_type", "area_field"),
    [("HOUSE", "built_area_m2"), ("LAND", "land_area_m2")],
)
def test_duplicate_fingerprint_uses_reference_area_by_property_type(
    property_type: str,
    area_field: str,
) -> None:
    first = valid_transaction(1, "SOURCE-A")
    first.update(
        {
            "property_type": property_type,
            "private_area_m2": "",
            area_field: "120",
        }
    )
    second = dict(first)
    second.update(
        {
            "observation_id": "OBS-002",
            "source_portal": "SOURCE-B",
            "source_url": "https://example.org/duplicate",
            "source_listing_id": "DUP-002",
        }
    )
    custom_policy = DatasetPolicy(
        city_ibge_code="3550308",
        city="São Paulo",
        state="SP",
        property_type=property_type,
        reference_date=date(2026, 7, 31),
        variable_count=1,
        required_features=(area_field,),
    )

    result = assess_market_dataset([first, second], custom_policy)

    assert result.assessments[1].duplicate_of == "OBS-001"


def test_reports_nbr_sample_requirements_for_seven_variables() -> None:
    result = assess_market_dataset([], policy(variable_count=7))

    assert result.required_sample_sizes == {"I": 24, "II": 32, "III": 48}
    assert result.sample_grade is None
    assert result.model_ready is False
    assert len(result.dataset_sha256) == 64


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"variable_count": 0}, "variable_count"),
        ({"max_age_days": -1}, "max_age_days"),
        ({"max_location_accuracy_meters": 0}, "max_location_accuracy"),
        ({"max_source_share": 0}, "max_source_share"),
    ],
)
def test_rejects_invalid_dataset_policies(
    override: dict[str, int],
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "city_ibge_code": "3550308",
        "city": "São Paulo",
        "state": "SP",
        "property_type": "APARTMENT",
        "reference_date": date(2026, 7, 31),
        "variable_count": 7,
    }
    arguments.update(override)

    with pytest.raises(ValueError, match=message):
        DatasetPolicy(**arguments)  # type: ignore[arg-type]


def test_reports_all_structural_failures_without_silent_cleanup() -> None:
    first = valid_transaction()
    invalid = dict(first)
    invalid.update(
        {
            "source_portal": "",
            "source_url": "https://[invalid",
            "source_listing_id": "",
            "source_stable_url": "unknown",
            "captured_at": "not-a-datetime",
            "source_reference_date": "2026-08-01",
            "evidence_type": "UNKNOWN",
            "property_type": "HOUSE",
            "state": "RJ",
            "city": "Rio de Janeiro",
            "city_ibge_code": "3304557",
            "private_area_m2": "",
            "bedrooms": "not-a-number",
            "street": "HIDDEN",
            "number": "0",
            "postal_code": "invalid",
            "latitude": "91",
            "longitude": "181",
            "location_accuracy_meters": "unknown",
            "geocoding_method": "",
            "geocoding_evidence_reference": "",
            "geocoding_verified_by": "",
        }
    )

    result = assess_market_dataset([first, invalid], policy())
    assessment = result.assessments[1]

    assert assessment.collection_valid is False
    assert "OBSERVATION_ID_DUPLICATE" in assessment.reason_codes
    assert "SOURCE_PORTAL_MISSING" in assessment.reason_codes
    assert "SOURCE_URL_INVALID" in assessment.reason_codes
    assert "SOURCE_LISTING_ID_MISSING" in assessment.reason_codes
    assert "CAPTURE_DATETIME_INVALID" in assessment.reason_codes
    assert "SOURCE_REFERENCE_DATE_IN_FUTURE" in assessment.reason_codes
    assert "EVIDENCE_TYPE_INVALID" in assessment.reason_codes
    assert "REFERENCE_AREA_MISSING" in assessment.reason_codes
    assert "COORDINATES_OUT_OF_RANGE" in assessment.reason_codes


def test_explains_unconfirmed_transaction_fields() -> None:
    row = valid_transaction()
    row.update(
        {
            "transaction_price_brl": "",
            "usable_market_value_brl": "",
            "market_value_basis": "UNCONFIRMED",
            "rt_review_reference": "",
        }
    )

    assessment = assess_market_dataset([row], policy()).assessments[0]

    assert "TRANSACTION_PRICE_MISSING" in assessment.reason_codes
    assert "USABLE_MARKET_VALUE_MISSING" in assessment.reason_codes
    assert "TRANSACTION_NOT_CONFIRMED" in assessment.reason_codes
    assert "RT_REVIEW_REFERENCE_MISSING" in assessment.reason_codes


@pytest.mark.parametrize(("count", "grade"), [(6, "I"), (8, "II")])
def test_computes_lower_sample_grades(count: int, grade: str) -> None:
    portals = ("SOURCE-A", "SOURCE-B")
    rows = [
        valid_transaction(index, portals[index % 2]) for index in range(1, count + 1)
    ]

    result = assess_market_dataset(rows, policy(variable_count=1))

    assert result.sample_grade == grade
