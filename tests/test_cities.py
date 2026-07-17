from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_cities() -> None:
    response = client.get("/cities")

    assert response.status_code == 200

    cities = response.json()

    assert len(cities) == 10

    assert cities[0] == {
        "city_ibge_code": "3106200",
        "name": "Belo Horizonte",
        "state": "MG",
        "active": True,
    }

    assert cities[-1] == {
        "city_ibge_code": "3550308",
        "name": "São Paulo",
        "state": "SP",
        "active": True,
    }


def test_all_returned_cities_are_active() -> None:
    response = client.get("/cities")

    assert response.status_code == 200

    cities = response.json()

    assert all(
        city["active"] is True
        for city in cities
    )


def test_cities_are_sorted_by_name() -> None:
    response = client.get("/cities")

    assert response.status_code == 200

    city_names = [
        city["name"]
        for city in response.json()
    ]

    assert city_names == sorted(city_names)
