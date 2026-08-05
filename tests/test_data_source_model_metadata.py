from app.domain.data_source_model import DataSourceModel
from app.infrastructure.database import Base


def test_data_source_model_is_registered_in_metadata() -> None:
    assert DataSourceModel.__table__ is Base.metadata.tables["data_sources"]


def test_data_source_model_declares_expected_indexes() -> None:
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in DataSourceModel.__table__.indexes
    }
    assert indexes["ix_data_sources_status_created_at"] == ("status", "created_at")
    assert indexes["ix_data_sources_type_created_at"] == (
        "source_type",
        "created_at",
    )
