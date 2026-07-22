import json
import os
import sys
import time
import uuid
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.getenv(
    "INTEGRATION_BASE_URL",
    "http://localhost:8000",
)

EXPECTED_APP_NAME = os.getenv(
    "APP_NAME",
    "AVM Imoveis API",
)

EXPECTED_APP_VERSION = os.getenv(
    "APP_VERSION",
    "0.1.0",
)

EXPECTED_APP_ENV = os.getenv(
    "APP_ENV",
    "development",
)

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


def assert_equal(
    actual: Any,
    expected: Any,
    field_name: str,
) -> None:
    if actual != expected:
        raise AssertionError(
            f"Valor inesperado para '{field_name}'. "
            f"Recebido: {actual!r}. "
            f"Esperado: {expected!r}."
        )


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


def validate_health_response(
    response: dict[str, Any],
    include_database: bool,
) -> None:
    assert_equal(
        response["status"],
        "ok",
        "status",
    )
    assert_equal(
        response["service"],
        "avm-api",
        "service",
    )
    assert_equal(
        response["name"],
        EXPECTED_APP_NAME,
        "name",
    )
    assert_equal(
        response["version"],
        EXPECTED_APP_VERSION,
        "version",
    )
    assert_equal(
        response["environment"],
        EXPECTED_APP_ENV,
        "environment",
    )

    if include_database:
        assert_equal(
            response["database"],
            "ok",
            "database",
        )


def run_integration_test() -> None:
    print(f"URL da API: {BASE_URL}")
    print(f"Nome esperado: {EXPECTED_APP_NAME}")
    print(f"Versão esperada: {EXPECTED_APP_VERSION}")
    print(f"Ambiente esperado: {EXPECTED_APP_ENV}")
    print("")

    wait_until_ready()

    print("Verificando rota principal...")
    root_response = request_json(
        method="GET",
        path="/",
    )

    assert_equal(
        root_response["message"],
        f"{EXPECTED_APP_NAME} em execução",
        "message",
    )
    assert_equal(
        root_response["name"],
        EXPECTED_APP_NAME,
        "name da rota principal",
    )
    assert_equal(
        root_response["version"],
        EXPECTED_APP_VERSION,
        "version da rota principal",
    )
    assert_equal(
        root_response["status"],
        "running",
        "status da rota principal",
    )
    assert_equal(
        root_response["documentation"],
        "/docs",
        "documentation",
    )

    print("Verificando liveness...")
    live_response = request_json(
        method="GET",
        path="/health/live",
    )
    validate_health_response(
        response=live_response,
        include_database=False,
    )

    print("Verificando readiness...")
    ready_response = request_json(
        method="GET",
        path="/health/ready",
    )
    validate_health_response(
        response=ready_response,
        include_database=True,
    )

    print("Verificando cidades...")
    cities = request_json(
        method="GET",
        path="/cities",
    )
    assert_equal(
        len(cities),
        10,
        "quantidade de cidades",
    )

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

    assert_equal(
        created_order["external_order_id"],
        external_order_id,
        "external_order_id",
    )
    assert_equal(
        created_order["status"],
        "RECEIVED",
        "status inicial",
    )

    print("Consultando ordem pelo identificador externo...")
    queried_order = request_json(
        method="GET",
        path=f"/orders/external/{external_order_id}",
    )

    assert_equal(
        queried_order["internal_order_id"],
        internal_order_id,
        "internal_order_id",
    )
    assert_equal(
        queried_order["external_order_id"],
        external_order_id,
        "external_order_id consultado",
    )

    print("Atualizando status da ordem...")
    updated_order = request_json(
        method="PATCH",
        path=f"/orders/{internal_order_id}/status",
        body={"status": "VALIDATING_INPUT"},
    )

    assert_equal(
        updated_order["status"],
        "VALIDATING_INPUT",
        "status atualizado",
    )

    print("Consultando histórico de status...")
    status_history = request_json(
        method="GET",
        path=f"/orders/{internal_order_id}/status-history",
    )

    if len(status_history) < 1:
        raise AssertionError("O histórico de status está vazio.")

    latest_history = status_history[-1]

    assert_equal(
        latest_history["previous_status"],
        "RECEIVED",
        "status anterior do histórico",
    )
    assert_equal(
        latest_history["new_status"],
        "VALIDATING_INPUT",
        "novo status do histórico",
    )

    print("Verificando bloqueio de duplicidade...")
    duplicate_response = request_json(
        method="POST",
        path="/orders",
        body=order_payload,
        expected_status=409,
    )

    if duplicate_response is None:
        raise AssertionError("A resposta de duplicidade está vazia.")

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
        print(f"Falha no teste de integração: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
