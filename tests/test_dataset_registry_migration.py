import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


MIGRATION = Path("migrations/versions/d4a8f1c7b920_cria_cadastro_datasets.py")


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dataset_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain() -> None:
    migration = load_migration()
    assert migration.revision == "d4a8f1c7b920"
    assert migration.down_revision == "c9f2a6d4e810"


def test_migration_upgrade_downgrade_and_reapply(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    metadata = sa.MetaData()
    sa.Table(
        "data_sources",
        metadata,
        sa.Column("data_source_id", sa.String(36), primary_key=True),
    )
    metadata.create_all(engine)
    migration = load_migration()

    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        migration.op = operations
        migration.upgrade()

    inspector = sa.inspect(engine)
    assert "datasets" in inspector.get_table_names()
    columns = {item["name"] for item in inspector.get_columns("datasets")}
    assert {
        "dataset_id",
        "data_source_id",
        "name_key",
        "reference_start",
        "reference_end",
        "metadata_json",
        "status",
    } <= columns
    indexes = {item["name"] for item in inspector.get_indexes("datasets")}
    assert "ix_datasets_source_status_created_at" in indexes
    assert "ix_datasets_reference_period" in indexes
    unique_constraints = {
        item["name"] for item in inspector.get_unique_constraints("datasets")
    }
    assert "uq_datasets_source_name_key" in unique_constraints

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
    assert "datasets" not in sa.inspect(engine).get_table_names()

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
    assert "datasets" in sa.inspect(engine).get_table_names()
    engine.dispose()
