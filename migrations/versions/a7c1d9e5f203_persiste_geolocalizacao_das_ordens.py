"""persiste geolocalizacao das ordens

Revision ID: a7c1d9e5f203
Revises: d4e6f8a1b2c3
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a7c1d9e5f203"
down_revision: str | Sequence[str] | None = "d4e6f8a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("location_is_confirmed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "location_confirmation_method",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "location_evidence_reference",
            sa.String(length=250),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "location_failure_reason",
            sa.String(length=500),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "location_verified_by",
            sa.String(length=100),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "location_accuracy_meters",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "location_accuracy_meters")
    op.drop_column("orders", "longitude")
    op.drop_column("orders", "latitude")
    op.drop_column("orders", "location_verified_by")
    op.drop_column("orders", "location_failure_reason")
    op.drop_column("orders", "location_evidence_reference")
    op.drop_column("orders", "location_confirmation_method")
    op.drop_column("orders", "location_is_confirmed")
