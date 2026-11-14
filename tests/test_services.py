import pytest

from app.core.errors import ConflictError
from app.core.security import hash_password, verify_password
from app.models.order import OrderStatus
from app.models.user import UserRole
from app.schemas.order import OrderItemInput
from tests.conftest import register_and_login


def test_password_hash_is_salted_and_verifies() -> None:
    first_hash = hash_password("sample-password-123")
    second_hash = hash_password("sample-password-123")

    assert first_hash != second_hash
    assert verify_password("sample-password-123", first_hash)
    assert not verify_password("wrong-password", first_hash)


def test_completed_order_cannot_be_cancelled(client) -> None:
    _, customer_token = register_and_login(client)
    context = client.app.state.context
    customer = context.users.get_user(1)
    assert customer is not None
    order = context.orders.create_order(
        customer.id,
        [OrderItemInput(sku="ITEM-1", quantity=1, unit_price="3.25")],
    )
    admin = context.users.register(
        "admin@example.com",
        "admin-password-123",
        "Sample Administrator",
        role=UserRole.ADMIN,
    )

    context.orders.update_status(order.id, OrderStatus.PAID, admin)
    context.orders.update_status(order.id, OrderStatus.SHIPPED, admin)
    context.orders.update_status(order.id, OrderStatus.COMPLETED, admin)

    with pytest.raises(ConflictError):
        context.orders.update_status(order.id, OrderStatus.CANCELLED, admin)
