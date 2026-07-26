"""adiciona explicabilidade avaliacoes

Revision ID: b2c9a134e7d5
Revises: 81e4b0f7c2a1
Create Date: 2026-07-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b2c9a134e7d5"
down_revision: Union[str, Sequence[str], None] = "81e4b0f7c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "valuations",
        sa.Column("factors_json", sa.Text(), server_default="{}", nullable=False),
    )
    op.add_column(
        "valuations",
        sa.Column(
            "confidence_reasons_json", sa.Text(), server_default="[]", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("valuations", "confidence_reasons_json")
    op.drop_column("valuations", "factors_json")
