"""cadastra cidades iniciais

Revision ID: 9c1f4e2d8a70
Revises: 7a3b58ae0f46
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9c1f4e2d8a70"
down_revision: str | None = "7a3b58ae0f46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


cities_table = sa.table(
    "cities",
    sa.column(
        "city_ibge_code",
        sa.String(length=7),
    ),
    sa.column(
        "name",
        sa.String(length=100),
    ),
    sa.column(
        "state",
        sa.String(length=2),
    ),
    sa.column(
        "active",
        sa.Boolean(),
    ),
)


CITY_IBGE_CODES = (
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
)


def upgrade() -> None:
    op.bulk_insert(
        cities_table,
        [
            {
                "city_ibge_code": "3304557",
                "name": "Rio de Janeiro",
                "state": "RJ",
                "active": True,
            },
            {
                "city_ibge_code": "3550308",
                "name": "São Paulo",
                "state": "SP",
                "active": True,
            },
            {
                "city_ibge_code": "5300108",
                "name": "Brasília",
                "state": "DF",
                "active": True,
            },
            {
                "city_ibge_code": "2927408",
                "name": "Salvador",
                "state": "BA",
                "active": True,
            },
            {
                "city_ibge_code": "3106200",
                "name": "Belo Horizonte",
                "state": "MG",
                "active": True,
            },
            {
                "city_ibge_code": "4106902",
                "name": "Curitiba",
                "state": "PR",
                "active": True,
            },
            {
                "city_ibge_code": "2611606",
                "name": "Recife",
                "state": "PE",
                "active": True,
            },
            {
                "city_ibge_code": "2304400",
                "name": "Fortaleza",
                "state": "CE",
                "active": True,
            },
            {
                "city_ibge_code": "5208707",
                "name": "Goiânia",
                "state": "GO",
                "active": True,
            },
            {
                "city_ibge_code": "4314902",
                "name": "Porto Alegre",
                "state": "RS",
                "active": True,
            },
        ],
    )


def downgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.delete(cities_table).where(
            cities_table.c.city_ibge_code.in_(
                CITY_IBGE_CODES
            )
        )
    )
