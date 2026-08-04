import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCENARIOS: dict[str, dict[str, Any]] = {
    "sp": {
        "state": "SP",
        "city": "São Paulo",
        "city_ibge_code": "3550308",
        "postal_code": "01001-000",
        "neighborhood": "Centro",
        "street": "Praça da Sé",
        "number": "100",
        "latitude": -23.55052,
        "longitude": -46.633308,
    },
    "rj": {
        "state": "RJ",
        "city": "Rio de Janeiro",
        "city_ibge_code": "3304557",
        "postal_code": "22021-001",
        "neighborhood": "Copacabana",
        "street": "Avenida Atlântica",
        "number": "1702",
        "latitude": -22.9711,
        "longitude": -43.1822,
    },
}


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


def credential_values(raw_value: str, variable_name: str) -> list[str]:
    try:
        credentials = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{variable_name} contém JSON inválido.") from error

    if not isinstance(credentials, dict) or not credentials:
        raise RuntimeError(f"{variable_name} deve conter ao menos uma credencial.")

    values = list(credentials.values())
    if any(not isinstance(value, str) or len(value) < 24 for value in values):
        raise RuntimeError(f"{variable_name} contém credencial inválida ou curta.")
    return values


def first_credential(raw_value: str, variable_name: str) -> str:
    return credential_values(raw_value, variable_name)[0]


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


def request_bytes(
    *,
    base_url: str,
    path: str,
    headers: dict[str, str],
) -> bytes:
    request = Request(
        url=f"{base_url.rstrip('/')}{path}",
        headers={"X-Request-ID": f"homologation-artifact-{uuid.uuid4()}", **headers},
        method="GET",
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise AssertionError(f"GET {path} retornou HTTP {response.status}.")
        return response.read()


def assert_value(actual: Any, expected: Any, field_name: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"Valor inesperado para {field_name}: "
            f"recebido={actual!r}, esperado={expected!r}."
        )


def build_order_payload(
    external_order_id: str,
    scenario_name: str = "sp",
) -> dict[str, Any]:
    scenario = SCENARIOS[scenario_name]
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": scenario["state"],
            "city": scenario["city"],
            "city_ibge_code": scenario["city_ibge_code"],
            "postal_code": scenario["postal_code"],
            "neighborhood": scenario["neighborhood"],
            "street": scenario["street"],
            "number": scenario["number"],
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
            "evidence_reference": (
                f"AUTOMATED-NON-CONTRACTUAL-TEST-{scenario_name.upper()}"
            ),
            "verified_by": "HOMOLOGATION_PIPELINE",
            "latitude": scenario["latitude"],
            "longitude": scenario["longitude"],
            "accuracy_meters": 50,
        },
    }


