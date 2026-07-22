import os
import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch


DATABASE_FILE = (
    Path(__file__).resolve().parents[1] / "app" / "infrastructure" / "database.py"
)


def execute_database_file(
    database_url: str,
) -> MagicMock:
    with (
        patch.dict(
            os.environ,
            {"DATABASE_URL": database_url},
            clear=False,
        ),
        patch("sqlalchemy.create_engine") as create_engine_mock,
    ):
        runpy.run_path(
            str(DATABASE_FILE),
            run_name="database_configuration_test",
        )

    return create_engine_mock


def test_sqlite_database_uses_check_same_thread() -> None:
    sqlite_url = "sqlite:///test-database.db"

    create_engine_mock = execute_database_file(sqlite_url)

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

    create_engine_mock = execute_database_file(postgresql_url)

    create_engine_mock.assert_called_once_with(
        postgresql_url,
        connect_args={
            "connect_timeout": 3,
        },
        pool_pre_ping=True,
        pool_recycle=300,
    )
