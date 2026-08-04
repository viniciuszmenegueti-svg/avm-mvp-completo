import hashlib
from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.core.admin_auth import require_admin_api_key
from app.schemas.statistical_model import (
    MarketDatasetAssessmentRequest,
    MarketDatasetAssessmentResponse,
    NBRGradeResponse,
    StatisticalModelApprovalRequest,
    StatisticalModelFitRequest,
    StatisticalModelFitResponse,
    StatisticalModelListResponse,
    StatisticalModelRecordResponse,
    StatisticalModelTrainRequest,
)
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.cities_sqlalchemy import get_active_city_by_ibge_code
from app.repositories.statistical_models_sqlalchemy import (
    get_statistical_dataset,
    get_statistical_model,
)
from app.services.model_report_service import build_statistical_model_report_pdf
from app.services.statistical_model_registry_service import (
    StatisticalModelNotFoundError,
    StatisticalModelRegistryError,
    approve_model_for_homologation,
    assert_model_artifact_integrity,
    get_model_record,
    list_model_records,
    train_statistical_model_candidate,
)
from engine.datasets.market_observations import (
    DatasetPolicy,
    assess_market_dataset,
)
from engine.models.linear_regression_nbr import (
    StatisticalModelError,
    fit_linear_model,
)


router = APIRouter(prefix="/statistical-models", tags=["Modelos estatísticos"])
AdminAuthorization = Annotated[str, Depends(require_admin_api_key)]


@router.post(
    "/datasets/assess",
    response_model=MarketDatasetAssessmentResponse,
    summary="Audita observações de mercado antes do ajuste estatístico",
)
def assess_statistical_dataset(
    payload: MarketDatasetAssessmentRequest,
    _: AdminAuthorization,
) -> MarketDatasetAssessmentResponse:
    policy = DatasetPolicy(
        city_ibge_code=payload.policy.city_ibge_code,
        city=payload.policy.city,
        state=payload.policy.state,
        property_type=payload.policy.property_type,
        reference_date=payload.policy.reference_date,
        variable_count=payload.policy.variable_count,
        max_age_days=payload.policy.max_age_days,
        max_location_accuracy_meters=(payload.policy.max_location_accuracy_meters),
        max_source_share=payload.policy.max_source_share,
        required_features=tuple(payload.policy.required_features),
    )
    result = assess_market_dataset(payload.observations, policy)
    return MarketDatasetAssessmentResponse.model_validate(result.as_dict())


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
        f_statistic=result.f_statistic,
        model_p_value=result.model_p_value,
        variance_inflation_factors=dict(
            zip(result.feature_names, result.variance_inflation_factors, strict=True)
        ),
        maximum_vif=result.maximum_vif,
        normality_test=result.normality_test,
        normality_p_value=result.normality_p_value,
        breusch_pagan_statistic=result.breusch_pagan_statistic,
        breusch_pagan_p_value=result.breusch_pagan_p_value,
        durbin_watson=result.durbin_watson,
        maximum_standardized_residual=result.maximum_standardized_residual,
        maximum_cooks_distance=result.maximum_cooks_distance,
        feature_ranges={
            name: bounds
            for name, bounds in zip(
                result.feature_names, result.feature_ranges, strict=True
            )
        },
        target_estimate=result.target_estimate,
        confidence_level=result.confidence_level,
        confidence_lower=result.confidence_lower,
        confidence_upper=result.confidence_upper,
        confidence_amplitude_percent=result.confidence_amplitude_percent,
        grades=NBRGradeResponse(
            sample=result.grades.sample,
            significance=result.grades.significance,
            model_significance=result.grades.model_significance,
            precision=result.grades.precision,
            automatic_fundamentation_gate=(result.grades.automatic_fundamentation_gate),
            overall=result.grades.overall,
        ),
        economic_gates_passed=result.economic_gates_passed,
        economic_gate_failures=list(result.economic_gate_failures),
        homologated=False,
        full_nbr_compliance_claimed=False,
        review_notice=(
            "Resultado candidato para revisão do Responsável Técnico. Os campos "
            "automáticos cobrem apenas parte dos itens da NBR 14653-2; precisão "
            "é separada da fundamentação e o cálculo não homologa modelo, cidade "
            "ou dataset."
        ),
    )


