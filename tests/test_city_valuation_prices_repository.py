from decimal import Decimal

from app.infrastructure.database import SessionLocal
from app.repositories.city_valuation_prices_sqlalchemy import (
    get_city_valuation_price,
    list_city_valuation_prices,
    update_city_valuation_price,
)
from app.schemas.property import PropertyType


def test_gets_city_valuation_price() -> None:
    with SessionLocal() as session:
        price = get_city_valuation_price(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
        )

    assert price is not None
    assert price.city_ibge_code == "3550308"
    assert price.property_type == PropertyType.APARTMENT
    assert price.price_per_m2 == Decimal("10500.00")


def test_returns_none_for_unknown_city_price() -> None:
    with SessionLocal() as session:
        price = get_city_valuation_price(
            session=session,
            city_ibge_code="3205309",
            property_type=PropertyType.APARTMENT,
        )

    assert price is None


def test_lists_all_prices_for_city() -> None:
    with SessionLocal() as session:
        prices = list_city_valuation_prices(
            session=session,
            city_ibge_code="3550308",
        )

    assert len(prices) == 3

    assert [price.property_type for price in prices] == [
        PropertyType.APARTMENT,
        PropertyType.HOUSE,
        PropertyType.LAND,
    ]

    assert [price.price_per_m2 for price in prices] == [
        Decimal("10500.00"),
        Decimal("7800.00"),
        Decimal("5200.00"),
    ]


def test_returns_empty_list_for_city_without_prices() -> None:
    with SessionLocal() as session:
        prices = list_city_valuation_prices(
            session=session,
            city_ibge_code="3304557",
        )

    assert prices == []


def test_updates_city_valuation_price() -> None:
    with SessionLocal() as session:
        updated_price = update_city_valuation_price(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            price_per_m2=Decimal("11000.00"),
        )

    assert updated_price is not None
    assert updated_price.city_ibge_code == "3550308"
    assert updated_price.property_type == PropertyType.APARTMENT
    assert updated_price.price_per_m2 == Decimal("11000.00")


def test_returns_none_when_updating_unknown_price() -> None:
    with SessionLocal() as session:
        updated_price = update_city_valuation_price(
            session=session,
            city_ibge_code="3205309",
            property_type=PropertyType.APARTMENT,
            price_per_m2=Decimal("11000.00"),
        )

    assert updated_price is None
