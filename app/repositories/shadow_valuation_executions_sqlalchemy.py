"""Persist?ncia das execu??es audit?veis do modelo sombra."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)


def add_shadow_valuation_execution(
    session: Session,
    execution: ShadowValuationExecutionModel,
    *,
    commit: bool = True,
) -> ShadowValuationExecutionModel:
    """Persiste uma execu??o sombra sem alterar a avalia??o oficial."""

    session.add(execution)

    try:
        if commit:
            session.commit()
            session.refresh(execution)
        else:
            session.flush()
    except Exception:
        if commit:
            session.rollback()
        raise

    return execution


def get_shadow_valuation_execution(
    session: Session,
    execution_id: str,
) -> ShadowValuationExecutionModel | None:
    return session.get(
        ShadowValuationExecutionModel,
        execution_id,
    )


def list_shadow_valuation_executions_by_order(
    session: Session,
    internal_order_id: str,
) -> list[ShadowValuationExecutionModel]:
    statement: Select[tuple[ShadowValuationExecutionModel]] = (
        select(ShadowValuationExecutionModel)
        .where(
            ShadowValuationExecutionModel.internal_order_id
            == internal_order_id
        )
        .order_by(
            ShadowValuationExecutionModel.executed_at.desc(),
            ShadowValuationExecutionModel.execution_id.desc(),
        )
    )

    return list(
        session.scalars(statement).all()
    )
