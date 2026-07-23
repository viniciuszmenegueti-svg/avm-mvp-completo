from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ADMIN_HEADERS = {
    "X-Admin-API-Key": "avm-local-admin-key",
}


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
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 200

    updated_price = response.json()

    assert updated_price["city_ibge_code"] == "3550308"
    assert updated_price["property_type"] == "APARTMENT"
    assert updated_price["price_per_m2"] == "11000.00"


def test_requires_admin_key_to_update_price() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == {
        "code": "ADMIN_API_KEY_REQUIRED",
        "message": ("A chave administrativa deve ser informada."),
    }


def test_rejects_invalid_admin_key() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers={
            "X-Admin-API-Key": "invalid-key",
        },
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 403

    assert response.json()["detail"] == {
        "code": "INVALID_ADMIN_API_KEY",
        "message": ("A chave administrativa informada é inválida."),
    }


def test_records_price_change_history() -> None:
    update_response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert update_response.status_code == 200

    history_response = client.get("/cities/3550308/valuation-prices/APARTMENT/history")

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total"] == 1
    assert history["limit"] == 20
    assert history["offset"] == 0
    assert len(history["items"]) == 1

    history_item = history["items"][0]

    assert history_item["city_ibge_code"] == "3550308"
    assert history_item["property_type"] == "APARTMENT"
    assert history_item["previous_price_per_m2"] == "10500.00"
    assert history_item["new_price_per_m2"] == "11000.00"


def test_paginates_price_change_history() -> None:
    first_update_response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert first_update_response.status_code == 200

    second_update_response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11500.00",
        },
    )

    assert second_update_response.status_code == 200

    history_response = client.get(
        ("/cities/3550308/valuation-prices/APARTMENT/history?limit=1&offset=1")
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total"] == 2
    assert history["limit"] == 1
    assert history["offset"] == 1
    assert len(history["items"]) == 1
    assert history["items"][0]["new_price_per_m2"] == "11000.00"


def test_does_not_record_history_when_price_is_unchanged() -> None:
    update_response = client.patch(
        "/cities/3550308/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "10500.00",
        },
    )

    assert update_response.status_code == 200

    history_response = client.get("/cities/3550308/valuation-prices/APARTMENT/history")

    assert history_response.status_code == 200
    assert history_response.json() == {
        "total": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


def test_returns_empty_history_for_price_without_changes() -> None:
    response = client.get("/cities/3550308/valuation-prices/HOUSE/history")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "limit": 20,
        "offset": 0,
        "items": [],
    }


def test_returns_not_found_when_updating_unknown_price() -> None:
    response = client.patch(
        "/cities/3304557/valuation-prices/APARTMENT",
        headers=ADMIN_HEADERS,
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
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "0.00",
        },
    )

    assert response.status_code == 422


def test_rejects_invalid_property_type() -> None:
    response = client.patch(
        "/cities/3550308/valuation-prices/COMMERCIAL",
        headers=ADMIN_HEADERS,
        json={
            "price_per_m2": "11000.00",
        },
    )

    assert response.status_code == 422


def test_rejects_invalid_history_pagination() -> None:
    response = client.get(
        ("/cities/3550308/valuation-prices/APARTMENT/history?limit=0&offset=-1")
    )

    assert response.status_code == 422
