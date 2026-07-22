from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CityValuationPriceModel(Base):
    __tablename__ = "city_valuation_prices"

    __table_args__ = (
        UniqueConstraint(
            "city_ibge_code",
            "property_type",
            name="uq_city_valuation_prices_city_property_type",
        ),
        CheckConstraint(
            "price_per_m2 > 0",
            name="ck_city_valuation_prices_positive_price",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        ForeignKey(
            "cities.city_ibge_code",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    property_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    price_per_m2: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=18,
            scale=2,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
