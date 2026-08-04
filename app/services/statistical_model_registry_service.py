import hashlib
import json
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import APP_ENV, MODEL_EXECUTION_MODE
from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel
from app.repositories.statistical_models_sqlalchemy import (
    create_dataset_and_model,
    disable_other_homologation_models,
    get_statistical_dataset,
    get_statistical_model,
    get_statistical_model_for_update,
    list_statistical_models,
)
from app.schemas.statistical_model import (
    StatisticalDatasetStatus,
    StatisticalModelRecordResponse,
    StatisticalModelStatus,
    StatisticalModelTrainRequest,
)
from engine.models.linear_regression_nbr import fit_linear_model


ALGORITHM_VERSION = "OLS_NBR_DIAGNOSTICS_V2"


class StatisticalModelRegistryError(ValueError):
    pass


class StatisticalModelNotFoundError(LookupError):
    pass


def _canonical_hash(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _diagnostics_dict(result: object) -> dict[str, object]:
    from engine.models.linear_regression_nbr import LinearModelDiagnostics

    if not isinstance(result, LinearModelDiagnostics):
        raise TypeError("Unexpected regression result.")
    return {
        "observation_count": result.observation_count,
        "variable_count": result.variable_count,
        "degrees_of_freedom": result.degrees_of_freedom,
        "r_squared": result.r_squared,
        "adjusted_r_squared": result.adjusted_r_squared,
        "correlation_coefficient": result.correlation_coefficient,
        "residual_standard_error": result.residual_standard_error,
        "residual_variance": result.residual_variance,
        "press": result.press,
        "loocv_rmse": result.loocv_rmse,
        "maximum_regressor_p_value": result.maximum_regressor_p_value,
        "f_statistic": result.f_statistic,
        "model_p_value": result.model_p_value,
        "variance_inflation_factors": dict(
            zip(result.feature_names, result.variance_inflation_factors, strict=True)
        ),
        "maximum_vif": result.maximum_vif,
        "normality_test": result.normality_test,
        "normality_p_value": result.normality_p_value,
        "breusch_pagan_statistic": result.breusch_pagan_statistic,
        "breusch_pagan_p_value": result.breusch_pagan_p_value,
        "durbin_watson": result.durbin_watson,
        "maximum_standardized_residual": result.maximum_standardized_residual,
        "maximum_cooks_distance": result.maximum_cooks_distance,
        "feature_ranges": {
            name: list(bounds)
            for name, bounds in zip(
                result.feature_names, result.feature_ranges, strict=True
            )
        },
        "confidence_level": result.confidence_level,
        "confidence_amplitude_percent": result.confidence_amplitude_percent,
        "grades": {
            "sample": result.grades.sample,
            "significance": result.grades.significance,
            "model_significance": result.grades.model_significance,
            "precision": result.grades.precision,
            "automatic_fundamentation_gate": (
                result.grades.automatic_fundamentation_gate
            ),
            "overall": result.grades.overall,
        },
        "full_nbr_fundamentation_grade": None,
        "full_nbr_compliance_claimed": False,
        "coefficient_p_values": list(result.coefficient_p_values),
        "economic_gates_passed": result.economic_gates_passed,
        "economic_gate_failures": list(result.economic_gate_failures),
    }


def train_statistical_model_candidate(
    session: Session,
    *,
    payload: StatisticalModelTrainRequest,
    trained_by: str,
) -> StatisticalModelRecordResponse:
    result = fit_linear_model(
        feature_names=payload.feature_names,
        observations=payload.observations,
        values=payload.values,
        target=payload.target,
        expected_signs=payload.expected_signs,
        confidence_level=payload.confidence_level,
    )
    matrix_payload = {
        "feature_names": payload.feature_names,
        "observations": payload.observations,
        "values": payload.values,
    }
    matrix_hash = _canonical_hash(matrix_payload)
    training_payload = {
        **matrix_payload,
        "city_ibge_code": payload.city_ibge_code,
        "property_type": payload.property_type,
        "reference_date": payload.reference_date.isoformat(),
        "dependent_variable": payload.dependent_variable,
        "dependent_variable_unit": payload.dependent_variable_unit,
        "dependent_variable_transformation": (
            payload.dependent_variable_transformation
        ),
        "feature_transformations": {
            name: payload.feature_transformations.get(name, "NONE")
            for name in payload.feature_names
        },
    }
    computed_dataset_hash = _canonical_hash(training_payload)
    if payload.dataset_sha256 is not None and not secrets.compare_digest(
        payload.dataset_sha256.lower(), computed_dataset_hash
    ):
        raise StatisticalModelRegistryError(
            "dataset_sha256 does not match the training data and its semantics."
        )
    feature_ranges = {
        name: [
            min(row[index] for row in payload.observations),
            max(row[index] for row in payload.observations),
        ]
        for index, name in enumerate(payload.feature_names)
    }
    diagnostics = _diagnostics_dict(result)
    artifact = {
        "algorithm_version": ALGORITHM_VERSION,
        "dataset_sha256": computed_dataset_hash,
        "training_matrix_sha256": matrix_hash,
        "dependent_variable": payload.dependent_variable,
        "dependent_variable_unit": payload.dependent_variable_unit,
        "dependent_variable_transformation": (
            payload.dependent_variable_transformation
        ),
        "feature_ranges": feature_ranges,
        "feature_names": list(result.feature_names),
        "coefficients": list(result.coefficients),
        "design_inverse": [list(row) for row in result.design_inverse],
        "diagnostics": diagnostics,
        "expected_signs": payload.expected_signs,
    }
    artifact_sha256 = _canonical_hash(artifact)
    dataset_id = str(uuid4())
    model_id = str(uuid4())
    dataset = StatisticalDatasetModel(
        dataset_id=dataset_id,
        dataset_version=payload.dataset_version,
        city_ibge_code=payload.city_ibge_code,
        property_type=payload.property_type,
        reference_date=payload.reference_date,
        observation_count=len(payload.observations),
        variable_count=len(payload.feature_names),
        dataset_sha256=computed_dataset_hash,
        training_matrix_sha256=matrix_hash,
        dependent_variable=payload.dependent_variable,
        dependent_variable_unit=payload.dependent_variable_unit,
        dependent_variable_transformation=(payload.dependent_variable_transformation),
        training_payload_json=_canonical_json(training_payload),
        feature_ranges_json=_canonical_json(feature_ranges),
        source_reference=payload.source_reference,
        status=StatisticalDatasetStatus.CANDIDATE.value,
        metadata_json=json.dumps(
            payload.dataset_metadata, ensure_ascii=False, sort_keys=True
        ),
        created_by=trained_by,
    )
    model = StatisticalModelVersionModel(
        model_id=model_id,
        dataset_id=dataset_id,
        city_ibge_code=payload.city_ibge_code,
        property_type=payload.property_type,
        method="LINEAR_REGRESSION_OLS",
        model_version=payload.model_version,
        status=StatisticalModelStatus.CANDIDATE.value,
        feature_names_json=json.dumps(list(result.feature_names)),
        coefficients_json=json.dumps(list(result.coefficients)),
        covariance_json=json.dumps([list(row) for row in result.design_inverse]),
        diagnostics_json=json.dumps(diagnostics, sort_keys=True),
        expected_signs_json=json.dumps(payload.expected_signs, sort_keys=True),
        artifact_sha256=artifact_sha256,
        algorithm_version=ALGORITHM_VERSION,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        trained_by=trained_by,
    )
    try:
        create_dataset_and_model(session, dataset=dataset, model=model)
    except IntegrityError as error:
        session.rollback()
        raise StatisticalModelRegistryError(
            "Já existe versão do modelo para esta cidade e tipologia."
        ) from error
    return model_to_response(model, dataset)


def approve_model_for_homologation(
    session: Session,
    *,
    model_id: str,
    approved_by: str,
    approval_reference: str,
) -> StatisticalModelRecordResponse:
    environment = APP_ENV.strip().lower()
    if environment in {"homologation", "staging"} and (
        MODEL_EXECUTION_MODE != "HOMOLOGATION_SHADOW"
    ):
        raise StatisticalModelRegistryError(
            "O ambiente não está no modo HOMOLOGATION_SHADOW."
        )
    if MODEL_EXECUTION_MODE == "CONTRACTUAL":
        raise StatisticalModelRegistryError(
            "Modelo candidato não pode ser aprovado como homologação em produção."
        )
    model = get_statistical_model_for_update(session, model_id)
    if model is None:
        raise StatisticalModelNotFoundError(model_id)
    dataset = get_statistical_dataset(session, model.dataset_id)
    if dataset is None:
        raise StatisticalModelRegistryError("Dataset vinculado não encontrado.")
    assert_model_artifact_integrity(model=model, dataset=dataset)
    if (
        dataset.dependent_variable != "usable_market_value_brl"
        or dataset.dependent_variable_unit != "BRL"
        or dataset.dependent_variable_transformation != "NONE"
    ):
        raise StatisticalModelRegistryError(
            "Treino exploratório sobre preço pedido não pode ser aprovado "
            "para homologação ou utilizado em inferência AVM."
        )
    if model.status != StatisticalModelStatus.CANDIDATE.value:
        raise StatisticalModelRegistryError(
            "Somente modelo CANDIDATE pode ser aprovado para homologação."
        )
    if model.trained_by == approved_by:
        raise StatisticalModelRegistryError(
            "Segregação de funções: o revisor não pode ser o mesmo ator do treino."
        )
    diagnostics = json.loads(model.diagnostics_json)
    if not diagnostics.get("economic_gates_passed"):
        raise StatisticalModelRegistryError(
            "O modelo falhou nos gates de coerência econômica."
        )
    if not diagnostics.get("grades", {}).get("automatic_fundamentation_gate"):
        raise StatisticalModelRegistryError(
            "O modelo não alcançou os itens automáticos mínimos de amostra, "
            "significância dos regressores e significância global."
        )
    disable_other_homologation_models(session, selected_model=model)
    now = datetime.now(timezone.utc)
    model.status = StatisticalModelStatus.HOMOLOGATION_APPROVED.value
    model.approved_by = approved_by
    model.approval_reference = approval_reference
    model.approved_at = now
    dataset.status = StatisticalDatasetStatus.HOMOLOGATION_APPROVED.value
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise StatisticalModelRegistryError(
            "Another homologation model is already active for this city and type."
        ) from error
    session.refresh(model)
    session.refresh(dataset)
    return model_to_response(model, dataset)


def get_model_record(
    session: Session, model_id: str
) -> StatisticalModelRecordResponse | None:
    model = get_statistical_model(session, model_id)
    if model is None:
        return None
    dataset = get_statistical_dataset(session, model.dataset_id)
    if dataset is None:
        raise StatisticalModelRegistryError("Dataset vinculado não encontrado.")
    return model_to_response(model, dataset)


def list_model_records(session: Session) -> list[StatisticalModelRecordResponse]:
    records: list[StatisticalModelRecordResponse] = []
    for model in list_statistical_models(session):
        dataset = get_statistical_dataset(session, model.dataset_id)
        if dataset is None:
            raise StatisticalModelRegistryError("Dataset vinculado não encontrado.")
        records.append(model_to_response(model, dataset))
    return records


def model_to_response(
    model: StatisticalModelVersionModel,
    dataset: StatisticalDatasetModel,
) -> StatisticalModelRecordResponse:
    return StatisticalModelRecordResponse(
        model_id=model.model_id,
        dataset_id=dataset.dataset_id,
        city_ibge_code=model.city_ibge_code,
        property_type=model.property_type,
        method=model.method,
        model_version=model.model_version,
        status=StatisticalModelStatus(model.status),
        dataset_status=StatisticalDatasetStatus(dataset.status),
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset.dataset_sha256,
        training_matrix_sha256=dataset.training_matrix_sha256,
        artifact_sha256=model.artifact_sha256,
        feature_names=json.loads(model.feature_names_json),
        coefficients=json.loads(model.coefficients_json),
        diagnostics=json.loads(model.diagnostics_json),
        dependent_variable=dataset.dependent_variable,
        dependent_variable_unit=dataset.dependent_variable_unit,
        dependent_variable_transformation=(dataset.dependent_variable_transformation),
        feature_ranges=json.loads(dataset.feature_ranges_json),
        valid_from=model.valid_from,
        valid_until=model.valid_until,
        trained_by=model.trained_by,
        trained_at=model.trained_at,
        approved_by=model.approved_by,
        approval_reference=model.approval_reference,
        approved_at=model.approved_at,
        contractual_validity=False,
    )


def _stored_artifact_payload(
    *,
    model: StatisticalModelVersionModel,
    dataset: StatisticalDatasetModel,
) -> dict[str, object]:
    return {
        "algorithm_version": model.algorithm_version,
        "dataset_sha256": dataset.dataset_sha256,
        "training_matrix_sha256": dataset.training_matrix_sha256,
        "dependent_variable": dataset.dependent_variable,
        "dependent_variable_unit": dataset.dependent_variable_unit,
        "dependent_variable_transformation": (
            dataset.dependent_variable_transformation
        ),
        "feature_ranges": json.loads(dataset.feature_ranges_json),
        "feature_names": json.loads(model.feature_names_json),
        "coefficients": json.loads(model.coefficients_json),
        "design_inverse": json.loads(model.covariance_json),
        "diagnostics": json.loads(model.diagnostics_json),
        "expected_signs": json.loads(model.expected_signs_json),
    }


def assert_model_artifact_integrity(
    *,
    model: StatisticalModelVersionModel,
    dataset: StatisticalDatasetModel,
) -> None:
    """Re-hash every persisted component before approval or inference."""

    if model.algorithm_version != ALGORITHM_VERSION:
        raise StatisticalModelRegistryError(
            "Legacy statistical artifact is disabled and must be retrained."
        )
    try:
        training_payload = json.loads(dataset.training_payload_json)
        feature_ranges = json.loads(dataset.feature_ranges_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise StatisticalModelRegistryError(
            "Stored statistical dataset is not reproducible."
        ) from error
    if not secrets.compare_digest(
        _canonical_hash(training_payload), dataset.dataset_sha256
    ):
        raise StatisticalModelRegistryError("Stored dataset hash verification failed.")
    matrix_payload = {
        key: training_payload.get(key)
        for key in ("feature_names", "observations", "values")
    }
    if not secrets.compare_digest(
        _canonical_hash(matrix_payload), dataset.training_matrix_sha256
    ):
        raise StatisticalModelRegistryError(
            "Stored training matrix hash verification failed."
        )
    if (
        feature_ranges
        != _stored_artifact_payload(model=model, dataset=dataset)["feature_ranges"]
    ):
        raise StatisticalModelRegistryError("Stored feature ranges are inconsistent.")
    if not secrets.compare_digest(
        _canonical_hash(_stored_artifact_payload(model=model, dataset=dataset)),
        model.artifact_sha256,
    ):
        raise StatisticalModelRegistryError(
            "Statistical model artifact hash verification failed."
        )
