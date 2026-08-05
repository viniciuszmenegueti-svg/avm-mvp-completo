"""Persistência auditável das execuções do modelo AVM sombra."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ShadowValuationExecutionModel(Base):
    __tablename__ = "shadow_valuation_executions"

    __table_args__ = (
        Index(
            "ix_shadow_executions_executed_at",
            "executed_at",
        ),
        Index(
            "ix_shadow_executions_status_executed_at",
            "result_status",
            "executed_at",
        ),
        Index(
            "ix_shadow_executions_requested_by_executed_at",
            "requested_by",
            "executed_at",
        ),
        Index(
            "ix_shadow_executions_model_version_executed_at",
            "model_version",
            "executed_at",
        ),
        Index(
            "ix_shadow_executions_order_executed_at",
            "internal_order_id",
            "executed_at",
        ),
    )

    execution_id: Mapped[str] = mapped_column(
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
        index=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    result_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    execution_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SHADOW",
    )

    contractual_validity: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    formal_homologation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    value_basis: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    estimated_value_brl: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    confidence_lower_brl: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    confidence_upper_brl: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    confidence_level: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 6),
        nullable=True,
    )

    confidence_amplitude_percent: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(12, 6),
        nullable=True,
    )

    price_per_m2_brl: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    artifact_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    neighborhood: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    private_area_m2: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
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

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
