import json
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel
from app.repositories.statistical_models_sqlalchemy import (
    get_applicable_statistical_model,
    get_statistical_dataset,
)
from app.schemas.property import PropertyInput
from app.schemas.statistical_model import StatisticalModelStatus
from app.schemas.valuation import ValuationMethod
from app.services.statistical_model_registry_service import (
    StatisticalModelRegistryError,
    assert_model_artifact_integrity,
)
from engine.models.linear_regression_nbr import (
    StatisticalModelError,
    predict_linear_model,
)
from engine.models.rule_based_v1 import (
    ValuationCalculation,
    get_reference_area,
    quantize_money,
)


@dataclass(frozen=True, slots=True)
class StatisticalValuationResult:
    calculation: ValuationCalculation
    model: StatisticalModelVersionModel
    dataset: StatisticalDatasetModel


class StatisticalModelInputError(ValueError):
    pass


def required_status_for_execution_mode(execution_mode: str) -> str:
    if execution_mode == "HOMOLOGATION_SHADOW":
        return StatisticalModelStatus.HOMOLOGATION_APPROVED.value
    if execution_mode == "CONTRACTUAL":
        return StatisticalModelStatus.CONTRACTUAL_ACTIVE.value
    raise StatisticalModelInputError(
        f"Modo {execution_mode} não utiliza modelo estatístico persistido."
    )


def find_applicable_model(
    session: Session,
    *,
    property_data: PropertyInput,
    execution_mode: str,
    reference_date: date,
) -> StatisticalModelVersionModel | None:
    return get_applicable_statistical_model(
        session,
        city_ibge_code=property_data.city_ibge_code,
        property_type=property_data.property_type.value,
        required_status=required_status_for_execution_mode(execution_mode),
        reference_date=reference_date,
    )


def _feature_value(property_data: PropertyInput, feature_name: str) -> float:
    allowed = {
        "private_area_m2": property_data.private_area_m2,
        "built_area_m2": property_data.built_area_m2,
        "land_area_m2": property_data.land_area_m2,
        "bedrooms": property_data.bedrooms,
        "bathrooms": property_data.bathrooms,
        "parking_spaces": property_data.parking_spaces,
    }
    if feature_name not in allowed:
        raise StatisticalModelInputError(
            f"Variável do modelo não suportada pela OS: {feature_name}."
        )
    value = allowed[feature_name]
    if value is None:
        raise StatisticalModelInputError(
            f"A OS não informou a variável exigida: {feature_name}."
        )
    return float(value)


