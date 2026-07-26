from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class PropertyAssetModel(Base):
    __tablename__ = "property_assets"

    property_asset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey("cities.city_ibge_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    postal_code: Mapped[str] = mapped_column(String(9), nullable=False, index=True)
    neighborhood: Mapped[str] = mapped_column(String(100), nullable=False)
    street: Mapped[str] = mapped_column(String(150), nullable=False)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    private_area_m2: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    built_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    land_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
