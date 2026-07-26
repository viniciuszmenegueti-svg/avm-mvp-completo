import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.valuation_model import ValuationModel
from app.schemas.valuation import ValuationMethod, ValuationResponse


def create_valuation(
    session: Session,
    valuation_id: str,
    internal_order_id: str,
    method: ValuationMethod,
    model_version: str,
    estimated_value: Decimal,
    minimum_value: Decimal,
    maximum_value: Decimal,
    price_per_m2: Decimal,
    reference_area_m2: Decimal,
    confidence_score: Decimal,
    calculated_at: datetime,
    factors: dict[str, str] | None = None,
    confidence_reasons: list[str] | None = None,
    commit: bool = True,
) -> ValuationResponse:
    database_valuation = ValuationModel(
        valuation_id=valuation_id,
        internal_order_id=internal_order_id,
        method=method.value,
        model_version=model_version,
        estimated_value=estimated_value,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        price_per_m2=price_per_m2,
        reference_area_m2=reference_area_m2,
        confidence_score=confidence_score,
        factors_json=json.dumps(factors or {}, ensure_ascii=False, sort_keys=True),
        confidence_reasons_json=json.dumps(
            confidence_reasons or [], ensure_ascii=False
        ),
        calculated_at=calculated_at,
    )
    session.add(database_valuation)
    if commit:
        session.commit()
        session.refresh(database_valuation)
    else:
        session.flush()
    return valuation_model_to_response(database_valuation)


def get_valuation_by_internal_order_id(
    session: Session, internal_order_id: str
) -> ValuationResponse | None:
    database_valuation = session.scalar(
        select(ValuationModel).where(
            ValuationModel.internal_order_id == internal_order_id
        )
    )
    return (
        None
        if database_valuation is None
        else valuation_model_to_response(database_valuation)
    )


def valuation_model_to_response(
    database_valuation: ValuationModel,
) -> ValuationResponse:
    return ValuationResponse(
        valuation_id=database_valuation.valuation_id,
        internal_order_id=database_valuation.internal_order_id,
        method=ValuationMethod(database_valuation.method),
        model_version=database_valuation.model_version,
        estimated_value=database_valuation.estimated_value,
        minimum_value=database_valuation.minimum_value,
        maximum_value=database_valuation.maximum_value,
        price_per_m2=database_valuation.price_per_m2,
        reference_area_m2=database_valuation.reference_area_m2,
        confidence_score=database_valuation.confidence_score,
        factors=json.loads(database_valuation.factors_json or "{}"),
        confidence_reasons=json.loads(
            database_valuation.confidence_reasons_json or "[]"
        ),
        calculated_at=database_valuation.calculated_at,
    )
