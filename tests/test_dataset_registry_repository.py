from datetime import date
from uuid import uuid4

from app.domain.data_source_model import DataSourceModel
from app.domain.dataset_model import DatasetModel
from app.infrastructure.database import SessionLocal
from app.repositories.datasets_sqlalchemy import (
    add_dataset,
    get_dataset,
    get_dataset_by_source_and_name_key,
    list_datasets,
    save_dataset,
)


def source(session, name: str = "Fonte") -> DataSourceModel:
    model = DataSourceModel(
        data_source_id=str(uuid4()),
        name=name,
        name_key=name.casefold(),
        source_type="CSV",
        responsible="Dados",
        metadata_json="{}",
        status="ACTIVE",
        created_by="tester",
        updated_by="tester",
    )
    session.add(model)
    session.commit()
    return model


def dataset(source_id: str, name: str = "Base 2026") -> DatasetModel:
    return DatasetModel(
        dataset_id=str(uuid4()),
        data_source_id=source_id,
        name=name,
        name_key=name.casefold(),
        reference_start=date(2026, 1, 1),
        reference_end=date(2026, 6, 30),
        metadata_json='{"rows": 10}',
        status="ACTIVE",
        created_by="tester",
        updated_by="tester",
    )


def test_add_get_and_save_dataset() -> None:
    with SessionLocal() as session:
        src = source(session)
        model = add_dataset(session, dataset(src.data_source_id))
        assert get_dataset(session, model.dataset_id) is not None
        model.description = "Atualizado"
        saved = save_dataset(session, model)
        assert saved.description == "Atualizado"


def test_get_by_source_and_normalized_name() -> None:
    with SessionLocal() as session:
        src = source(session)
        add_dataset(session, dataset(src.data_source_id))
        found = get_dataset_by_source_and_name_key(
            session,
            data_source_id=src.data_source_id,
            name_key="base 2026",
        )
        assert found is not None


def test_same_name_is_allowed_for_different_sources() -> None:
    with SessionLocal() as session:
        first = source(session, "Fonte A")
        second = source(session, "Fonte B")
        add_dataset(session, dataset(first.data_source_id))
        add_dataset(session, dataset(second.data_source_id))
        total, _ = list_datasets(session, name="base", limit=20, offset=0)
        assert total == 2


def test_list_filters_and_paginates() -> None:
    with SessionLocal() as session:
        src = source(session)
        add_dataset(session, dataset(src.data_source_id, "Base A"))
        inactive = dataset(src.data_source_id, "Base B")
        inactive.status = "INACTIVE"
        add_dataset(session, inactive)
        total, items = list_datasets(
            session,
            data_source_id=src.data_source_id,
            status="INACTIVE",
            name="base",
            reference_from=date(2026, 2, 1),
            reference_until=date(2026, 5, 1),
            limit=1,
            offset=0,
        )
        assert total == 1
        assert items[0].name == "Base B"
