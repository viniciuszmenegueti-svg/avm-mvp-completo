"""adiciona SLA operacional e auditoria append-only de status

Revision ID: f2b6c8d0e125
Revises: e1a5b7c9d014
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f2b6c8d0e125"
down_revision: str | Sequence[str] | None = "e1a5b7c9d014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _install_append_only_guard(dialect: str) -> None:
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_order_status_history_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'order_status_history is append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_order_status_history_append_only
            BEFORE UPDATE OR DELETE ON order_status_history
            FOR EACH ROW EXECUTE FUNCTION prevent_order_status_history_mutation()
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_order_status_history_no_update
            BEFORE UPDATE ON order_status_history
            BEGIN
                SELECT RAISE(ABORT, 'order_status_history is append-only');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_order_status_history_no_delete
            BEFORE DELETE ON order_status_history
            BEGIN
                SELECT RAISE(ABORT, 'order_status_history is append-only');
            END
            """
        )


def _remove_append_only_guard(dialect: str) -> None:
    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_order_status_history_append_only "
            "ON order_status_history"
        )
        op.execute("DROP FUNCTION IF EXISTS prevent_order_status_history_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_order_status_history_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_order_status_history_no_delete")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise RuntimeError(f"Dialeto não homologado para a migração: {dialect}")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(
            sa.Column("response_deadline_at", sa.DateTime(timezone=True))
        )
        batch_op.add_column(sa.Column("responded_at", sa.DateTime(timezone=True)))

    if dialect == "postgresql":
        op.execute(
            "UPDATE orders SET response_deadline_at = "
            "received_at + INTERVAL '300 seconds' "
            "WHERE response_deadline_at IS NULL"
        )
    else:
        op.execute(
            "UPDATE orders SET response_deadline_at = "
            "datetime(received_at, '+300 seconds') "
            "WHERE response_deadline_at IS NULL"
        )

    op.execute(
        """
        UPDATE orders
        SET responded_at = (
            SELECT MAX(order_status_history.changed_at)
            FROM order_status_history
            WHERE order_status_history.internal_order_id = orders.internal_order_id
              AND order_status_history.new_status IN ('COMPLETED', 'REFUSED', 'CANCELLED')
        )
        WHERE status IN ('COMPLETED', 'REFUSED', 'CANCELLED')
          AND responded_at IS NULL
        """
    )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("response_deadline_at", nullable=False)
        batch_op.create_index(
            "ix_orders_response_deadline_at",
            ["response_deadline_at"],
            unique=False,
        )

    with op.batch_alter_table("order_status_history") as batch_op:
        batch_op.add_column(
            sa.Column(
                "changed_by",
                sa.String(length=100),
                server_default=sa.text("'legacy-system'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "request_id",
                sa.String(length=128),
                server_default=sa.text("'migration-backfill'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "reason_code",
                sa.String(length=100),
                server_default=sa.text("'LEGACY_STATUS_TRANSITION'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "context_json",
                sa.Text(),
                server_default=sa.text("'{}'"),
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_order_status_history_request_id",
            ["request_id"],
            unique=False,
        )

    _install_append_only_guard(dialect)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    _remove_append_only_guard(dialect)

    with op.batch_alter_table("order_status_history") as batch_op:
        batch_op.drop_index("ix_order_status_history_request_id")
        batch_op.drop_column("context_json")
        batch_op.drop_column("reason_code")
        batch_op.drop_column("request_id")
        batch_op.drop_column("changed_by")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_response_deadline_at")
        batch_op.drop_column("responded_at")
        batch_op.drop_column("response_deadline_at")
