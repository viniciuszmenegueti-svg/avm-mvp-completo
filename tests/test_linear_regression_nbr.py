import pytest

from engine.models.linear_regression_nbr import (
    StatisticalModelError,
    fit_linear_model,
    predict_linear_model,
)


def market_sample() -> tuple[list[list[float]], list[float]]:
    observations: list[list[float]] = []
    values: list[float] = []
    noise = (-9000, 3000, 7000, -4000, 2000)
    for index in range(30):
        area = 45.0 + index * 2.5
        parking = float(index % 3)
        observations.append([area, parking])
        values.append(
            110_000.0 + 6_200.0 * area + 28_000.0 * parking + noise[index % 5]
        )
    return observations, values


def test_fits_auditable_linear_model_with_press_and_nbr_grades() -> None:
    observations, values = market_sample()
    result = fit_linear_model(
        feature_names=["area_m2", "parking_spaces"],
        observations=observations,
        values=values,
        target=[82.0, 1.0],
        expected_signs={"area_m2": 1, "parking_spaces": 1},
    )

    assert result.observation_count == 30
    assert result.variable_count == 2
    assert result.grades.sample == "III"
    assert result.grades.significance == "III"
    assert result.grades.model_significance == "III"
    assert result.grades.automatic_fundamentation_gate == "III"
    assert result.grades.overall is None
    assert result.target_estimate > 0
    assert result.confidence_lower < result.target_estimate < result.confidence_upper
    assert result.press > 0
    assert result.loocv_rmse > 0
    assert result.economic_gates_passed is True
    assert result.economic_gate_failures == ()
    assert result.f_statistic > 0
    assert 0 <= result.model_p_value <= 0.01
    assert result.maximum_vif >= 1
    assert len(result.feature_ranges) == 2


def test_reports_failed_economic_sign_gate_without_changing_model() -> None:
    observations, values = market_sample()
    result = fit_linear_model(
        feature_names=["area_m2", "parking_spaces"],
        observations=observations,
        values=values,
        target=[82.0, 1.0],
        expected_signs={"area_m2": -1},
    )

    assert result.economic_gates_passed is False
    assert result.economic_gate_failures[0].startswith("area_m2:")
    assert result.coefficients[1] > 0


def test_rejects_rank_deficient_sample() -> None:
    with pytest.raises(StatisticalModelError, match="rank deficient"):
        fit_linear_model(
            feature_names=["x1", "x2"],
            observations=[[1, 2], [2, 4], [3, 6], [4, 8], [5, 10]],
            values=[10, 20, 30, 40, 50],
            target=[6, 12],
        )


def test_prediction_classifies_precision_for_the_specific_property() -> None:
    observations, values = market_sample()
    result = fit_linear_model(
        feature_names=["area_m2", "parking_spaces"],
        observations=observations,
        values=values,
        target=[82.0, 1.0],
        expected_signs={"area_m2": 1, "parking_spaces": 1},
    )

    prediction = predict_linear_model(
        coefficients=list(result.coefficients),
        target=[82.0, 1.0],
        residual_variance=result.residual_variance,
        design_inverse=[list(row) for row in result.design_inverse],
        degrees_of_freedom=result.degrees_of_freedom,
    )

    assert prediction.precision_grade in {"I", "II", "III"}


def test_rejects_confidence_level_other_than_eighty_percent() -> None:
    observations, values = market_sample()
    with pytest.raises(StatisticalModelError, match="80%"):
        fit_linear_model(
            feature_names=["area_m2", "parking_spaces"],
            observations=observations,
            values=values,
            target=[82.0, 1.0],
            expected_signs={"area_m2": 1, "parking_spaces": 1},
            confidence_level=0.95,
        )
