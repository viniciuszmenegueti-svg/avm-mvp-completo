from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import ALLOW_SYNTHETIC_PRICING
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
from engine.registry import DEFAULT_MODEL_METHOD, get_active_model_version


def calculate_and_store_valuation(
    session: Session,
    internal_order_id: str,
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

    city_price = get_city_valuation_price(
        session=session,
        city_ibge_code=order.property.city_ibge_code,
        property_type=order.property.property_type,
    )

    evidence = {
        "city_ibge_code": order.property.city_ibge_code,
        "property_type": order.property.property_type.value,
        "pricing_method": DEFAULT_MODEL_METHOD.value,
    }

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
        )

        return None

    validate_order_status_transition(
        current_status=order.status,
        new_status=OrderStatus.COMPLETED,
    )

    model_version = get_active_model_version(DEFAULT_MODEL_METHOD)
    calculation = model_version.calculator(
        order.property,
        city_price.price_per_m2,
    )

    try:
        valuation = create_valuation(
            session=session,
            valuation_id=str(uuid4()),
            internal_order_id=internal_order_id,
            method=model_version.method,
            model_version=model_version.version,
            estimated_value=calculation.estimated_value,
            minimum_value=calculation.minimum_value,
            maximum_value=calculation.maximum_value,
            price_per_m2=calculation.price_per_m2,
            reference_area_m2=calculation.reference_area_m2,
            confidence_score=calculation.confidence_score,
            factors=calculation.factors,
            confidence_reasons=calculation.confidence_reasons,
            calculated_at=datetime.now(timezone.utc),
            commit=False,
        )

        updated_order = update_order_status(
            session=session,
            internal_order_id=internal_order_id,
            new_status=OrderStatus.COMPLETED,
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
            commit=False,
        )

        session.commit()

        return valuation

    except Exception:
        session.rollback()
        raise
