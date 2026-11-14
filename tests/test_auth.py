from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def test_registration_login_and_authenticated_profile(client: TestClient) -> None:
    user_id, token = register_and_login(client)

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["role"] == "user"
    assert "password_hash" not in response.json()


def test_login_rejects_incorrect_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "customer@example.com",
            "password": "sample-password-123",
            "display_name": "Sample Customer",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": "customer@example.com", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "Email or password is incorrect"


def test_registration_cannot_assign_admin_role(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "customer@example.com",
            "password": "sample-password-123",
            "display_name": "Sample Customer",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_invalid_or_missing_bearer_token_is_rejected(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["error"] == "A bearer token is required"


def test_registration_reports_invalid_input_as_validation_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "short",
            "display_name": "",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed"
    assert response.json()["details"]
    assert '"input"' not in response.text
