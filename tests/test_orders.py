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
