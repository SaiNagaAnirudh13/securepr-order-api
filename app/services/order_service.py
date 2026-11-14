import logging
from decimal import Decimal

from app.core.errors import AuthorizationError, ConflictError, NotFoundError
from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderItemInput
from app.services.notification_service import log_order_created

logger = logging.getLogger(__name__)

_ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def create_order(self, user_id: int, items: list[OrderItemInput]) -> Order:
        total = sum(
            (item.unit_price * item.quantity for item in items), Decimal("0.00")
        )
        order = self._repository.create(user_id, items, total)
        log_order_created(order)
        return order

    def get_order(self, order_id: int, actor: User) -> Order:
        order = self._repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if actor.role != UserRole.ADMIN and order.user_id != actor.id:
            raise AuthorizationError("You cannot access another account's order")
        return order

    def list_for_user(self, user_id: int) -> list[Order]:
        return self._repository.list_for_user(user_id)

    def list_all(self) -> list[Order]:
        return self._repository.list_all()

    def update_status(
        self, order_id: int, new_status: OrderStatus, actor: User
    ) -> Order:
        order = self._repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if actor.role != UserRole.ADMIN and order.user_id != actor.id:
            raise AuthorizationError("You cannot change another account's order")
        if actor.role != UserRole.ADMIN and new_status != OrderStatus.CANCELLED:
            raise AuthorizationError("Customers may only cancel their own orders")
        if new_status not in _ALLOWED_TRANSITIONS[order.status]:
            raise ConflictError(
                f"Order cannot move from {order.status.value} to {new_status.value}"
            )
        updated = self._repository.update_status(order_id, new_status)
        if updated is None:
            raise NotFoundError("Order not found")
        logger.info(
            "Order status updated",
            extra={"order_id": order_id, "status": new_status.value},
        )
        return updated
