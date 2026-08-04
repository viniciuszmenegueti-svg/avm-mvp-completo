from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.cnefe_address_model import CnefeAddressModel
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus
from app.domain.geocoding_audit_model import GeocodingAuditModel


def get_current_active_cnefe_import(
    session: Session,
    city_ibge_code: str,
) -> CnefeImportModel | None:
    statement = (
        select(CnefeImportModel)
        .where(
            CnefeImportModel.city_ibge_code == city_ibge_code,
            CnefeImportModel.status == CnefeImportStatus.ACTIVE.value,
        )
        .order_by(
            CnefeImportModel.activated_at.desc(),
            CnefeImportModel.started_at.desc(),
            CnefeImportModel.import_id.desc(),
        )
        .limit(1)
    )
    return session.scalar(statement)


def city_has_cnefe_data(session: Session, city_ibge_code: str) -> bool:
    active_import = get_current_active_cnefe_import(session, city_ibge_code)
    if active_import is None:
        return False
    statement = (
        select(func.count())
        .select_from(CnefeAddressModel)
        .where(CnefeAddressModel.import_id == active_import.import_id)
    )
    return bool(session.scalar(statement))


def find_exact_cnefe_addresses(
    session: Session,
    *,
    city_ibge_code: str,
    postal_code: str,
    normalized_street: str,
    normalized_number: str,
    limit: int = 11,
) -> list[CnefeAddressModel]:
    active_import = get_current_active_cnefe_import(session, city_ibge_code)
    if active_import is None:
        return []
    statement = (
        select(CnefeAddressModel)
        .where(
            CnefeAddressModel.import_id == active_import.import_id,
            CnefeAddressModel.city_ibge_code == city_ibge_code,
            CnefeAddressModel.postal_code == postal_code,
            CnefeAddressModel.normalized_number == normalized_number,
            or_(
                CnefeAddressModel.normalized_street == normalized_street,
                CnefeAddressModel.normalized_street_name == normalized_street,
            ),
        )
        .order_by(
            CnefeAddressModel.geocoding_level.asc(),
            CnefeAddressModel.provider_record_id.asc(),
        )
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def create_geocoding_audit(
    session: Session,
    audit: GeocodingAuditModel,
) -> GeocodingAuditModel:
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit
