from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class GeocodingAuditModel(Base):
    __tablename__ = "geocoding_audits"

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    city_ibge_code: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    normalized_postal_code: Mapped[str] = mapped_column(String(8), nullable=False)
    normalized_street: Mapped[str] = mapped_column(String(250), nullable=False)
    normalized_number: Mapped[str] = mapped_column(String(40), nullable=False)
    result_status: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_record_key: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("cnefe_addresses.record_key", ondelete="SET NULL"),
        nullable=True,
    )
    dataset_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_reference: Mapped[str | None] = mapped_column(String(250), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
