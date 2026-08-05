import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext


MIGRATION = Path(
    "migrations/versions/e6c3b9a2f410_cria_versoes_datasets.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dataset_version_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_revision_chain() -> None:
    migration = load_migration()
    assert migration.revision == "e6c3b9a2f410"
    assert migration.down_revision == "d4a8f1c7b920"


def test_migration_upgrade_downgrade_and_reapply(tmp_path: Path) -> None:
    database = tmp_path / "dataset-versions.db"
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    metadata = sa.MetaData()
    sa.Table(
        "datasets",
        metadata,
        sa.Column("dataset_id", sa.String(36), primary_key=True),
    )
    metadata.create_all(engine)
    migration = load_migration()

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

    inspector = sa.inspect(engine)
    assert "dataset_versions" in inspector.get_table_names()
    columns = {item["name"] for item in inspector.get_columns("dataset_versions")}
    assert {
        "dataset_version_id",
        "dataset_id",
        "version_number",
        "checksum_sha256",
        "record_count",
        "processing_started_at",
        "completed_at",
    } <= columns
    indexes = {item["name"] for item in inspector.get_indexes("dataset_versions")}
    assert "ix_dataset_versions_dataset_status_created_at" in indexes
    assert "ix_dataset_versions_created_by_created_at" in indexes
    unique_constraints = {
        item["name"] for item in inspector.get_unique_constraints("dataset_versions")
    }
    assert "uq_dataset_versions_dataset_version_number" in unique_constraints
    assert "uq_dataset_versions_dataset_checksum" in unique_constraints

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
    assert "dataset_versions" not in sa.inspect(engine).get_table_names()

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
    assert "dataset_versions" in sa.inspect(engine).get_table_names()
    engine.dispose()
