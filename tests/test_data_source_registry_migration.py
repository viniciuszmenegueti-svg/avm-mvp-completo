import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


MIGRATION = Path(
    "migrations/versions/c9f2a6d4e810_cria_cadastro_fontes_dados.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("data_source_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain() -> None:
    migration = load_migration()
    assert migration.revision == "c9f2a6d4e810"
    assert migration.down_revision == "b7e4c2a9d610"


def test_migration_upgrade_downgrade_and_reapply(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    migration = load_migration()

    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        migration.op = operations
        migration.upgrade()

    inspector = sa.inspect(engine)
    assert "data_sources" in inspector.get_table_names()
    columns = {item["name"] for item in inspector.get_columns("data_sources")}
    assert {"data_source_id", "name_key", "metadata_json", "status"} <= columns
    indexes = {item["name"] for item in inspector.get_indexes("data_sources")}
    assert "ix_data_sources_status_created_at" in indexes

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
    assert "data_sources" not in sa.inspect(engine).get_table_names()

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
    assert "data_sources" in sa.inspect(engine).get_table_names()
    engine.dispose()
