"""Tests for the Bank API Routers."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.bank_statement_service import (
    BankStatementParseError,
    BankStatementValidationError,
)
from main import app


@pytest.fixture
def test_client():
    # Use ASGITransport for testing async FastAPI endpoints
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_upload_bank_statement_success(test_client: AsyncClient):

    mock_summary = {"total_parsed": 10, "new_inserted": 5, "duplicates_ignored": 5}

    with patch(
        "app.api.routers.bank.BankStatementService.process_statement", return_value=mock_summary
    ) as mock_process:
        # Test HTTP multipart form data
        files = {"file": ("statement.csv", b"dummy,csv,content", "text/csv")}
        data = {"company_id": 1, "company_registration_date": "2026-01-01"}

        response = await test_client.post("/api/v1/bank/upload", data=data, files=files)

        assert response.status_code == 200
        assert response.json() == mock_summary
        mock_process.assert_called_once()
        kwargs = mock_process.call_args.kwargs
        assert kwargs["company_id"] == 1
        assert kwargs["file_content"] == b"dummy,csv,content"


@pytest.mark.asyncio
async def test_upload_bank_statement_validation_error(test_client: AsyncClient):

    with patch(
        "app.api.routers.bank.BankStatementService.process_statement",
        side_effect=BankStatementValidationError("Для 100% гарантии..."),
    ):
        files = {"file": ("statement.csv", b"dummy", "text/csv")}
        data = {"company_id": 1}

        response = await test_client.post("/api/v1/bank/upload", data=data, files=files)

        assert response.status_code == 400
        assert response.json()["detail"] == "Для 100% гарантии..."


@pytest.mark.asyncio
async def test_upload_bank_statement_parse_error(test_client: AsyncClient):

    with patch(
        "app.api.routers.bank.BankStatementService.process_statement",
        side_effect=BankStatementParseError("Invalid bank format"),
    ):
        files = {"file": ("statement.csv", b"dummy", "text/csv")}
        data = {"company_id": 1}

        response = await test_client.post("/api/v1/bank/upload", data=data, files=files)

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid bank format"


@pytest.mark.asyncio
async def test_upload_bank_statement_empty_file(test_client: AsyncClient):
    files = {"file": ("statement.csv", b"", "text/csv")}
    data = {"company_id": 1}

    response = await test_client.post("/api/v1/bank/upload", data=data, files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."
