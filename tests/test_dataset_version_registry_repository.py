from datetime import date
from uuid import uuid4

from app.domain.data_source_model import DataSourceModel
from app.domain.dataset_model import DatasetModel
from app.domain.dataset_version_model import DatasetVersionModel
from app.infrastructure.database import SessionLocal
from app.repositories.dataset_versions_sqlalchemy import (
    add_dataset_version,
    get_dataset_version,
    get_dataset_version_by_checksum,
    list_dataset_versions,
    next_dataset_version_number,
    save_dataset_version,
)


def seed_dataset(session) -> DatasetModel:
    source = DataSourceModel(
        data_source_id=str(uuid4()),
        name="Fonte",
        name_key="fonte",
        source_type="CSV",
        responsible="Dados",
        metadata_json="{}",
        status="ACTIVE",
        created_by="tester",
        updated_by="tester",
    )
    dataset = DatasetModel(
        dataset_id=str(uuid4()),
        data_source_id=source.data_source_id,
        name="Base",
        name_key="base",
        metadata_json="{}",
        status="ACTIVE",
        created_by="tester",
        updated_by="tester",
    )
    session.add_all([source, dataset])
    session.commit()
    return dataset


def version(dataset_id: str, number: int, checksum: str) -> DatasetVersionModel:
    return DatasetVersionModel(
        dataset_version_id=str(uuid4()),
        dataset_id=dataset_id,
        version_number=number,
        file_name=f"base-v{number}.csv",
        storage_path=f"datasets/base/v{number}.csv",
        checksum_sha256=checksum,
        file_size_bytes=100,
        mime_type="text/csv",
        reference_start=date(2026, 1, 1),
        reference_end=date(2026, 1, 31),
        status="REGISTERED",
        metadata_json="{}",
        created_by="tester",
        updated_by="tester",
    )


def test_add_get_and_save_dataset_version() -> None:
    with SessionLocal() as session:
        dataset = seed_dataset(session)
        model = add_dataset_version(session, version(dataset.dataset_id, 1, "a" * 64))
        assert get_dataset_version(session, model.dataset_version_id) is not None
        model.status = "PROCESSING"
        assert save_dataset_version(session, model).status == "PROCESSING"


def test_get_by_checksum_is_scoped_to_dataset() -> None:
    with SessionLocal() as session:
        dataset = seed_dataset(session)
        add_dataset_version(session, version(dataset.dataset_id, 1, "b" * 64))
        found = get_dataset_version_by_checksum(
            session,
            dataset_id=dataset.dataset_id,
            checksum_sha256="b" * 64,
        )
        assert found is not None


def test_next_version_number_is_sequential() -> None:
    with SessionLocal() as session:
        dataset = seed_dataset(session)
        assert next_dataset_version_number(session, dataset.dataset_id) == 1
        add_dataset_version(session, version(dataset.dataset_id, 1, "c" * 64))
        add_dataset_version(session, version(dataset.dataset_id, 2, "d" * 64))
        assert next_dataset_version_number(session, dataset.dataset_id) == 3


def test_list_filters_and_paginates() -> None:
    with SessionLocal() as session:
        dataset = seed_dataset(session)
        add_dataset_version(session, version(dataset.dataset_id, 1, "e" * 64))
        failed = version(dataset.dataset_id, 2, "f" * 64)
        failed.status = "FAILED"
        failed.created_by = "reviewer"
        add_dataset_version(session, failed)
        total, items = list_dataset_versions(
            session,
            dataset_id=dataset.dataset_id,
            status="FAILED",
            created_by="reviewer",
            checksum_sha256="f" * 64,
            reference_from=date(2026, 1, 10),
            reference_until=date(2026, 1, 20),
            limit=1,
            offset=0,
        )
        assert total == 1
        assert items[0].version_number == 2
