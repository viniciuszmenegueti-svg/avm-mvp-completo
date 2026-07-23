from decimal import Decimal
from unittest.mock import patch

import pytest

from app.infrastructure.database import SessionLocal
from app.repositories.city_valuation_price_history_sqlalchemy import (
    list_city_valuation_price_history,
)
from app.repositories.city_valuation_prices_sqlalchemy import (
    get_city_valuation_price,
)
from app.schemas.property import PropertyType
from app.services.city_valuation_price_service import (
    update_city_valuation_price_with_history,
)


def test_updates_price_and_creates_history() -> None:
    with SessionLocal() as session:
        updated_price = update_city_valuation_price_with_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            price_per_m2=Decimal("11000.00"),
            changed_by="service-test",
        )

        history, total = list_city_valuation_price_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            limit=20,
            offset=0,
        )

    assert updated_price is not None
    assert updated_price.price_per_m2 == Decimal("11000.00")

    assert total == 1
    assert len(history) == 1
    assert history[0].previous_price_per_m2 == Decimal("10500.00")
    assert history[0].new_price_per_m2 == Decimal("11000.00")
    assert history[0].changed_by == "service-test"


def test_does_not_create_history_for_unchanged_price() -> None:
    with SessionLocal() as session:
        updated_price = update_city_valuation_price_with_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            price_per_m2=Decimal("10500.00"),
            changed_by="service-test",
        )

        history, total = list_city_valuation_price_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            limit=20,
            offset=0,
        )

    assert updated_price is not None
    assert updated_price.price_per_m2 == Decimal("10500.00")
    assert total == 0
    assert history == []


def test_returns_none_for_unknown_price() -> None:
    with SessionLocal() as session:
        updated_price = update_city_valuation_price_with_history(
            session=session,
            city_ibge_code="3304557",
            property_type=PropertyType.APARTMENT,
            price_per_m2=Decimal("11000.00"),
            changed_by="service-test",
        )

    assert updated_price is None


def test_rolls_back_price_when_history_creation_fails() -> None:
    with SessionLocal() as session:
        with patch(
            (
                "app.services.city_valuation_price_service."
                "create_city_valuation_price_history"
            ),
            side_effect=RuntimeError("Falha ao registrar histórico"),
        ):
            with pytest.raises(
                RuntimeError,
                match="Falha ao registrar histórico",
            ):
                update_city_valuation_price_with_history(
                    session=session,
                    city_ibge_code="3550308",
                    property_type=PropertyType.APARTMENT,
                    price_per_m2=Decimal("11000.00"),
                    changed_by="service-test",
                )

        current_price = get_city_valuation_price(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
        )

        history, total = list_city_valuation_price_history(
            session=session,
            city_ibge_code="3550308",
            property_type=PropertyType.APARTMENT,
            limit=20,
            offset=0,
        )

    assert current_price is not None
    assert current_price.price_per_m2 == Decimal("10500.00")
    assert total == 0
    assert history == []
