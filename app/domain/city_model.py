from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CityModel(Base):
    __tablename__ = "cities"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "state",
            name="uq_cities_name_state",
        ),
        CheckConstraint(
            "length(city_ibge_code) = 7",
            name="ck_cities_ibge_code_length",
        ),
        CheckConstraint(
            "length(state) = 2",
            name="ck_cities_state_length",
        ),
    )

    city_ibge_code: Mapped[str] = mapped_column(
        String(7),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
