import hashlib
import math
import re
import unicodedata
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.request_id import get_request_id
from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus
from app.domain.geocoding_audit_model import GeocodingAuditModel
from app.repositories.geocoding_sqlalchemy import (
    city_has_cnefe_data,
    create_geocoding_audit,
    find_exact_cnefe_addresses,
    get_current_active_cnefe_import,
)
from app.schemas.geocoding import (
    GeocodingAddressRequest,
    GeocodingCandidateResponse,
    GeocodingResponse,
    GeocodingStatus,
)
from app.schemas.order import OrderCreate


POSITIONAL_LEVEL_DESCRIPTIONS = {
    1: "coordenada original do endereço no Censo 2022",
    2: "coordenada de endereço ajustada por agrupamento do mesmo número",
    3: "coordenada estimada do endereço",
    4: "coordenada da face de quadra",
    5: "coordenada da localidade",
    6: "coordenada do setor censitário",
}
AUTOMATIC_SUGGESTION_LEVELS = frozenset({1, 2})


class GeocodingAuditIntegrityError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", ascii_value.upper()).split())


def normalize_postal_code(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _query_sha256(
    payload: GeocodingAddressRequest,
    postal_code: str,
    normalized_street: str,
    normalized_number: str,
) -> str:
    canonical = "|".join(
        (
            payload.city_ibge_code,
            payload.state,
            normalize_text(payload.city),
            postal_code,
            normalized_street,
            normalized_number,
            normalize_text(payload.complement or ""),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate(model: CnefeAddressModel) -> GeocodingCandidateResponse:
    return GeocodingCandidateResponse(
        provider_record_id=model.provider_record_id,
        dataset_version=model.dataset_version,
        source_file_sha256=model.source_file_sha256,
        city_ibge_code=model.city_ibge_code,
        state=model.state,
        postal_code=model.postal_code,
        locality=model.locality,
        street=model.street,
        number=model.number,
        number_modifier=model.number_modifier,
        complement=model.complement,
        latitude=float(model.latitude),
        longitude=float(model.longitude),
        geocoding_level=model.geocoding_level,
        geocoding_level_description=POSITIONAL_LEVEL_DESCRIPTIONS[
            model.geocoding_level
        ],
    )


def validate_cnefe_audit_for_order(
    session: Session,
    *,
    order: OrderCreate,
    requested_by: str,
) -> None:
    declaration = order.location_confirmation
    method = (declaration.confirmation_method or "").strip().upper()
    if method != "CNEFE_IBGE":
        return

    audit_id = declaration.geocoding_audit_id
    if audit_id is None:
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_REQUIRED",
            "O método CNEFE_IBGE exige uma auditoria explícita.",
        )
    audit = session.get(GeocodingAuditModel, audit_id)
    if audit is None:
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_NOT_FOUND",
            "A auditoria de geocodificação informada não existe.",
        )
    if audit.result_status != GeocodingStatus.MATCHED.value:
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_NOT_MATCHED",
            "Somente uma auditoria CNEFE com resultado MATCHED pode confirmar a ordem.",
        )
    if audit.requested_by != requested_by:
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_ACTOR_MISMATCH",
            "A auditoria CNEFE pertence a outra identidade de integração.",
        )

    selected = (
        session.get(CnefeAddressModel, audit.selected_record_key)
        if audit.selected_record_key is not None
        else None
    )
    registry = (
        session.get(CnefeImportModel, selected.import_id)
        if selected is not None
        else None
    )
    current_import = get_current_active_cnefe_import(
        session,
        order.property.city_ibge_code,
    )
    if (
        selected is None
        or registry is None
        or registry.status != CnefeImportStatus.ACTIVE.value
        or current_import is None
        or current_import.import_id != registry.import_id
    ):
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_DATASET_INACTIVE",
            "A auditoria não pertence à versão CNEFE ativa da cidade.",
        )

    address = GeocodingAddressRequest(
        city_ibge_code=order.property.city_ibge_code,
        state=order.property.state,
        city=order.property.city,
        postal_code=order.property.postal_code,
        street=order.property.street,
        number=order.property.number,
        complement=order.property.complement,
    )
    postal_code = normalize_postal_code(address.postal_code)
    normalized_street = normalize_text(address.street)
    normalized_number = normalize_text(address.number)
    expected_query_hash = _query_sha256(
        address,
        postal_code,
        normalized_street,
        normalized_number,
    )
    if (
        audit.query_sha256 != expected_query_hash
        or audit.city_ibge_code != address.city_ibge_code
        or audit.normalized_postal_code != postal_code
        or audit.normalized_street != normalized_street
        or audit.normalized_number != normalized_number
    ):
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_ADDRESS_MISMATCH",
            "O endereço da ordem diverge do endereço auditado no CNEFE.",
        )

    latitude = declaration.latitude
    longitude = declaration.longitude
    if (
        latitude is None
        or longitude is None
        or not math.isclose(latitude, float(selected.latitude), abs_tol=0.0000005)
        or not math.isclose(longitude, float(selected.longitude), abs_tol=0.0000005)
    ):
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_COORDINATES_MISMATCH",
            "As coordenadas da ordem divergem do registro selecionado no CNEFE.",
        )
    if not declaration.evidence_reference or (
        audit.evidence_reference not in declaration.evidence_reference
        if audit.evidence_reference is not None
        else True
    ):
        raise GeocodingAuditIntegrityError(
            "GEOCODING_AUDIT_EVIDENCE_MISMATCH",
            "A evidência da ordem não referencia a auditoria CNEFE informada.",
        )


