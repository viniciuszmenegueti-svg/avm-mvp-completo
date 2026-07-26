from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.domain.property_model import PropertyModel
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

    property_asset_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("property_assets.property_asset_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    property_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    property_record: Mapped[PropertyModel | None] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
