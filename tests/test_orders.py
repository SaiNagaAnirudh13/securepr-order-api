from fastapi.testclient import TestClient

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


def test_admin_can_bulk_update_order_statuses(client: TestClient) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_ids = [
        _create_order(client, customer_token),
        _create_order(client, customer_token),
    ]

    response = client.patch(
        "/admin/orders/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"order_ids": order_ids, "status": "paid"},
    )

    assert response.status_code == 200
    assert [order["id"] for order in response.json()] == order_ids
    assert [order["status"] for order in response.json()] == ["paid", "paid"]


def test_customer_cannot_bulk_update_order_statuses(client: TestClient) -> None:
    _, token = register_and_login(client)
    order_id = _create_order(client, token)

    response = client.patch(
        "/admin/orders/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"order_ids": [order_id], "status": "paid"},
    )

    assert response.status_code == 403


def test_bulk_update_rejects_missing_order_without_updating_existing_orders(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_id = _create_order(client, customer_token)

    response = client.patch(
        "/admin/orders/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"order_ids": [order_id, 9999], "status": "paid"},
    )

    assert response.status_code == 404
    assert (
        client.get(
            f"/orders/{order_id}",
            headers={"Authorization": f"Bearer {customer_token}"},
        ).json()["status"]
        == "pending"
    )


def test_bulk_update_rejects_invalid_transition_without_partial_updates(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    first_order_id = _create_order(client, customer_token)
    completed_order_id = _create_order(client, customer_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    for status in ("paid", "shipped", "completed"):
        advanced = client.patch(
            f"/orders/{completed_order_id}/status",
            headers=admin_headers,
            json={"status": status},
        )
        assert advanced.status_code == 200

    response = client.patch(
        "/admin/orders/status",
        headers=admin_headers,
        json={
            "order_ids": [first_order_id, completed_order_id],
            "status": "paid",
        },
    )

    assert response.status_code == 409
    orders = client.get("/admin/orders", headers=admin_headers).json()
    statuses = {order["id"]: order["status"] for order in orders}
    assert statuses[first_order_id] == "pending"
    assert statuses[completed_order_id] == "completed"


def test_bulk_update_requires_unique_nonempty_order_ids(
    client: TestClient,
) -> None:
    _, customer_token = register_and_login(client)
    admin_token = _create_admin_token(client)
    order_id = _create_order(client, customer_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    empty_response = client.patch(
        "/admin/orders/status",
        headers=headers,
        json={"order_ids": [], "status": "paid"},
    )
    duplicate_response = client.patch(
        "/admin/orders/status",
        headers=headers,
        json={"order_ids": [order_id, order_id], "status": "paid"},
    )

    assert empty_response.status_code == 422
    assert duplicate_response.status_code == 422
