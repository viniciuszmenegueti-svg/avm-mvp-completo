"""versiona importacoes CNEFE e vincula auditoria as ordens

Revision ID: d0f4a6b8c903
Revises: c9e3f5a7b802
Create Date: 2026-07-31
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision: str = "d0f4a6b8c903"
down_revision: str | Sequence[str] | None = "c9e3f5a7b802"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cnefe_imports",
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("source_file_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.String(length=250), nullable=False),
        sa.Column("city_ibge_code", sa.String(length=7), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["city_ibge_code"],
            ["cities.city_ibge_code"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("import_id"),
    )
    op.create_index(
        "ix_cnefe_imports_active_lookup",
        "cnefe_imports",
        ["city_ibge_code", "status", "activated_at"],
        unique=False,
    )

    op.add_column(
        "cnefe_addresses",
        sa.Column("import_id", sa.String(length=36), nullable=True),
    )

    connection = op.get_bind()
    legacy_groups = connection.execute(
        sa.text(
            """
            select city_ibge_code, state, dataset_version, source_file_sha256,
                   count(*) as record_count, min(imported_at) as started_at,
                   max(imported_at) as completed_at
              from cnefe_addresses
             group by city_ibge_code, state, dataset_version, source_file_sha256
            """
        )
    ).mappings()
    for group in legacy_groups:
        import_id = str(uuid4())
        connection.execute(
            sa.text(
                """
                insert into cnefe_imports (
                    import_id, dataset_version, source_file_sha256,
                    source_filename, city_ibge_code, state, status,
                    record_count, failure_reason, started_at,
                    completed_at, activated_at
                ) values (
                    :import_id, :dataset_version, :source_file_sha256,
                    :source_filename, :city_ibge_code, :state, 'ACTIVE',
                    :record_count, null, :started_at,
                    :completed_at, :activated_at
                )
                """
            ),
            {
                "import_id": import_id,
                "dataset_version": group["dataset_version"],
                "source_file_sha256": group["source_file_sha256"],
                "source_filename": "LEGACY-BACKFILL",
                "city_ibge_code": group["city_ibge_code"],
                "state": group["state"],
                "record_count": group["record_count"],
                "started_at": group["started_at"],
                "completed_at": group["completed_at"],
                "activated_at": group["completed_at"],
            },
        )
        connection.execute(
            sa.text(
                """
                update cnefe_addresses
                   set import_id = :import_id
                 where city_ibge_code = :city_ibge_code
                   and dataset_version = :dataset_version
                   and source_file_sha256 = :source_file_sha256
                """
            ),
            {
                "import_id": import_id,
                "city_ibge_code": group["city_ibge_code"],
                "dataset_version": group["dataset_version"],
                "source_file_sha256": group["source_file_sha256"],
            },
        )

    op.alter_column("cnefe_addresses", "import_id", nullable=False)
    op.create_index(
        op.f("ix_cnefe_addresses_import_id"),
        "cnefe_addresses",
        ["import_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_cnefe_addresses_import_id",
        "cnefe_addresses",
        "cnefe_imports",
        ["import_id"],
        ["import_id"],
        ondelete="RESTRICT",
    )

    op.add_column(
        "orders",
        sa.Column("geocoding_audit_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_orders_geocoding_audit_id"),
        "orders",
        ["geocoding_audit_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_orders_geocoding_audit_id",
        "orders",
        "geocoding_audits",
        ["geocoding_audit_id"],
        ["audit_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_orders_geocoding_audit_id",
        "orders",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_orders_geocoding_audit_id"), table_name="orders")
    op.drop_column("orders", "geocoding_audit_id")

    op.drop_constraint(
        "fk_cnefe_addresses_import_id",
        "cnefe_addresses",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_cnefe_addresses_import_id"), table_name="cnefe_addresses")
    op.drop_column("cnefe_addresses", "import_id")
    op.drop_index("ix_cnefe_imports_active_lookup", table_name="cnefe_imports")
    op.drop_table("cnefe_imports")
