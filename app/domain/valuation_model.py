from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ValuationModel(Base):
    __tablename__ = "valuations"

    valuation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    internal_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.internal_order_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    minimum_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    maximum_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    price_per_m2: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference_area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    confidence_reasons_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
