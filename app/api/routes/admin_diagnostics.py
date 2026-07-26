from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text

from app.core.admin_auth import require_admin_api_key
from app.domain.order_model import OrderModel
from app.domain.property_asset_model import PropertyAssetModel
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
