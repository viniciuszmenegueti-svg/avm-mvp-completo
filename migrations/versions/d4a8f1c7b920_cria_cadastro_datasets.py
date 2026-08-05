"""cria cadastro de datasets

Revision ID: d4a8f1c7b920
Revises: c9f2a6d4e810
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d4a8f1c7b920"
down_revision: str | None = "c9f2a6d4e810"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "datasets"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("data_source_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_key", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_start", sa.Date(), nullable=True),
        sa.Column("reference_end", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_sources.data_source_id"],
            name="fk_datasets_data_source_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
        sa.UniqueConstraint(
            "data_source_id",
            "name_key",
            name="uq_datasets_source_name_key",
        ),
    )
    op.create_index("ix_datasets_data_source_id", TABLE_NAME, ["data_source_id"])
    op.create_index("ix_datasets_status", TABLE_NAME, ["status"])
    op.create_index(
        "ix_datasets_source_status_created_at",
        TABLE_NAME,
        ["data_source_id", "status", "created_at"],
    )
    op.create_index(
        "ix_datasets_status_created_at",
        TABLE_NAME,
        ["status", "created_at"],
    )
    op.create_index(
        "ix_datasets_reference_period",
        TABLE_NAME,
        ["reference_start", "reference_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_datasets_reference_period", table_name=TABLE_NAME)
    op.drop_index("ix_datasets_status_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_datasets_source_status_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_datasets_status", table_name=TABLE_NAME)
    op.drop_index("ix_datasets_data_source_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
