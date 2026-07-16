from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class OrderModel(Base):
    __tablename__ = "orders"

    internal_order_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    external_order_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    property_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
