from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CnefeImportStatus(StrEnum):
    LOADING = "LOADING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


class CnefeImportModel(Base):
    __tablename__ = "cnefe_imports"

    __table_args__ = (
        Index(
            "ix_cnefe_imports_active_lookup",
            "city_ibge_code",
            "status",
            "activated_at",
        ),
    )

    import_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(250), nullable=False)
    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey("cities.city_ibge_code", ondelete="RESTRICT"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
