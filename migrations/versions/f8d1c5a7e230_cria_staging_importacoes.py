"""cria staging e validacao de importacoes

Revision ID: f8d1c5a7e230
Revises: e6c3b9a2f410
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f8d1c5a7e230"
down_revision: str | None = "e6c3b9a2f410"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_import_executions",
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["dataset_versions.dataset_version_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    op.create_index(
        "ix_dataset_import_executions_dataset_version_id",
        "dataset_import_executions",
        ["dataset_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_executions_status",
        "dataset_import_executions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_executions_version_created_at",
        "dataset_import_executions",
        ["dataset_version_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_executions_status_created_at",
        "dataset_import_executions",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "dataset_import_rows",
        sa.Column("row_id", sa.String(length=36), nullable=False),
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("original_json", sa.Text(), nullable=False),
        sa.Column("normalized_json", sa.Text(), nullable=True),
        sa.Column("errors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("row_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["dataset_import_executions.execution_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["dataset_versions.dataset_version_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("row_id"),
        sa.UniqueConstraint(
            "execution_id",
            "line_number",
            name="uq_dataset_import_rows_execution_line",
        ),
    )
    op.create_index(
        "ix_dataset_import_rows_execution_id",
        "dataset_import_rows",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_rows_dataset_version_id",
        "dataset_import_rows",
        ["dataset_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_rows_status",
        "dataset_import_rows",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_rows_execution_status_line",
        "dataset_import_rows",
        ["execution_id", "status", "line_number"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_rows_version_status",
        "dataset_import_rows",
        ["dataset_version_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_import_rows_execution_row_hash",
        "dataset_import_rows",
        ["execution_id", "row_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dataset_import_rows_execution_row_hash",
        table_name="dataset_import_rows",
    )
    op.drop_index(
        "ix_dataset_import_rows_version_status",
        table_name="dataset_import_rows",
    )
    op.drop_index(
        "ix_dataset_import_rows_execution_status_line",
        table_name="dataset_import_rows",
    )
    op.drop_index("ix_dataset_import_rows_status", table_name="dataset_import_rows")
    op.drop_index(
        "ix_dataset_import_rows_dataset_version_id",
        table_name="dataset_import_rows",
    )
    op.drop_index(
        "ix_dataset_import_rows_execution_id",
        table_name="dataset_import_rows",
    )
    op.drop_table("dataset_import_rows")
    op.drop_index(
        "ix_dataset_import_executions_status_created_at",
        table_name="dataset_import_executions",
    )
    op.drop_index(
        "ix_dataset_import_executions_version_created_at",
        table_name="dataset_import_executions",
    )
    op.drop_index(
        "ix_dataset_import_executions_status",
        table_name="dataset_import_executions",
    )
    op.drop_index(
        "ix_dataset_import_executions_dataset_version_id",
        table_name="dataset_import_executions",
    )
    op.drop_table("dataset_import_executions")
