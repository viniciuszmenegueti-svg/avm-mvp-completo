from app.services.backtest_report_service import (
    _status_label,
    build_backtest_report_pdf,
)
from engine.validation.backtest import (
    BacktestResult,
    BacktestStatus,
    BacktestSummary,
)


def test_builds_a_valid_exploratory_backtest_pdf() -> None:
    result = BacktestResult(
        validation_id="VAL-1",
        source_reference="evidence://1",
        neighborhood="Centro",
        reference_value_basis="MARKET_VALUE_RT_REVIEWED",
        reference_value_brl=500_000.0,
        estimated_value_brl=510_000.0,
        confidence_level=0.8,
        confidence_lower_brl=480_000.0,
        confidence_upper_brl=540_000.0,
        confidence_amplitude_percent=11.76,
        precision_grade="III",
        signed_error_brl=10_000.0,
        absolute_error_brl=10_000.0,
        signed_percentage_error=0.02,
        absolute_percentage_error=0.02,
        reference_inside_ic80=True,
        extrapolation=False,
        status=BacktestStatus.APPROVED_EXPLORATORY,
        reasons=(),
    )
    summary = BacktestSummary(
        observation_count=1,
        conclusive_count=1,
        approved_exploratory_count=1,
        rejected_exploratory_count=0,
        inconclusive_count=0,
        mean_absolute_error_brl=10_000.0,
        root_mean_squared_error_brl=10_000.0,
        median_absolute_percentage_error=0.02,
        mean_signed_percentage_error=0.02,
        ic80_empirical_coverage=1.0,
        exploratory_approval_rate=1.0,
    )

    content = build_backtest_report_pdf(
        summary=summary,
        results=[result],
        metadata={
            "scope": "Sao Paulo/SP - APARTMENT",
            "training_count": 80,
            "validation_count": 20,
            "split_seed": "seed",
            "source_audit_sha256": "a" * 64,
            "training_sha256": "b" * 64,
            "validation_sha256": "c" * 64,
            "subject": "Validacao exploratoria em base externa candidata",
        },
        segment_rows=[
            {
                "segment": "Bairro: Centro",
                "count": 1,
                "mae_brl": 10_000.0,
                "median_ape": 0.02,
                "ic80_coverage": 1.0,
                "approval_rate": 1.0,
            }
        ],
    )

    assert content.startswith(b"%PDF-")
    assert len(content) > 10_000
    assert b"Validacao exploratoria em base externa candidata" in content
    assert _status_label("APPROVED_EXPLORATORY") == "APROVADA (EXPL.)"
    assert _status_label("REJECTED_EXPLORATORY") == "REPROVADA (EXPL.)"
