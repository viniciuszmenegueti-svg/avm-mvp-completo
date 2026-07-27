"""enriquece dossie de recusa contratual

Revision ID: d4e6f8a1b2c3
Revises: c8d7e6f5a4b3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e6f8a1b2c3"
down_revision: str | Sequence[str] | None = "c8d7e6f5a4b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_refusals",
        sa.Column(
            "contract_reference",
            sa.String(length=100),
            nullable=False,
            server_default="TR §9.5",
        ),
    )

    op.add_column(
        "order_refusals",
        sa.Column(
            "evidence",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.add_column(
        "order_refusals",
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "order_refusals",
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "order_refusals",
        sa.Column(
            "dataset_version",
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("order_refusals", "dataset_version")
    op.drop_column("order_refusals", "model_version")
    op.drop_column("order_refusals", "detected_at")
    op.drop_column("order_refusals", "evidence")
    op.drop_column("order_refusals", "contract_reference")
