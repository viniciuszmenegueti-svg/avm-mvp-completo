"""cadastra precos iniciais de avaliacao

Revision ID: f55aafc1d077
Revises: c4f5ea746445
Create Date: 2026-07-23 08:47:28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f55aafc1d077"
down_revision: Union[str, Sequence[str], None] = "c4f5ea746445"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


city_valuation_prices = sa.table(
    "city_valuation_prices",
    sa.column(
        "city_ibge_code",
        sa.String(length=7),
    ),
    sa.column(
        "property_type",
        sa.String(length=20),
    ),
    sa.column(
        "price_per_m2",
        sa.Numeric(precision=18, scale=2),
    ),
)


INITIAL_PRICES = [
    {
        "city_ibge_code": "3304557",
        "property_type": "APARTMENT",
        "price_per_m2": 9500,
    },
    {
        "city_ibge_code": "3304557",
        "property_type": "HOUSE",
        "price_per_m2": 7200,
    },
    {
        "city_ibge_code": "3304557",
        "property_type": "LAND",
        "price_per_m2": 4800,
    },
    {
        "city_ibge_code": "3550308",
        "property_type": "APARTMENT",
        "price_per_m2": 10500,
    },
    {
        "city_ibge_code": "3550308",
        "property_type": "HOUSE",
        "price_per_m2": 7800,
    },
    {
        "city_ibge_code": "3550308",
        "property_type": "LAND",
        "price_per_m2": 5200,
    },
    {
        "city_ibge_code": "5300108",
        "property_type": "APARTMENT",
        "price_per_m2": 8200,
    },
    {
        "city_ibge_code": "5300108",
        "property_type": "HOUSE",
        "price_per_m2": 6500,
    },
    {
        "city_ibge_code": "5300108",
        "property_type": "LAND",
        "price_per_m2": 4000,
    },
    {
        "city_ibge_code": "2927408",
        "property_type": "APARTMENT",
        "price_per_m2": 6800,
    },
    {
        "city_ibge_code": "2927408",
        "property_type": "HOUSE",
        "price_per_m2": 5200,
    },
    {
        "city_ibge_code": "2927408",
        "property_type": "LAND",
        "price_per_m2": 3200,
    },
    {
        "city_ibge_code": "3106200",
        "property_type": "APARTMENT",
        "price_per_m2": 7600,
    },
    {
        "city_ibge_code": "3106200",
        "property_type": "HOUSE",
        "price_per_m2": 5900,
    },
    {
        "city_ibge_code": "3106200",
        "property_type": "LAND",
        "price_per_m2": 3600,
    },
    {
        "city_ibge_code": "4106902",
        "property_type": "APARTMENT",
        "price_per_m2": 7900,
    },
    {
        "city_ibge_code": "4106902",
        "property_type": "HOUSE",
        "price_per_m2": 6100,
    },
    {
        "city_ibge_code": "4106902",
        "property_type": "LAND",
        "price_per_m2": 3800,
    },
    {
        "city_ibge_code": "2611606",
        "property_type": "APARTMENT",
        "price_per_m2": 6500,
    },
    {
        "city_ibge_code": "2611606",
        "property_type": "HOUSE",
        "price_per_m2": 5000,
    },
    {
        "city_ibge_code": "2611606",
        "property_type": "LAND",
        "price_per_m2": 3100,
    },
    {
        "city_ibge_code": "2304400",
        "property_type": "APARTMENT",
        "price_per_m2": 6400,
    },
    {
        "city_ibge_code": "2304400",
        "property_type": "HOUSE",
        "price_per_m2": 4900,
    },
    {
        "city_ibge_code": "2304400",
        "property_type": "LAND",
        "price_per_m2": 3000,
    },
    {
        "city_ibge_code": "5208707",
        "property_type": "APARTMENT",
        "price_per_m2": 6100,
    },
    {
        "city_ibge_code": "5208707",
        "property_type": "HOUSE",
        "price_per_m2": 4700,
    },
    {
        "city_ibge_code": "5208707",
        "property_type": "LAND",
        "price_per_m2": 2900,
    },
    {
        "city_ibge_code": "4314902",
        "property_type": "APARTMENT",
        "price_per_m2": 7000,
    },
    {
        "city_ibge_code": "4314902",
        "property_type": "HOUSE",
        "price_per_m2": 5400,
    },
    {
        "city_ibge_code": "4314902",
        "property_type": "LAND",
        "price_per_m2": 3300,
    },
]


CITY_IBGE_CODES = [
    "3304557",
    "3550308",
    "5300108",
    "2927408",
    "3106200",
    "4106902",
    "2611606",
    "2304400",
    "5208707",
    "4314902",
]


def upgrade() -> None:
    """Cadastra os preços-base iniciais."""
    op.bulk_insert(
        city_valuation_prices,
        INITIAL_PRICES,
    )


def downgrade() -> None:
    """Remove os preços-base iniciais."""
    op.execute(
        city_valuation_prices.delete().where(
            city_valuation_prices.c.city_ibge_code.in_(CITY_IBGE_CODES)
        )
    )
