import csv
import io

from fastapi.testclient import TestClient

from app.main import app
from app.services.report_service import (
    _neutralize_csv_formula,
    _trusted_numeric_engine_value,
)


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
            "location_confirmation": {
                "is_confirmed": True,
                "confirmation_method": "CNEFE",
                "evidence_reference": "CNEFE-TESTE-REPORT-001",
                "verified_by": "GEOCODER-TESTE",
                "latitude": -23.550520,
                "longitude": -46.633308,
                "accuracy_meters": 35,
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
    assert len(response.content) > 30_000


def test_exports_csv_report() -> None:
    order_id = _create_valuation()
    response = client.get(f"/orders/{order_id}/valuation/report.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    decoded = response.content.decode("utf-8-sig")
    assert "campo,valor" in decoded
    assert "identificacao.Ordem de Serviço externa,REPORT-001" in decoded
    assert 'imovel.Endereço,"Rua de Teste, 100' in decoded
    assert "imovel.Quartos,2" in decoded
    assert "geolocalizacao.Latitude,-23.550520°" in decoded
    assert "geolocalizacao.Longitude,-46.633308°" in decoded
    assert 'geolocalizacao.Imprecisão declarada,"35,00 m"' in decoded
    assert 'resultado.Valor estimado,"R$ 735.000,00"' in decoded
    assert "conformidade.Assinatura eletrônica do Responsável Técnico.status" in decoded
    assert ",PENDENTE" in decoded
    assert (
        "conformidade.Coordenadas e precisão máxima de 50 m.status,ATENDIDO" in decoded
    )


def test_csv_neutralizes_formula_injection_and_preserves_numeric_output() -> None:
    create_response = client.post(
        "/orders",
        json={
            "external_order_id": "=HYPERLINK(1)",
            "property": {
                "property_type": "APARTMENT",
                "state": "SP",
                "city": "São Paulo",
                "city_ibge_code": "3550308",
                "postal_code": "-1234567",
                "neighborhood": "@NEIGHBORHOOD",
                "street": "+STREET",
                "number": "=1",
                "complement": "@UNIT",
                "private_area_m2": 70,
                "built_area_m2": 80,
                "land_area_m2": None,
                "bedrooms": 2,
                "bathrooms": 2,
                "parking_spaces": 1,
            },
            "location_confirmation": {
                "is_confirmed": True,
                "confirmation_method": "\t=METHOD",
                "evidence_reference": "\r=EVIDENCE",
                "verified_by": "  @VERIFIER",
                "latitude": -23.550520,
                "longitude": -46.633308,
                "accuracy_meters": 35,
            },
        },
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["internal_order_id"]
    assert (
        client.patch(
            f"/orders/{order_id}/status",
            json={"status": "VALIDATING_INPUT"},
        ).status_code
        == 200
    )
    assert client.post(f"/orders/{order_id}/valuation").status_code == 201

    response = client.get(f"/orders/{order_id}/valuation/report.csv")

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    decoded = response.content.decode("utf-8-sig")
    rows = dict(csv.reader(io.StringIO(decoded, newline="")))
    assert rows["identificacao.Ordem de Serviço externa"] == "'=HYPERLINK(1)"
    assert rows["imovel.Endereço"].startswith("'+STREET")
    assert rows["imovel.Bairro"] == "'@NEIGHBORHOOD"
    assert rows["imovel.Município/UF"] == "São Paulo/SP"
    assert rows["imovel.CEP"] == "'-1234567"
    assert rows["geolocalizacao.Método de confirmação"] == "'\t=METHOD"
    assert rows["geolocalizacao.Referência da evidência/fonte"] == "'\r=EVIDENCE"
    assert rows["geolocalizacao.Verificado por"] == "'  @VERIFIER"
    assert rows["geolocalizacao.Latitude"] == "-23.550520°"
    assert rows["geolocalizacao.Longitude"] == "-46.633308°"

    negative_engine_number = _trusted_numeric_engine_value("-0.125")
    assert _neutralize_csv_formula(negative_engine_number) == "-0.125"
    assert _neutralize_csv_formula("-0.125") == "'-0.125"
    for dangerous in (
        "=FORMULA",
        "+FORMULA",
        "-FORMULA",
        "@FORMULA",
        "\t=FORMULA",
        "\r=FORMULA",
        "\n=FORMULA",
        "\v=FORMULA",
        "\f=FORMULA",
        "  =FORMULA",
        "\ufeff=FORMULA",
    ):
        assert _neutralize_csv_formula(dangerous).startswith("'")
