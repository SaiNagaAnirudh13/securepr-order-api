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
    OrderStatus.PAID: {
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.SHIPPED: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
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
            raise AuthorizationError(
                "You cannot access another account's order")
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
            raise AuthorizationError(
                "You cannot change another account's order")
        if actor.role != UserRole.ADMIN and new_status != OrderStatus.CANCELLED:
            raise AuthorizationError(
                "Customers may only cancel their own orders")
        self._validate_status_transition(order, new_status)
        updated = self._repository.update_status(order_id, new_status)
        if updated is None:
            raise NotFoundError("Order not found")
        logger.info(
            "Order status updated",
            extra={"order_id": order_id, "status": new_status.value},
        )
        return updated

    def bulk_update_statuses(
        self, order_ids: list[int], new_status: OrderStatus, actor: User
    ) -> list[Order]:
        if actor.role != UserRole.ADMIN:
            raise AuthorizationError("Administrator access is required")
        if len(order_ids) != len(set(order_ids)):
            raise ConflictError("Duplicate order IDs are not allowed")

        orders: list[Order] = []
        for order_id in order_ids:
            order = self._repository.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order not found")
            self._validate_status_transition(order, new_status)
            orders.append(order)

        updated = self._repository.update_statuses(
            order_ids,
            new_status,
            {order.id: order.status for order in orders},
        )
        if updated is None:
            raise ConflictError(
                "Order status changed during bulk update; please retry"
            )
        logger.info(
            "Order statuses bulk updated",
            extra={
                "order_ids": order_ids,
                "status": new_status.value,
                "count": len(updated),
            },
        )
        return updated

    @staticmethod
    def _validate_status_transition(
        order: Order, new_status: OrderStatus
    ) -> None:
        if new_status not in _ALLOWED_TRANSITIONS[order.status]:
            raise ConflictError(
                f"Order cannot move from {order.status.value} to {new_status.value}"
            )
