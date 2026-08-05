from app.domain.dataset_version_model import DatasetVersionModel
from app.infrastructure.database import Base


def test_dataset_version_table_is_registered_in_metadata() -> None:
    assert "dataset_versions" in Base.metadata.tables
    assert DatasetVersionModel.__table__ is Base.metadata.tables["dataset_versions"]


def test_dataset_version_constraints_and_indexes() -> None:
    table = DatasetVersionModel.__table__
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert "uq_dataset_versions_dataset_version_number" in unique_names
    assert "uq_dataset_versions_dataset_checksum" in unique_names
    index_names = {index.name for index in table.indexes}
    assert "ix_dataset_versions_dataset_status_created_at" in index_names
    assert "ix_dataset_versions_reference_period" in index_names
