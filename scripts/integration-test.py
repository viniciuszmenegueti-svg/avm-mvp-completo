import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
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
    "0.3.1",
)

EXPECTED_APP_ENV = os.getenv(
    "APP_ENV",
    "development",
)


def read_local_env() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[1] / ".env"

    if not env_path.exists():
        return {}

    values: dict[str, str] = {}

    for raw_line in env_path.read_text(
        encoding="utf-8",
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    return values


LOCAL_ENV = read_local_env()

ADMIN_CREDENTIALS_JSON = (
    os.getenv(
        "ADMIN_CREDENTIALS_JSON",
        "",
    ).strip()
    or LOCAL_ENV.get(
        "ADMIN_CREDENTIALS_JSON",
        "",
    ).strip()
)

ADMIN_API_KEY = os.getenv(
    "ADMIN_API_KEY",
    "",
) or LOCAL_ENV.get(
    "ADMIN_API_KEY",
    "",
)

ADMIN_ACTOR = (
    os.getenv(
        "ADMIN_ACTOR",
        "",
    ).strip()
    or LOCAL_ENV.get(
        "ADMIN_ACTOR",
        "integration-test",
    ).strip()
)


def resolve_admin_credentials() -> tuple[str, str]:
    if ADMIN_CREDENTIALS_JSON:
        try:
            credentials = json.loads(ADMIN_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "A variável ADMIN_CREDENTIALS_JSON contém JSON inválido."
            ) from exc

        if not isinstance(credentials, dict) or not credentials:
            raise RuntimeError(
                "A variável ADMIN_CREDENTIALS_JSON deve conter ao menos uma credencial."
            )

        actor, api_key = next(iter(credentials.items()))

        if (
            not isinstance(actor, str)
            or not actor.strip()
            or not isinstance(api_key, str)
            or not api_key
        ):
            raise RuntimeError(
                "A primeira credencial administrativa configurada é inválida."
            )

        return actor.strip(), api_key

    if not ADMIN_API_KEY:
        raise RuntimeError("Nenhuma credencial administrativa foi definida.")

    if not ADMIN_ACTOR:
        raise RuntimeError("A variável ADMIN_ACTOR não foi definida.")

    return ADMIN_ACTOR, ADMIN_API_KEY


RESOLVED_ADMIN_ACTOR, RESOLVED_ADMIN_API_KEY = resolve_admin_credentials()

MAX_READY_ATTEMPTS = 30
READY_INTERVAL_SECONDS = 2

REFUSAL_CITY_IBGE_CODE = "9999999"
REFUSAL_CITY_NAME = "Cidade de Integracao"
REFUSAL_CITY_STATE = "ES"


def request_json(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    expected_status: int = 200,
    additional_headers: dict[str, str] | None = None,
) -> Any:
    data = None
    headers = {
        "Accept": "application/json",
        "X-Request-ID": f"integration-test-{uuid.uuid4()}",
    }

    if additional_headers is not None:
        headers.update(additional_headers)

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
        with urlopen(
            request,
            timeout=10,
        ) as response:
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
            f"{method} {path} retornou HTTP "
            f"{status_code}. "
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


def execute_postgres_sql(sql: str) -> None:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "avm_app",
        "-d",
        "avm",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao executar comando no PostgreSQL. "
            f"Saida: {result.stdout.strip()} "
            f"Erro: {result.stderr.strip()}"
        )


def prepare_refusal_test_city() -> None:
    execute_postgres_sql(
        "DELETE FROM city_valuation_prices "
        f"WHERE city_ibge_code = '{REFUSAL_CITY_IBGE_CODE}'; "
        "DELETE FROM cities "
        f"WHERE city_ibge_code = '{REFUSAL_CITY_IBGE_CODE}'; "
        "INSERT INTO cities "
        "(city_ibge_code, name, state, active) VALUES "
        f"('{REFUSAL_CITY_IBGE_CODE}', "
        f"'{REFUSAL_CITY_NAME}', "
        f"'{REFUSAL_CITY_STATE}', true);"
    )


def remove_refusal_test_city() -> None:
    execute_postgres_sql(
        "DELETE FROM city_valuation_prices "
        f"WHERE city_ibge_code = '{REFUSAL_CITY_IBGE_CODE}'; "
        "DELETE FROM cities "
        f"WHERE city_ibge_code = '{REFUSAL_CITY_IBGE_CODE}';"
    )


def wait_until_ready() -> None:
    print("Aguardando a API ficar pronta...")

    for attempt in range(
        1,
        MAX_READY_ATTEMPTS + 1,
    ):
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


def build_refused_order_payload(
    external_order_id: str,
) -> dict[str, Any]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": REFUSAL_CITY_STATE,
            "city": REFUSAL_CITY_NAME,
            "city_ibge_code": REFUSAL_CITY_IBGE_CODE,
            "postal_code": "29000-000",
            "neighborhood": "Centro",
            "street": "Rua de Integracao",
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


