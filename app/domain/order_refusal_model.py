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

    details: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    contract_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, default="TR §9.5"
    )

    evidence: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    refused_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
