from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.db.models.user import User
from main import app

client = TestClient(app)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    # Mock refresh to populate db generated fields
    from datetime import datetime, timezone

    async def _mock_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = 1
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_mock_refresh)
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture(autouse=True)
def override_get_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.clear()


def test_register_user_success(mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    with patch("app.api.routers.auth.send_verification_email_task") as mock_task:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        mock_task.delay.assert_called_once()

        args = mock_db.add.call_args[0]
        user = args[0]
        assert user.email == "test@example.com"
        assert user.hashed_password != "securepassword123"
        assert user.is_verified is False


def test_register_user_duplicate(mock_db):
    mock_result = MagicMock()
    mock_user = User(email="testdupe@example.com", hashed_password="abc", is_verified=False)
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "testdupe@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"


def test_verify_email_success(mock_db):
    from app.services.auth_service import create_verification_token

    token = create_verification_token("verify@example.com")

    mock_result = MagicMock()
    mock_user = User(email="verify@example.com", hashed_password="abc", is_verified=False)
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.get(f"/api/v1/auth/verify-email?token={token}")
    assert response.status_code == 200
    assert response.json()["message"] == "Email verified successfully"
    assert mock_user.is_verified is True


def test_verify_email_invalid_token(mock_db):
    response = client.get("/api/v1/auth/verify-email?token=invalid_token")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification token"


def test_rate_limiting(mock_db):
    from app.core.limiter import limiter

    limiter._storage.reset()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    with patch("app.api.routers.auth.send_verification_email_task"):
        # Hit the register limit 5 times
        for _ in range(5):
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "rate@example.com", "password": "securepassword123"},
                headers={"X-Forwarded-For": "192.168.1.1"},
            )
            assert response.status_code == 201

        # 6th time should fail
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "rate@example.com", "password": "securepassword123"},
            headers={"X-Forwarded-For": "192.168.1.1"},
        )
        assert response.status_code == 429
