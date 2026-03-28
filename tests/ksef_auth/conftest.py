from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings
from app.services.ksef_auth import KsefAuthService


@pytest.fixture
def master_key() -> str:
    """Generate a valid Fernet master key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def mock_settings(master_key: str) -> Settings:
    """Mock application settings with test URLs and master key."""
    return Settings(
        ENVIRONMENT="test",
        KSEF_BASE_URL="https://api-test.ksef.mf.gov.pl",
        ENCRYPTION_MASTER_KEY=master_key,
        # Default mock values for other required config fields (if not loaded from .env)
        KSEF_NIP="1111111111",
        KSEF_TOKEN="test_token",
    )


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def ksef_auth_service(mock_settings: Settings) -> KsefAuthService:
    """Instance of KsefAuthService initialized with mock settings."""
    return KsefAuthService(settings=mock_settings)
