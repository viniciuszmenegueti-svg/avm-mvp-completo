from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class StatisticalModelVersionModel(Base):
    __tablename__ = "statistical_model_versions"

    __table_args__ = (
        UniqueConstraint(
            "city_ibge_code",
            "property_type",
            "model_version",
            name="uq_statistical_model_city_type_version",
        ),
        Index(
            "ix_statistical_model_applicability",
            "city_ibge_code",
            "property_type",
            "status",
            "valid_from",
            "valid_until",
        ),
        Index(
            "uq_statistical_model_one_homologation_approved",
            "city_ibge_code",
            "property_type",
            unique=True,
            postgresql_where=text("status = 'HOMOLOGATION_APPROVED'"),
            sqlite_where=text("status = 'HOMOLOGATION_APPROVED'"),
        ),
    )

    model_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("statistical_datasets.dataset_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey("cities.city_ibge_code", ondelete="RESTRICT"),
        nullable=False,
    )
    property_type: Mapped[str] = mapped_column(String(30), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    feature_names_json: Mapped[str] = mapped_column(Text, nullable=False)
    coefficients_json: Mapped[str] = mapped_column(Text, nullable=False)
    covariance_json: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostics_json: Mapped[str] = mapped_column(Text, nullable=False)
    expected_signs_json: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    trained_by: Mapped[str] = mapped_column(String(100), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(250), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
