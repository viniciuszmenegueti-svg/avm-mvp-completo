"""expande property assets

Revision ID: 81e4b0f7c2a1
Revises: 4f0be0101ba0
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "81e4b0f7c2a1"
down_revision: Union[str, Sequence[str], None] = "4f0be0101ba0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "property_assets", sa.Column("complement", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("property_assets", "complement")
