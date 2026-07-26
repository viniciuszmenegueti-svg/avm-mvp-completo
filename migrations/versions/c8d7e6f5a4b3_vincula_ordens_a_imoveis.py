"""vincula ordens a imoveis

Revision ID: c8d7e6f5a4b3
Revises: b2c9a134e7d5
Create Date: 2026-07-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c8d7e6f5a4b3"
down_revision: Union[str, Sequence[str], None] = "b2c9a134e7d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("property_asset_id", sa.String(length=36), nullable=True)
    )
    op.create_index(
        op.f("ix_orders_property_asset_id"),
        "orders",
        ["property_asset_id"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "orders",
        "property_assets",
        ["property_asset_id"],
        ["property_asset_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(None, "orders", type_="foreignkey")
    op.drop_index(op.f("ix_orders_property_asset_id"), table_name="orders")
    op.drop_column("orders", "property_asset_id")
