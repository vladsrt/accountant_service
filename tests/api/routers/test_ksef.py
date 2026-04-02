"""Unit tests for FastAPI routers managing KSeF integrations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import ksef
from app.core.config import settings
from app.db.models.company import Company
from app.db.models.user import User
from app.services.auth_service import get_current_user

# ---------------------------------------------------------------------------
# Setup FastAPI app for testing
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(ksef.router)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

mock_user = User(id=1, email="test@example.com")


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provides a mocked AsyncSession with explicit method mocks."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture()
def override_deps(mock_db: AsyncMock):
    """Overrides get_db and get_current_user dependencies."""

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[ksef.get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_deps):
    """Provides an AsyncClient configured with the test FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


def _mock_company_query(mock_db: AsyncMock, company: Company | None) -> None:
    """Helper to configure mock_db.execute to return a company via scalars().first()."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = company
    mock_db.execute.return_value = mock_result


# ---------------------------------------------------------------------------
# Tests: POST /setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_ksef_success(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /setup encrypts token and saves to user's company."""
    existing_company = Company(id=1, user_id=1, nip="0000000000", ksef_token=None)
    _mock_company_query(mock_db, existing_company)

    payload = {"nip": "1234567890", "ksef_token": "raw-sensitive-token"}

    with patch(
        "app.api.routers.ksef.CryptoUtil.encrypt", return_value="encrypted-token"
    ) as mock_encrypt:
        with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
            response = await async_client.post("/api/v1/ksef/setup", json=payload)

            assert response.status_code == 200
            assert response.json()["status"] == "KSeF credentials saved and initial sync triggered"

            mock_encrypt.assert_called_once_with(
                "raw-sensitive-token", settings.ENCRYPTION_MASTER_KEY
            )

            assert existing_company.nip == "1234567890"
            assert existing_company.ksef_token == "encrypted-token"

            mock_db.commit.assert_called_once()
            mock_delay.assert_called_once_with(company_id=1)


@pytest.mark.asyncio
async def test_setup_ksef_no_company(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /setup returns 404 when user has no company profile."""
    _mock_company_query(mock_db, None)

    payload = {"nip": "1234567890", "ksef_token": "raw-token"}
    response = await async_client.post("/api/v1/ksef/setup", json=payload)

    assert response.status_code == 404
    assert "does not have a company profile" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests: POST /sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_ksef_sync_success(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /sync triggers background task for user's company."""
    existing_company = Company(id=1, user_id=1, nip="1234567890", ksef_token="encrypted-token")
    _mock_company_query(mock_db, existing_company)

    with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
        response = await async_client.post("/api/v1/ksef/sync")

        assert response.status_code == 202
        assert response.json()["status"] == "Sync triggered in background"
        mock_delay.assert_called_once_with(company_id=1)


@pytest.mark.asyncio
async def test_trigger_ksef_sync_no_company(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /sync returns 404 when user has no company."""
    _mock_company_query(mock_db, None)

    response = await async_client.post("/api/v1/ksef/sync")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_ksef_sync_no_token(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /sync returns 400 when company has no KSeF credentials."""
    existing_company = Company(id=1, user_id=1, nip="1234567890", ksef_token=None)
    _mock_company_query(mock_db, existing_company)

    with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
        response = await async_client.post("/api/v1/ksef/sync")

        assert response.status_code == 400
        assert "credentials not configured" in response.json()["detail"]
        mock_delay.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: DELETE /token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_ksef_token_success(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test DELETE /token clears the stored ksef_token."""
    existing_company = Company(id=1, user_id=1, nip="1234567890", ksef_token="encrypted-token")
    _mock_company_query(mock_db, existing_company)

    response = await async_client.delete("/api/v1/ksef/token")

    assert response.status_code == 200
    assert response.json()["status"] == "KSeF token removed"
    assert existing_company.ksef_token is None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_ksef_token_no_company(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test DELETE /token returns 404 when user has no company."""
    _mock_company_query(mock_db, None)

    response = await async_client.delete("/api/v1/ksef/token")

    assert response.status_code == 404
