from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.infrastructure.database import SessionLocal
from app.repositories.orders_sqlalchemy import create_order
from app.schemas.order import (
    OrderCreate,
    OrderStatus,
)
from app.schemas.valuation import ValuationMethod
from app.services.order_status_update import (
    update_order_status_with_history,
)
from app.services.valuation_service import (
    calculate_and_store_valuation,
)
from engine.models.rule_based_v1 import (
    ValuationCalculation,
)
from engine.registry import (
    DEFAULT_MODEL_METHOD,
    ModelStatus,
    ModelVersion,
    ModelVersionNotActiveError,
)


def order_payload(
    external_order_id: str,
) -> dict[str, object]:
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


def create_test_order(
    external_order_id: str,
) -> str:
    internal_order_id = str(uuid4())

    order = OrderCreate.model_validate(order_payload(external_order_id))

    with SessionLocal() as session:
        create_order(
            session=session,
            order=order,
            internal_order_id=internal_order_id,
            received_at=datetime.now(timezone.utc),
        )

    with SessionLocal() as session:
        updated_order = update_order_status_with_history(
            session=session,
            internal_order_id=internal_order_id,
            new_status=(OrderStatus.VALIDATING_INPUT),
        )

    assert updated_order is not None

    return internal_order_id


def test_valuation_service_uses_active_registry_model() -> None:
    internal_order_id = create_test_order("VALUATION-REGISTRY-001")

    calculator = Mock(
        return_value=ValuationCalculation(
            method=ValuationMethod.RULE_BASED_V1,
            estimated_value=Decimal("700000.00"),
            minimum_value=Decimal("630000.00"),
            maximum_value=Decimal("770000.00"),
            price_per_m2=Decimal("10000.00"),
            reference_area_m2=Decimal("70.00"),
            confidence_score=Decimal("0.8000"),
        )
    )

    model_version = ModelVersion(
        method=ValuationMethod.RULE_BASED_V1,
        version="1.0.0-test",
        status=ModelStatus.ACTIVE,
        calculator=calculator,
        description=("Modelo usado no teste do registry."),
    )

    with (
        patch(
            ("app.services.valuation_service.get_active_model_version"),
            return_value=model_version,
        ) as registry_mock,
        SessionLocal() as session,
    ):
        valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=internal_order_id,
        )

    assert valuation is not None
    assert valuation.method == ValuationMethod.RULE_BASED_V1
    assert valuation.model_version == "1.0.0-test"
    assert valuation.estimated_value == Decimal("700000.00")

    registry_mock.assert_called_once_with(DEFAULT_MODEL_METHOD)
    calculator.assert_called_once()


def test_valuation_service_rejects_inactive_model() -> None:
    internal_order_id = create_test_order("VALUATION-REGISTRY-002")

    error = ModelVersionNotActiveError(
        method=ValuationMethod.RULE_BASED_V1,
        model_status=ModelStatus.DISABLED,
    )

    with (
        patch(
            ("app.services.valuation_service.get_active_model_version"),
            side_effect=error,
        ) as registry_mock,
        SessionLocal() as session,
    ):
        with pytest.raises(
            ModelVersionNotActiveError,
            match=("Modelo AVM não está ativo: RULE_BASED_V1. Status atual: DISABLED."),
        ):
            calculate_and_store_valuation(
                session=session,
                internal_order_id=internal_order_id,
            )

    registry_mock.assert_called_once_with(DEFAULT_MODEL_METHOD)
