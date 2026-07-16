import os
from pathlib import Path

import pytest
from sqlalchemy import delete

TEST_DATABASE_FILE = (
    Path(__file__).resolve().parent / "test_avm.db"
)

os.environ["DATABASE_URL"] = (
    f"sqlite:///{TEST_DATABASE_FILE.as_posix()}"
)

from app.domain.order_model import OrderModel
from app.infrastructure.database import (
    Base,
    SessionLocal,
    engine,
)

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_test_database():
    with SessionLocal() as session:
        session.execute(delete(OrderModel))
        session.commit()

    yield

    with SessionLocal() as session:
        session.execute(delete(OrderModel))
        session.commit()


def pytest_sessionfinish(
    session,
    exitstatus,
) -> None:
    engine.dispose()

    if TEST_DATABASE_FILE.exists():
        TEST_DATABASE_FILE.unlink()
