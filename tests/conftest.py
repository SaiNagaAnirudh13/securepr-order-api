from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    application = create_app(
        Settings(
            database_path=str(tmp_path / "test.sqlite3"),
            session_ttl_seconds=60,
            log_level="WARNING",
        )
    )
    with TestClient(application) as test_client:
        yield test_client


def register_and_login(
    client: TestClient, email: str = "customer@example.com"
) -> tuple[int, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "sample-password-123",
            "display_name": "Sample Customer",
        },
    )
    assert response.status_code == 201
    user_id = response.json()["id"]
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "sample-password-123"},
    )
    assert login.status_code == 200
    return user_id, login.json()["access_token"]
