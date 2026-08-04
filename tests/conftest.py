import os
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import delete


TEST_DATABASE_FILE = Path(__file__).resolve().parent / "test_avm.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_FILE.as_posix()}"
os.environ["APP_NAME"] = "AVM Imóveis API"
os.environ["APP_VERSION"] = "0.3.1"
os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["ALLOW_SYNTHETIC_PRICING"] = "true"

os.environ["ADMIN_CREDENTIALS_JSON"] = (
    '{"avm-test-admin":"avm-test-admin-key",'
    '"avm-test-reviewer":"avm-test-reviewer-key"}'
)
os.environ["ADMIN_API_KEY"] = ""
os.environ["ADMIN_ACTOR"] = ""

from app.domain.city_model import CityModel
from app.domain.city_valuation_price_history_model import (
    CityValuationPriceHistoryModel,
)
from app.domain.city_valuation_price_model import (
    CityValuationPriceModel,
)
from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel
from app.domain.geocoding_audit_model import GeocodingAuditModel
from app.domain.order_model import OrderModel
from app.domain.order_refusal_model import OrderRefusalModel
from app.domain.order_status_history_model import (
    OrderStatusHistoryModel,
)
from app.domain.property_asset_model import PropertyAssetModel
from app.domain.property_model import PropertyModel
from app.domain.statistical_dataset_model import StatisticalDatasetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel
from app.domain.valuation_model import ValuationModel
from app.infrastructure.database import (
    Base,
    SessionLocal,
    engine,
)


TEST_CITIES_DATA = [
    {
        "city_ibge_code": "3304557",
        "name": "Rio de Janeiro",
        "state": "RJ",
        "active": True,
    },
    {
        "city_ibge_code": "3550308",
        "name": "São Paulo",
        "state": "SP",
        "active": True,
    },
    {
        "city_ibge_code": "5300108",
        "name": "Brasília",
        "state": "DF",
        "active": True,
    },
    {
        "city_ibge_code": "2927408",
        "name": "Salvador",
        "state": "BA",
        "active": True,
    },
    {
        "city_ibge_code": "3106200",
        "name": "Belo Horizonte",
        "state": "MG",
        "active": True,
    },
    {
        "city_ibge_code": "4106902",
        "name": "Curitiba",
        "state": "PR",
        "active": True,
    },
    {
        "city_ibge_code": "2611606",
        "name": "Recife",
        "state": "PE",
        "active": True,
    },
    {
        "city_ibge_code": "2304400",
        "name": "Fortaleza",
        "state": "CE",
        "active": True,
    },
    {
        "city_ibge_code": "5208707",
        "name": "Goiânia",
        "state": "GO",
        "active": True,
    },
    {
        "city_ibge_code": "4314902",
        "name": "Porto Alegre",
        "state": "RS",
        "active": True,
    },
]


TEST_CITY_VALUATION_PRICES_DATA = [
    {
        "city_ibge_code": "3550308",
        "property_type": "APARTMENT",
        "price_per_m2": 10500,
    },
    {
        "city_ibge_code": "3550308",
        "property_type": "HOUSE",
        "price_per_m2": 7800,
    },
    {
        "city_ibge_code": "3550308",
        "property_type": "LAND",
        "price_per_m2": 5200,
    },
]


Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def prepare_test_database() -> Generator[None, None, None]:
    with SessionLocal() as session:
        session.execute(delete(GeocodingAuditModel))
        session.execute(delete(CnefeAddressModel))
        session.execute(delete(CnefeImportModel))
        session.execute(delete(CityValuationPriceHistoryModel))
        session.execute(delete(ValuationModel))
        session.execute(delete(StatisticalModelVersionModel))
        session.execute(delete(StatisticalDatasetModel))
        session.execute(delete(OrderRefusalModel))
        session.execute(delete(OrderStatusHistoryModel))
        session.execute(delete(PropertyAssetModel))
        session.execute(delete(PropertyModel))
        session.execute(delete(OrderModel))
        session.execute(delete(CityValuationPriceModel))
        session.execute(delete(CityModel))

        session.add_all([CityModel(**city_data) for city_data in TEST_CITIES_DATA])

        session.add_all(
            [
                CityValuationPriceModel(**price_data)
                for price_data in TEST_CITY_VALUATION_PRICES_DATA
            ]
        )

        session.commit()

    yield

    with SessionLocal() as session:
        session.execute(delete(GeocodingAuditModel))
        session.execute(delete(CnefeAddressModel))
        session.execute(delete(CnefeImportModel))
        session.execute(delete(CityValuationPriceHistoryModel))
        session.execute(delete(ValuationModel))
        session.execute(delete(StatisticalModelVersionModel))
        session.execute(delete(StatisticalDatasetModel))
        session.execute(delete(OrderRefusalModel))
        session.execute(delete(OrderStatusHistoryModel))
        session.execute(delete(PropertyAssetModel))
        session.execute(delete(PropertyModel))
        session.execute(delete(OrderModel))
        session.execute(delete(CityValuationPriceModel))
        session.execute(delete(CityModel))
        session.commit()


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: int,
) -> None:
    del session
    del exitstatus

    engine.dispose()

    if TEST_DATABASE_FILE.exists():
        TEST_DATABASE_FILE.unlink()
