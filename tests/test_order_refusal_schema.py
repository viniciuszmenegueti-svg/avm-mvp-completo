from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.order_refusal import (
    OrderRefusalCreate,
    OrderRefusalReason,
    OrderRefusalResponse,
)


def valid_refusal_payload() -> dict[str, object]:
    return {
        "reason_code": "MISSING_BASE_PRICE",
        "message": ("Não existe preço-base configurado para a cidade e tipologia."),
        "details": {
            "city_ibge_code": "3550308",
            "property_type": "APARTMENT",
        },
    }


def test_accepts_valid_order_refusal_create() -> None:
    refusal = OrderRefusalCreate.model_validate(valid_refusal_payload())

    assert refusal.reason_code == OrderRefusalReason.MISSING_BASE_PRICE
    assert refusal.details["city_ibge_code"] == "3550308"


def test_accepts_valid_order_refusal_response() -> None:
    payload = {
        **valid_refusal_payload(),
        "refusal_id": "00000000-0000-0000-0000-000000000001",
        "internal_order_id": "00000000-0000-0000-0000-000000000002",
        "refused_at": datetime.now(timezone.utc),
    }

    refusal = OrderRefusalResponse.model_validate(payload)

    assert refusal.refusal_id
    assert refusal.internal_order_id
    assert refusal.refused_at is not None


def test_uses_empty_details_by_default() -> None:
    refusal = OrderRefusalCreate.model_validate(
        {
            "reason_code": "LOW_CONFIDENCE",
            "message": "A confiança da avaliação ficou abaixo do limite.",
        }
    )

    assert refusal.details == {}


def test_rejects_unknown_refusal_reason() -> None:
    payload = valid_refusal_payload()
    payload["reason_code"] = "UNKNOWN_REASON"

    with pytest.raises(ValidationError):
        OrderRefusalCreate.model_validate(payload)


def test_rejects_missing_refusal_message() -> None:
    payload = valid_refusal_payload()
    del payload["message"]

    with pytest.raises(ValidationError):
        OrderRefusalCreate.model_validate(payload)


def test_rejects_short_refusal_message() -> None:
    payload = valid_refusal_payload()
    payload["message"] = "X"

    with pytest.raises(ValidationError):
        OrderRefusalCreate.model_validate(payload)
