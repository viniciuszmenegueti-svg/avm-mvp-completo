import json
import sys
import time
import uuid
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"
MAX_READY_ATTEMPTS = 30
READY_INTERVAL_SECONDS = 2


def request_json(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> Any:
    data = None
    headers = {
        "Accept": "application/json",
        "X-Request-ID": f"integration-test-{uuid.uuid4()}",
    }

    if body is not None:
        data = json.dumps(
            body,
            ensure_ascii=False,
        ).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(
        url=f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=10) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8")

    except HTTPError as error:
        status_code = error.code
        response_body = error.read().decode("utf-8")

    except OSError as error:
        raise RuntimeError(
            f"Não foi possível acessar {BASE_URL}{path}: {error}"
        ) from error

    if status_code != expected_status:
        raise AssertionError(
            f"{method} {path} retornou HTTP {status_code}. "
            f"Esperado: {expected_status}. "
            f"Resposta: {response_body}"
        )

    if not response_body:
        return None

    return json.loads(response_body)


def wait_until_ready() -> None:
    print("Aguardando a API ficar pronta...")

    for attempt in range(1, MAX_READY_ATTEMPTS + 1):
        try:
            response = request_json(
                method="GET",
                path="/health/ready",
            )

            if response.get("status") == "ok" and response.get("database") == "ok":
                print("API pronta.")
                return

        except (
            AssertionError,
            RuntimeError,
            json.JSONDecodeError,
        ) as error:
            print(f"Tentativa {attempt}/{MAX_READY_ATTEMPTS} falhou: {error}")

        if attempt < MAX_READY_ATTEMPTS:
            print(f"Nova tentativa em {READY_INTERVAL_SECONDS} segundos.")
            time.sleep(READY_INTERVAL_SECONDS)

    raise RuntimeError("A API não ficou pronta dentro do prazo.")


def build_order_payload(
    external_order_id: str,
) -> dict[str, Any]:
    return {
        "external_order_id": external_order_id,
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
    }


def run_integration_test() -> None:
    wait_until_ready()

    print("Verificando liveness...")
    live_response = request_json(
        method="GET",
        path="/health/live",
    )

    assert live_response["status"] == "ok"
    assert live_response["service"] == "avm-api"
    assert live_response["name"] == "AVM Imoveis API"
    assert live_response["version"] == "0.1.0"
    assert live_response["environment"] == "test"

    print("Verificando readiness...")
    ready_response = request_json(
        method="GET",
        path="/health/ready",
    )

    assert ready_response["status"] == "ok"
    assert ready_response["service"] == "avm-api"
    assert ready_response["name"] == "AVM Imoveis API"
    assert ready_response["version"] == "0.1.0"
    assert ready_response["environment"] == "test"
    assert ready_response["database"] == "ok"

    print("Verificando cidades...")
    cities = request_json(
        method="GET",
        path="/cities",
    )
    assert len(cities) == 10

    external_order_id = f"INTEGRATION-{uuid.uuid4().hex[:12].upper()}"
    order_payload = build_order_payload(external_order_id)

    print(f"Criando ordem {external_order_id}...")
    created_order = request_json(
        method="POST",
        path="/orders",
        body=order_payload,
        expected_status=201,
    )

    internal_order_id = created_order["internal_order_id"]

    assert created_order["external_order_id"] == external_order_id
    assert created_order["status"] == "RECEIVED"

    print("Consultando ordem pelo identificador externo...")
    queried_order = request_json(
        method="GET",
        path=f"/orders/external/{external_order_id}",
    )

    assert queried_order["internal_order_id"] == internal_order_id
    assert queried_order["external_order_id"] == external_order_id

    print("Atualizando status da ordem...")
    updated_order = request_json(
        method="PATCH",
        path=f"/orders/{internal_order_id}/status",
        body={"status": "VALIDATING_INPUT"},
    )

    assert updated_order["status"] == "VALIDATING_INPUT"

    print("Consultando histórico de status...")
    status_history = request_json(
        method="GET",
        path=f"/orders/{internal_order_id}/status-history",
    )

    assert len(status_history) >= 1

    latest_history = status_history[-1]

    assert latest_history["previous_status"] == "RECEIVED"
    assert latest_history["new_status"] == "VALIDATING_INPUT"

    print("Verificando bloqueio de duplicidade...")
    duplicate_response = request_json(
        method="POST",
        path="/orders",
        body=order_payload,
        expected_status=409,
    )

    assert duplicate_response is not None

    print("")
    print("Teste de integração concluído com sucesso.")
    print(f"Ordem externa: {external_order_id}")
    print(f"Ordem interna: {internal_order_id}")
    print("Status final: VALIDATING_INPUT")
    print("Duplicidade: bloqueada com HTTP 409")


def main() -> int:
    try:
        run_integration_test()
        return 0

    except Exception as error:
        print("")
        print(f"Falha no teste de integração: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
