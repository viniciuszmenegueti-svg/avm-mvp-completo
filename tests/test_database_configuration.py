import os
import runpy
from unittest.mock import patch


DATABASE_MODULE = "app.infrastructure.database"


def execute_database_module(
    database_url: str,
):
    with (
        patch.dict(
            os.environ,
            {"DATABASE_URL": database_url},
            clear=False,
        ),
        patch("sqlalchemy.create_engine") as create_engine_mock,
    ):
        runpy.run_module(
            DATABASE_MODULE,
            run_name=f"{DATABASE_MODULE}.__configuration_test__",
        )

    return create_engine_mock


def test_sqlite_database_uses_check_same_thread() -> None:
    sqlite_url = "sqlite:///test-database.db"

    create_engine_mock = execute_database_module(sqlite_url)

    create_engine_mock.assert_called_once_with(
        sqlite_url,
        connect_args={
            "check_same_thread": False,
        },
        pool_pre_ping=True,
        pool_recycle=300,
    )


def test_postgresql_database_uses_connect_timeout() -> None:
    postgresql_url = "postgresql+psycopg://user:password@localhost:5432/avm"

    create_engine_mock = execute_database_module(postgresql_url)

    create_engine_mock.assert_called_once_with(
        postgresql_url,
        connect_args={
            "connect_timeout": 3,
        },
        pool_pre_ping=True,
        pool_recycle=300,
    )