def build_shadow_training_payload(
    model_version: str,
    scenario_name: str = "sp",
) -> dict[str, Any]:
    scenario = SCENARIOS[scenario_name]
    observations: list[list[float]] = []
    values: list[float] = []
    for index in range(48):
        area = 45.0 + index * 1.75
        bedrooms = float(1 + (index % 4))
        bathrooms = float(1 + (index % 3))
        observations.append([area, bedrooms, bathrooms])
        noise = float((index % 7) - 3) * 250.0
        values.append(
            80_000.0
            + 8_500.0 * area
            + 17_000.0 * bedrooms
            + 11_000.0 * bathrooms
            + noise
        )
    matrix = {
        "feature_names": ["private_area_m2", "bedrooms", "bathrooms"],
        "observations": observations,
        "values": values,
    }
    return {
        "city_ibge_code": scenario["city_ibge_code"],
        "property_type": "APARTMENT",
        "dataset_version": (
            f"SHADOW-SYNTHETIC-{scenario_name.upper()}-{model_version}"
        ),
        "source_reference": "AUTOMATED-SHADOW-HOMOLOGATION-NON-CONTRACTUAL",
        "reference_date": "2026-07-31",
        "model_version": model_version,
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "dataset_metadata": {
            "classification": "SYNTHETIC_HOMOLOGATION_ONLY",
            "contractual_use": False,
            "scenario": scenario_name.upper(),
            "city_ibge_code": scenario["city_ibge_code"],
            "purpose": "END_TO_END_INFRASTRUCTURE_VALIDATION_ONLY",
        },
        "dependent_variable": "usable_market_value_brl",
        "dependent_variable_unit": "BRL",
        "dependent_variable_transformation": "NONE",
        "feature_transformations": {},
        **matrix,
        "target": [70.0, 2.0, 2.0],
        "expected_signs": {
            "private_area_m2": 1,
            "bedrooms": 1,
            "bathrooms": 1,
        },
        "confidence_level": 0.8,
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
    admin_keys = credential_values(
        env_values.get("ADMIN_CREDENTIALS_JSON", ""),
        "ADMIN_CREDENTIALS_JSON",
    )
    client_headers = {"X-Client-API-Key": client_key}
    admin_headers = {"X-Admin-API-Key": admin_keys[0]}

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
    configured_mode = env_values.get("MODEL_EXECUTION_MODE", "").strip().upper()
    assert_value(health.get("execution_mode"), configured_mode, "health.execution_mode")

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

    model: dict[str, Any] | None = None
    if configured_mode == "HOMOLOGATION_SHADOW":
        if len(admin_keys) < 2:
            raise RuntimeError(
                "HOMOLOGATION_SHADOW exige duas credenciais administrativas "
                "distintas para separar treino e revisão."
            )
        reviewer_headers = {"X-Admin-API-Key": admin_keys[1]}
        model_version = f"SHADOW-{uuid.uuid4().hex[:12].upper()}"
        model = request_json(
            base_url=args.base_url,
            method="POST",
            path="/statistical-models/train",
            expected_status=201,
            headers=admin_headers,
            body=build_shadow_training_payload(model_version, args.scenario),
        )
        assert_value(model.get("status"), "CANDIDATE", "status do candidato")
        model = request_json(
            base_url=args.base_url,
            method="POST",
            path=f"/statistical-models/{model['model_id']}/approve-homologation",
            expected_status=200,
            headers=reviewer_headers,
            body={
                "approval_reference": (
                    "AUTOMATED-TECHNICAL-HOMOLOGATION-NON-CONTRACTUAL"
                )
            },
        )
        assert_value(
            model.get("status"),
            "HOMOLOGATION_APPROVED",
            "aprovação exclusiva de homologação",
        )
        model_pdf = request_bytes(
            base_url=args.base_url,
            path=f"/statistical-models/{model['model_id']}/report.pdf",
            headers=admin_headers,
        )
        if not model_pdf.startswith(b"%PDF-"):
            raise AssertionError("Relatório do modelo sombra não é um PDF válido.")
        args.artifacts_dir.mkdir(parents=True, exist_ok=True)
        model_pdf_path = args.artifacts_dir / (
            f"MODELO-SOMBRA-{args.scenario.upper()}-{model_version}.pdf"
        )
        model_pdf_path.write_bytes(model_pdf)

    external_order_id = (
        f"HOMOLOGATION-{args.scenario.upper()}-{uuid.uuid4().hex[:12].upper()}"
    )
    order = request_json(
        base_url=args.base_url,
        method="POST",
        path="/orders",
        expected_status=201,
        headers=client_headers,
        body=build_order_payload(external_order_id, args.scenario),
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

    if configured_mode == "HOMOLOGATION_SHADOW":
        valuation = request_json(
            base_url=args.base_url,
            method="POST",
            path=f"/orders/{internal_order_id}/valuation",
            expected_status=201,
            headers=client_headers,
        )
        assert_value(
            valuation.get("method"),
            "LINEAR_REGRESSION_OLS",
            "método estatístico",
        )
        assert_value(
            valuation.get("execution_mode"),
            "HOMOLOGATION_SHADOW",
            "modo da avaliação",
        )
        assert_value(
            valuation.get("contractual_validity"),
            False,
            "validade contratual",
        )
        pdf = request_bytes(
            base_url=args.base_url,
            path=f"/orders/{internal_order_id}/valuation/report.pdf",
            headers=client_headers,
        )
        csv_report = request_bytes(
            base_url=args.base_url,
            path=f"/orders/{internal_order_id}/valuation/report.csv",
            headers=client_headers,
        )
        if not pdf.startswith(b"%PDF-"):
            raise AssertionError("Relatório de homologação não é um PDF válido.")
        args.artifacts_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = args.artifacts_dir / f"{external_order_id}.pdf"
        csv_path = args.artifacts_dir / f"{external_order_id}.csv"
        pdf_path.write_bytes(pdf)
        csv_path.write_bytes(csv_report)
        blocked_delivery = request_json(
            base_url=args.base_url,
            method="PATCH",
            path=f"/orders/{internal_order_id}/status",
            expected_status=409,
            headers=client_headers,
            body={"status": "DELIVERING"},
        )
        assert_value(
            blocked_delivery["detail"]["code"],
            "SHADOW_DELIVERY_BLOCKED",
            "bloqueio de entrega",
        )
        result_details = {
            "model_id": model["model_id"] if model else None,
            "artifact_sha256": model["artifact_sha256"] if model else None,
            "model_report_pdf": str(model_pdf_path.resolve()),
            "model_report_pdf_sha256": hashlib.sha256(model_pdf).hexdigest(),
            "valuation_id": valuation["valuation_id"],
            "estimated_value": valuation["estimated_value"],
            "pdf": str(pdf_path.resolve()),
            "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
            "csv": str(csv_path.resolve()),
            "csv_sha256": hashlib.sha256(csv_report).hexdigest(),
            "delivery_blocked": True,
        }
    else:
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
        result_details = {
            "refusal_code": refusal["reason_code"],
            "refusal_condition": refusal["evidence"]["condition"],
        }

    return {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "environment": configured_environment,
        "execution_mode": configured_mode,
        "scenario": args.scenario,
        "city_ibge_code": SCENARIOS[args.scenario]["city_ibge_code"],
        "external_order_id": external_order_id,
        "internal_order_id": internal_order_id,
        "client_authentication": "passed",
        "admin_authentication": "passed",
        **result_details,
        "approved": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida autenticação, regressão congelada, relatórios e bloqueio "
            "contratual na homologação sombra."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="sp",
        help="Cenário municipal controlado usado no teste ponta a ponta.",
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
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path(".audit/homologation-shadow"),
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
        print(f"Modo de execução: {result['execution_mode']}")
        print(
            f"Cenário: {result['scenario'].upper()} / IBGE {result['city_ibge_code']}"
        )
        if result["execution_mode"] == "HOMOLOGATION_SHADOW":
            print(f"Modelo sombra: {result['model_id']}")
            print(f"PDF: {result['pdf']}")
            print("Entrega contratual: bloqueada")
        else:
            print(f"Recusa segura: {result['refusal_code']}")
        return 0
    except Exception as error:
        print(f"Falha na homologação: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
