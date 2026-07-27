from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.order_refusal_model import OrderRefusalModel
from app.schemas.order_refusal import OrderRefusalCreate


def create_order_refusal(
    session: Session,
    refusal_id: str,
    internal_order_id: str,
    refusal: OrderRefusalCreate,
    refused_at: datetime,
    commit: bool = True,
) -> OrderRefusalModel:
    database_refusal = OrderRefusalModel(
        refusal_id=refusal_id,
        internal_order_id=internal_order_id,
        reason_code=refusal.reason_code.value,
        message=refusal.message,
        details=refusal.details,
        contract_reference=refusal.contract_reference,
        evidence=refusal.evidence,
        detected_at=refusal.detected_at,
        model_version=refusal.model_version,
        dataset_version=refusal.dataset_version,
        refused_at=refused_at,
    )

    session.add(database_refusal)

    if commit:
        session.commit()
        session.refresh(database_refusal)
    else:
        session.flush()

    return database_refusal


def get_order_refusal_by_internal_order_id(
    session: Session,
    internal_order_id: str,
) -> OrderRefusalModel | None:
    statement = select(OrderRefusalModel).where(
        OrderRefusalModel.internal_order_id == internal_order_id
    )

    return session.scalar(statement)
