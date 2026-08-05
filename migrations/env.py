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
from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel
from app.domain.data_source_model import DataSourceModel
from app.domain.dataset_model import DatasetModel
from app.domain.dataset_version_model import DatasetVersionModel
from app.domain.geocoding_audit_model import GeocodingAuditModel
from app.domain.order_model import OrderModel
from app.domain.shadow_valuation_execution_model import (
    ShadowValuationExecutionModel,
)
from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel
from app.domain.order_refusal_model import OrderRefusalModel
from app.domain.order_status_history_model import (
    OrderStatusHistoryModel,
)
from app.domain.property_model import PropertyModel
from app.domain.property_asset_model import PropertyAssetModel
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
    CnefeAddressModel,
    CnefeImportModel,
    GeocodingAuditModel,
    DataSourceModel,
    DatasetModel,
    DatasetVersionModel,
    StatisticalDatasetModel,
    StatisticalModelVersionModel,
    OrderModel,
    PropertyModel,
    PropertyAssetModel,
    OrderRefusalModel,
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
