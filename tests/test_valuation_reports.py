from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _create_valuation() -> str:
    response = client.post(
        "/orders",
        json={
            "external_order_id": "REPORT-001",
            "property": {
                "property_type": "APARTMENT",
                "state": "SP",
                "city": "São Paulo",
                "city_ibge_code": "3550308",
                "postal_code": "01001-000",
                "neighborhood": "Centro",
                "street": "Rua de Teste",
                "number": "100",
                "complement": "Apartamento 10",
                "private_area_m2": 70,
                "built_area_m2": 80,
                "land_area_m2": None,
                "bedrooms": 2,
                "bathrooms": 2,
                "parking_spaces": 1,
            },
        },
    )
    assert response.status_code == 201
    order_id = response.json()["internal_order_id"]
    assert (
        client.patch(
            f"/orders/{order_id}/status",
            json={"status": "VALIDATING_INPUT"},
        ).status_code
        == 200
    )
    assert client.post(f"/orders/{order_id}/valuation").status_code == 201
    return order_id


def test_exports_pdf_report() -> None:
    order_id = _create_valuation()
    response = client.get(f"/orders/{order_id}/valuation/report.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1_000


def test_exports_csv_report() -> None:
    order_id = _create_valuation()
    response = client.get(f"/orders/{order_id}/valuation/report.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    decoded = response.content.decode("utf-8-sig")
    assert "campo,valor" in decoded
    assert "Ordem externa,REPORT-001" in decoded
    assert "Valor estimado (R$),735000.00" in decoded
