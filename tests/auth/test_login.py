from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models.user import User
from app.services.auth_service import get_current_user
from main import app

# Provide dynamic mocked endpoint inside our fastAPI app
test_router = APIRouter()


@test_router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": "You are in", "user": current_user.email}


app.include_router(test_router)

client = TestClient(app)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture(autouse=True)
def override_get_db(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.clear()


def test_login_success(mock_db):
    from app.services.auth_service import get_password_hash

    mock_result = MagicMock()
    mock_user = User(
        email="test@example.com",
        hashed_password=get_password_hash("realpassword"),
        is_verified=True,
    )
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.post(
        "/api/v1/auth/login", data={"username": "test@example.com", "password": "realpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    mock_db.add.assert_called_once()
    saved_user = mock_db.add.call_args[0][0]
    assert saved_user.last_login_at is not None


def test_login_invalid_password(mock_db):
    from app.services.auth_service import get_password_hash

    mock_result = MagicMock()
    mock_user = User(
        email="test@example.com",
        hashed_password=get_password_hash("realpassword"),
        is_verified=True,
    )
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.post(
        "/api/v1/auth/login", data={"username": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_unverified_email(mock_db):
    from app.services.auth_service import get_password_hash

    mock_result = MagicMock()
    mock_user = User(
        email="test@example.com",
        hashed_password=get_password_hash("realpassword"),
        is_verified=False,
    )
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.post(
        "/api/v1/auth/login", data={"username": "test@example.com", "password": "realpassword"}
    )
    assert response.status_code == 403


def test_refresh_token_success(mock_db):
    from app.services.auth_service import create_refresh_token

    token = create_refresh_token("test@example.com")

    mock_result = MagicMock()
    mock_user = User(email="test@example.com", is_verified=True)
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_protected_route_success(mock_db):
    from app.services.auth_service import create_access_token

    token = create_access_token("test@example.com")

    mock_result = MagicMock()
    mock_user = User(email="test@example.com", is_verified=True)
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_db.execute.return_value = mock_result

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"] == "test@example.com"


def test_protected_route_unauthorized():
    response = client.get("/protected")
    assert response.status_code == 401

    response = client.get("/protected", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401


def test_login_rate_limiting(mock_db):
    limiter._storage.reset()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", data={"username": "ratelimit@example.com", "password": "pwd"}
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login", data={"username": "ratelimit@example.com", "password": "pwd"}
    )
    assert response.status_code == 429
