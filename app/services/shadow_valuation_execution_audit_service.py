"""Registro operacional das execu??es do modelo AVM sombra."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.repositories.shadow_valuation_executions_sqlalchemy import (
    add_shadow_valuation_execution,
)
from app.schemas.property import PropertyInput
from app.services.shadow_valuation_service import (
    ShadowValuationResult,
)


class ShadowExecutionResultStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def _decimal_or_none(
    value: int | float | Decimal | None,
) -> Decimal | None:
    if value is None:
        return None

    return Decimal(str(value))


def _base_execution(
    *,
    internal_order_id: str,
    property_data: PropertyInput,
    requested_by: str,
    request_id: str | None,
    result_status: ShadowExecutionResultStatus,
    error_message: str | None,
) -> ShadowValuationExecutionModel:
    return ShadowValuationExecutionModel(
        execution_id=str(uuid4()),
        internal_order_id=internal_order_id,
        request_id=request_id,
        requested_by=requested_by,
        result_status=result_status.value,
        execution_mode="SHADOW",
        contractual_validity=False,
        formal_homologation=False,
        neighborhood=property_data.neighborhood,
        private_area_m2=_decimal_or_none(
            property_data.private_area_m2
        ),
        bedrooms=property_data.bedrooms,
        bathrooms=property_data.bathrooms,
        parking_spaces=property_data.parking_spaces,
        error_message=error_message,
    )


def record_successful_shadow_execution(
    *,
    session: Session,
    internal_order_id: str,
    property_data: PropertyInput,
    result: ShadowValuationResult,
    requested_by: str,
    request_id: str | None,
    commit: bool = True,
) -> ShadowValuationExecutionModel:
    prediction = result.prediction

    execution = _base_execution(
        internal_order_id=internal_order_id,
        property_data=property_data,
        requested_by=requested_by,
        request_id=request_id,
        result_status=ShadowExecutionResultStatus.SUCCESS,
        error_message=None,
    )

    execution.model_name = prediction.model_name
    execution.model_version = prediction.model_version
    execution.value_basis = prediction.value_basis
    execution.estimated_value_brl = _decimal_or_none(
        prediction.estimated_value_brl
    )
    execution.confidence_lower_brl = _decimal_or_none(
        prediction.confidence_lower_brl
    )
    execution.confidence_upper_brl = _decimal_or_none(
        prediction.confidence_upper_brl
    )
    execution.confidence_level = _decimal_or_none(
        prediction.confidence_level
    )
    execution.confidence_amplitude_percent = _decimal_or_none(
        prediction.confidence_amplitude_percent
    )
    execution.price_per_m2_brl = _decimal_or_none(
        prediction.price_per_m2_brl
    )
    execution.artifact_sha256 = prediction.artifact_sha256

    return add_shadow_valuation_execution(
        session,
        execution,
        commit=commit,
    )


def record_not_applicable_shadow_execution(
    *,
    session: Session,
    internal_order_id: str,
    property_data: PropertyInput,
    requested_by: str,
    request_id: str | None,
    error_message: str,
    commit: bool = True,
) -> ShadowValuationExecutionModel:
    execution = _base_execution(
        internal_order_id=internal_order_id,
        property_data=property_data,
        requested_by=requested_by,
        request_id=request_id,
        result_status=(
            ShadowExecutionResultStatus.NOT_APPLICABLE
        ),
        error_message=error_message[:2000],
    )

    return add_shadow_valuation_execution(
        session,
        execution,
        commit=commit,
    )