@router.post(
    "/train",
    response_model=StatisticalModelRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajusta e persiste um candidato estatístico versionado",
)
def train_statistical_model(
    payload: StatisticalModelTrainRequest,
    session: DatabaseSession,
    actor: AdminAuthorization,
) -> StatisticalModelRecordResponse:
    city = get_active_city_by_ibge_code(session, payload.city_ibge_code)
    if city is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_CITY",
                "message": "Cidade não habilitada para o AVM.",
            },
        )
    try:
        return train_statistical_model_candidate(
            session,
            payload=payload,
            trained_by=actor,
        )
    except (StatisticalModelError, StatisticalModelRegistryError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "STATISTICAL_MODEL_NOT_REGISTERED",
                "message": str(error),
            },
        ) from error


@router.post(
    "/{model_id}/approve-homologation",
    response_model=StatisticalModelRecordResponse,
    summary="Aprova candidato exclusivamente para homologação sombra",
)
def approve_statistical_model_for_homologation(
    model_id: UUID,
    payload: StatisticalModelApprovalRequest,
    session: DatabaseSession,
    actor: AdminAuthorization,
) -> StatisticalModelRecordResponse:
    try:
        return approve_model_for_homologation(
            session,
            model_id=str(model_id),
            approved_by=actor,
            approval_reference=payload.approval_reference,
        )
    except StatisticalModelNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STATISTICAL_MODEL_NOT_FOUND"},
        ) from error
    except StatisticalModelRegistryError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "HOMOLOGATION_APPROVAL_BLOCKED",
                "message": str(error),
            },
        ) from error


@router.get(
    "",
    response_model=StatisticalModelListResponse,
    summary="Lista candidatos e modelos estatísticos registrados",
)
def list_registered_statistical_models(
    session: DatabaseSession,
    _: AdminAuthorization,
) -> StatisticalModelListResponse:
    items = list_model_records(session)
    return StatisticalModelListResponse(total=len(items), items=items)


@router.get(
    "/{model_id}/report.pdf",
    response_class=Response,
    summary="Gera a minuta técnica auditável do Relatório do Modelo",
)
def get_statistical_model_report(
    model_id: UUID,
    session: DatabaseSession,
    _: AdminAuthorization,
) -> Response:
    model = get_statistical_model(session, str(model_id))
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STATISTICAL_MODEL_NOT_FOUND"},
        )
    dataset = get_statistical_dataset(session, model.dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "STATISTICAL_DATASET_NOT_FOUND"},
        )
    try:
        assert_model_artifact_integrity(model=model, dataset=dataset)
    except StatisticalModelRegistryError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "STATISTICAL_ARTIFACT_INTEGRITY_FAILED",
                "message": str(error),
            },
        ) from error
    content = build_statistical_model_report_pdf(model=model, dataset=dataset)
    report_sha256 = hashlib.sha256(content).hexdigest()
    research_only = dataset.dependent_variable == "asking_price_brl"
    filename_prefix = "PESQUISA" if research_only else "HOMOLOGACAO"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_prefix}-modelo-{model.model_id}.pdf"'
            ),
            "X-Report-SHA256": report_sha256,
            "X-Model-Artifact-SHA256": model.artifact_sha256,
            "X-Contractual-Validity": "false",
            "X-Model-Use-Scope": (
                "research-only" if research_only else "homologation-shadow"
            ),
        },
    )


@router.get(
    "/{model_id}",
    response_model=StatisticalModelRecordResponse,
    summary="Consulta artefato estatístico e sua rastreabilidade",
)
def get_registered_statistical_model(
    model_id: UUID,
    session: DatabaseSession,
    _: AdminAuthorization,
) -> StatisticalModelRecordResponse:
    record = get_model_record(session, str(model_id))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STATISTICAL_MODEL_NOT_FOUND"},
        )
    return record
