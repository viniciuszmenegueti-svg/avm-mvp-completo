from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class StatisticalDatasetModel(Base):
    __tablename__ = "statistical_datasets"

    dataset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey("cities.city_ibge_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    variable_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    training_matrix_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dependent_variable: Mapped[str] = mapped_column(String(80), nullable=False)
    dependent_variable_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    dependent_variable_transformation: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    training_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    feature_ranges_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
