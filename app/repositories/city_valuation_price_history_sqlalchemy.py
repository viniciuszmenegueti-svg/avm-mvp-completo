from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.city_valuation_price_history_model import (
    CityValuationPriceHistoryModel,
)
from app.schemas.city_valuation_price_history import (
    CityValuationPriceHistoryResponse,
)
from app.schemas.property import PropertyType


def create_city_valuation_price_history(
    session: Session,
    city_valuation_price_id: int,
    city_ibge_code: str,
    property_type: PropertyType,
    previous_price_per_m2: Decimal,
    new_price_per_m2: Decimal,
    commit: bool = True,
) -> CityValuationPriceHistoryResponse:
    database_history = CityValuationPriceHistoryModel(
        city_valuation_price_id=city_valuation_price_id,
        city_ibge_code=city_ibge_code,
        property_type=property_type.value,
        previous_price_per_m2=previous_price_per_m2,
        new_price_per_m2=new_price_per_m2,
    )

    session.add(database_history)

    if commit:
        session.commit()
        session.refresh(database_history)
    else:
        session.flush()

    return CityValuationPriceHistoryResponse.model_validate(database_history)


def list_city_valuation_price_history(
    session: Session,
    city_ibge_code: str,
    property_type: PropertyType,
    limit: int,
    offset: int,
) -> tuple[
    list[CityValuationPriceHistoryResponse],
    int,
]:
    filters = (
        CityValuationPriceHistoryModel.city_ibge_code == city_ibge_code,
        CityValuationPriceHistoryModel.property_type == property_type.value,
    )

    total_statement = select(func.count(CityValuationPriceHistoryModel.id)).where(
        *filters
    )

    total = session.scalar(total_statement) or 0

    statement = (
        select(CityValuationPriceHistoryModel)
        .where(*filters)
        .order_by(
            CityValuationPriceHistoryModel.changed_at.desc(),
            CityValuationPriceHistoryModel.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    database_history = session.scalars(statement).all()

    items = [
        CityValuationPriceHistoryResponse.model_validate(history_item)
        for history_item in database_history
    ]

    return items, total