def resolve_cnefe_address(
    session: Session,
    *,
    payload: GeocodingAddressRequest,
    requested_by: str,
) -> GeocodingResponse:
    audit_id = str(uuid4())
    postal_code = normalize_postal_code(payload.postal_code)
    normalized_street = normalize_text(payload.street)
    normalized_number = normalize_text(payload.number)
    query_sha256 = _query_sha256(
        payload,
        postal_code,
        normalized_street,
        normalized_number,
    )

    status = GeocodingStatus.NOT_FOUND
    message = "Endereço não localizado por correspondência exata no CNEFE importado."
    selected_model: CnefeAddressModel | None = None
    evidence_reference: str | None = None
    automatic_coordinates_allowed = False

    if not city_has_cnefe_data(session, payload.city_ibge_code):
        candidates: list[CnefeAddressModel] = []
        status = GeocodingStatus.DATASET_NOT_LOADED
        message = "A base CNEFE desta cidade ainda não foi importada."
    else:
        candidates = find_exact_cnefe_addresses(
            session,
            city_ibge_code=payload.city_ibge_code,
            postal_code=postal_code,
            normalized_street=normalized_street,
            normalized_number=normalized_number,
        )

    if len(candidates) > 1:
        status = GeocodingStatus.AMBIGUOUS
        message = (
            "Mais de um registro CNEFE corresponde ao endereço. "
            "A seleção automática foi bloqueada."
        )
    elif len(candidates) == 1:
        selected_model = candidates[0]
        evidence_reference = f"CNEFE-AUDIT:{audit_id}"
        if selected_model.geocoding_level in AUTOMATIC_SUGGESTION_LEVELS:
            status = GeocodingStatus.MATCHED
            automatic_coordinates_allowed = True
            message = (
                "Coordenadas sugeridas pelo CNEFE. A precisão em metros deve ser "
                "confirmada com evidência aprovada antes de criar a ordem."
            )
        else:
            status = GeocodingStatus.INSUFFICIENT_POSITIONAL_QUALITY
            message = (
                "O registro usa coordenada estimada ou agregada. A seleção "
                "automática foi bloqueada; faça validação documental ou de campo."
            )

    audit = GeocodingAuditModel(
        audit_id=audit_id,
        request_id=get_request_id(),
        requested_by=requested_by,
        query_sha256=query_sha256,
        city_ibge_code=payload.city_ibge_code,
        normalized_postal_code=postal_code,
        normalized_street=normalized_street,
        normalized_number=normalized_number,
        result_status=status.value,
        candidate_count=len(candidates),
        selected_record_key=(selected_model.record_key if selected_model else None),
        dataset_version=(selected_model.dataset_version if selected_model else None),
        source_file_sha256=(
            selected_model.source_file_sha256 if selected_model else None
        ),
        evidence_reference=evidence_reference,
    )
    create_geocoding_audit(session, audit)

    return GeocodingResponse(
        audit_id=audit_id,
        status=status,
        message=message,
        candidate_count=len(candidates),
        selected=_candidate(selected_model) if selected_model else None,
        evidence_reference=evidence_reference,
        automatic_coordinates_allowed=automatic_coordinates_allowed,
    )
