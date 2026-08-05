from hashlib import sha256
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus
from app.domain.geocoding_audit_model import GeocodingAuditModel
from app.infrastructure.database import SessionLocal
from app.main import app
from app.services.geocoding_service import normalize_postal_code, normalize_text


client = TestClient(app)

REQUEST = {
    "city_ibge_code": "3550308",
    "state": "SP",
    "city": "São Paulo",
    "postal_code": "01001-000",
    "street": "Praça da Sé",
    "number": "100",
    "complement": "Apartamento 10",
}


def order_payload_from_audit(
    audit: dict,
    *,
    external_order_id: str,
) -> dict[str, object]:
    selected = audit["selected"]
    return {
        "external_order_id": external_order_id,
        "property": {
            "property_type": "APARTMENT",
            "state": REQUEST["state"],
            "city": REQUEST["city"],
            "city_ibge_code": REQUEST["city_ibge_code"],
            "postal_code": REQUEST["postal_code"],
            "neighborhood": "Centro",
            "street": REQUEST["street"],
            "number": REQUEST["number"],
            "complement": REQUEST["complement"],
            "private_area_m2": 70,
            "built_area_m2": 80,
            "bedrooms": 2,
            "bathrooms": 2,
            "parking_spaces": 1,
        },
        "location_confirmation": {
            "is_confirmed": True,
            "confirmation_method": "CNEFE_IBGE",
            "geocoding_audit_id": audit["audit_id"],
            "evidence_reference": (
                f"{audit['evidence_reference']};PRECISAO:MEDICAO-TESTE-20M"
            ),
            "verified_by": "RESPONSAVEL-TESTE",
            "latitude": selected["latitude"],
            "longitude": selected["longitude"],
            "accuracy_meters": 20,
        },
    }


def add_cnefe_address(
    *,
    suffix: str = "1",
    geocoding_level: int = 1,
    latitude: float = -23.55052,
    longitude: float = -46.633308,
    import_id: str = "00000000-0000-0000-0000-000000000001",
    dataset_version: str = "CNEFE-CENSO-2022-20240521",
    import_status: CnefeImportStatus = CnefeImportStatus.ACTIVE,
    activated_at: datetime | None = None,
) -> None:
    record_key = sha256(f"{import_id}-record-{suffix}".encode()).hexdigest()
    with SessionLocal() as session:
        registry = session.get(CnefeImportModel, import_id)
        if registry is None:
            session.add(
                CnefeImportModel(
                    import_id=import_id,
                    dataset_version=dataset_version,
                    source_file_sha256="a" * 64,
                    source_filename="cnefe-teste.csv",
                    city_ibge_code="3550308",
                    state="SP",
                    status=import_status.value,
                    record_count=0,
                    completed_at=(
                        activated_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
                        if import_status != CnefeImportStatus.LOADING
                        else None
                    ),
                    activated_at=(
                        activated_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
                        if import_status == CnefeImportStatus.ACTIVE
                        else None
                    ),
                )
            )
        session.add(
            CnefeAddressModel(
                record_key=record_key,
                import_id=import_id,
                provider_record_id=f"CNEFE-SP-000{suffix}",
                dataset_version=dataset_version,
                source_file_sha256="a" * 64,
                city_ibge_code="3550308",
                state="SP",
                postal_code="01001000",
                locality="São Paulo",
                street="Praça da Sé",
                street_name="da Sé",
                number="100",
                number_modifier=None,
                complement=None,
                normalized_street="PRACA DA SE",
                normalized_street_name="DA SE",
                normalized_number="100",
                latitude=latitude,
                longitude=longitude,
                geocoding_level=geocoding_level,
            )
        )
        registry = session.get(CnefeImportModel, import_id)
        if registry is not None:
            registry.record_count += 1
        session.commit()


def test_normalizes_address_without_losing_digits() -> None:
    assert normalize_text("  Praça   da Sé, 100-A ") == "PRACA DA SE 100 A"
    assert normalize_postal_code("01001-000") == "01001000"


