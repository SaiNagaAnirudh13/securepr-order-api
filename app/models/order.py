from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Order:
    id: int
    user_id: int
    status: OrderStatus
    items: tuple[OrderItem, ...]
    total: Decimal
    created_at: datetime


@dataclass(frozen=True)
class OrderStatusHistory:
    id: int
    order_id: int
    previous_status: OrderStatus | None
    new_status: OrderStatus
    changed_at: datetime
