"""cria tabela properties

Revision ID: 5053c3aae8b1
Revises: e0e8e75d67eb
Create Date: 2026-07-23 17:07:41.879627

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "5053c3aae8b1"
down_revision: Union[str, Sequence[str], None] = "e0e8e75d67eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria a tabela normalizada e migra os imóveis existentes."""
    op.create_table(
        "properties",
        sa.Column(
            "internal_order_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "property_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=2),
            nullable=False,
        ),
        sa.Column(
            "city",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "city_ibge_code",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "postal_code",
            sa.String(length=9),
            nullable=False,
        ),
        sa.Column(
            "neighborhood",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "street",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "number",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "complement",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "private_area_m2",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "built_area_m2",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "land_area_m2",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
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
        sa.ForeignKeyConstraint(
            ["internal_order_id"],
            ["orders.internal_order_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("internal_order_id"),
    )

    op.create_index(
        op.f("ix_properties_city_ibge_code"),
        "properties",
        ["city_ibge_code"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO properties (
                internal_order_id,
                property_type,
                state,
                city,
                city_ibge_code,
                postal_code,
                neighborhood,
                street,
                number,
                complement,
                private_area_m2,
                built_area_m2,
                land_area_m2,
                bedrooms,
                bathrooms,
                parking_spaces
            )
            SELECT
                internal_order_id,
                property_json::jsonb ->> 'property_type',
                property_json::jsonb ->> 'state',
                property_json::jsonb ->> 'city',
                property_json::jsonb ->> 'city_ibge_code',
                property_json::jsonb ->> 'postal_code',
                property_json::jsonb ->> 'neighborhood',
                property_json::jsonb ->> 'street',
                property_json::jsonb ->> 'number',
                property_json::jsonb ->> 'complement',
                NULLIF(
                    property_json::jsonb ->> 'private_area_m2',
                    ''
                )::numeric(12, 2),
                NULLIF(
                    property_json::jsonb ->> 'built_area_m2',
                    ''
                )::numeric(12, 2),
                NULLIF(
                    property_json::jsonb ->> 'land_area_m2',
                    ''
                )::numeric(12, 2),
                NULLIF(
                    property_json::jsonb ->> 'bedrooms',
                    ''
                )::integer,
                NULLIF(
                    property_json::jsonb ->> 'bathrooms',
                    ''
                )::integer,
                NULLIF(
                    property_json::jsonb ->> 'parking_spaces',
                    ''
                )::integer
            FROM orders
            WHERE property_json IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    """Remove a tabela normalizada de imóveis."""
    op.drop_index(
        op.f("ix_properties_city_ibge_code"),
        table_name="properties",
    )
    op.drop_table("properties")
