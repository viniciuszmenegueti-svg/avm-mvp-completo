"""cria versoes de datasets e registro de importacoes

Revision ID: e6c3b9a2f410
Revises: d4a8f1c7b920
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e6c3b9a2f410"
down_revision: str | None = "d4a8f1c7b920"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "dataset_versions"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=True),
        sa.Column("reference_start", sa.Date(), nullable=True),
        sa.Column("reference_end", sa.Date(), nullable=True),
        sa.Column("record_count", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["dataset_id"],
            ["datasets.dataset_id"],
            name="fk_dataset_versions_dataset_id_datasets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("dataset_version_id"),
        sa.UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_dataset_versions_dataset_version_number",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "checksum_sha256",
            name="uq_dataset_versions_dataset_checksum",
        ),
    )
    op.create_index(
        "ix_dataset_versions_dataset_id", TABLE_NAME, ["dataset_id"], unique=False
    )
    op.create_index(
        "ix_dataset_versions_checksum_sha256",
        TABLE_NAME,
        ["checksum_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_versions_status", TABLE_NAME, ["status"], unique=False
    )
    op.create_index(
        "ix_dataset_versions_dataset_status_created_at",
        TABLE_NAME,
        ["dataset_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_versions_status_created_at",
        TABLE_NAME,
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_versions_created_by_created_at",
        TABLE_NAME,
        ["created_by", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_versions_reference_period",
        TABLE_NAME,
        ["reference_start", "reference_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_versions_reference_period", table_name=TABLE_NAME)
    op.drop_index("ix_dataset_versions_created_by_created_at", table_name=TABLE_NAME)
    op.drop_index("ix_dataset_versions_status_created_at", table_name=TABLE_NAME)
    op.drop_index(
        "ix_dataset_versions_dataset_status_created_at", table_name=TABLE_NAME
    )
    op.drop_index("ix_dataset_versions_status", table_name=TABLE_NAME)
    op.drop_index("ix_dataset_versions_checksum_sha256", table_name=TABLE_NAME)
    op.drop_index("ix_dataset_versions_dataset_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
