"""otimiza consultas das execucoes do modelo sombra

Revision ID: b7e4c2a9d610
Revises: a3d7e9f1b204
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op


revision: str = "b7e4c2a9d610"
down_revision: str | None = "a3d7e9f1b204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_NAME = "shadow_valuation_executions"


def upgrade() -> None:
    op.create_index(
        "ix_shadow_executions_executed_at",
        TABLE_NAME,
        ["executed_at"],
        unique=False,
    )

    op.create_index(
        "ix_shadow_executions_status_executed_at",
        TABLE_NAME,
        [
            "result_status",
            "executed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_shadow_executions_requested_by_executed_at",
        TABLE_NAME,
        [
            "requested_by",
            "executed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_shadow_executions_model_version_executed_at",
        TABLE_NAME,
        [
            "model_version",
            "executed_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_shadow_executions_order_executed_at",
        TABLE_NAME,
        [
            "internal_order_id",
            "executed_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shadow_executions_order_executed_at",
        table_name=TABLE_NAME,
    )

    op.drop_index(
        "ix_shadow_executions_model_version_executed_at",
        table_name=TABLE_NAME,
    )

    op.drop_index(
        "ix_shadow_executions_requested_by_executed_at",
        table_name=TABLE_NAME,
    )

    op.drop_index(
        "ix_shadow_executions_status_executed_at",
        table_name=TABLE_NAME,
    )

    op.drop_index(
        "ix_shadow_executions_executed_at",
        table_name=TABLE_NAME,
    )
