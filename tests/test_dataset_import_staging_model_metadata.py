from app.domain.dataset_import_staging_model import (
    DatasetImportExecutionModel,
    DatasetImportRowModel,
)


def test_staging_tables_are_registered_in_metadata() -> None:
    assert DatasetImportExecutionModel.__table__.name == "dataset_import_executions"
    assert DatasetImportRowModel.__table__.name == "dataset_import_rows"


def test_staging_row_has_unique_line_constraint() -> None:
    constraints = {
        constraint.name for constraint in DatasetImportRowModel.__table__.constraints
    }
    assert "uq_dataset_import_rows_execution_line" in constraints


def test_staging_indexes_cover_operational_queries() -> None:
    execution_indexes = {
        index.name for index in DatasetImportExecutionModel.__table__.indexes
    }
    row_indexes = {index.name for index in DatasetImportRowModel.__table__.indexes}
    assert "ix_dataset_import_executions_version_created_at" in execution_indexes
    assert "ix_dataset_import_rows_execution_status_line" in row_indexes
    assert "ix_dataset_import_rows_execution_row_hash" in row_indexes
