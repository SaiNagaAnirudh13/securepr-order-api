import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.models.order import OrderStatus
from app.models.user import UserRole
from tests.conftest import register_and_login


def test_customer_can_create_and_read_own_order(client: TestClient) -> None:
    _, token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/orders",
        headers=headers,
        json={
            "items": [
                {"sku": "ITEM-1", "quantity": 2, "unit_price": "12.50"}
            ]
        },
    )

    assert created.status_code == 201
    order = created.json()
    assert order["total"] == "25.00"
    assert order["status"] == "pending"
    assert client.get(f"/orders/{order['id']}", headers=headers).status_code == 200


def test_customer_cannot_read_another_users_order(client: TestClient) -> None:
    _, first_token = register_and_login(client, "first@example.com")
    _, second_token = register_and_login(client, "second@example.com")
    created = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"items": [{"sku": "ITEM-1", "quantity": 1, "unit_price": "3.25"}]},
    )

    response = client.get(
        f"/orders/{created.json()['id']}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 403


def test_customer_can_cancel_pending_order_but_not_mark_it_paid(
    client: TestClient,
) -> None:
    _, token = register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/orders",
        headers=headers,
        json={"items": [{"sku": "ITEM-1", "quantity": 1, "unit_price": "3.25"}]},
    )
    order_id = created.json()["id"]

    forbidden = client.patch(
        f"/orders/{order_id}/status",
        headers=headers,
        json={"status": "paid"},
    )
    cancelled = client.patch(
        f"/orders/{order_id}/status",
        headers=headers,
        json={"status": "cancelled"},
    )

    assert forbidden.status_code == 403
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_admin_can_advance_order_status(client: TestClient) -> None:
    _, customer_token = register_and_login(client)
    context = client.app.state.context
    admin = context.users.register(
        "admin@example.com",
        "admin-password-123",
        "Sample Administrator",
        role=UserRole.ADMIN,
    )
    admin_token = context.sessions.create(admin.id)
    created = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"items": [{"sku": "ITEM-1", "quantity": 1, "unit_price": "3.25"}]},
    )

    response = client.patch(
        f"/orders/{created.json()['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "paid"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"

    history = context.orders._repository.get_status_history(
        created.json()["id"]
    )
    assert [
        (entry.previous_status, entry.new_status) for entry in history
    ] == [(OrderStatus.PENDING, OrderStatus.PAID)]


def _create_admin_token(client: TestClient) -> str:
    context = client.app.state.context
    admin = context.users.register(
        "admin@example.com",
        "admin-password-123",
        "Sample Administrator",
        role=UserRole.ADMIN,
    )
    return context.sessions.create(admin.id)


def _create_order(client: TestClient, token: str) -> int:
    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"sku": "ITEM-1", "quantity": 1, "unit_price": "3.25"}]},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_admin_can_bulk_update_order_statuses_and_records_history(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_ids = [
        _create_order(client, customer_token),
        _create_order(client, customer_token),
    ]

    response = client.patch(
        "/admin/orders/bulk-status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"order_ids": order_ids, "status": "paid"},
    )

    assert response.status_code == 200
    assert [order["id"] for order in response.json()] == order_ids
    assert [order["status"] for order in response.json()] == ["paid", "paid"]

    repository = client.app.state.context.orders._repository
    for order_id in order_ids:
        history = repository.get_status_history(order_id)
        assert [
            (entry.previous_status, entry.new_status) for entry in history
        ] == [(OrderStatus.PENDING, OrderStatus.PAID)]


def test_bulk_update_supports_existing_refund_transition(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_id = _create_order(client, customer_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    paid = client.patch(
        f"/orders/{order_id}/status",
        headers=admin_headers,
        json={"status": "paid"},
    )
    assert paid.status_code == 200

    refunded = client.patch(
        "/admin/orders/bulk-status",
        headers=admin_headers,
        json={"order_ids": [order_id], "status": "refunded"},
    )

    assert refunded.status_code == 200
    assert refunded.json()[0]["status"] == "refunded"


def test_customer_cannot_bulk_update_order_statuses(client: TestClient) -> None:
    _, customer_token = register_and_login(client)
    order_id = _create_order(client, customer_token)

    response = client.patch(
        "/admin/orders/bulk-status",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={"order_ids": [order_id], "status": "paid"},
    )

    assert response.status_code == 403


def test_missing_order_in_bulk_request_does_not_update_existing_orders(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_id = _create_order(client, customer_token)

    response = client.patch(
        "/admin/orders/bulk-status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"order_ids": [order_id, 9999], "status": "paid"},
    )

    assert response.status_code == 404
    order = client.get(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert order.json()["status"] == "pending"


def test_invalid_transition_in_bulk_request_does_not_update_other_orders(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    pending_order_id = _create_order(client, customer_token)
    cancelled_order_id = _create_order(client, customer_token)
    customer_headers = {"Authorization": f"Bearer {customer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    cancelled = client.patch(
        f"/orders/{cancelled_order_id}/status",
        headers=customer_headers,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200

    response = client.patch(
        "/admin/orders/bulk-status",
        headers=admin_headers,
        json={
            "order_ids": [pending_order_id, cancelled_order_id],
            "status": "paid",
        },
    )

    assert response.status_code == 409
    pending = client.get(
        f"/orders/{pending_order_id}", headers=customer_headers
    )
    assert pending.json()["status"] == "pending"


def test_duplicate_order_ids_are_rejected(client: TestClient) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_id = _create_order(client, customer_token)

    response = client.patch(
        "/admin/orders/bulk-status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"order_ids": [order_id, order_id], "status": "paid"},
    )

    assert response.status_code == 422


def test_database_failure_rolls_back_bulk_order_updates(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    order_ids = [
        _create_order(client, customer_token),
        _create_order(client, customer_token),
    ]
    context = client.app.state.context
    admin = context.users.register(
        "admin@example.com",
        "admin-password-123",
        "Sample Administrator",
        role=UserRole.ADMIN,
    )
    repository = context.orders._repository

    with repository._database.transaction() as connection:
        connection.execute(
            f"""
            CREATE TRIGGER fail_second_order_history
            BEFORE INSERT ON order_status_history
            WHEN NEW.order_id = {order_ids[1]}
            BEGIN
                SELECT RAISE(ABORT, 'simulated audit write failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        context.orders.bulk_update_statuses(
            order_ids, OrderStatus.PAID, admin
        )

    assert [
        repository.get_by_id(order_id).status for order_id in order_ids
    ] == [OrderStatus.PENDING, OrderStatus.PENDING]
    assert [
        repository.get_status_history(order_id) for order_id in order_ids
    ] == [[], []]
