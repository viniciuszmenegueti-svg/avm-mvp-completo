from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class DataSourceModel(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        Index("ix_data_sources_status_created_at", "status", "created_at"),
        Index("ix_data_sources_type_created_at", "source_type", "created_at"),
        Index("ix_data_sources_responsible_created_at", "responsible", "created_at"),
    )

    data_source_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_key: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    responsible: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", index=True
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
