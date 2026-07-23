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
