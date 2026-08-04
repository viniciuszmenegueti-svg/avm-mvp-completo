from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import ALLOW_SYNTHETIC_PRICING, MODEL_EXECUTION_MODE
from app.repositories.city_valuation_prices_sqlalchemy import get_city_valuation_price
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
    update_order_status,
)
from app.repositories.order_status_history_sqlalchemy import create_order_status_history
from app.repositories.valuations_sqlalchemy import (
    create_valuation,
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderStatus
from app.schemas.order_refusal import OrderRefusalCreate, OrderRefusalReason
from app.schemas.valuation import ValuationResponse
from app.services.order_refusal_service import refuse_order_with_evidence
from app.services.order_status import validate_order_status_transition
from app.services.order_status_update import resolve_audit_request_id
from app.services.statistical_valuation_service import (
    StatisticalModelInputError,
    calculate_statistical_valuation,
    find_applicable_model,
)
from engine.registry import DEFAULT_MODEL_METHOD, get_active_model_version


def calculate_and_store_valuation(
    session: Session,
    internal_order_id: str,
    changed_by: str = "system:valuation",
    request_id: str | None = None,
) -> ValuationResponse | None:
    order = get_order_by_internal_id(
        session=session,
        internal_order_id=internal_order_id,
    )

    if order is None:
        return None

    existing_valuation = get_valuation_by_internal_order_id(
        session=session,
        internal_order_id=internal_order_id,
    )

    if existing_valuation is not None:
        return existing_valuation

    evidence = {
        "city_ibge_code": order.property.city_ibge_code,
        "property_type": order.property.property_type.value,
        "execution_mode": MODEL_EXECUTION_MODE,
    }

    statistical_model_id: str | None = None
    model_artifact_sha256: str | None = None
    dataset_sha256: str | None = None

    if MODEL_EXECUTION_MODE in {"HOMOLOGATION_SHADOW", "CONTRACTUAL"}:
        model = find_applicable_model(
            session,
            property_data=order.property,
            execution_mode=MODEL_EXECUTION_MODE,
            reference_date=datetime.now(timezone.utc).date(),
        )
        if model is None:
            refusal = OrderRefusalCreate(
                reason_code=OrderRefusalReason.MODEL_NOT_APPLICABLE,
                contract_reference="TR §9.5(a) e §9.6",
                message=(
                    "Não existe modelo estatístico aprovado, vigente e aplicável "
                    "à cidade e tipologia no modo de execução atual."
                ),
                evidence={
                    **evidence,
                    "condition": "APPROVED_STATISTICAL_MODEL_UNAVAILABLE",
                },
                details=evidence,
                model_version=None,
                dataset_version=None,
            )
            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal,
                changed_by=changed_by,
                request_id=request_id,
            )
            return None
        try:
            statistical_result = calculate_statistical_valuation(
                session,
                property_data=order.property,
                model=model,
            )
        except StatisticalModelInputError as error:
            refusal = OrderRefusalCreate(
                reason_code=OrderRefusalReason.MODEL_NOT_APPLICABLE,
                contract_reference="TR §9.5(a) e §9.6",
                message="O modelo aplicável não pode processar os dados desta OS.",
                evidence={
                    **evidence,
                    "condition": "MODEL_INPUT_UNAVAILABLE",
                    "error": str(error),
                    "model_id": model.model_id,
                },
                details={**evidence, "model_id": model.model_id},
                model_version=model.model_version,
                dataset_version=None,
            )
            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal,
                changed_by=changed_by,
                request_id=request_id,
            )
            return None
        calculation = statistical_result.calculation
        model_version = statistical_result.model.model_version
        statistical_model_id = statistical_result.model.model_id
        model_artifact_sha256 = statistical_result.model.artifact_sha256
        dataset_sha256 = statistical_result.dataset.dataset_sha256
    else:
        city_price = get_city_valuation_price(
            session=session,
            city_ibge_code=order.property.city_ibge_code,
            property_type=order.property.property_type,
        )

        evidence["pricing_method"] = DEFAULT_MODEL_METHOD.value

        if city_price is None:
            refusal = OrderRefusalCreate(
                reason_code=OrderRefusalReason.MODEL_NOT_APPLICABLE,
                contract_reference="TR §9.5(a) e §9.6",
                message=(
                    "O modelo estatístico não permite precificar o imóvel: "
                    "não há modelo/dataset aplicável à cidade e tipologia."
                ),
                evidence={
                    **evidence,
                    "condition": "MODEL_OR_DATASET_UNAVAILABLE",
                },
                details=evidence,
                model_version=None,
                dataset_version=None,
            )

            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal,
                changed_by=changed_by,
                request_id=request_id,
            )

            return None

        if not ALLOW_SYNTHETIC_PRICING:
            refusal = OrderRefusalCreate(
                reason_code=OrderRefusalReason.MODEL_NOT_APPLICABLE,
                contract_reference="TR §9.5(a) e §9.6",
                message=(
                    "O modelo estatístico não permite precificar o imóvel: "
                    "somente preço-base demonstrativo está disponível."
                ),
                evidence={
                    **evidence,
                    "condition": "SYNTHETIC_PRICING_BLOCKED",
                    "synthetic_price_per_m2": str(city_price.price_per_m2),
                    "allow_synthetic_pricing": False,
                },
                details=evidence,
                model_version="RULE_BASED_V1/1.0.0",
                dataset_version=None,
            )

            refuse_order_with_evidence(
                session=session,
                internal_order_id=internal_order_id,
                refusal=refusal,
                changed_by=changed_by,
                request_id=request_id,
            )

            return None

        rule_model = get_active_model_version(DEFAULT_MODEL_METHOD)
        calculation = rule_model.calculator(order.property, city_price.price_per_m2)
        model_version = rule_model.version

    validate_order_status_transition(
        current_status=order.status,
        new_status=OrderStatus.COMPLETED,
    )

    calculated_at = datetime.now(timezone.utc)

    try:
        valuation = create_valuation(
            session=session,
            valuation_id=str(uuid4()),
            internal_order_id=internal_order_id,
            method=calculation.method,
            model_version=model_version,
            estimated_value=calculation.estimated_value,
            minimum_value=calculation.minimum_value,
            maximum_value=calculation.maximum_value,
            price_per_m2=calculation.price_per_m2,
            reference_area_m2=calculation.reference_area_m2,
            confidence_score=calculation.confidence_score,
            factors=calculation.factors,
            confidence_reasons=calculation.confidence_reasons,
            execution_mode=MODEL_EXECUTION_MODE,
            statistical_model_id=statistical_model_id,
            model_artifact_sha256=model_artifact_sha256,
            dataset_sha256=dataset_sha256,
            calculated_at=calculated_at,
            commit=False,
        )

        updated_order = update_order_status(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.COMPLETED,
            responded_at=calculated_at,
            commit=False,
        )

        if updated_order is None:
            session.rollback()
            return None

        create_order_status_history(
            session=session,
            internal_order_id=internal_order_id,
            previous_status=order.status,
            new_status=OrderStatus.COMPLETED,
            changed_by=changed_by,
            request_id=resolve_audit_request_id(request_id),
            reason_code="VALUATION_COMPLETED",
            context={
                "execution_mode": MODEL_EXECUTION_MODE,
                "method": calculation.method.value,
                "model_version": model_version,
            },
            commit=False,
        )

        session.commit()

        return valuation

    except Exception:
        session.rollback()
        raise
