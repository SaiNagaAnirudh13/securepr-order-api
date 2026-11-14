import logging

from app.models.order import Order

logger = logging.getLogger(__name__)


def log_order_created(order: Order) -> None:
    logger.info(
        "Order created",
        extra={"order_id": order.id, "user_id": order.user_id},
    )
