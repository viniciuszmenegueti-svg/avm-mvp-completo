"""Validação DDL real dos índices de consulta da execução sombra."""

from importlib import util
from pathlib import Path
from types import ModuleType

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = Path(
    "migrations/versions/"
    "b7e4c2a9d610_otimiza_consultas_execucoes_sombra.py"
)

TABLE_NAME = "shadow_valuation_executions"

EXPECTED_INDEXES = {
    "ix_shadow_executions_executed_at": (
        "executed_at",
    ),
    "ix_shadow_executions_status_executed_at": (
        "result_status",
        "executed_at",
    ),
    "ix_shadow_executions_requested_by_executed_at": (
        "requested_by",
        "executed_at",
    ),
    "ix_shadow_executions_model_version_executed_at": (
        "model_version",
        "executed_at",
    ),
    "ix_shadow_executions_order_executed_at": (
        "internal_order_id",
        "executed_at",
    ),
}


def load_migration() -> ModuleType:
    spec = util.spec_from_file_location(
        "shadow_execution_query_indexes_migration",
        MIGRATION_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def create_base_table(connection) -> None:  # type: ignore[no-untyped-def]
    connection.execute(
        text(
            f"""
            CREATE TABLE {TABLE_NAME} (
                execution_id VARCHAR(36) NOT NULL,
                internal_order_id VARCHAR(36) NOT NULL,
                requested_by VARCHAR(100) NOT NULL,
                result_status VARCHAR(30) NOT NULL,
                model_version VARCHAR(50),
                executed_at DATETIME NOT NULL,
                PRIMARY KEY (execution_id)
            )
            """
        )
    )


def database_indexes(connection) -> dict[str, tuple[str, ...]]:  # type: ignore[no-untyped-def]
    return {
        str(index["name"]): tuple(index["column_names"])
        for index in inspect(connection).get_indexes(TABLE_NAME)
    }


def test_runtime_upgrade_downgrade_and_reapply_indexes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        create_base_table(connection)

        context = MigrationContext.configure(connection)
        operations = Operations(context)
        migration = load_migration()
        migration.op = operations

        migration.upgrade()
        indexes_after_upgrade = database_indexes(connection)

        for name, columns in EXPECTED_INDEXES.items():
            assert indexes_after_upgrade[name] == columns

        migration.downgrade()
        indexes_after_downgrade = database_indexes(connection)

        assert set(indexes_after_downgrade).isdisjoint(EXPECTED_INDEXES)

        migration.upgrade()
        indexes_after_reapply = database_indexes(connection)

        for name, columns in EXPECTED_INDEXES.items():
            assert indexes_after_reapply[name] == columns

    engine.dispose()


def test_runtime_indexes_are_non_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        create_base_table(connection)

        context = MigrationContext.configure(connection)
        migration = load_migration()
        migration.op = Operations(context)
        migration.upgrade()

        indexes = {
            str(index["name"]): index
            for index in inspect(connection).get_indexes(TABLE_NAME)
        }

        for name in EXPECTED_INDEXES:
            assert indexes[name]["unique"] == 0

    engine.dispose()
