"""Deterministic OLS diagnostics used by the NBR-oriented AVM pipeline.

This module does not claim that a fitted model is homologated. It implements
the reproducible calculations needed by a Responsible Technician to review a
candidate: OLS coefficients, significance, PRESS/LOOCV, confidence interval
and the objective sample-size/precision grade gates described by NBR 14653-2.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
from numpy.typing import NDArray
from scipy.stats import t as student_t  # type: ignore[import-untyped]


FloatArray = NDArray[np.float64]


class StatisticalModelError(ValueError):
    """Raised when a statistically defensible model cannot be fitted."""


@dataclass(frozen=True, slots=True)
class NBRGrade:
    sample: str | None
    significance: str | None
    precision: str | None

    @property
    def overall(self) -> str | None:
        grades = (self.sample, self.significance, self.precision)
        if any(grade is None for grade in grades):
            return None
        order = {"I": 1, "II": 2, "III": 3}
        return min(grades, key=order.__getitem__)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class LinearModelDiagnostics:
    feature_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    coefficient_p_values: tuple[float, ...]
    observation_count: int
    variable_count: int
    degrees_of_freedom: int
    r_squared: float
    adjusted_r_squared: float
    correlation_coefficient: float
    residual_standard_error: float
    press: float
    loocv_rmse: float
    maximum_regressor_p_value: float
    target_estimate: float
    confidence_level: float
    confidence_lower: float
    confidence_upper: float
    confidence_amplitude_percent: float
    grades: NBRGrade
    economic_gates_passed: bool
    economic_gate_failures: tuple[str, ...]


def _grade_descending(
    value: float,
    thresholds: tuple[tuple[str, float], ...],
) -> str | None:
    for grade, maximum in thresholds:
        if value <= maximum:
            return grade
    return None


def _sample_grade(observation_count: int, variable_count: int) -> str | None:
    multiplier = observation_count / (variable_count + 1)
    if multiplier >= 6:
        return "III"
    if multiplier >= 4:
        return "II"
    if multiplier >= 3:
        return "I"
    return None


def fit_linear_model(
    *,
    feature_names: list[str],
    observations: list[list[float]],
    values: list[float],
    target: list[float],
    expected_signs: dict[str, int] | None = None,
    confidence_level: float = 0.80,
) -> LinearModelDiagnostics:
    """Fit a full-rank OLS model and return audit-ready diagnostics.

    ``expected_signs`` accepts ``1`` for an expected positive coefficient and
    ``-1`` for an expected negative coefficient. These are economic coherence
    gates, never silent coefficient manipulation.
    """

    x = np.asarray(observations, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)

    if x.ndim != 2 or y.ndim != 1:
        raise StatisticalModelError(
            "Observations must be a matrix and values a vector."
        )
    n, k = x.shape
    if len(feature_names) != k or target_array.shape != (k,):
        raise StatisticalModelError(
            "Feature names, observations and target do not align."
        )
    if y.shape != (n,):
        raise StatisticalModelError("One market value is required per observation.")
    if n <= k + 1:
        raise StatisticalModelError("Insufficient degrees of freedom for regression.")
    if not 0 < confidence_level < 1:
        raise StatisticalModelError("Confidence level must be between zero and one.")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise StatisticalModelError("Observations and values must be finite.")
    if not np.all(np.isfinite(target_array)):
        raise StatisticalModelError("Target values must be finite.")
    if np.any(y <= 0):
        raise StatisticalModelError("Market values must be positive.")

    design = np.column_stack((np.ones(n, dtype=np.float64), x))
    if np.linalg.matrix_rank(design) != k + 1:
        raise StatisticalModelError("Regression design matrix is rank deficient.")

    coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coefficients
    residuals = y - fitted
    degrees_of_freedom = n - (k + 1)
    sse = float(residuals @ residuals)
    centered = y - float(np.mean(y))
    total_sum_squares = float(centered @ centered)
    if total_sum_squares <= 0:
        raise StatisticalModelError("Market values have no variation.")

    residual_variance = sse / degrees_of_freedom
    xtx_inverse = np.linalg.inv(design.T @ design)
    standard_errors = np.sqrt(np.diag(xtx_inverse) * residual_variance)
    with np.errstate(divide="ignore", invalid="ignore"):
        t_statistics = coefficients / standard_errors
    p_values = 2 * student_t.sf(np.abs(t_statistics), degrees_of_freedom)

    leverage = np.einsum("ij,jk,ik->i", design, xtx_inverse, design)
    if np.any(np.isclose(leverage, 1.0)):
        raise StatisticalModelError("LOOCV is undefined for unit leverage.")
    deleted_residuals = residuals / (1.0 - leverage)
    press = float(deleted_residuals @ deleted_residuals)

    r_squared = 1.0 - (sse / total_sum_squares)
    adjusted_r_squared = 1.0 - ((1.0 - r_squared) * (n - 1) / degrees_of_freedom)
    correlation = sqrt(max(0.0, r_squared))

    target_design = np.concatenate(([1.0], target_array))
    estimate = float(target_design @ coefficients)
    if estimate <= 0:
        raise StatisticalModelError("Model produced a non-positive target estimate.")

    alpha = 1.0 - confidence_level
    critical_t = float(student_t.ppf(1.0 - alpha / 2.0, degrees_of_freedom))
    mean_standard_error = sqrt(
        residual_variance * float(target_design @ xtx_inverse @ target_design)
    )
    margin = critical_t * mean_standard_error
    lower = estimate - margin
    upper = estimate + margin
    amplitude_percent = ((upper - lower) / estimate) * 100.0

    regressor_p_values = p_values[1:]
    maximum_regressor_p_value = float(np.max(regressor_p_values))
    significance_grade = _grade_descending(
        maximum_regressor_p_value,
        (("III", 0.10), ("II", 0.20), ("I", 0.30)),
    )
    precision_grade = _grade_descending(
        amplitude_percent,
        (("III", 30.0), ("II", 40.0), ("I", 50.0)),
    )

    failures: list[str] = []
    for feature_name, expected_sign in (expected_signs or {}).items():
        if expected_sign not in {-1, 1}:
            raise StatisticalModelError("Expected signs must be either -1 or 1.")
        try:
            index = feature_names.index(feature_name) + 1
        except ValueError as exc:
            raise StatisticalModelError(
                f"Economic gate references unknown feature: {feature_name}."
            ) from exc
        coefficient = float(coefficients[index])
        if coefficient == 0 or (coefficient > 0) != (expected_sign > 0):
            failures.append(
                f"{feature_name}: expected sign {expected_sign:+d}, "
                f"obtained {coefficient:+.6g}"
            )

    return LinearModelDiagnostics(
        feature_names=tuple(feature_names),
        coefficients=tuple(float(value) for value in coefficients),
        coefficient_p_values=tuple(float(value) for value in p_values),
        observation_count=n,
        variable_count=k,
        degrees_of_freedom=degrees_of_freedom,
        r_squared=float(r_squared),
        adjusted_r_squared=float(adjusted_r_squared),
        correlation_coefficient=correlation,
        residual_standard_error=sqrt(residual_variance),
        press=press,
        loocv_rmse=sqrt(press / n),
        maximum_regressor_p_value=maximum_regressor_p_value,
        target_estimate=estimate,
        confidence_level=confidence_level,
        confidence_lower=lower,
        confidence_upper=upper,
        confidence_amplitude_percent=amplitude_percent,
        grades=NBRGrade(
            sample=_sample_grade(n, k),
            significance=significance_grade,
            precision=precision_grade,
        ),
        economic_gates_passed=not failures,
        economic_gate_failures=tuple(failures),
    )
