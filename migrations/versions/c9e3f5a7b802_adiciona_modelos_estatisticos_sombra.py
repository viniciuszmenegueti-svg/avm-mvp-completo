"""adiciona modelos estatisticos para homologacao sombra

Revision ID: c9e3f5a7b802
Revises: b8d2e4f6a701
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c9e3f5a7b802"
down_revision: str | Sequence[str] | None = "b8d2e4f6a701"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "statistical_datasets",
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("city_ibge_code", sa.String(length=7), nullable=False),
        sa.Column("property_type", sa.String(length=30), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("variable_count", sa.Integer(), nullable=False),
        sa.Column("dataset_sha256", sa.String(length=64), nullable=False),
        sa.Column("training_matrix_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_ibge_code"], ["cities.city_ibge_code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index(
        op.f("ix_statistical_datasets_city_ibge_code"),
        "statistical_datasets",
        ["city_ibge_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_statistical_datasets_property_type"),
        "statistical_datasets",
        ["property_type"],
        unique=False,
    )

    op.create_table(
        "statistical_model_versions",
        sa.Column("model_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("city_ibge_code", sa.String(length=7), nullable=False),
        sa.Column("property_type", sa.String(length=30), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("feature_names_json", sa.Text(), nullable=False),
        sa.Column("coefficients_json", sa.Text(), nullable=False),
        sa.Column("covariance_json", sa.Text(), nullable=False),
        sa.Column("diagnostics_json", sa.Text(), nullable=False),
        sa.Column("expected_signs_json", sa.Text(), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("trained_by", sa.String(length=100), nullable=False),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approval_reference", sa.String(length=250), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["city_ibge_code"], ["cities.city_ibge_code"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["statistical_datasets.dataset_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("model_id"),
        sa.UniqueConstraint(
            "city_ibge_code",
            "property_type",
            "model_version",
            name="uq_statistical_model_city_type_version",
        ),
    )
    op.create_index(
        op.f("ix_statistical_model_versions_dataset_id"),
        "statistical_model_versions",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "ix_statistical_model_applicability",
        "statistical_model_versions",
        [
            "city_ibge_code",
            "property_type",
            "status",
            "valid_from",
            "valid_until",
        ],
        unique=False,
    )

    op.add_column(
        "valuations",
        sa.Column(
            "execution_mode",
            sa.String(length=40),
            server_default="DEMONSTRATION",
            nullable=False,
        ),
    )
    op.add_column(
        "valuations",
        sa.Column("statistical_model_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "valuations",
        sa.Column("model_artifact_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "valuations",
        sa.Column("dataset_sha256", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_valuations_statistical_model_id",
        "valuations",
        "statistical_model_versions",
        ["statistical_model_id"],
        ["model_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_valuations_statistical_model_id", "valuations", type_="foreignkey"
    )
    op.drop_column("valuations", "dataset_sha256")
    op.drop_column("valuations", "model_artifact_sha256")
    op.drop_column("valuations", "statistical_model_id")
    op.drop_column("valuations", "execution_mode")
    op.drop_index(
        "ix_statistical_model_applicability",
        table_name="statistical_model_versions",
    )
    op.drop_index(
        op.f("ix_statistical_model_versions_dataset_id"),
        table_name="statistical_model_versions",
    )
    op.drop_table("statistical_model_versions")
    op.drop_index(
        op.f("ix_statistical_datasets_property_type"),
        table_name="statistical_datasets",
    )
    op.drop_index(
        op.f("ix_statistical_datasets_city_ibge_code"),
        table_name="statistical_datasets",
    )
    op.drop_table("statistical_datasets")
