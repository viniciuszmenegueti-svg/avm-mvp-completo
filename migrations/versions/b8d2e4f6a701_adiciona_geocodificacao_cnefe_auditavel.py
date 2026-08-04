"""adiciona geocodificacao CNEFE auditavel

Revision ID: b8d2e4f6a701
Revises: a7c1d9e5f203
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b8d2e4f6a701"
down_revision: str | Sequence[str] | None = "a7c1d9e5f203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cnefe_addresses",
        sa.Column("record_key", sa.String(length=64), nullable=False),
        sa.Column("provider_record_id", sa.String(length=100), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("source_file_sha256", sa.String(length=64), nullable=False),
        sa.Column("city_ibge_code", sa.String(length=7), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("postal_code", sa.String(length=8), nullable=False),
        sa.Column("locality", sa.String(length=150), nullable=True),
        sa.Column("street", sa.String(length=250), nullable=False),
        sa.Column("street_name", sa.String(length=200), nullable=False),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("number_modifier", sa.String(length=40), nullable=True),
        sa.Column("complement", sa.String(length=250), nullable=True),
        sa.Column("normalized_street", sa.String(length=250), nullable=False),
        sa.Column("normalized_street_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_number", sa.String(length=40), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("geocoding_level", sa.SmallInteger(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "geocoding_level between 1 and 6",
            name="ck_cnefe_addresses_geocoding_level",
        ),
        sa.CheckConstraint(
            "latitude between -90 and 90",
            name="ck_cnefe_addresses_latitude",
        ),
        sa.CheckConstraint(
            "longitude between -180 and 180",
            name="ck_cnefe_addresses_longitude",
        ),
        sa.ForeignKeyConstraint(
            ["city_ibge_code"],
            ["cities.city_ibge_code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("record_key"),
    )
    op.create_index(
        "ix_cnefe_addresses_exact_lookup",
        "cnefe_addresses",
        ["city_ibge_code", "postal_code", "normalized_street", "normalized_number"],
        unique=False,
    )
    op.create_index(
        "ix_cnefe_addresses_name_lookup",
        "cnefe_addresses",
        [
            "city_ibge_code",
            "postal_code",
            "normalized_street_name",
            "normalized_number",
        ],
        unique=False,
    )

    op.create_table(
        "geocoding_audits",
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("query_sha256", sa.String(length=64), nullable=False),
        sa.Column("city_ibge_code", sa.String(length=7), nullable=False),
        sa.Column("normalized_postal_code", sa.String(length=8), nullable=False),
        sa.Column("normalized_street", sa.String(length=250), nullable=False),
        sa.Column("normalized_number", sa.String(length=40), nullable=False),
        sa.Column("result_status", sa.String(length=50), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("selected_record_key", sa.String(length=64), nullable=True),
        sa.Column("dataset_version", sa.String(length=80), nullable=True),
        sa.Column("source_file_sha256", sa.String(length=64), nullable=True),
        sa.Column("evidence_reference", sa.String(length=250), nullable=True),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["selected_record_key"],
            ["cnefe_addresses.record_key"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        op.f("ix_geocoding_audits_city_ibge_code"),
        "geocoding_audits",
        ["city_ibge_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_geocoding_audits_request_id"),
        "geocoding_audits",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_geocoding_audits_request_id"),
        table_name="geocoding_audits",
    )
    op.drop_index(
        op.f("ix_geocoding_audits_city_ibge_code"),
        table_name="geocoding_audits",
    )
    op.drop_table("geocoding_audits")
    op.drop_index("ix_cnefe_addresses_name_lookup", table_name="cnefe_addresses")
    op.drop_index("ix_cnefe_addresses_exact_lookup", table_name="cnefe_addresses")
    op.drop_table("cnefe_addresses")
