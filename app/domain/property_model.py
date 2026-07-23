from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.infrastructure.database import Base


if TYPE_CHECKING:
    from app.domain.order_model import OrderModel


class PropertyModel(Base):
    __tablename__ = "properties"

    internal_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "orders.internal_order_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    property_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
    )

    postal_code: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
    )

    neighborhood: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    street: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    complement: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    private_area_m2: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=12,
            scale=2,
        ),
        nullable=True,
    )

    built_area_m2: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=12,
            scale=2,
        ),
        nullable=True,
    )

    land_area_m2: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=12,
            scale=2,
        ),
        nullable=True,
    )

    bedrooms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    bathrooms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    parking_spaces: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    order: Mapped[OrderModel] = relationship(
        back_populates="property_record",
    )
