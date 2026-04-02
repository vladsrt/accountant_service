from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.schemas.company import CompanyCreate
from app.services.auth_service import get_current_user
from main import app

client = TestClient(app)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    async def mock_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = 1

    db.refresh.side_effect = mock_refresh
    return db


@pytest.fixture
def override_deps(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="test@example.com")
    yield
    app.dependency_overrides.clear()


def test_nip_validation_success():
    comp = CompanyCreate(nip="5252344078")
    assert comp.nip == "5252344078"


def test_nip_validation_invalid_checksum():
    with pytest.raises(ValueError, match="Invalid NIP checksum"):
        CompanyCreate(nip="5252344079")


def test_nip_validation_invalid_checksum_10():
    with pytest.raises(ValueError, match="Invalid NIP checksum"):
        CompanyCreate(nip="1234567890")


def test_nip_validation_bad_format():
    with pytest.raises(ValueError, match="NIP must contain exactly 10 digits"):
        CompanyCreate(nip="525234407A")
    with pytest.raises(ValueError, match="NIP must contain exactly 10 digits"):
        CompanyCreate(nip="123")


def test_create_company_success(override_deps, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [None, None]
    mock_db.execute.return_value = mock_result

    response = client.post("/api/v1/company", json={"nip": "5252344078"})

    assert response.status_code == 201
    mock_db.add.assert_called_once()
    added_company = mock_db.add.call_args[0][0]
    assert added_company.nip == "5252344078"
    assert added_company.user_id == 1


def test_create_company_already_exists(override_deps, mock_db):
    mock_result = MagicMock()
    mock_company = Company(id=1, user_id=1, nip="5252344078")
    mock_result.scalars.return_value.first.side_effect = [mock_company]
    mock_db.execute.return_value = mock_result

    response = client.post("/api/v1/company", json={"nip": "5252344078"})

    assert response.status_code == 400
    assert response.json()["detail"] == "User already has a company profile"


def test_get_my_company_success(override_deps, mock_db):
    mock_result = MagicMock()
    mock_company = Company(id=1, user_id=1, nip="5252344078")
    mock_result.scalars.return_value.first.return_value = mock_company
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/company/me")

    assert response.status_code == 200
    assert response.json()["nip"] == "5252344078"


def test_get_my_company_not_found(override_deps, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    response = client.get("/api/v1/company/me")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"
