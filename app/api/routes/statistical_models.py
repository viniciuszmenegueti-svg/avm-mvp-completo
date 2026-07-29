from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.admin_auth import require_admin_api_key
from app.schemas.statistical_model import (
    NBRGradeResponse,
    StatisticalModelFitRequest,
    StatisticalModelFitResponse,
)
from engine.models.linear_regression_nbr import (
    StatisticalModelError,
    fit_linear_model,
)


router = APIRouter(prefix="/statistical-models", tags=["Modelos estatísticos"])
AdminAuthorization = Annotated[str, Depends(require_admin_api_key)]


@router.post(
    "/fit",
    response_model=StatisticalModelFitResponse,
    summary="Ajusta e diagnostica candidato de regressão linear",
)
def fit_statistical_model(
    payload: StatisticalModelFitRequest,
    _: AdminAuthorization,
) -> StatisticalModelFitResponse:
    try:
        result = fit_linear_model(
            feature_names=payload.feature_names,
            observations=payload.observations,
            values=payload.values,
            target=payload.target,
            expected_signs=payload.expected_signs,
            confidence_level=payload.confidence_level,
        )
    except StatisticalModelError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "STATISTICAL_MODEL_INVALID",
                "message": str(error),
            },
        ) from error

    return StatisticalModelFitResponse(
        feature_names=list(result.feature_names),
        coefficients=list(result.coefficients),
        coefficient_p_values=list(result.coefficient_p_values),
        observation_count=result.observation_count,
        variable_count=result.variable_count,
        degrees_of_freedom=result.degrees_of_freedom,
        r_squared=result.r_squared,
        adjusted_r_squared=result.adjusted_r_squared,
        correlation_coefficient=result.correlation_coefficient,
        residual_standard_error=result.residual_standard_error,
        press=result.press,
        loocv_rmse=result.loocv_rmse,
        maximum_regressor_p_value=result.maximum_regressor_p_value,
        target_estimate=result.target_estimate,
        confidence_level=result.confidence_level,
        confidence_lower=result.confidence_lower,
        confidence_upper=result.confidence_upper,
        confidence_amplitude_percent=result.confidence_amplitude_percent,
        grades=NBRGradeResponse(
            sample=result.grades.sample,
            significance=result.grades.significance,
            precision=result.grades.precision,
            overall=result.grades.overall,
        ),
        economic_gates_passed=result.economic_gates_passed,
        economic_gate_failures=list(result.economic_gate_failures),
        homologated=False,
        review_notice=(
            "Resultado candidato para revisão do Responsável Técnico. "
            "O cálculo não homologa modelo, cidade ou dataset."
        ),
    )
