from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.domain.exceptions import (
    InvalidOrderStatusTransitionError,
)
from app.infrastructure.dependencies import DatabaseSession
from app.repositories.valuations_sqlalchemy import (
    get_valuation_by_internal_order_id,
)
from app.schemas.valuation import ValuationResponse
from app.services.valuation_service import (
    calculate_and_store_valuation,
)
from engine.registry import ModelVersionNotActiveError


router = APIRouter(
    prefix="/orders",
    tags=["Avaliações AVM"],
)


@router.post(
    "/{internal_order_id}/valuation",
    response_model=ValuationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calcula e armazena a avaliação AVM de uma ordem",
)
def create_order_valuation(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> ValuationResponse:
    order_id = str(internal_order_id)

    try:
        valuation = calculate_and_store_valuation(
            session=session,
            internal_order_id=order_id,
        )
    except InvalidOrderStatusTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATUS_TRANSITION",
                "message": str(error),
                "current_status": error.current_status,
                "new_status": error.new_status,
            },
        ) from error
    except ModelVersionNotActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AVM_MODEL_NOT_ACTIVE",
                "message": str(error),
                "method": error.method.value,
                "model_status": error.model_status.value,
                "internal_order_id": order_id,
            },
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "code": "VALUATION_CALCULATION_ERROR",
                "message": str(error),
                "internal_order_id": order_id,
            },
        ) from error

    if valuation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORDER_NOT_FOUND",
                "message": ("Ordem de Serviço não encontrada."),
                "internal_order_id": order_id,
            },
        )

    return valuation


@router.get(
    "/{internal_order_id}/valuation",
    response_model=ValuationResponse,
    summary="Consulta a avaliação AVM de uma ordem",
)
def get_order_valuation(
    internal_order_id: UUID,
    session: DatabaseSession,
) -> ValuationResponse:
    order_id = str(internal_order_id)

    valuation = get_valuation_by_internal_order_id(
        session=session,
        internal_order_id=order_id,
    )

    if valuation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "VALUATION_NOT_FOUND",
                "message": ("Avaliação AVM não encontrada."),
                "internal_order_id": order_id,
            },
        )

    return valuation
