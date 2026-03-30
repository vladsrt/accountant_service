"""Unit tests for FastAPI routers managing KSeF integrations."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers import ksef
from app.core.config import settings
from app.db.models.company import Company

# ---------------------------------------------------------------------------
# Setup FastAPI app for testing
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(ksef.router)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Provides a mocked AsyncSession with explicit method mocks."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture()
def override_get_db(mock_db: AsyncMock):
    """Overrides the get_db dependency with an async generator."""

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[ksef.get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    """Provides an AsyncClient configured with the test FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_ksef_new_company(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /setup endpoint for a new company: encrypts token and triggers sync."""
    mock_db.get.return_value = None  # Company does not exist

    payload = {"company_id": 1, "nip": "1234567890", "ksef_token": "raw-sensitive-token"}

    with patch(
        "app.api.routers.ksef.CryptoUtil.encrypt", return_value="encrypted-token"
    ) as mock_encrypt:
        with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
            response = await async_client.post("/api/v1/ksef/setup", json=payload)

            assert response.status_code == 200
            assert response.json()["status"] == "KSeF credentials saved and initial sync triggered"

            # Assert encryption happened with master key
            mock_encrypt.assert_called_once_with(
                "raw-sensitive-token", settings.ENCRYPTION_MASTER_KEY
            )

            # Assert new company was created and added to db
            mock_db.add.assert_called_once()
            added_company = mock_db.add.call_args[0][0]
            assert isinstance(added_company, Company)
            assert added_company.id == 1
            assert added_company.nip == "1234567890"
            assert added_company.ksef_token == "encrypted-token"

            # Assert DB commit
            mock_db.commit.assert_called_once()

            # Assert task triggered
            mock_delay.assert_called_once_with(company_id=1)


@pytest.mark.asyncio
async def test_setup_ksef_existing_company(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /setup endpoint for an existing company: updates token and triggers sync."""
    existing_company = Company(id=1, nip="0000000000", ksef_token="old-token")
    mock_db.get.return_value = existing_company

    payload = {"company_id": 1, "nip": "1234567890", "ksef_token": "new-raw-token"}

    with patch("app.api.routers.ksef.CryptoUtil.encrypt", return_value="new-encrypted-token"):
        with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
            response = await async_client.post("/api/v1/ksef/setup", json=payload)

            assert response.status_code == 200

            # Assert existing company fields were updated
            assert existing_company.nip == "1234567890"
            assert existing_company.ksef_token == "new-encrypted-token"

            # Since existing, db.add() should NOT be called
            mock_db.add.assert_not_called()
            mock_db.commit.assert_called_once()

            # task triggered
            mock_delay.assert_called_once_with(company_id=1)


@pytest.mark.asyncio
async def test_trigger_ksef_sync_success(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /sync endpoint for an existing configured company triggers background task."""
    existing_company = Company(id=1, nip="1234567890", ksef_token="encrypted-token")
    mock_db.get.return_value = existing_company

    payload = {"company_id": 1}

    with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
        response = await async_client.post("/api/v1/ksef/sync", json=payload)

        assert response.status_code == 202
        assert response.json()["status"] == "Sync triggered in background"

        mock_delay.assert_called_once_with(company_id=1)


@pytest.mark.asyncio
async def test_trigger_ksef_sync_company_not_found(
    async_client: AsyncClient, mock_db: AsyncMock
) -> None:
    """Test /sync endpoint when company is not found."""
    mock_db.get.return_value = None

    payload = {"company_id": 1}

    with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
        response = await async_client.post("/api/v1/ksef/sync", json=payload)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        mock_delay.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_ksef_sync_no_token(async_client: AsyncClient, mock_db: AsyncMock) -> None:
    """Test /sync endpoint when company has no complete KSeF setup."""
    existing_company = Company(id=1, nip="1234567890", ksef_token="")
    mock_db.get.return_value = existing_company

    payload = {"company_id": 1}

    with patch("app.api.routers.ksef.sync_company_task.delay") as mock_delay:
        response = await async_client.post("/api/v1/ksef/sync", json=payload)

        assert response.status_code == 400
        assert "credentials not configured" in response.json()["detail"]
        mock_delay.assert_not_called()
