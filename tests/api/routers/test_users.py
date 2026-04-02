"""Unit tests for FastAPI routers managing user account operations."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import users
from app.db.models.user import User
from app.services.auth_service import get_current_user, get_password_hash

# ---------------------------------------------------------------------------
# Setup FastAPI app for testing
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(users.router, prefix="/api/v1")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provides a mocked AsyncSession with explicit method mocks."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def test_user() -> User:
    user = User(
        id=1, email="gdpr@example.com", hashed_password=get_password_hash("correct_password")
    )
    return user


@pytest.fixture()
def override_deps(mock_db: AsyncMock, test_user: User):
    """Overrides dependencies for endpoints."""

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[users.get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_deps):
    """Provides an AsyncClient configured with the test FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Tests: DELETE /users/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_account_success(
    async_client: AsyncClient, mock_db: AsyncMock, test_user: User
) -> None:
    """Test successful hard delete when correct password is provided."""
    response = await async_client.request(
        "DELETE", "/api/v1/users/me", json={"password": "correct_password"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Account and all associated data permanently deleted"

    mock_db.delete.assert_called_once_with(test_user)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_account_wrong_password(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test delete returns 403 for an incorrect password."""
    response = await async_client.request(
        "DELETE", "/api/v1/users/me", json={"password": "wrong_password"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Incorrect password"

    mock_db.delete.assert_not_called()
    mock_db.commit.assert_not_called()
