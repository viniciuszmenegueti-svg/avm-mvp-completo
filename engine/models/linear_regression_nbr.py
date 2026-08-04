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
from scipy.stats import chi2, f as fisher_f, normaltest, shapiro  # type: ignore[import-untyped]
from scipy.stats import t as student_t  # type: ignore[import-untyped]


FloatArray = NDArray[np.float64]


class StatisticalModelError(ValueError):
    """Raised when a statistically defensible model cannot be fitted."""


@dataclass(frozen=True, slots=True)
class NBRGrade:
    sample: str | None
    significance: str | None
    model_significance: str | None
    precision: str | None

    @property
    def automatic_fundamentation_gate(self) -> str | None:
        """Return only the minimum of the three automated table items.

        This is deliberately *not* the overall NBR fundamentation grade.  The
        latter also depends on the remaining scored items in NBR 14653-2,
        technical review and the contents of the complete appraisal report.
        Precision is classified separately by the standard.
        """

        grades = (self.sample, self.significance, self.model_significance)
        if any(grade is None for grade in grades):
            return None
        order = {"I": 1, "II": 2, "III": 3}
        return min(grades, key=order.__getitem__)  # type: ignore[arg-type]

    @property
    def overall(self) -> None:
        """Never claim a complete NBR grade from the automated subset."""

        return None


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
    f_statistic: float
    model_p_value: float
    variance_inflation_factors: tuple[float, ...]
    maximum_vif: float
    normality_test: str
    normality_p_value: float
    breusch_pagan_statistic: float
    breusch_pagan_p_value: float
    durbin_watson: float
    maximum_standardized_residual: float
    maximum_cooks_distance: float
    feature_ranges: tuple[tuple[float, float], ...]
    target_estimate: float
    confidence_level: float
    confidence_lower: float
    confidence_upper: float
    confidence_amplitude_percent: float
    grades: NBRGrade
    economic_gates_passed: bool
    economic_gate_failures: tuple[str, ...]
    residual_variance: float
    design_inverse: tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class LinearPrediction:
    estimate: float
    confidence_lower: float
    confidence_upper: float
    confidence_amplitude_percent: float
    precision_grade: str | None


def classify_precision_grade(amplitude_percent: float) -> str | None:
    """Classify the 80 % confidence interval amplitude for one estimate."""

    if not np.isfinite(amplitude_percent) or amplitude_percent < 0:
        return None
    return _grade_descending(
        amplitude_percent,
        (("III", 30.0), ("II", 40.0), ("I", 50.0)),
    )


def predict_linear_model(
    *,
    coefficients: list[float],
    target: list[float],
    residual_variance: float,
    design_inverse: list[list[float]],
    degrees_of_freedom: int,
    confidence_level: float = 0.80,
) -> LinearPrediction:
    coefficient_array = np.asarray(coefficients, dtype=np.float64)
    target_design = np.concatenate(
        (np.ones(1, dtype=np.float64), np.asarray(target, dtype=np.float64))
    )
    inverse = np.asarray(design_inverse, dtype=np.float64)
    if coefficient_array.shape != target_design.shape:
        raise StatisticalModelError("Coefficients and target do not align.")
    if inverse.shape != (target_design.size, target_design.size):
        raise StatisticalModelError("Stored design inverse has an invalid shape.")
    if residual_variance < 0 or degrees_of_freedom <= 0:
        raise StatisticalModelError("Stored regression diagnostics are invalid.")
    if confidence_level != 0.80:
        raise StatisticalModelError(
            "Contract diagnostics require an 80% confidence interval."
        )
    estimate = float(target_design @ coefficient_array)
    if estimate <= 0:
        raise StatisticalModelError("Model produced a non-positive target estimate.")
    alpha = 1.0 - confidence_level
    critical_t = float(student_t.ppf(1.0 - alpha / 2.0, degrees_of_freedom))
    standard_error = sqrt(
        residual_variance * float(target_design @ inverse @ target_design)
    )
    margin = critical_t * standard_error
    lower = estimate - margin
    upper = estimate + margin
    amplitude_percent = ((upper - lower) / estimate) * 100.0
    return LinearPrediction(
        estimate=estimate,
        confidence_lower=lower,
        confidence_upper=upper,
        confidence_amplitude_percent=amplitude_percent,
        precision_grade=classify_precision_grade(amplitude_percent),
    )


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


def _model_significance_grade(model_p_value: float) -> str | None:
    return _grade_descending(
        model_p_value,
        (("III", 0.01), ("II", 0.02), ("I", 0.05)),
    )


