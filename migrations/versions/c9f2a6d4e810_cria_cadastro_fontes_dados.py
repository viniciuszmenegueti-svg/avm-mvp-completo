"""cria cadastro de fontes de dados

Revision ID: c9f2a6d4e810
Revises: b7e4c2a9d610
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c9f2a6d4e810"
down_revision: str | None = "b7e4c2a9d610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_NAME = "data_sources"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("data_source_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_key", sa.String(length=150), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("responsible", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
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
        sa.PrimaryKeyConstraint("data_source_id"),
        sa.UniqueConstraint("name_key", name="uq_data_sources_name_key"),
    )
    op.create_index("ix_data_sources_name_key", TABLE_NAME, ["name_key"])
    op.create_index("ix_data_sources_source_type", TABLE_NAME, ["source_type"])
    op.create_index("ix_data_sources_responsible", TABLE_NAME, ["responsible"])
    op.create_index("ix_data_sources_status", TABLE_NAME, ["status"])
    op.create_index(
        "ix_data_sources_status_created_at",
        TABLE_NAME,
        ["status", "created_at"],
    )
    op.create_index(
        "ix_data_sources_type_created_at",
        TABLE_NAME,
        ["source_type", "created_at"],
    )
    op.create_index(
        "ix_data_sources_responsible_created_at",
        TABLE_NAME,
        ["responsible", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_sources_responsible_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_type_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_status_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_status", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_responsible", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_source_type", table_name=TABLE_NAME)
    op.drop_index("ix_data_sources_name_key", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
