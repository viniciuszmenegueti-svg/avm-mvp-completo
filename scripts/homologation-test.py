import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"Arquivo de ambiente não encontrado: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def first_credential(raw_value: str, variable_name: str) -> str:
    try:
        credentials = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{variable_name} contém JSON inválido.") from error

    if not isinstance(credentials, dict) or not credentials:
        raise RuntimeError(f"{variable_name} deve conter ao menos uma credencial.")

    credential = next(iter(credentials.values()))
    if not isinstance(credential, str) or len(credential) < 24:
        raise RuntimeError(f"{variable_name} contém credencial inválida ou curta.")
    return credential


def request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    expected_status: int,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request_headers = {
        "Accept": "application/json",
        "X-Request-ID": f"homologation-test-{uuid.uuid4()}",
        **(headers or {}),
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=data,
        headers=request_headers,
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
            f"Não foi possível acessar {request.full_url}: {error}"
        ) from error

    if status_code != expected_status:
        raise AssertionError(
            f"{method} {path} retornou HTTP {status_code}; "
            f"esperado {expected_status}. Resposta: {response_body}"
        )
    if not response_body:
        return {}
    parsed = json.loads(response_body)
    if not isinstance(parsed, dict):
        raise AssertionError(f"{method} {path} não retornou um objeto JSON.")
    return parsed


def assert_value(actual: Any, expected: Any, field_name: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"Valor inesperado para {field_name}: "
            f"recebido={actual!r}, esperado={expected!r}."
        )


def build_order_payload(external_order_id: str) -> dict[str, Any]:
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Praça da Sé",
            "number": "100",
            "complement": "Teste automatizado de homologação",
            "private_area_m2": 70,
            "built_area_m2": 80,
            "land_area_m2": None,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
        "conflict_of_interest": {
            "has_conflict": False,
        },
        "location_confirmation": {
            "is_confirmed": True,
            "confirmation_method": "HOMOLOGATION_TEST",
            "evidence_reference": "AUTOMATED-NON-CONTRACTUAL-TEST",
            "verified_by": "HOMOLOGATION_PIPELINE",
            "latitude": -23.55052,
            "longitude": -46.633308,
            "accuracy_meters": 50,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    env_values = read_env_file(args.env_file)
    configured_environment = env_values.get("APP_ENV", "").strip().lower()
    if configured_environment not in {
        "homologation",
        "staging",
        "production",
        "prod",
    }:
        raise RuntimeError(
            "O teste exige APP_ENV seguro (homologation, staging ou production)."
        )
    if env_values.get("ALLOW_SYNTHETIC_PRICING", "").strip().lower() != "false":
        raise RuntimeError("ALLOW_SYNTHETIC_PRICING deve estar explicitamente false.")

    client_key = first_credential(
        env_values.get("CLIENT_CREDENTIALS_JSON", ""),
        "CLIENT_CREDENTIALS_JSON",
    )
    admin_key = first_credential(
        env_values.get("ADMIN_CREDENTIALS_JSON", ""),
        "ADMIN_CREDENTIALS_JSON",
    )
    client_headers = {"X-Client-API-Key": client_key}
    admin_headers = {"X-Admin-API-Key": admin_key}

    health = request_json(
        base_url=args.base_url,
        method="GET",
        path="/health/ready",
        expected_status=200,
    )
    assert_value(health.get("status"), "ok", "health.status")
    assert_value(health.get("database"), "ok", "health.database")
    assert_value(
        str(health.get("environment", "")).lower(),
        configured_environment,
        "health.environment",
    )

    missing_client = request_json(
        base_url=args.base_url,
        method="GET",
        path="/orders",
        expected_status=401,
    )
    assert_value(
        missing_client["detail"]["code"],
        "CLIENT_API_KEY_REQUIRED",
        "erro sem credencial cliente",
    )
    invalid_client = request_json(
        base_url=args.base_url,
        method="GET",
        path="/orders",
        expected_status=403,
        headers={"X-Client-API-Key": "invalid-homologation-key"},
    )
    assert_value(
        invalid_client["detail"]["code"],
        "INVALID_CLIENT_API_KEY",
        "erro com credencial cliente inválida",
    )
    request_json(
        base_url=args.base_url,
        method="GET",
        path="/orders",
        expected_status=200,
        headers=client_headers,
    )

    missing_admin = request_json(
        base_url=args.base_url,
        method="GET",
        path="/admin/diagnostics",
        expected_status=401,
    )
    assert_value(
        missing_admin["detail"]["code"],
        "ADMIN_API_KEY_REQUIRED",
        "erro sem credencial administrativa",
    )
    invalid_admin = request_json(
        base_url=args.base_url,
        method="GET",
        path="/admin/diagnostics",
        expected_status=403,
        headers={"X-Admin-API-Key": "invalid-homologation-key"},
    )
    assert_value(
        invalid_admin["detail"]["code"],
        "INVALID_ADMIN_API_KEY",
        "erro com credencial administrativa inválida",
    )
    request_json(
        base_url=args.base_url,
        method="GET",
        path="/admin/diagnostics",
        expected_status=200,
        headers=admin_headers,
    )

    external_order_id = f"HOMOLOGATION-{uuid.uuid4().hex[:16].upper()}"
    order = request_json(
        base_url=args.base_url,
        method="POST",
        path="/orders",
        expected_status=201,
        headers=client_headers,
        body=build_order_payload(external_order_id),
    )
    assert_value(order.get("status"), "RECEIVED", "status inicial da ordem")
    internal_order_id = str(order["internal_order_id"])

    validating_order = request_json(
        base_url=args.base_url,
        method="PATCH",
        path=f"/orders/{internal_order_id}/status",
        expected_status=200,
        headers=client_headers,
        body={"status": "VALIDATING_INPUT"},
    )
    assert_value(
        validating_order.get("status"),
        "VALIDATING_INPUT",
        "status antes da tentativa de avaliação",
    )

    refused_valuation = request_json(
        base_url=args.base_url,
        method="POST",
        path=f"/orders/{internal_order_id}/valuation",
        expected_status=409,
        headers=client_headers,
    )
    assert_value(
        refused_valuation["detail"]["code"],
        "ORDER_REFUSED",
        "resposta da avaliação bloqueada",
    )
    refusal = request_json(
        base_url=args.base_url,
        method="GET",
        path=f"/orders/{internal_order_id}/refusal",
        expected_status=200,
        headers=client_headers,
    )
    assert_value(refusal.get("reason_code"), "TR_9_5_A", "motivo de recusa")
    assert_value(
        refusal["evidence"].get("condition"),
        "SYNTHETIC_PRICING_BLOCKED",
        "condição de recusa",
    )

    return {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "environment": configured_environment,
        "external_order_id": external_order_id,
        "internal_order_id": internal_order_id,
        "client_authentication": "passed",
        "admin_authentication": "passed",
        "synthetic_pricing_status": 409,
        "refusal_code": refusal["reason_code"],
        "refusal_condition": refusal["evidence"]["condition"],
        "approved": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida autenticação e bloqueio sintético na homologação."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env.homologation"),
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8001",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".audit/homologation-result.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Homologação técnica validada com sucesso.")
        print(f"Evidência: {args.output.resolve()}")
        print(f"Ordem: {result['external_order_id']}")
        print("Autenticação cliente: ok")
        print("Autenticação administrativa: ok")
        print("Bloqueio sintético: TR_9_5_A / SYNTHETIC_PRICING_BLOCKED")
        return 0
    except Exception as error:
        print(f"Falha na homologação: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
