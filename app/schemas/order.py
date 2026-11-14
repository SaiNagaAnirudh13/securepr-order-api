from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import Order, OrderItem, OrderStatus


class OrderItemInput(BaseModel):
    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    quantity: int = Field(ge=1, le=100)
    unit_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class OrderCreate(BaseModel):
    items: list[OrderItemInput] = Field(min_length=1, max_length=50)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    sku: str
    quantity: int
    unit_price: Decimal

    @classmethod
    def from_model(cls, item: OrderItem) -> "OrderItemResponse":
        return cls(
            sku=item.sku, quantity=item.quantity, unit_price=item.unit_price
        )


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    items: list[OrderItemResponse]
    total: Decimal
    created_at: datetime

    @classmethod
    def from_model(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            items=[OrderItemResponse.from_model(item) for item in order.items],
            total=order.total,
            created_at=order.created_at,
        )
