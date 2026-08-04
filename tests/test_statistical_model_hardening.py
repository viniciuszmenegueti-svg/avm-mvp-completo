import json
import hashlib
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.database import SessionLocal
from app.main import app
from app.repositories.statistical_models_sqlalchemy import get_statistical_model
from app.schemas.property import PropertyInput
from app.services.model_report_service import _format_axis_value, _scatter_plot
from app.services.statistical_valuation_service import (
    StatisticalModelInputError,
    calculate_statistical_valuation,
)


client = TestClient(app)
TRAINER_HEADERS = {"X-Admin-API-Key": "avm-test-admin-key"}
REVIEWER_HEADERS = {"X-Admin-API-Key": "avm-test-reviewer-key"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_824_000.0, "1.82 mi"),
        (30_000.0, "30 mil"),
        (2.94, "2.94"),
    ],
)
def test_formats_report_axis_values_without_clipping(
    value: float, expected: str
) -> None:
    assert _format_axis_value(value) == expected


def test_scatter_plot_accepts_constant_axes() -> None:
    drawing = _scatter_plot(
        x=np.asarray([1.0, 1.0]),
        y=np.asarray([2.0, 2.0]),
        x_label="Eixo X",
        y_label="Eixo Y",
    )

    assert drawing.width == 500.0
    assert drawing.height == 210.0


def training_payload() -> dict[str, object]:
    observations: list[list[float]] = []
    values: list[float] = []
    for index in range(36):
        area = 50.0 + index * 2.0
        bedrooms = float(1 + index % 4)
        observations.append([area, bedrooms])
        noise = float((index % 5) - 2) * 400.0
        values.append(90_000.0 + 7_000.0 * area + 20_000.0 * bedrooms + noise)
    return {
        "city_ibge_code": "3550308",
        "property_type": "APARTMENT",
        "dataset_version": f"CONTROLLED-{uuid4().hex}",
        "source_reference": "CONTROLLED-REPRODUCIBLE-HOMOLOGATION-DATASET",
        "reference_date": "2026-07-31",
        "model_version": f"HARDENED-{uuid4().hex}",
        "valid_from": "2026-01-01",
        "valid_until": "2026-12-31",
        "dataset_metadata": {"classification": "SYNTHETIC_TEST_ONLY"},
        "dependent_variable": "usable_market_value_brl",
        "dependent_variable_unit": "BRL",
        "dependent_variable_transformation": "NONE",
        "feature_transformations": {},
        "feature_names": ["private_area_m2", "bedrooms"],
        "observations": observations,
        "values": values,
        "target": [80.0, 2.0],
        "expected_signs": {"private_area_m2": 1, "bedrooms": 1},
        "confidence_level": 0.8,
    }


def apartment(*, area: float) -> PropertyInput:
    return PropertyInput.model_validate(
        {
            "property_type": "APARTMENT",
            "state": "SP",
            "city": "São Paulo",
            "city_ibge_code": "3550308",
            "postal_code": "01001-000",
            "neighborhood": "Centro",
            "street": "Praça da Sé",
            "number": "100",
            "private_area_m2": area,
            "built_area_m2": area + 10,
            "bedrooms": 2,
            "bathrooms": 1,
            "parking_spaces": 1,
        }
    )


