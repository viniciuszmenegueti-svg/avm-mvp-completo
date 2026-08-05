"""Persistência das execuções auditáveis do modelo sombra."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
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
    """Persiste uma execução sombra sem alterar a avaliação oficial."""

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


def list_paginated_shadow_valuation_executions_by_order(
    session: Session,
    internal_order_id: str,
    *,
    limit: int,
    offset: int,
) -> tuple[
    list[ShadowValuationExecutionModel],
    int,
]:
    """Lista o histórico sombra da ordem com paginação."""

    filters = (
        ShadowValuationExecutionModel.internal_order_id
        == internal_order_id,
    )

    total_statement = select(
        func.count(
            ShadowValuationExecutionModel.execution_id
        )
    ).where(*filters)

    total = int(
        session.scalar(total_statement) or 0
    )

    statement: Select[
        tuple[ShadowValuationExecutionModel]
    ] = (
        select(ShadowValuationExecutionModel)
        .where(*filters)
        .order_by(
            ShadowValuationExecutionModel.executed_at.desc(),
            ShadowValuationExecutionModel.execution_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    executions = list(
        session.scalars(statement).all()
    )

    return executions, total


def search_shadow_valuation_executions(
    session: Session,
    *,
    result_status: str | None = None,
    internal_order_id: str | None = None,
    requested_by: str | None = None,
    model_version: str | None = None,
    neighborhood: str | None = None,
    executed_from: datetime | None = None,
    executed_until: datetime | None = None,
    limit: int,
    offset: int,
) -> tuple[
    list[ShadowValuationExecutionModel],
    int,
]:
    """Pesquisa globalmente as execu??es sombra audit?veis."""

    filters = []

    if result_status is not None:
        filters.append(
            ShadowValuationExecutionModel.result_status
            == result_status
        )

    if internal_order_id is not None:
        filters.append(
            ShadowValuationExecutionModel.internal_order_id
            == internal_order_id
        )

    if requested_by is not None:
        filters.append(
            ShadowValuationExecutionModel.requested_by
            == requested_by
        )

    if model_version is not None:
        filters.append(
            ShadowValuationExecutionModel.model_version
            == model_version
        )

    if neighborhood is not None:
        filters.append(
            ShadowValuationExecutionModel.neighborhood
            == neighborhood
        )

    if executed_from is not None:
        filters.append(
            ShadowValuationExecutionModel.executed_at
            >= executed_from
        )

    if executed_until is not None:
        filters.append(
            ShadowValuationExecutionModel.executed_at
            <= executed_until
        )

    total_statement = select(
        func.count(
            ShadowValuationExecutionModel.execution_id
        )
    ).where(*filters)

    total = int(
        session.scalar(total_statement) or 0
    )

    statement: Select[
        tuple[ShadowValuationExecutionModel]
    ] = (
        select(ShadowValuationExecutionModel)
        .where(*filters)
        .order_by(
            ShadowValuationExecutionModel.executed_at.desc(),
            ShadowValuationExecutionModel.execution_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    executions = list(
        session.scalars(statement).all()
    )

    return executions, total

