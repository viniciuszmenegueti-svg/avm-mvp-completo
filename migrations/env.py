from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.domain.city_model import CityModel
from app.domain.city_valuation_price_history_model import (
    CityValuationPriceHistoryModel,
)
from app.domain.city_valuation_price_model import (
    CityValuationPriceModel,
)
from app.domain.order_model import OrderModel
from app.domain.order_status_history_model import (
    OrderStatusHistoryModel,
)
from app.domain.valuation_model import ValuationModel
from app.infrastructure.database import Base, DATABASE_URL


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%"),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

MODEL_CLASSES = (
    CityModel,
    CityValuationPriceModel,
    CityValuationPriceHistoryModel,
    OrderModel,
    OrderStatusHistoryModel,
    ValuationModel,
)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
