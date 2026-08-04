"""Reproducible exploratory backtest for a stored linear AVM model.

The decisions produced here are quality-control labels, not contractual or
professional approval. Formal acceptance requires an independent validation
base, an approved policy and review by the Responsible Technician (RT).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from math import sqrt
from statistics import mean, median
import unicodedata

from engine.models.linear_regression_nbr import (
    StatisticalModelError,
    predict_linear_model,
)


class BacktestStatus(StrEnum):
    APPROVED_EXPLORATORY = "APPROVED_EXPLORATORY"
    REJECTED_EXPLORATORY = "REJECTED_EXPLORATORY"
    INCONCLUSIVE_INVALID_INPUT = "INCONCLUSIVE_INVALID_INPUT"


@dataclass(frozen=True, slots=True)
class BacktestObservation:
    validation_id: str
    features: tuple[float, ...]
    reference_value_brl: float
    source_reference: str
    neighborhood: str = "NAO_INFORMADO"
    reference_value_basis: str = "ASKING_PRICE"


@dataclass(frozen=True, slots=True)
class BacktestResult:
    validation_id: str
    source_reference: str
    neighborhood: str
    reference_value_basis: str
    reference_value_brl: float
    estimated_value_brl: float | None
    confidence_level: float
    confidence_lower_brl: float | None
    confidence_upper_brl: float | None
    confidence_amplitude_percent: float | None
    precision_grade: str | None
    signed_error_brl: float | None
    absolute_error_brl: float | None
    signed_percentage_error: float | None
    absolute_percentage_error: float | None
    reference_inside_ic80: bool | None
    extrapolation: bool
    status: BacktestStatus
    reasons: tuple[str, ...]
    formal_approval: bool = False

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["status"] = self.status.value
        value["reasons"] = "|".join(self.reasons)
        return value


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    observation_count: int
    conclusive_count: int
    approved_exploratory_count: int
    rejected_exploratory_count: int
    inconclusive_count: int
    mean_absolute_error_brl: float | None
    root_mean_squared_error_brl: float | None
    median_absolute_percentage_error: float | None
    mean_signed_percentage_error: float | None
    ic80_empirical_coverage: float | None
    exploratory_approval_rate: float | None
    external_independence: bool = False
    formal_homologation: bool = False
    decision_basis: str = "IC80_COVERAGE_PRECISION_AND_TRAINING_DOMAIN"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _required_conclusive_metric(value: float | None, field_name: str) -> float:
    assert value is not None, (
        f"Resultado conclusivo sem a métrica obrigatória {field_name}."
    )
    return value


def _is_extrapolation(
    features: tuple[float, ...], feature_ranges: tuple[tuple[float, float], ...]
) -> bool:
    return any(
        value < lower or value > upper
        for value, (lower, upper) in zip(features, feature_ranges, strict=True)
    )


def _normalized_segment(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return (
        "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        .strip()
        .upper()
    )


def run_exploratory_backtest(
    *,
    observations: list[BacktestObservation],
    feature_names: tuple[str, ...],
    coefficients: tuple[float, ...],
    residual_variance: float,
    design_inverse: tuple[tuple[float, ...], ...],
    degrees_of_freedom: int,
    feature_ranges: tuple[tuple[float, float], ...],
    allowed_neighborhoods: tuple[str, ...] | None = None,
) -> tuple[list[BacktestResult], BacktestSummary]:
    """Evaluate validation observations without claiming formal homologation."""

    if not feature_names:
        raise ValueError("At least one feature is required.")
    if len(feature_ranges) != len(feature_names):
        raise ValueError("Feature ranges do not align with feature names.")

    results: list[BacktestResult] = []
    for observation in observations:
        if len(observation.features) != len(feature_names):
            raise ValueError(
                f"{observation.validation_id}: feature vector does not align."
            )
        if observation.reference_value_brl <= 0:
            results.append(
                BacktestResult(
                    validation_id=observation.validation_id,
                    source_reference=observation.source_reference,
                    neighborhood=observation.neighborhood,
                    reference_value_basis=observation.reference_value_basis,
                    reference_value_brl=observation.reference_value_brl,
                    estimated_value_brl=None,
                    confidence_level=0.80,
                    confidence_lower_brl=None,
                    confidence_upper_brl=None,
                    confidence_amplitude_percent=None,
                    precision_grade=None,
                    signed_error_brl=None,
                    absolute_error_brl=None,
                    signed_percentage_error=None,
                    absolute_percentage_error=None,
                    reference_inside_ic80=None,
                    extrapolation=False,
                    status=BacktestStatus.INCONCLUSIVE_INVALID_INPUT,
                    reasons=("NON_POSITIVE_REFERENCE_VALUE",),
                )
            )
            continue

        numeric_extrapolation = _is_extrapolation(observation.features, feature_ranges)
        allowed_segments = {
            _normalized_segment(value) for value in (allowed_neighborhoods or ())
        }
        geographic_extrapolation = bool(allowed_segments) and (
            _normalized_segment(observation.neighborhood) not in allowed_segments
        )
        extrapolation = numeric_extrapolation or geographic_extrapolation
        try:
            prediction = predict_linear_model(
                coefficients=list(coefficients),
                target=list(observation.features),
                residual_variance=residual_variance,
                design_inverse=[list(row) for row in design_inverse],
                degrees_of_freedom=degrees_of_freedom,
            )
        except StatisticalModelError as error:
            results.append(
                BacktestResult(
                    validation_id=observation.validation_id,
                    source_reference=observation.source_reference,
                    neighborhood=observation.neighborhood,
                    reference_value_basis=observation.reference_value_basis,
                    reference_value_brl=observation.reference_value_brl,
                    estimated_value_brl=None,
                    confidence_level=0.80,
                    confidence_lower_brl=None,
                    confidence_upper_brl=None,
                    confidence_amplitude_percent=None,
                    precision_grade=None,
                    signed_error_brl=None,
                    absolute_error_brl=None,
                    signed_percentage_error=None,
                    absolute_percentage_error=None,
                    reference_inside_ic80=None,
                    extrapolation=extrapolation,
                    status=BacktestStatus.INCONCLUSIVE_INVALID_INPUT,
                    reasons=(f"PREDICTION_ERROR:{error}",),
                )
            )
            continue

        signed_error = prediction.estimate - observation.reference_value_brl
        signed_percentage_error = signed_error / observation.reference_value_brl
        inside = (
            prediction.confidence_lower
            <= observation.reference_value_brl
            <= prediction.confidence_upper
        )
        reasons: list[str] = []
        if numeric_extrapolation:
            reasons.append("EXTRAPOLATION")
        if geographic_extrapolation:
            reasons.append("GEOGRAPHIC_SEGMENT_OUTSIDE_TRAINING_DOMAIN")
        if prediction.precision_grade is None:
            reasons.append("IC80_AMPLITUDE_ABOVE_50_PERCENT")
        if not inside:
            reasons.append("REFERENCE_OUTSIDE_IC80")
        status = (
            BacktestStatus.APPROVED_EXPLORATORY
            if not reasons
            else BacktestStatus.REJECTED_EXPLORATORY
        )
        results.append(
            BacktestResult(
                validation_id=observation.validation_id,
                source_reference=observation.source_reference,
                neighborhood=observation.neighborhood,
                reference_value_basis=observation.reference_value_basis,
                reference_value_brl=observation.reference_value_brl,
                estimated_value_brl=prediction.estimate,
                confidence_level=0.80,
                confidence_lower_brl=prediction.confidence_lower,
                confidence_upper_brl=prediction.confidence_upper,
                confidence_amplitude_percent=prediction.confidence_amplitude_percent,
                precision_grade=prediction.precision_grade,
                signed_error_brl=signed_error,
                absolute_error_brl=abs(signed_error),
                signed_percentage_error=signed_percentage_error,
                absolute_percentage_error=abs(signed_percentage_error),
                reference_inside_ic80=inside,
                extrapolation=extrapolation,
                status=status,
                reasons=tuple(reasons),
            )
        )

    conclusive = [
        result
        for result in results
        if result.status != BacktestStatus.INCONCLUSIVE_INVALID_INPUT
    ]
    approved = [
        result
        for result in conclusive
        if result.status == BacktestStatus.APPROVED_EXPLORATORY
    ]
    errors = [
        _required_conclusive_metric(result.signed_error_brl, "signed_error_brl")
        for result in conclusive
    ]
    absolute_errors = [
        _required_conclusive_metric(result.absolute_error_brl, "absolute_error_brl")
        for result in conclusive
    ]
    absolute_percentage_errors = [
        _required_conclusive_metric(
            result.absolute_percentage_error,
            "absolute_percentage_error",
        )
        for result in conclusive
    ]
    signed_percentage_errors = [
        _required_conclusive_metric(
            result.signed_percentage_error,
            "signed_percentage_error",
        )
        for result in conclusive
    ]
    summary = BacktestSummary(
        observation_count=len(results),
        conclusive_count=len(conclusive),
        approved_exploratory_count=len(approved),
        rejected_exploratory_count=len(conclusive) - len(approved),
        inconclusive_count=len(results) - len(conclusive),
        mean_absolute_error_brl=mean(absolute_errors) if conclusive else None,
        root_mean_squared_error_brl=(
            sqrt(mean([error**2 for error in errors])) if conclusive else None
        ),
        median_absolute_percentage_error=(
            median(absolute_percentage_errors) if conclusive else None
        ),
        mean_signed_percentage_error=(
            mean(signed_percentage_errors) if conclusive else None
        ),
        ic80_empirical_coverage=(
            mean([bool(result.reference_inside_ic80) for result in conclusive])
            if conclusive
            else None
        ),
        exploratory_approval_rate=(
            len(approved) / len(conclusive) if conclusive else None
        ),
    )
    return results, summary
