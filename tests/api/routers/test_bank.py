"""Tests for the Bank API Routers.

All tests mock authentication (get_current_user) and company lookup
since the endpoint derives company_id from the authenticated user's
company profile (IDOR-safe design).
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.services.auth_service import get_current_user
from app.services.bank_statement_service import (
    BankStatementParseError,
    BankStatementValidationError,
)
from main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user() -> User:
    user = User(email="bank@example.com", hashed_password="hashed", is_verified=True)
    user.id = 1
    return user


@pytest.fixture
def mock_company() -> Company:
    company = Company(nip="1234567890")
    company.id = 42
    company.user_id = 1
    return company


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture(autouse=True)
def override_deps(mock_user, mock_company, mock_db):
    """Override FastAPI dependencies to bypass real auth and DB."""

    async def _fake_user():
        return mock_user

    async def _fake_db():
        yield mock_db

    # Mock _get_user_company at the router level to return our fake company
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_bank_statement_success(test_client: AsyncClient, mock_company):
    mock_summary = {"total_parsed": 10, "new_inserted": 5, "duplicates_ignored": 5}

    with (
        patch(
            "app.api.routers.bank.BankStatementService.process_statement",
            return_value=mock_summary,
        ) as mock_process,
        patch(
            "app.api.routers.bank._get_user_company",
            return_value=mock_company,
        ),
    ):
        files = {"file": ("statement.csv", b"dummy,csv,content", "text/csv")}

        response = await test_client.post("/api/v1/bank/upload", files=files)

        assert response.status_code == 200
        assert response.json() == mock_summary
        mock_process.assert_called_once()
        kwargs = mock_process.call_args.kwargs
        assert kwargs["company_id"] == 42  # Derived from mock_company.id
        assert kwargs["file_content"] == b"dummy,csv,content"


@pytest.mark.asyncio
async def test_upload_bank_statement_validation_error(test_client: AsyncClient, mock_company):
    with (
        patch(
            "app.api.routers.bank.BankStatementService.process_statement",
            side_effect=BankStatementValidationError("Для 100% гарантии..."),
        ),
        patch(
            "app.api.routers.bank._get_user_company",
            return_value=mock_company,
        ),
    ):
        files = {"file": ("statement.csv", b"dummy", "text/csv")}

        response = await test_client.post("/api/v1/bank/upload", files=files)

        assert response.status_code == 400
        assert response.json()["detail"] == "Для 100% гарантии..."


@pytest.mark.asyncio
async def test_upload_bank_statement_parse_error(test_client: AsyncClient, mock_company):
    with (
        patch(
            "app.api.routers.bank.BankStatementService.process_statement",
            side_effect=BankStatementParseError("Invalid bank format"),
        ),
        patch(
            "app.api.routers.bank._get_user_company",
            return_value=mock_company,
        ),
    ):
        files = {"file": ("statement.csv", b"dummy", "text/csv")}

        response = await test_client.post("/api/v1/bank/upload", files=files)

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid bank format"


@pytest.mark.asyncio
async def test_upload_bank_statement_empty_file(test_client: AsyncClient, mock_company):
    with patch(
        "app.api.routers.bank._get_user_company",
        return_value=mock_company,
    ):
        files = {"file": ("statement.csv", b"", "text/csv")}

        response = await test_client.post("/api/v1/bank/upload", files=files)

        assert response.status_code == 400
        assert response.json()["detail"] == "Uploaded file is empty."
