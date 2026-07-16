from app.schemas.order import OrderResponse

orders_storage: dict[str, OrderResponse] = {}

external_order_index: dict[str, str] = {}
