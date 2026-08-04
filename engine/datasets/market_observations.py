"""Validate market observations before statistical fitting.

Internet listings are evidence of an asking price, not confirmed transactions.
This module preserves every collected row and returns explicit gates instead of
silently cleaning, imputing or converting an offer into a market value.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence
from urllib.parse import urlparse


Row = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class DatasetPolicy:
    """Versionable rules for one city, property type and reference date."""

    city_ibge_code: str
    city: str
    state: str
    property_type: str
    reference_date: date
    variable_count: int
    max_age_days: int = 365
    max_location_accuracy_meters: float = 50.0
    max_source_share: float = 0.50
    required_features: tuple[str, ...] = (
        "private_area_m2",
        "bedrooms",
        "bathrooms",
        "parking_spaces",
    )

    def __post_init__(self) -> None:
        if self.variable_count < 1:
            raise ValueError("variable_count must be positive.")
        if self.max_age_days < 0:
            raise ValueError("max_age_days cannot be negative.")
        if self.max_location_accuracy_meters <= 0:
            raise ValueError("max_location_accuracy_meters must be positive.")
        if not 0 < self.max_source_share <= 1:
            raise ValueError("max_source_share must be between zero and one.")


@dataclass(frozen=True, slots=True)
class ObservationAssessment:
    observation_id: str
    collection_valid: bool
    model_eligible: bool
    reason_codes: tuple[str, ...]
    duplicate_of: str | None
    price_per_m2_brl: float | None
    source_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "collection_valid": self.collection_valid,
            "model_eligible": self.model_eligible,
            "reason_codes": list(self.reason_codes),
            "duplicate_of": self.duplicate_of,
            "price_per_m2_brl": self.price_per_m2_brl,
            "source_fingerprint": self.source_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class DatasetAssessment:
    assessments: tuple[ObservationAssessment, ...]
    total_count: int
    collection_valid_count: int
    model_eligible_count: int
    excluded_count: int
    source_counts: dict[str, int]
    maximum_source_share: float | None
    source_distribution_passed: bool
    sample_grade: str | None
    required_sample_sizes: dict[str, int]
    dataset_sha256: str
    model_ready: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "total_count": self.total_count,
            "collection_valid_count": self.collection_valid_count,
            "model_eligible_count": self.model_eligible_count,
            "excluded_count": self.excluded_count,
            "source_counts": self.source_counts,
            "maximum_source_share": self.maximum_source_share,
            "source_distribution_passed": self.source_distribution_passed,
            "sample_grade": self.sample_grade,
            "required_sample_sizes": self.required_sample_sizes,
            "dataset_sha256": self.dataset_sha256,
            "model_ready": self.model_ready,
            "assessments": [item.as_dict() for item in self.assessments],
        }


def assess_market_dataset(
    rows: Sequence[Row],
    policy: DatasetPolicy,
) -> DatasetAssessment:
    """Assess all rows without dropping rejected or duplicate observations."""

    seen_observations: set[str] = set()
    seen_properties: dict[str, str] = {}
    assessments: list[ObservationAssessment] = []

    for position, row in enumerate(rows, start=1):
        observation_id = _text(row, "observation_id") or f"ROW-{position:06d}"
        reasons: list[str] = []
        collection_reasons: list[str] = []

        if observation_id in seen_observations:
            _add_reason(reasons, "OBSERVATION_ID_DUPLICATE")
            _add_reason(collection_reasons, "OBSERVATION_ID_DUPLICATE")
        seen_observations.add(observation_id)

        _validate_source(row, reasons, collection_reasons)
        _validate_scope(row, policy, reasons, collection_reasons)
        _validate_reference_date(row, policy, reasons)
        price = _validate_prices(row, reasons, collection_reasons)
        area = _validate_features(row, policy, reasons, collection_reasons)
        _validate_location(row, policy, reasons)
        _validate_evidence(row, reasons)

        property_fingerprint = _property_fingerprint(row)
        duplicate_of = seen_properties.get(property_fingerprint)
        if duplicate_of is not None:
            _add_reason(reasons, "POTENTIAL_DUPLICATE")
        elif property_fingerprint:
            seen_properties[property_fingerprint] = observation_id

        source_fingerprint = _source_fingerprint(row)
        price_per_m2 = None
        if price is not None and area is not None and area > 0:
            price_per_m2 = round(price / area, 2)

        assessments.append(
            ObservationAssessment(
                observation_id=observation_id,
                collection_valid=not collection_reasons,
                model_eligible=not reasons,
                reason_codes=tuple(reasons),
                duplicate_of=duplicate_of,
                price_per_m2_brl=price_per_m2,
                source_fingerprint=source_fingerprint,
            )
        )

    eligible_indexes = [
        index
        for index, assessment in enumerate(assessments)
        if assessment.model_eligible
    ]
    source_counts: dict[str, int] = {}
    for index in eligible_indexes:
        portal = _normalized(_text(rows[index], "source_portal")) or "UNKNOWN"
        source_counts[portal] = source_counts.get(portal, 0) + 1

    eligible_count = len(eligible_indexes)
    maximum_source_share = None
    if eligible_count:
        maximum_source_share = max(source_counts.values()) / eligible_count
    source_distribution_passed = (
        maximum_source_share is not None
        and maximum_source_share <= policy.max_source_share
    )

    required_sizes = {
        "I": 3 * (policy.variable_count + 1),
        "II": 4 * (policy.variable_count + 1),
        "III": 6 * (policy.variable_count + 1),
    }
    sample_grade = _sample_grade(eligible_count, required_sizes)
    collection_valid_count = sum(item.collection_valid for item in assessments)
    dataset_hash = _dataset_hash(rows, policy)

    return DatasetAssessment(
        assessments=tuple(assessments),
        total_count=len(rows),
        collection_valid_count=collection_valid_count,
        model_eligible_count=eligible_count,
        excluded_count=len(rows) - eligible_count,
        source_counts=source_counts,
        maximum_source_share=maximum_source_share,
        source_distribution_passed=source_distribution_passed,
        sample_grade=sample_grade,
        required_sample_sizes=required_sizes,
        dataset_sha256=dataset_hash,
        model_ready=sample_grade is not None and source_distribution_passed,
    )


def _validate_source(
    row: Row,
    reasons: list[str],
    collection_reasons: list[str],
) -> None:
    portal = _text(row, "source_portal")
    url = _text(row, "source_url")
    listing_id = _text(row, "source_listing_id")
    captured_at = _parse_datetime(_text(row, "captured_at"))

    if not portal:
        _add_both(reasons, collection_reasons, "SOURCE_PORTAL_MISSING")
    if not _is_valid_https_url(url):
        _add_both(reasons, collection_reasons, "SOURCE_URL_INVALID")
    if not listing_id:
        _add_both(reasons, collection_reasons, "SOURCE_LISTING_ID_MISSING")
    if _boolean(row, "source_stable_url") is not True:
        _add_reason(reasons, "SOURCE_URL_NOT_STABLE")
    if captured_at is None:
        _add_both(reasons, collection_reasons, "CAPTURE_DATETIME_INVALID")


def _validate_scope(
    row: Row,
    policy: DatasetPolicy,
    reasons: list[str],
    collection_reasons: list[str],
) -> None:
    checks = (
        ("city_ibge_code", policy.city_ibge_code, "IBGE_CODE_OUT_OF_SCOPE"),
        ("city", policy.city, "CITY_OUT_OF_SCOPE"),
        ("state", policy.state, "STATE_OUT_OF_SCOPE"),
        ("property_type", policy.property_type, "PROPERTY_TYPE_OUT_OF_SCOPE"),
    )
    for field, expected, reason in checks:
        if _normalized(_text(row, field)) != _normalized(expected):
            _add_both(reasons, collection_reasons, reason)


def _validate_reference_date(
    row: Row,
    policy: DatasetPolicy,
    reasons: list[str],
) -> None:
    reference = _parse_date(_text(row, "source_reference_date"))
    precision = _text(row, "source_reference_date_precision")
    if reference is None:
        _add_reason(reasons, "SOURCE_REFERENCE_DATE_MISSING")
        return
    if _normalized(precision) != "EXACT":
        _add_reason(reasons, "SOURCE_REFERENCE_DATE_NOT_EXACT")
    age_days = (policy.reference_date - reference).days
    if age_days < 0:
        _add_reason(reasons, "SOURCE_REFERENCE_DATE_IN_FUTURE")
    elif age_days > policy.max_age_days:
        _add_reason(reasons, "SOURCE_REFERENCE_DATE_STALE")


def _validate_prices(
    row: Row,
    reasons: list[str],
    collection_reasons: list[str],
) -> float | None:
    evidence_type = _normalized(_text(row, "evidence_type"))
    asking = _positive_float(row, "asking_price_brl")
    transaction = _positive_float(row, "transaction_price_brl")
    usable = _positive_float(row, "usable_market_value_brl")
    basis = _normalized(_text(row, "market_value_basis"))

    if evidence_type == "OFFER":
        if asking is None:
            _add_both(reasons, collection_reasons, "ASKING_PRICE_MISSING")
        if usable is None:
            _add_reason(reasons, "USABLE_MARKET_VALUE_MISSING")
        if basis != "RT_APPROVED_OFFER_ADJUSTMENT":
            _add_reason(reasons, "OFFER_ADJUSTMENT_NOT_RT_APPROVED")
        if not _text(row, "market_adjustment_reference"):
            _add_reason(reasons, "OFFER_ADJUSTMENT_REFERENCE_MISSING")
        if not _text(row, "rt_review_reference"):
            _add_reason(reasons, "RT_REVIEW_REFERENCE_MISSING")
    elif evidence_type == "TRANSACTION":
        if transaction is None:
            _add_both(reasons, collection_reasons, "TRANSACTION_PRICE_MISSING")
        if usable is None:
            _add_reason(reasons, "USABLE_MARKET_VALUE_MISSING")
        if basis != "CONFIRMED_TRANSACTION":
            _add_reason(reasons, "TRANSACTION_NOT_CONFIRMED")
        if not _text(row, "rt_review_reference"):
            _add_reason(reasons, "RT_REVIEW_REFERENCE_MISSING")
    else:
        _add_both(reasons, collection_reasons, "EVIDENCE_TYPE_INVALID")

    return usable


def _validate_features(
    row: Row,
    policy: DatasetPolicy,
    reasons: list[str],
    collection_reasons: list[str],
) -> float | None:
    area_field = {
        "APARTMENT": "private_area_m2",
        "HOUSE": "built_area_m2",
        "LAND": "land_area_m2",
    }.get(_normalized(policy.property_type))
    area = _positive_float(row, area_field) if area_field else None
    if area is None:
        _add_both(reasons, collection_reasons, "REFERENCE_AREA_MISSING")

    for field in policy.required_features:
        if field.endswith("_m2"):
            valid = _positive_float(row, field) is not None
        else:
            valid = _nonnegative_float(row, field) is not None
        if not valid:
            _add_reason(reasons, f"REQUIRED_FEATURE_MISSING:{field}")

    street = _text(row, "street")
    number = _text(row, "number")
    postal_code = _text(row, "postal_code")
    if not street or _normalized(street) in {"HIDDEN", "UNAVAILABLE"}:
        _add_reason(reasons, "STREET_MISSING")
    if not number or _normalized(number) in {"0", "SN", "S/N", "HIDDEN"}:
        _add_reason(reasons, "ADDRESS_NUMBER_MISSING")
    if not re.fullmatch(r"\d{5}-?\d{3}", postal_code):
        _add_reason(reasons, "POSTAL_CODE_MISSING_OR_INVALID")
    return area


def _validate_location(
    row: Row,
    policy: DatasetPolicy,
    reasons: list[str],
) -> None:
    latitude = _finite_float(row, "latitude")
    longitude = _finite_float(row, "longitude")
    accuracy = _nonnegative_float(row, "location_accuracy_meters")
    if latitude is None or longitude is None:
        _add_reason(reasons, "COORDINATES_MISSING")
    elif not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        _add_reason(reasons, "COORDINATES_OUT_OF_RANGE")
    if accuracy is None:
        _add_reason(reasons, "LOCATION_ACCURACY_MISSING")
    elif accuracy > policy.max_location_accuracy_meters:
        _add_reason(reasons, "LOCATION_ACCURACY_ABOVE_LIMIT")
    if not _text(row, "geocoding_method"):
        _add_reason(reasons, "GEOCODING_METHOD_MISSING")
    if not _text(row, "geocoding_evidence_reference"):
        _add_reason(reasons, "GEOCODING_EVIDENCE_MISSING")
    if not _text(row, "geocoding_verified_by"):
        _add_reason(reasons, "GEOCODING_VERIFIER_MISSING")


def _validate_evidence(row: Row, reasons: list[str]) -> None:
    if not _text(row, "evidence_reference"):
        _add_reason(reasons, "EVIDENCE_REFERENCE_MISSING")
    evidence_hash = _text(row, "evidence_sha256")
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", evidence_hash):
        _add_reason(reasons, "EVIDENCE_SHA256_MISSING_OR_INVALID")


def _property_fingerprint(row: Row) -> str:
    street = _normalized(_text(row, "street"))
    number = _normalized(_text(row, "number"))
    property_type = _normalized(_text(row, "property_type"))
    area_field = {
        "APARTMENT": "private_area_m2",
        "HOUSE": "built_area_m2",
        "LAND": "land_area_m2",
    }.get(property_type)
    area = _positive_float(row, area_field) if area_field else None
    if not street or not number or area is None or number in {"0", "SN", "S/N"}:
        return ""
    values = (
        _normalized(_text(row, "city_ibge_code")),
        property_type,
        street,
        number,
        f"{area:.1f}",
        _numeric_key(row, "bedrooms"),
        _numeric_key(row, "bathrooms"),
        _numeric_key(row, "parking_spaces"),
    )
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _source_fingerprint(row: Row) -> str:
    values = (
        _normalized(_text(row, "source_portal")),
        _text(row, "source_listing_id"),
        _text(row, "source_url"),
        _text(row, "captured_at"),
    )
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _dataset_hash(rows: Sequence[Row], policy: DatasetPolicy) -> str:
    canonical = {
        "policy": {
            "city_ibge_code": policy.city_ibge_code,
            "city": policy.city,
            "state": policy.state,
            "property_type": policy.property_type,
            "reference_date": policy.reference_date.isoformat(),
            "variable_count": policy.variable_count,
            "max_age_days": policy.max_age_days,
            "max_location_accuracy_meters": policy.max_location_accuracy_meters,
            "max_source_share": policy.max_source_share,
            "required_features": list(policy.required_features),
        },
        "rows": [
            {key: str(value) for key, value in sorted(row.items())} for row in rows
        ],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sample_grade(count: int, required: Mapping[str, int]) -> str | None:
    if count >= required["III"]:
        return "III"
    if count >= required["II"]:
        return "II"
    if count >= required["I"]:
        return "I"
    return None


def _is_valid_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname)


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _text(row: Row, field: str | None) -> str:
    if field is None:
        return ""
    value = row.get(field, "")
    return "" if value is None else str(value).strip()


def _finite_float(row: Row, field: str | None) -> float | None:
    text = _text(row, field)
    if not text:
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _positive_float(row: Row, field: str | None) -> float | None:
    value = _finite_float(row, field)
    return value if value is not None and value > 0 else None


def _nonnegative_float(row: Row, field: str | None) -> float | None:
    value = _finite_float(row, field)
    return value if value is not None and value >= 0 else None


def _boolean(row: Row, field: str) -> bool | None:
    value = _normalized(_text(row, field))
    if value in {"TRUE", "1", "YES", "SIM"}:
        return True
    if value in {"FALSE", "0", "NO", "NAO"}:
        return False
    return None


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(ascii_value.upper().split())


def _numeric_key(row: Row, field: str) -> str:
    value = _nonnegative_float(row, field)
    return "" if value is None else f"{value:.2f}"


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _add_both(
    reasons: list[str],
    collection_reasons: list[str],
    reason: str,
) -> None:
    _add_reason(reasons, reason)
    _add_reason(collection_reasons, reason)