def validate_valuation(
    valuation: dict[str, Any],
    internal_order_id: str,
) -> None:
    assert_equal(
        valuation["internal_order_id"],
        internal_order_id,
        "internal_order_id da avaliação",
    )
    assert_equal(
        valuation["method"],
        "RULE_BASED_V1",
        "método da avaliação",
    )
    assert_equal(
        valuation["estimated_value"],
        "735000.00",
        "valor estimado",
    )
    assert_equal(
        valuation["minimum_value"],
        "661500.00",
        "valor mínimo",
    )
    assert_equal(
        valuation["maximum_value"],
        "808500.00",
        "valor máximo",
    )
    assert_equal(
        valuation["price_per_m2"],
        "10500.00",
        "preço por metro quadrado",
    )
    assert_equal(
        valuation["reference_area_m2"],
        "70.00",
        "área de referência",
    )
    assert_equal(
        valuation["confidence_score"],
        "0.8000",
        "índice de confiança",
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

    print("Verificando bloqueio sem chave administrativa...")
    missing_key_response = request_json(
        method="PATCH",
        path=("/cities/3550308/valuation-prices/APARTMENT"),
        body={
            "price_per_m2": "10500.00",
        },
        expected_status=401,
    )

    assert_equal(
        missing_key_response["detail"]["code"],
        "ADMIN_API_KEY_REQUIRED",
        "código de erro sem chave administrativa",
    )

    print("Verificando bloqueio com chave administrativa inválida...")
    invalid_key_response = request_json(
        method="PATCH",
        path=("/cities/3550308/valuation-prices/APARTMENT"),
        body={
            "price_per_m2": "10500.00",
        },
        expected_status=403,
        additional_headers={
            "X-Admin-API-Key": ("invalid-integration-key"),
        },
    )

    assert_equal(
        invalid_key_response["detail"]["code"],
        "INVALID_ADMIN_API_KEY",
        ("código de erro com chave administrativa inválida"),
    )

    print("Verificando atualização com chave administrativa válida...")
    authorized_price = request_json(
        method="PATCH",
        path=("/cities/3550308/valuation-prices/APARTMENT"),
        body={
            "price_per_m2": "11000.00",
        },
        additional_headers={
            "X-Admin-API-Key": (RESOLVED_ADMIN_API_KEY),
        },
    )

    assert_equal(
        authorized_price["price_per_m2"],
        "11000.00",
        ("preço atualizado com chave administrativa"),
    )

    print("Verificando histórico da alteração de preço...")
    price_history = request_json(
        method="GET",
        path=("/cities/3550308/valuation-prices/APARTMENT/history?limit=1&offset=0"),
    )

    latest_price_history = price_history["items"][0]

    assert_equal(
        latest_price_history["previous_price_per_m2"],
        "10500.00",
        "preço anterior no histórico",
    )
    assert_equal(
        latest_price_history["new_price_per_m2"],
        "11000.00",
        "novo preço no histórico",
    )
    assert_equal(
        latest_price_history["changed_by"],
        RESOLVED_ADMIN_ACTOR,
        "responsável pela alteração de preço",
    )

    print("Restaurando preço-base utilizado pela avaliação...")
    restored_price = request_json(
        method="PATCH",
        path=("/cities/3550308/valuation-prices/APARTMENT"),
        body={
            "price_per_m2": "10500.00",
        },
        additional_headers={
            "X-Admin-API-Key": (RESOLVED_ADMIN_API_KEY),
        },
    )

    assert_equal(
        restored_price["price_per_m2"],
        "10500.00",
        "preço-base restaurado",
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
        path=(f"/orders/external/{external_order_id}"),
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

    print("Atualizando status para VALIDATING_INPUT...")
    updated_order = request_json(
        method="PATCH",
        path=(f"/orders/{internal_order_id}/status"),
        body={
            "status": "VALIDATING_INPUT",
        },
    )

    assert_equal(
        updated_order["status"],
        "VALIDATING_INPUT",
        "status após validação",
    )

    print("Calculando avaliação AVM...")
    created_valuation = request_json(
        method="POST",
        path=(f"/orders/{internal_order_id}/valuation"),
        expected_status=201,
    )

    validate_valuation(
        valuation=created_valuation,
        internal_order_id=internal_order_id,
    )

    valuation_id = created_valuation["valuation_id"]

    print("Consultando avaliação AVM...")
    queried_valuation = request_json(
        method="GET",
        path=(f"/orders/{internal_order_id}/valuation"),
    )

    validate_valuation(
        valuation=queried_valuation,
        internal_order_id=internal_order_id,
    )

    assert_equal(
        queried_valuation["valuation_id"],
        valuation_id,
        "valuation_id consultado",
    )

    print("Confirmando status final da ordem...")
    completed_order = request_json(
        method="GET",
        path=f"/orders/{internal_order_id}",
    )

    assert_equal(
        completed_order["status"],
        "COMPLETED",
        "status final da ordem",
    )

    print("Consultando histórico de status...")
    status_history = request_json(
        method="GET",
        path=(f"/orders/{internal_order_id}/status-history"),
    )

    assert_equal(
        len(status_history),
        2,
        "quantidade de registros no histórico",
    )

    first_history = status_history[0]
    latest_history = status_history[-1]

    assert_equal(
        first_history["previous_status"],
        "RECEIVED",
        "primeiro status anterior",
    )
    assert_equal(
        first_history["new_status"],
        "VALIDATING_INPUT",
        "primeiro status novo",
    )
    assert_equal(
        latest_history["previous_status"],
        "VALIDATING_INPUT",
        "último status anterior",
    )
    assert_equal(
        latest_history["new_status"],
        "COMPLETED",
        "último status novo",
    )

    print("Verificando idempotência da avaliação...")
    repeated_valuation = request_json(
        method="POST",
        path=(f"/orders/{internal_order_id}/valuation"),
        expected_status=201,
    )

    assert_equal(
        repeated_valuation["valuation_id"],
        valuation_id,
        "valuation_id repetido",
    )

    print("Verificando bloqueio de duplicidade da ordem...")
    duplicate_response = request_json(
        method="POST",
        path="/orders",
        body=order_payload,
        expected_status=409,
    )

    if duplicate_response is None:
        raise AssertionError("A resposta de duplicidade está vazia.")

    refused_external_order_id = f"INTEGRATION-REFUSED-{uuid.uuid4().hex[:8].upper()}"

    print("Preparando cidade temporaria sem preco-base...")
    prepare_refusal_test_city()

    try:
        refused_payload = build_refused_order_payload(refused_external_order_id)

        print(f"Criando ordem para recusa {refused_external_order_id}...")
        refused_order = request_json(
            method="POST",
            path="/orders",
            body=refused_payload,
            expected_status=201,
        )

        refused_internal_order_id = refused_order["internal_order_id"]

        assert_equal(
            refused_order["status"],
            "RECEIVED",
            "status inicial da ordem de recusa",
        )

        print("Atualizando ordem de recusa para VALIDATING_INPUT...")
        refused_validating_order = request_json(
            method="PATCH",
            path=(f"/orders/{refused_internal_order_id}/status"),
            body={"status": "VALIDATING_INPUT"},
        )

        assert_equal(
            refused_validating_order["status"],
            "VALIDATING_INPUT",
            "status da ordem antes da recusa",
        )

        print("Verificando recusa por ausencia de preco-base...")
        refused_valuation_response = request_json(
            method="POST",
            path=(f"/orders/{refused_internal_order_id}/valuation"),
            expected_status=409,
        )

        refusal_detail = refused_valuation_response["detail"]

        assert_equal(
            refusal_detail["code"],
            "ORDER_REFUSED",
            "codigo da resposta de ordem recusada",
        )
        assert_equal(
            refusal_detail["internal_order_id"],
            refused_internal_order_id,
            "internal_order_id da resposta de recusa",
        )
        assert_equal(
            refusal_detail["refusal_url"],
            f"/orders/{refused_internal_order_id}/refusal",
            "URL da recusa",
        )

        print("Consultando motivo da recusa...")
        refusal = request_json(
            method="GET",
            path=(f"/orders/{refused_internal_order_id}/refusal"),
        )

        assert_equal(
            refusal["internal_order_id"],
            refused_internal_order_id,
            "internal_order_id da recusa persistida",
        )
        assert_equal(
            refusal["reason_code"],
            "TR_9_5_A",
            "motivo contratual estruturado da recusa",
        )
        assert_equal(
            refusal["details"]["city_ibge_code"],
            REFUSAL_CITY_IBGE_CODE,
            "codigo IBGE nos detalhes da recusa",
        )
        assert_equal(
            refusal["details"]["property_type"],
            "APARTMENT",
            "tipologia nos detalhes da recusa",
        )

        print("Confirmando status REFUSED da ordem...")
        refused_order_after_valuation = request_json(
            method="GET",
            path=f"/orders/{refused_internal_order_id}",
        )

        assert_equal(
            refused_order_after_valuation["status"],
            "REFUSED",
            "status final da ordem recusada",
        )

        print("Consultando historico da ordem recusada...")
        refused_status_history = request_json(
            method="GET",
            path=(f"/orders/{refused_internal_order_id}/status-history"),
        )

        assert_equal(
            len(refused_status_history),
            2,
            "quantidade de registros da ordem recusada",
        )

        refused_latest_history = refused_status_history[-1]

        assert_equal(
            refused_latest_history["previous_status"],
            "VALIDATING_INPUT",
            "status anterior da recusa",
        )
        assert_equal(
            refused_latest_history["new_status"],
            "REFUSED",
            "novo status da recusa",
        )

    finally:
        print("Removendo cidade temporaria do teste...")
        remove_refusal_test_city()

    print("")
    print("Teste de integração concluído com sucesso.")
    print(f"Ordem externa: {external_order_id}")
    print(f"Ordem interna: {internal_order_id}")
    print(f"Avaliação: {valuation_id}")
    print("Valor estimado: R$ 735.000,00")
    print("Status final: COMPLETED")
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