def calculate_statistical_valuation(
    session: Session,
    *,
    property_data: PropertyInput,
    model: StatisticalModelVersionModel,
) -> StatisticalValuationResult:
    dataset = get_statistical_dataset(session, model.dataset_id)
    if dataset is None:
        raise StatisticalModelInputError("Dataset do modelo não foi encontrado.")
    try:
        assert_model_artifact_integrity(model=model, dataset=dataset)
    except StatisticalModelRegistryError as error:
        raise StatisticalModelInputError(str(error)) from error
    if (
        dataset.dependent_variable != "usable_market_value_brl"
        or dataset.dependent_variable_unit != "BRL"
        or dataset.dependent_variable_transformation != "NONE"
    ):
        raise StatisticalModelInputError(
            "A semântica da variável dependente não é suportada pela avaliação."
        )
    feature_names: list[str] = json.loads(model.feature_names_json)
    coefficients: list[float] = json.loads(model.coefficients_json)
    design_inverse: list[list[float]] = json.loads(model.covariance_json)
    diagnostics = json.loads(model.diagnostics_json)
    target = [_feature_value(property_data, name) for name in feature_names]
    feature_ranges: dict[str, list[float]] = json.loads(dataset.feature_ranges_json)
    for feature_name, value in zip(feature_names, target, strict=True):
        bounds = feature_ranges.get(feature_name)
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise StatisticalModelInputError(
                f"Domínio amostral ausente para {feature_name}."
            )
        minimum, maximum = (float(bounds[0]), float(bounds[1]))
        if value < minimum or value > maximum:
            raise StatisticalModelInputError(
                f"Extrapolação bloqueada para {feature_name}: {value:g} fora de "
                f"[{minimum:g}, {maximum:g}]."
            )
    try:
        prediction = predict_linear_model(
            coefficients=coefficients,
            target=target,
            residual_variance=float(diagnostics["residual_variance"]),
            design_inverse=design_inverse,
            degrees_of_freedom=int(diagnostics["degrees_of_freedom"]),
            confidence_level=float(diagnostics["confidence_level"]),
        )
    except StatisticalModelError as error:
        raise StatisticalModelInputError(str(error)) from error
    if prediction.confidence_lower <= 0:
        raise StatisticalModelInputError(
            "O intervalo do modelo produziu limite não positivo."
        )
    if prediction.precision_grade is None:
        raise StatisticalModelInputError(
            "A amplitude do intervalo de confiança de 80% excede 50%; "
            "a avaliação não alcança grau de precisão e foi recusada."
        )
    reference_area = get_reference_area(property_data)
    estimate = quantize_money(Decimal(str(prediction.estimate)))
    lower = quantize_money(Decimal(str(prediction.confidence_lower)))
    upper = quantize_money(Decimal(str(prediction.confidence_upper)))
    price_per_m2 = quantize_money(estimate / reference_area)
    automatic_gate = diagnostics.get("grades", {}).get("automatic_fundamentation_gate")
    precision_grade = prediction.precision_grade
    confidence_score = {
        "III": Decimal("0.9000"),
        "II": Decimal("0.8000"),
        "I": Decimal("0.7000"),
    }[precision_grade]
    factors = {
        "intercept": f"{coefficients[0]:.10g}",
        "dataset_version": dataset.dataset_version,
        "dataset_sha256": dataset.dataset_sha256,
        "model_artifact_sha256": model.artifact_sha256,
        "automatic_fundamentation_gate": str(automatic_gate or "NONE"),
        "full_nbr_fundamentation_grade": "NOT_CALCULATED",
        "precision_grade_for_property": precision_grade,
        "confidence_amplitude_percent": (
            f"{prediction.confidence_amplitude_percent:.6f}"
        ),
    }
    for index, feature_name in enumerate(feature_names, start=1):
        factors[f"input.{feature_name}"] = f"{target[index - 1]:.10g}"
        factors[f"coefficient.{feature_name}"] = f"{coefficients[index]:.10g}"
        factors[f"contribution.{feature_name}"] = (
            f"{coefficients[index] * target[index - 1]:.10g}"
        )
    calculation = ValuationCalculation(
        method=ValuationMethod.LINEAR_REGRESSION_OLS,
        estimated_value=estimate,
        minimum_value=lower,
        maximum_value=upper,
        price_per_m2=price_per_m2,
        reference_area_m2=reference_area,
        confidence_score=confidence_score.quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ),
        factors=factors,
        confidence_reasons=[
            (
                f"Modelo estatístico {model.model_version} selecionado "
                "por cidade e tipologia."
            ),
            f"Dataset congelado: {dataset.dataset_version}.",
            (
                "Itens automáticos de fundamentação: "
                f"{automatic_gate or 'não classificados'}; a pontuação NBR "
                "completa depende de revisão técnica."
            ),
            (
                f"Grau de precisão desta estimativa: {precision_grade} "
                f"(amplitude IC80 {prediction.confidence_amplitude_percent:.2f}%)."
            ),
            "A extrapolação além do domínio observado foi bloqueada.",
            "Resultado executado exclusivamente no modo sombra de homologação.",
        ],
    )
    return StatisticalValuationResult(
        calculation=calculation,
        model=model,
        dataset=dataset,
    )