def test_reports_when_city_dataset_is_not_loaded_and_audits_attempt() -> None:
    response = client.post(
        "/geocoding/resolve",
        json=REQUEST,
        headers={"X-Request-ID": "TRACE-DATASET-AUSENTE"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "DATASET_NOT_LOADED"
    assert body["candidate_count"] == 0
    assert body["selected"] is None
    assert body["automatic_coordinates_allowed"] is False
    assert body["requires_accuracy_confirmation"] is True

    with SessionLocal() as session:
        audit = session.scalar(select(GeocodingAuditModel))
        assert audit is not None
        assert audit.request_id == "TRACE-DATASET-AUSENTE"
        assert audit.result_status == "DATASET_NOT_LOADED"
        assert audit.requested_by == "development-anonymous"


def test_loading_and_failed_imports_remain_invisible() -> None:
    import_id = "00000000-0000-0000-0000-000000000010"
    add_cnefe_address(
        import_id=import_id,
        import_status=CnefeImportStatus.LOADING,
    )

    loading = client.post("/geocoding/resolve", json=REQUEST).json()
    assert loading["status"] == "DATASET_NOT_LOADED"

    with SessionLocal() as session:
        registry = session.get(CnefeImportModel, import_id)
        assert registry is not None
        registry.status = CnefeImportStatus.FAILED.value
        registry.failure_reason = "Falha controlada depois do primeiro lote."
        session.commit()

    failed = client.post("/geocoding/resolve", json=REQUEST).json()
    assert failed["status"] == "DATASET_NOT_LOADED"


def test_only_newest_active_city_version_is_visible() -> None:
    add_cnefe_address(
        import_id="00000000-0000-0000-0000-000000000011",
        dataset_version="CNEFE-V1",
        latitude=-23.55,
        activated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    add_cnefe_address(
        import_id="00000000-0000-0000-0000-000000000012",
        dataset_version="CNEFE-V2",
        latitude=-23.56,
        activated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    result = client.post("/geocoding/resolve", json=REQUEST).json()

    assert result["status"] == "MATCHED"
    assert result["selected"]["dataset_version"] == "CNEFE-V2"
    assert result["selected"]["latitude"] == -23.56


def test_suggests_unique_high_quality_match_without_inventing_accuracy() -> None:
    add_cnefe_address()

    response = client.post("/geocoding/resolve", json=REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MATCHED"
    assert body["automatic_coordinates_allowed"] is True
    assert body["requires_accuracy_confirmation"] is True
    assert body["maximum_contract_accuracy_meters"] == 50.0
    assert body["selected"]["latitude"] == -23.55052
    assert body["selected"]["geocoding_level"] == 1
    assert "accuracy_meters" not in body["selected"]
    assert body["evidence_reference"].startswith("CNEFE-AUDIT:")

    with SessionLocal() as session:
        audit = session.get(GeocodingAuditModel, body["audit_id"])
        assert audit is not None
        assert audit.selected_record_key is not None
        assert audit.source_file_sha256 == "a" * 64
        assert audit.query_sha256 != "a" * 64


def test_blocks_estimated_or_aggregated_coordinate() -> None:
    add_cnefe_address(geocoding_level=4)

    body = client.post("/geocoding/resolve", json=REQUEST).json()

    assert body["status"] == "INSUFFICIENT_POSITIONAL_QUALITY"
    assert body["automatic_coordinates_allowed"] is False
    assert body["selected"]["geocoding_level_description"] == (
        "coordenada da face de quadra"
    )


def test_blocks_ambiguous_exact_match() -> None:
    add_cnefe_address(suffix="1")
    add_cnefe_address(suffix="2", latitude=-23.5508)

    body = client.post("/geocoding/resolve", json=REQUEST).json()

    assert body["status"] == "AMBIGUOUS"
    assert body["candidate_count"] == 2
    assert body["selected"] is None
    assert body["automatic_coordinates_allowed"] is False


def test_reports_not_found_when_city_has_data_but_address_does_not_match() -> None:
    add_cnefe_address()
    request = {**REQUEST, "number": "99999"}

    body = client.post("/geocoding/resolve", json=request).json()

    assert body["status"] == "NOT_FOUND"
    assert body["candidate_count"] == 0


def test_rejects_inconsistent_city_identification() -> None:
    response = client.post(
        "/geocoding/resolve",
        json={**REQUEST, "state": "RJ"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CITY_DATA_MISMATCH"


def test_rejects_invalid_postal_code() -> None:
    response = client.post(
        "/geocoding/resolve",
        json={**REQUEST, "postal_code": "ABCDE-XYZ"},
    )

    assert response.status_code == 422


def test_binds_matched_audit_to_created_order() -> None:
    add_cnefe_address()
    audit = client.post("/geocoding/resolve", json=REQUEST).json()

    response = client.post(
        "/orders",
        json=order_payload_from_audit(audit, external_order_id="CNEFE-ORDER-001"),
    )

    assert response.status_code == 201, response.text
    assert (
        response.json()["location_confirmation"]["geocoding_audit_id"]
        == (audit["audit_id"])
    )


def test_rejects_nonexistent_audit() -> None:
    add_cnefe_address()
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    payload = order_payload_from_audit(audit, external_order_id="CNEFE-ORDER-FAKE")
    fake_id = "00000000-0000-0000-0000-999999999999"
    payload["location_confirmation"]["geocoding_audit_id"] = fake_id
    payload["location_confirmation"]["evidence_reference"] = f"CNEFE-AUDIT:{fake_id}"

    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GEOCODING_AUDIT_NOT_FOUND"


def test_rejects_audit_without_matched_result() -> None:
    add_cnefe_address(geocoding_level=4)
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    assert audit["status"] == "INSUFFICIENT_POSITIONAL_QUALITY"
    payload = order_payload_from_audit(
        audit,
        external_order_id="CNEFE-ORDER-NOT-MATCHED",
    )

    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GEOCODING_AUDIT_NOT_MATCHED"


def test_rejects_audit_requested_by_another_actor() -> None:
    add_cnefe_address()
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    with SessionLocal() as session:
        stored = session.get(GeocodingAuditModel, audit["audit_id"])
        assert stored is not None
        stored.requested_by = "another-client-actor"
        session.commit()

    response = client.post(
        "/orders",
        json=order_payload_from_audit(audit, external_order_id="CNEFE-ORDER-ACTOR"),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GEOCODING_AUDIT_ACTOR_MISMATCH"


def test_rejects_address_divergent_from_audit() -> None:
    add_cnefe_address()
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    payload = order_payload_from_audit(audit, external_order_id="CNEFE-ORDER-ADDRESS")
    payload["property"]["number"] = "101"

    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GEOCODING_AUDIT_ADDRESS_MISMATCH"


def test_rejects_coordinates_divergent_from_audit() -> None:
    add_cnefe_address()
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    payload = order_payload_from_audit(
        audit,
        external_order_id="CNEFE-ORDER-COORDINATES",
    )
    payload["location_confirmation"]["latitude"] = -22.9

    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == ("GEOCODING_AUDIT_COORDINATES_MISMATCH")


def test_rejects_audit_after_new_city_version_becomes_current() -> None:
    add_cnefe_address(
        import_id="00000000-0000-0000-0000-000000000020",
        dataset_version="CNEFE-V1",
        activated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    audit = client.post("/geocoding/resolve", json=REQUEST).json()
    add_cnefe_address(
        import_id="00000000-0000-0000-0000-000000000021",
        dataset_version="CNEFE-V2",
        activated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    response = client.post(
        "/orders",
        json=order_payload_from_audit(audit, external_order_id="CNEFE-ORDER-OLD"),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == ("GEOCODING_AUDIT_DATASET_INACTIVE")
