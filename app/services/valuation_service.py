from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.city_valuation_prices_sqlalchemy import (
    get_city_valuation_price,
)
from app.repositories.order_refusals_sqlalchemy import (
    create_order_refusal,
)
from app.repositories.order_status_history_sqlalchemy import (
    create_order_status_history,
)
from app.repositories.orders_sqlalchemy import (
    get_order_by_internal_id,
    update_order_status,
)
from app.repositories.valuations_sqlalchemy import (
    create_valuation,
    get_valuation_by_internal_order_id,
)
from app.schemas.order import OrderStatus
from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalReason,
)
from app.schemas.valuation import ValuationResponse
from app.services.order_status import (
    validate_order_status_transition,
)
from engine.registry import get_default_model_version


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

    if city_price is None:
        validate_order_status_transition(
            current_status=order.status,
            new_status=OrderStatus.REFUSED,
        )

        refusal = OrderRefusalCreate(
            reason_code=OrderRefusalReason.MISSING_BASE_PRICE,
            message=("Não existe preço-base configurado para a cidade e tipologia."),
            details={
                "city_ibge_code": order.property.city_ibge_code,
                "property_type": order.property.property_type.value,
            },
        )

        try:
            create_order_refusal(
                session=session,
                refusal_id=str(uuid4()),
                internal_order_id=internal_order_id,
                refusal=refusal,
                refused_at=datetime.now(timezone.utc),
                commit=False,
            )

            updated_order = update_order_status(
                session=session,
                internal_order_id=internal_order_id,
                new_status=OrderStatus.REFUSED,
                commit=False,
            )

            if updated_order is None:
                session.rollback()
                return None

            create_order_status_history(
                session=session,
                internal_order_id=internal_order_id,
                previous_status=order.status,
                new_status=OrderStatus.REFUSED,
                commit=False,
            )

            session.commit()

            return None

        except Exception:
            session.rollback()
            raise

    validate_order_status_transition(
        current_status=order.status,
        new_status=OrderStatus.COMPLETED,
    )

    model_version = get_default_model_version()

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
            estimated_value=calculation.estimated_value,
            minimum_value=calculation.minimum_value,
            maximum_value=calculation.maximum_value,
            price_per_m2=calculation.price_per_m2,
            reference_area_m2=calculation.reference_area_m2,
            confidence_score=calculation.confidence_score,
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
