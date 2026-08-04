import json
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class OrderStatusHistoryModel(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
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

    previous_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    new_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    changed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="system",
    )

    request_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="internal",
        index=True,
    )

    reason_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="STATUS_TRANSITION",
    )

    context_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    @property
    def context(self) -> dict[str, Any]:
        value = json.loads(self.context_json or "{}")
        return value if isinstance(value, dict) else {}


def _reject_history_mutation(*_: object, **__: object) -> None:
    raise RuntimeError("O histórico de status é append-only.")


event.listen(OrderStatusHistoryModel, "before_update", _reject_history_mutation)
event.listen(OrderStatusHistoryModel, "before_delete", _reject_history_mutation)
