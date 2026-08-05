"""endurece artefatos estatisticos e bloqueia modelos legados

Revision ID: e1a5b7c9d014
Revises: d0f4a6b8c903
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e1a5b7c9d014"
down_revision: str | Sequence[str] | None = "d0f4a6b8c903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "statistical_datasets",
        sa.Column(
            "dependent_variable",
            sa.String(length=80),
            server_default="usable_market_value_brl",
            nullable=False,
        ),
    )
    op.add_column(
        "statistical_datasets",
        sa.Column(
            "dependent_variable_unit",
            sa.String(length=30),
            server_default="BRL",
            nullable=False,
        ),
    )
    op.add_column(
        "statistical_datasets",
        sa.Column(
            "dependent_variable_transformation",
            sa.String(length=30),
            server_default="NONE",
            nullable=False,
        ),
    )
    op.add_column(
        "statistical_datasets",
        sa.Column(
            "training_payload_json",
            sa.Text(),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "statistical_datasets",
        sa.Column(
            "feature_ranges_json",
            sa.Text(),
            server_default="{}",
            nullable=False,
        ),
    )

    # V1 did not persist the training payload and therefore cannot be
    # reproduced or re-hashed by the hardened runtime. Fail closed.
    op.execute(
        sa.text(
            "UPDATE statistical_model_versions "
            "SET status = 'DISABLED' "
            "WHERE algorithm_version <> 'OLS_NBR_DIAGNOSTICS_V2'"
        )
    )
    op.create_index(
        "uq_statistical_model_one_homologation_approved",
        "statistical_model_versions",
        ["city_ibge_code", "property_type"],
        unique=True,
        postgresql_where=sa.text("status = 'HOMOLOGATION_APPROVED'"),
        sqlite_where=sa.text("status = 'HOMOLOGATION_APPROVED'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_statistical_model_one_homologation_approved",
        table_name="statistical_model_versions",
    )
    op.drop_column("statistical_datasets", "feature_ranges_json")
    op.drop_column("statistical_datasets", "training_payload_json")
    op.drop_column("statistical_datasets", "dependent_variable_transformation")
    op.drop_column("statistical_datasets", "dependent_variable_unit")
    op.drop_column("statistical_datasets", "dependent_variable")
