import argparse
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus
from app.infrastructure.database import SessionLocal
from app.main import app
from app.services.cnefe_import_service import (
    activate_cnefe_import,
    fail_cnefe_import,
    start_cnefe_import,
    update_cnefe_import_count,
)


client = TestClient(app)


def load_importer_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "import-cnefe.py"
    spec = importlib.util.spec_from_file_location("avm_import_cnefe", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_address_to_import(session, import_id: str) -> None:
    session.add(
        CnefeAddressModel(
            record_key="b" * 64,
            import_id=import_id,
            provider_record_id="CNEFE-SERVICE-TEST-1",
            dataset_version="CNEFE-SERVICE-TEST",
            source_file_sha256="a" * 64,
            city_ibge_code="3550308",
            state="SP",
            postal_code="01001000",
            locality="Sao Paulo",
            street="Praca da Se",
            street_name="da Se",
            number="100",
            number_modifier=None,
            complement=None,
            normalized_street="PRACA DA SE",
            normalized_street_name="DA SE",
            normalized_number="100",
            latitude=-23.55052,
            longitude=-46.633308,
            geocoding_level=1,
        )
    )
    session.commit()


def test_import_registry_counts_and_activates_complete_batch() -> None:
    with SessionLocal() as session:
        registry = start_cnefe_import(
            session,
            dataset_version="CNEFE-SERVICE-TEST",
            source_file_sha256="a" * 64,
            source_filename="cnefe-service-test.csv",
            city_ibge_code="3550308",
            state="SP",
        )

        assert registry.status == CnefeImportStatus.LOADING.value
        assert update_cnefe_import_count(session, registry.import_id) == 0

        add_address_to_import(session, registry.import_id)
        assert update_cnefe_import_count(session, registry.import_id) == 1

        activated = activate_cnefe_import(session, registry.import_id)

        assert activated.status == CnefeImportStatus.ACTIVE.value
        assert activated.record_count == 1
        assert activated.completed_at is not None
        assert activated.activated_at is not None
        assert activated.failure_reason is None

        with pytest.raises(ValueError):
            activate_cnefe_import(session, registry.import_id)


def test_import_registry_rejects_missing_or_empty_batches_and_records_failure() -> None:
    missing_import_id = "00000000-0000-0000-0000-000000000099"
    with SessionLocal() as session:
        with pytest.raises(ValueError):
            update_cnefe_import_count(session, missing_import_id)
        with pytest.raises(ValueError):
            activate_cnefe_import(session, missing_import_id)
        with pytest.raises(ValueError):
            fail_cnefe_import(session, missing_import_id, RuntimeError("failure"))

        registry = start_cnefe_import(
            session,
            dataset_version="CNEFE-EMPTY-TEST",
            source_file_sha256="c" * 64,
            source_filename="cnefe-empty-test.csv",
            city_ibge_code="3550308",
            state="SP",
        )

        with pytest.raises(ValueError):
            activate_cnefe_import(session, registry.import_id)

        failed = fail_cnefe_import(
            session,
            registry.import_id,
            RuntimeError("x" * 2100),
        )

        assert failed.status == CnefeImportStatus.FAILED.value
        assert failed.record_count == 0
        assert failed.completed_at is not None
        assert failed.activated_at is None
        assert failed.failure_reason == "x" * 2000


def test_failed_import_keeps_committed_partial_batch_invisible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "cnefe-failure.csv"
    source.write_text(
        "COD_UNICO_ENDERECO;COD_MUN;COD_CEP;NOM_TIPO_SEGLOGR;"
        "NOM_SEGLOGR;NUM_ENDERECO;LATITUDE;LONGITUDE;NV_GEO_COORD\n"
        "OK-1;3550308;01001000;PRACA;DA SE;100;-23.55052;-46.633308;1\n"
        "BAD-2;3550308;01001000;PRACA;DA SE;101;999;-46.633308;1\n",
        encoding="utf-8",
    )
    importer = load_importer_module()
    monkeypatch.setattr(
        importer,
        "parse_arguments",
        lambda: argparse.Namespace(
            csv_file=source,
            dataset_version="CNEFE-FAILED-TEST",
            city_ibge_code="3550308",
            state="SP",
            encoding="utf-8",
            batch_size=1,
        ),
    )

    with pytest.raises(ValueError, match="Linha 3"):
        importer.main()

    with SessionLocal() as session:
        registry = session.scalar(select(CnefeImportModel))
        assert registry is not None
        assert registry.status == CnefeImportStatus.FAILED.value
        assert registry.record_count == 1
        assert registry.failure_reason is not None
        address_count = len(session.scalars(select(CnefeAddressModel)).all())
        assert address_count == 1

    response = client.post(
        "/geocoding/resolve",
        json={
            "city_ibge_code": "3550308",
            "state": "SP",
            "city": "Sao Paulo",
            "postal_code": "01001-000",
            "street": "Praca da Se",
            "number": "100",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "DATASET_NOT_LOADED"
