from app.domain.data_source_model import DataSourceModel
from app.infrastructure.database import SessionLocal
from app.repositories.data_sources_sqlalchemy import (
    add_data_source,
    get_data_source_by_name_key,
    list_data_sources,
)


def model(source_id: str, name: str, status: str = "ACTIVE") -> DataSourceModel:
    return DataSourceModel(
        data_source_id=source_id,
        name=name,
        name_key=name.casefold(),
        source_type="CSV",
        responsible="Dados",
        metadata_json="{}",
        status=status,
        created_by="test",
        updated_by="test",
    )


def test_repository_adds_and_finds_by_normalized_name() -> None:
    with SessionLocal() as session:
        add_data_source(session, model("source-1", "Fonte A"))
        found = get_data_source_by_name_key(session, "fonte a")
        assert found is not None
        assert found.name == "Fonte A"


def test_repository_filters_and_counts() -> None:
    with SessionLocal() as session:
        add_data_source(session, model("source-1", "Fonte A"))
        add_data_source(session, model("source-2", "Fonte B", "INACTIVE"))
        total, items = list_data_sources(
            session,
            status="INACTIVE",
            source_type=None,
            responsible=None,
            name="fonte",
            limit=10,
            offset=0,
        )
        assert total == 1
        assert [item.name for item in items] == ["Fonte B"]
