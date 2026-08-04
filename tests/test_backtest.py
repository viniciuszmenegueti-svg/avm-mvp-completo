from __future__ import annotations

from engine.models.linear_regression_nbr import fit_linear_model, predict_linear_model
from engine.validation.backtest import (
    BacktestObservation,
    BacktestStatus,
    run_exploratory_backtest,
)


def _model():  # type: ignore[no-untyped-def]
    observations: list[list[float]] = []
    values: list[float] = []
    for index in range(40):
        area = 50.0 + index * 2.0
        parking = float(index % 3)
        noise = (-6000.0, 3000.0, 5000.0, -2000.0)[index % 4]
        observations.append([area, parking])
        values.append(100_000.0 + area * 6_000.0 + parking * 25_000.0 + noise)
    return fit_linear_model(
        feature_names=["area", "parking"],
        observations=observations,
        values=values,
        target=[85.0, 1.0],
        expected_signs={"area": 1, "parking": 1},
    )


def _run(observations: list[BacktestObservation]):  # type: ignore[no-untyped-def]
    model = _model()
    return run_exploratory_backtest(
        observations=observations,
        feature_names=model.feature_names,
        coefficients=model.coefficients,
        residual_variance=model.residual_variance,
        design_inverse=model.design_inverse,
        degrees_of_freedom=model.degrees_of_freedom,
        feature_ranges=model.feature_ranges,
    )


def test_approves_only_inside_domain_precision_and_ic80() -> None:
    model = _model()
    prediction = predict_linear_model(
        coefficients=list(model.coefficients),
        target=[85.0, 1.0],
        residual_variance=model.residual_variance,
        design_inverse=[list(row) for row in model.design_inverse],
        degrees_of_freedom=model.degrees_of_freedom,
    )
    results, summary = _run(
        [
            BacktestObservation(
                validation_id="VAL-1",
                features=(85.0, 1.0),
                reference_value_brl=prediction.estimate,
                source_reference="evidence://1",
            )
        ]
    )

    assert results[0].status == BacktestStatus.APPROVED_EXPLORATORY
    assert results[0].formal_approval is False
    assert summary.approved_exploratory_count == 1
    assert summary.formal_homologation is False
    assert summary.external_independence is False


def test_rejects_reference_outside_ic80_and_extrapolation() -> None:
    results, summary = _run(
        [
            BacktestObservation(
                validation_id="VAL-2",
                features=(500.0, 1.0),
                reference_value_brl=10_000_000.0,
                source_reference="evidence://2",
            )
        ]
    )

    assert results[0].status == BacktestStatus.REJECTED_EXPLORATORY
    assert results[0].extrapolation is True
    assert "EXTRAPOLATION" in results[0].reasons
    assert "REFERENCE_OUTSIDE_IC80" in results[0].reasons
    assert summary.rejected_exploratory_count == 1


def test_preserves_invalid_reference_as_inconclusive() -> None:
    results, summary = _run(
        [
            BacktestObservation(
                validation_id="VAL-3",
                features=(85.0, 1.0),
                reference_value_brl=0.0,
                source_reference="evidence://3",
            )
        ]
    )

    assert results[0].status == BacktestStatus.INCONCLUSIVE_INVALID_INPUT
    assert results[0].estimated_value_brl is None
    assert summary.inconclusive_count == 1
    assert summary.mean_absolute_error_brl is None


def test_rejects_misaligned_feature_vectors() -> None:
    try:
        _run(
            [
                BacktestObservation(
                    validation_id="VAL-4",
                    features=(85.0,),
                    reference_value_brl=500_000.0,
                    source_reference="evidence://4",
                )
            ]
        )
    except ValueError as error:
        assert "does not align" in str(error)
    else:
        raise AssertionError("A misaligned feature vector must be rejected.")


def test_rejects_a_geographic_segment_outside_the_training_domain() -> None:
    model = _model()
    prediction = predict_linear_model(
        coefficients=list(model.coefficients),
        target=[85.0, 1.0],
        residual_variance=model.residual_variance,
        design_inverse=[list(row) for row in model.design_inverse],
        degrees_of_freedom=model.degrees_of_freedom,
    )
    results, _ = run_exploratory_backtest(
        observations=[
            BacktestObservation(
                validation_id="VAL-GEO",
                features=(85.0, 1.0),
                reference_value_brl=prediction.estimate,
                source_reference="evidence://geo",
                neighborhood="Barra Olimpica",
            )
        ],
        feature_names=model.feature_names,
        coefficients=model.coefficients,
        residual_variance=model.residual_variance,
        design_inverse=model.design_inverse,
        degrees_of_freedom=model.degrees_of_freedom,
        feature_ranges=model.feature_ranges,
        allowed_neighborhoods=("Copacabana",),
    )

    assert results[0].status == BacktestStatus.REJECTED_EXPLORATORY
    assert results[0].extrapolation is True
    assert "GEOGRAPHIC_SEGMENT_OUTSIDE_TRAINING_DOMAIN" in results[0].reasons
