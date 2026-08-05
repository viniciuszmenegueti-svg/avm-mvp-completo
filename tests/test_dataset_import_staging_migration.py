import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


MIGRATION_PATH = Path(
    "migrations/versions/f8d1c5a7e230_cria_staging_importacoes.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("staging_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain() -> None:
    migration = load_migration()
    assert migration.revision == "f8d1c5a7e230"
    assert migration.down_revision == "e6c3b9a2f410"


def test_migration_upgrade_and_downgrade(tmp_path, monkeypatch) -> None:
    migration = load_migration()
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE dataset_versions (dataset_version_id VARCHAR(36) PRIMARY KEY)"
        )
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()
        inspector = inspect(connection)
        assert "dataset_import_executions" in inspector.get_table_names()
        assert "dataset_import_rows" in inspector.get_table_names()
        row_indexes = {item["name"] for item in inspector.get_indexes("dataset_import_rows")}
        assert "ix_dataset_import_rows_execution_status_line" in row_indexes
        migration.downgrade()
        assert "dataset_import_rows" not in inspect(connection).get_table_names()
        assert "dataset_import_executions" not in inspect(connection).get_table_names()
