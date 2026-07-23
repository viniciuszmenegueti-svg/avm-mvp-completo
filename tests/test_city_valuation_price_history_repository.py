from decimal import Decimal

from app.infrastructure.database import SessionLocal
from app.repositories.city_valuation_price_history_sqlalchemy import (
    create_city_valuation_price_history,
    list_city_valuation_price_history,
)
from app.repositories.city_valuation_prices_sqlalchemy import (
    get_city_valuation_price,
)
from app.schemas.property import PropertyType


def test_creates_city_valuation_price_history() -> None:
    with SessionLocal() as session:
        current_price = get_city_valuation_price(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
        )

        assert current_price is not None

        history = create_city_valuation_price_history(
            session=session,
            city_valuation_price_id=current_price.id,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            previous_price_per_m2=Decimal("10500.00"),
            new_price_per_m2=Decimal("11000.00"),
        )

    assert history.city_valuation_price_id == current_price.id
    assert history.city_ibge_code == "3550308"
    assert history.property_type == PropertyType.APARTMENT
    assert history.previous_price_per_m2 == Decimal("10500.00")
    assert history.new_price_per_m2 == Decimal("11000.00")


def test_lists_city_valuation_price_history() -> None:
    with SessionLocal() as session:
        current_price = get_city_valuation_price(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
        )

        assert current_price is not None

        create_city_valuation_price_history(
            session=session,
            city_valuation_price_id=current_price.id,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            previous_price_per_m2=Decimal("10500.00"),
            new_price_per_m2=Decimal("11000.00"),
        )

        create_city_valuation_price_history(
            session=session,
            city_valuation_price_id=current_price.id,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            previous_price_per_m2=Decimal("11000.00"),
            new_price_per_m2=Decimal("11500.00"),
        )

        history = list_city_valuation_price_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
        )

    assert len(history) == 2
    assert history[0].new_price_per_m2 == Decimal("11500.00")
    assert history[1].new_price_per_m2 == Decimal("11000.00")


def test_returns_empty_history_for_unknown_price() -> None:
    with SessionLocal() as session:
        history = list_city_valuation_price_history(
            session=session,
            city_ibge_code="3304557",
            property_type=PropertyType.APARTMENT,
        )

    assert history == []
