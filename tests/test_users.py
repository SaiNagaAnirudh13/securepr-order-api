from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def test_user_can_update_own_display_name(client: TestClient) -> None:
    _, token = register_and_login(client)
    response = client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Updated Customer"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Customer"


def test_customer_cannot_access_admin_user_list(client: TestClient) -> None:
    _, token = register_and_login(client)
    response = client.get(
        "/admin/users", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_profile_update_requires_a_field(client: TestClient) -> None:
    _, token = register_and_login(client)
    response = client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert response.status_code == 422
