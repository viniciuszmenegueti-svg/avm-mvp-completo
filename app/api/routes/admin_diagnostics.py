from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text

from app.core.admin_auth import require_admin_api_key
from app.core.config import APP_ENV, MODEL_EXECUTION_MODE
from app.domain.cnefe_import_model import CnefeImportModel, CnefeImportStatus
from app.domain.order_model import OrderModel
from app.domain.property_asset_model import PropertyAssetModel
from app.domain.statistical_model_version_model import StatisticalModelVersionModel
from app.domain.valuation_model import ValuationModel
from app.infrastructure.dependencies import DatabaseSession
from app.schemas.order import OrderStatus


router = APIRouter(prefix="/admin", tags=["Administração"])
AdminActor = Annotated[str, Depends(require_admin_api_key)]


@router.get("/diagnostics", summary="Diagnóstico operacional")
def diagnostics(session: DatabaseSession, actor: AdminActor) -> dict[str, object]:
    session.execute(text("SELECT 1"))
    order_counts = {
        status.value: session.scalar(
            select(func.count(OrderModel.internal_order_id)).where(
                OrderModel.status == status.value
            )
        )
        or 0
        for status in OrderStatus
    }
    return {
        "status": "ok",
        "database": "ok",
        "actor": actor,
        "counts": {
            "orders": session.scalar(select(func.count(OrderModel.internal_order_id)))
            or 0,
            "property_assets": session.scalar(
                select(func.count(PropertyAssetModel.property_asset_id))
            )
            or 0,
            "valuations": session.scalar(
                select(func.count(ValuationModel.valuation_id))
            )
            or 0,
        },
        "orders_by_status": order_counts,
    }


@router.get(
    "/homologation-readiness",
    summary="Expõe gates objetivos sem declarar homologação contratual",
)
def homologation_readiness(
    session: DatabaseSession,
    actor: AdminActor,
) -> dict[str, object]:
    active_cnefe_imports = int(
        session.scalar(
            select(func.count(CnefeImportModel.import_id)).where(
                CnefeImportModel.status == CnefeImportStatus.ACTIVE.value
            )
        )
        or 0
    )
    approved_shadow_models = int(
        session.scalar(
            select(func.count(StatisticalModelVersionModel.model_id)).where(
                StatisticalModelVersionModel.status == "HOMOLOGATION_APPROVED"
            )
        )
        or 0
    )
    controlled_testing_ready = (
        MODEL_EXECUTION_MODE == "HOMOLOGATION_SHADOW"
        and active_cnefe_imports > 0
        and approved_shadow_models > 0
    )
    return {
        "status": (
            "READY_FOR_CONTROLLED_TECHNICAL_TESTING"
            if controlled_testing_ready
            else "SETUP_REQUIRED"
        ),
        "environment": APP_ENV,
        "execution_mode": MODEL_EXECUTION_MODE,
        "requested_by": actor,
        "controlled_technical_testing_ready": controlled_testing_ready,
        "formal_caixa_homologation_ready": False,
        "contractual_operation_ready": False,
        "objective_counts": {
            "active_cnefe_imports": active_cnefe_imports,
            "approved_shadow_models": approved_shadow_models,
        },
        "external_blockers": [
            "OFFICIAL_CAIXA_API_AND_SANDBOX",
            "REAL_DATASET_AND_RESPONSIBLE_TECHNICIAN_APPROVAL",
            "MODEL_REPORT_SIGNED_PER_CITY",
            "PAIRED_FLOW_FOR_30_DAYS",
            "CAIXA_PERFORMANCE_THRESHOLDS",
            "QUALIFIED_ELECTRONIC_SIGNATURE_AND_ART_RRT",
            "EXPLICIT_CAIXA_AUTHORIZATION",
        ],
        "software_blockers_for_formal_homologation": [
            "MATRICULA_AI_AND_CROSS_DOCUMENT_VALIDATION",
            "OIDC_MFA_AND_FINE_GRAINED_RBAC",
            "IMMUTABLE_EXTERNAL_AUDIT_STORAGE",
            "DEVIATION_INGESTION_AND_MODEL_SUSPENSION",
            "POST_ISSUANCE_REVIEW_AND_BILLING_WORKFLOWS",
        ],
        "notice": (
            "Internal evidence never substitutes the CAIXA approval, the "
            "Responsible Technicians or the paired validation flow."
        ),
    }
