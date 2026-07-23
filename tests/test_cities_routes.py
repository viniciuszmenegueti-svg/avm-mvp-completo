from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_lists_active_cities() -> None:
    response = client.get("/cities")

    assert response.status_code == 200

    cities = response.json()

    assert len(cities) == 10

    sao_paulo = next(city for city in cities if city["city_ibge_code"] == "3550308")

    assert sao_paulo == {
        "city_ibge_code": "3550308",
        "name": "São Paulo",
        "state": "SP",
        "active": True,
    }


def test_lists_valuation_prices_for_city() -> None:
    response = client.get("/cities/3550308/valuation-prices")

    assert response.status_code == 200

    prices = response.json()

    assert len(prices) == 3

    assert [price["property_type"] for price in prices] == [
        "APARTMENT",
        "HOUSE",
        "LAND",
    ]

    assert [price["price_per_m2"] for price in prices] == [
        "10500.00",
        "7800.00",
        "5200.00",
    ]

    assert all(price["city_ibge_code"] == "3550308" for price in prices)


def test_returns_empty_list_for_city_without_prices() -> None:
    response = client.get("/cities/3304557/valuation-prices")

    assert response.status_code == 200
    assert response.json() == []


def test_updates_city_valuation_price() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 200

    updated_price = response.json()

    assert updated_price["city_ibge_code"] == "3550308"
    assert updated_price["property_type"] == "APARTMENT"
    assert updated_price["price_per_m2"] == "11000.00"


def test_returns_not_found_when_updating_unknown_price() -> None:
    response = client.patch(
        "/cities/3304557/valuation-prices/APARTMENT",
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == {
        "code": "CITY_VALUATION_PRICE_NOT_FOUND",
        "message": (
            "Não existe preço-base configurado para a cidade e tipologia informadas."
        ),
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
    }


def test_rejects_invalid_price_per_m2() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        json={
            "price_per_m2": "0.00",
        },
    )

    assert response.status_code == 422


def test_rejects_invalid_property_type() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/COMMERCIAL",
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 422
