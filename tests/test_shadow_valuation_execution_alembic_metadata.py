"""Garantias de registro do modelo sombra no metadata do Alembic."""

from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.infrastructure.database import Base


def test_shadow_execution_table_is_registered_in_base_metadata() -> None:
    assert (
        Base.metadata.tables["shadow_valuation_executions"]
        is ShadowValuationExecutionModel.__table__
    )
