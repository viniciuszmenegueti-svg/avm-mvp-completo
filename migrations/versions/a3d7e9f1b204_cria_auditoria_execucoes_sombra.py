"""cria auditoria das execucoes do modelo sombra

Revision ID: a3d7e9f1b204
Revises: f2b6c8d0e125
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a3d7e9f1b204"
down_revision: str | Sequence[str] | None = "f2b6c8d0e125"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shadow_valuation_executions",
        sa.Column(
            "execution_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "internal_order_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "requested_by",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "result_status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "execution_mode",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "contractual_validity",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "formal_homologation",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "value_basis",
            sa.String(length=80),
            nullable=True,
        ),
        sa.Column(
            "estimated_value_brl",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column(
            "confidence_lower_brl",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column(
            "confidence_upper_brl",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column(
            "confidence_level",
            sa.Numeric(precision=7, scale=6),
            nullable=True,
        ),
        sa.Column(
            "confidence_amplitude_percent",
            sa.Numeric(precision=12, scale=6),
            nullable=True,
        ),
        sa.Column(
            "price_per_m2_brl",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),
        sa.Column(
            "artifact_sha256",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "neighborhood",
            sa.String(length=150),
            nullable=True,
        ),
        sa.Column(
            "private_area_m2",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "bedrooms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "bathrooms",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "parking_spaces",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["internal_order_id"],
            ["orders.internal_order_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("execution_id"),
    )

    op.create_index(
        "ix_shadow_valuation_executions_internal_order_id",
        "shadow_valuation_executions",
        ["internal_order_id"],
        unique=False,
    )

    op.create_index(
        "ix_shadow_valuation_executions_request_id",
        "shadow_valuation_executions",
        ["request_id"],
        unique=False,
    )

    op.create_index(
        "ix_shadow_valuation_executions_result_status",
        "shadow_valuation_executions",
        ["result_status"],
        unique=False,
    )

    op.create_index(
        "ix_shadow_valuation_executions_artifact_sha256",
        "shadow_valuation_executions",
        ["artifact_sha256"],
        unique=False,
    )

    op.create_index(
        "ix_shadow_valuation_executions_neighborhood",
        "shadow_valuation_executions",
        ["neighborhood"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shadow_valuation_executions_neighborhood",
        table_name="shadow_valuation_executions",
    )
    op.drop_index(
        "ix_shadow_valuation_executions_artifact_sha256",
        table_name="shadow_valuation_executions",
    )
    op.drop_index(
        "ix_shadow_valuation_executions_result_status",
        table_name="shadow_valuation_executions",
    )
    op.drop_index(
        "ix_shadow_valuation_executions_request_id",
        table_name="shadow_valuation_executions",
    )
    op.drop_index(
        "ix_shadow_valuation_executions_internal_order_id",
        table_name="shadow_valuation_executions",
    )
    op.drop_table("shadow_valuation_executions")
