from app.domain.dataset_model import DatasetModel


def test_dataset_table_metadata() -> None:
    table = DatasetModel.__table__
    assert table.name == "datasets"
    assert set(table.primary_key.columns.keys()) == {"dataset_id"}
    assert table.c.data_source_id.foreign_keys


def test_dataset_unique_constraint_and_indexes() -> None:
    table = DatasetModel.__table__
    constraints = {constraint.name for constraint in table.constraints}
    indexes = {index.name for index in table.indexes}
    assert "uq_datasets_source_name_key" in constraints
    assert "ix_datasets_source_status_created_at" in indexes
    assert "ix_datasets_reference_period" in indexes
