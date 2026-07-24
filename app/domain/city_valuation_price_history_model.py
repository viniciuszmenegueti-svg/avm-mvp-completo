from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CityValuationPriceHistoryModel(Base):
    __tablename__ = "city_valuation_price_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    city_valuation_price_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "city_valuation_prices.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )

    property_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    previous_price_per_m2: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=18,
            scale=2,
        ),
        nullable=False,
    )

    new_price_per_m2: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=18,
            scale=2,
        ),
        nullable=False,
    )

    changed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default=text("'system'"),
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
