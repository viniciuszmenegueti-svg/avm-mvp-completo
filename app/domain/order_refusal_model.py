from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class OrderRefusalModel(Base):
    __tablename__ = "order_refusals"

    refusal_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    internal_order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "orders.internal_order_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    details: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    refused_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