def train_and_approve() -> dict[str, object]:
    trained = client.post(
        "/statistical-models/train",
        json=training_payload(),
        headers=TRAINER_HEADERS,
    )
    assert trained.status_code == 201, trained.text
    approved = client.post(
        f"/statistical-models/{trained.json()['model_id']}/approve-homologation",
        json={"approval_reference": "INDEPENDENT-TECHNICAL-REVIEW"},
        headers=REVIEWER_HEADERS,
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_server_computes_dataset_hash_and_rejects_a_false_claim() -> None:
    payload = training_payload()
    payload["dataset_sha256"] = "a" * 64

    response = client.post(
        "/statistical-models/train", json=payload, headers=TRAINER_HEADERS
    )

    assert response.status_code == 422
    assert "does not match" in response.json()["detail"]["message"]


def test_training_rejects_feature_incompatible_with_property_type() -> None:
    payload = training_payload()
    payload["feature_names"] = ["land_area_m2", "bedrooms"]
    payload["expected_signs"] = {"land_area_m2": 1, "bedrooms": 1}

    response = client.post(
        "/statistical-models/train", json=payload, headers=TRAINER_HEADERS
    )

    assert response.status_code == 422


def test_homologation_requires_independent_reviewer() -> None:
    trained = client.post(
        "/statistical-models/train",
        json=training_payload(),
        headers=TRAINER_HEADERS,
    )
    response = client.post(
        f"/statistical-models/{trained.json()['model_id']}/approve-homologation",
        json={"approval_reference": "SELF-REVIEW-MUST-FAIL"},
        headers=TRAINER_HEADERS,
    )

    assert response.status_code == 409
    assert "Segregação de funções" in response.json()["detail"]["message"]


def test_inference_rechecks_artifact_hash_domain_and_property_precision() -> None:
    approved = train_and_approve()
    model_id = str(approved["model_id"])

    with SessionLocal() as session:
        model = get_statistical_model(session, model_id)
        assert model is not None
        valid = calculate_statistical_valuation(
            session, property_data=apartment(area=80.0), model=model
        )
        assert valid.calculation.factors["precision_grade_for_property"] in {
            "I",
            "II",
            "III",
        }
        assert (
            valid.calculation.factors["full_nbr_fundamentation_grade"]
            == "NOT_CALCULATED"
        )

        with pytest.raises(StatisticalModelInputError, match="Extrapolação bloqueada"):
            calculate_statistical_valuation(
                session, property_data=apartment(area=1.0), model=model
            )

        coefficients = json.loads(model.coefficients_json)
        coefficients[0] += 1.0
        model.coefficients_json = json.dumps(coefficients)
        session.commit()

        with pytest.raises(StatisticalModelInputError, match="artifact hash"):
            calculate_statistical_valuation(
                session, property_data=apartment(area=80.0), model=model
            )


def test_generates_separate_non_contractual_model_report() -> None:
    approved = train_and_approve()

    response = client.get(
        f"/statistical-models/{approved['model_id']}/report.pdf",
        headers=REVIEWER_HEADERS,
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10_000
    assert response.headers["x-contractual-validity"] == "false"
    assert response.headers["x-model-artifact-sha256"] == approved["artifact_sha256"]
    assert (
        response.headers["x-report-sha256"]
        == hashlib.sha256(response.content).hexdigest()
    )
    assert "HOMOLOGACAO-modelo-" in response.headers["content-disposition"]


def test_asking_price_training_is_persisted_as_research_and_cannot_be_approved() -> (
    None
):
    payload = training_payload()
    payload["dependent_variable"] = "asking_price_brl"
    payload["dataset_metadata"] = {
        "training_classification": "RESEARCH_ONLY",
        "market_dataset_model_ready": False,
    }

    trained = client.post(
        "/statistical-models/train",
        json=payload,
        headers=TRAINER_HEADERS,
    )

    assert trained.status_code == 201, trained.text
    assert trained.json()["status"] == "CANDIDATE"
    assert trained.json()["dependent_variable"] == "asking_price_brl"

    report = client.get(
        f"/statistical-models/{trained.json()['model_id']}/report.pdf",
        headers=TRAINER_HEADERS,
    )
    assert report.status_code == 200
    assert report.headers["x-model-use-scope"] == "research-only"
    assert "PESQUISA-modelo-" in report.headers["content-disposition"]

    approval = client.post(
        f"/statistical-models/{trained.json()['model_id']}/approve-homologation",
        json={"approval_reference": "RESEARCH-CANNOT-BE-PROMOTED"},
        headers=REVIEWER_HEADERS,
    )
    assert approval.status_code == 409
    assert "preço pedido" in approval.json()["detail"]["message"]


def test_asking_price_training_requires_explicit_research_classification() -> None:
    payload = training_payload()
    payload["dependent_variable"] = "asking_price_brl"

    response = client.post(
        "/statistical-models/train",
        json=payload,
        headers=TRAINER_HEADERS,
    )

    assert response.status_code == 422
    assert "RESEARCH_ONLY" in response.text
