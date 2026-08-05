from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
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

    response_deadline_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    location_is_confirmed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    location_confirmation_method: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    location_evidence_reference: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    location_failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    location_verified_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )

    location_accuracy_meters: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    geocoding_audit_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("geocoding_audits.audit_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    property_record: Mapped[PropertyModel | None] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
