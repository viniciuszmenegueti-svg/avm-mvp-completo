from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CnefeAddressModel(Base):
    __tablename__ = "cnefe_addresses"

    __table_args__ = (
        CheckConstraint(
            "geocoding_level between 1 and 6",
            name="ck_cnefe_addresses_geocoding_level",
        ),
        CheckConstraint(
            "latitude between -90 and 90",
            name="ck_cnefe_addresses_latitude",
        ),
        CheckConstraint(
            "longitude between -180 and 180",
            name="ck_cnefe_addresses_longitude",
        ),
        Index(
            "ix_cnefe_addresses_exact_lookup",
            "city_ibge_code",
            "postal_code",
            "normalized_street",
            "normalized_number",
        ),
        Index(
            "ix_cnefe_addresses_name_lookup",
            "city_ibge_code",
            "postal_code",
            "normalized_street_name",
            "normalized_number",
        ),
    )

    record_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cnefe_imports.import_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey("cities.city_ibge_code", ondelete="RESTRICT"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(8), nullable=False)
    locality: Mapped[str | None] = mapped_column(String(150), nullable=True)
    street: Mapped[str] = mapped_column(String(250), nullable=False)
    street_name: Mapped[str] = mapped_column(String(200), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    number_modifier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(250), nullable=True)
    normalized_street: Mapped[str] = mapped_column(String(250), nullable=False)
    normalized_street_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_number: Mapped[str] = mapped_column(String(40), nullable=False)
    latitude: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=7), nullable=False
    )
    longitude: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=7), nullable=False
    )
    geocoding_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