def _variance_inflation_factors(x: FloatArray) -> FloatArray:
    """Return VIF for every regressor without silently regularising the data."""

    _, k = x.shape
    if k == 1:
        return np.ones(1, dtype=np.float64)
    centered = x - np.mean(x, axis=0)
    scales = np.std(centered, axis=0, ddof=1)
    if np.any(np.isclose(scales, 0.0)):
        raise StatisticalModelError("A regressor has no variation.")
    correlation = np.corrcoef(centered / scales, rowvar=False)
    try:
        inverse = np.linalg.inv(correlation)
    except np.linalg.LinAlgError as error:
        raise StatisticalModelError(
            "Regressor correlation matrix is singular."
        ) from error
    return np.diag(inverse).astype(np.float64)


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
    if confidence_level != 0.80:
        raise StatisticalModelError(
            "NBR precision diagnostics in this pipeline require an 80% "
            "confidence interval."
        )
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

    explained_sum_squares = total_sum_squares - sse
    if sse <= 0:
        raise StatisticalModelError(
            "Perfect fit does not provide estimable residual uncertainty."
        )
    f_statistic = (explained_sum_squares / k) / (sse / degrees_of_freedom)
    model_p_value = float(fisher_f.sf(f_statistic, k, degrees_of_freedom))

    vifs = _variance_inflation_factors(x)
    standardized_residuals = residuals / np.sqrt(
        residual_variance * np.maximum(1.0 - leverage, np.finfo(float).eps)
    )
    cooks_distances = (residuals**2 / ((k + 1) * residual_variance)) * (
        leverage / np.maximum((1.0 - leverage) ** 2, np.finfo(float).eps)
    )
    if n <= 5000:
        normality_test = "SHAPIRO_WILK"
        normality_p_value = float(shapiro(residuals).pvalue)
    else:
        normality_test = "DAGOSTINO_K2"
        normality_p_value = float(normaltest(residuals).pvalue)

    squared_residuals = residuals**2
    auxiliary_coefficients, _, _, _ = np.linalg.lstsq(
        design, squared_residuals, rcond=None
    )
    auxiliary_fitted = design @ auxiliary_coefficients
    auxiliary_centered = squared_residuals - float(np.mean(squared_residuals))
    auxiliary_tss = float(auxiliary_centered @ auxiliary_centered)
    if auxiliary_tss <= 0:
        breusch_pagan_statistic = 0.0
        breusch_pagan_p_value = 1.0
    else:
        auxiliary_residuals = squared_residuals - auxiliary_fitted
        auxiliary_sse = float(auxiliary_residuals @ auxiliary_residuals)
        auxiliary_r_squared = max(0.0, 1.0 - auxiliary_sse / auxiliary_tss)
        breusch_pagan_statistic = n * auxiliary_r_squared
        breusch_pagan_p_value = float(chi2.sf(breusch_pagan_statistic, k))
    durbin_watson = float(np.diff(residuals) @ np.diff(residuals) / sse)
    ranges = tuple(
        (float(np.min(x[:, index])), float(np.max(x[:, index]))) for index in range(k)
    )

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
    precision_grade = classify_precision_grade(amplitude_percent)

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
        f_statistic=float(f_statistic),
        model_p_value=model_p_value,
        variance_inflation_factors=tuple(float(value) for value in vifs),
        maximum_vif=float(np.max(vifs)),
        normality_test=normality_test,
        normality_p_value=normality_p_value,
        breusch_pagan_statistic=float(breusch_pagan_statistic),
        breusch_pagan_p_value=breusch_pagan_p_value,
        durbin_watson=durbin_watson,
        maximum_standardized_residual=float(np.max(np.abs(standardized_residuals))),
        maximum_cooks_distance=float(np.max(cooks_distances)),
        feature_ranges=ranges,
        target_estimate=estimate,
        confidence_level=confidence_level,
        confidence_lower=lower,
        confidence_upper=upper,
        confidence_amplitude_percent=amplitude_percent,
        grades=NBRGrade(
            sample=_sample_grade(n, k),
            significance=significance_grade,
            model_significance=_model_significance_grade(model_p_value),
            precision=precision_grade,
        ),
        economic_gates_passed=not failures,
        economic_gate_failures=tuple(failures),
        residual_variance=float(residual_variance),
        design_inverse=tuple(
            tuple(float(value) for value in row) for row in xtx_inverse
        ),
    )
