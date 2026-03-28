import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import async_session_factory
from app.db.models import Company, KsefSession
from app.services.ksef_auth import CryptoUtil, KsefAuthService


@pytest.fixture
async def real_db_session() -> AsyncSession:
    """Provides a real async database session for integration tests."""
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def test_company(real_db_session: AsyncSession) -> int:
    """
    Setup: Inserts a test company into the actual DB with real KSeF credentials
    encrypted via Fernet.
    Teardown: Deletes the test company and its KSeF session from the DB.
    """
    company_id = 99999

    # Pre-cleanup in case a previous test run failed mid-execution
    await real_db_session.execute(delete(KsefSession).where(KsefSession.company_id == company_id))
    await real_db_session.execute(delete(Company).where(Company.id == company_id))
    await real_db_session.commit()

    # Ensure settings actually have values so we don't insert empty credentials
    if not settings.KSEF_NIP or not settings.KSEF_TOKEN or not settings.ENCRYPTION_MASTER_KEY:
        pytest.skip(
            "Skipping integration test: Missing KSEF_NIP, KSEF_TOKEN or ENCRYPTION_MASTER_KEY in settings."
        )

    # Encrypt the real (test environment) token using the master key
    encrypted_token = CryptoUtil.encrypt(settings.KSEF_TOKEN, settings.ENCRYPTION_MASTER_KEY)

    # Insert test company
    await real_db_session.execute(
        insert(Company).values(
            id=company_id,
            nip=settings.KSEF_NIP,
            ksef_token=encrypted_token,
        )
    )
    await real_db_session.commit()

    yield company_id

    # Teardown logic
    await real_db_session.execute(delete(KsefSession).where(KsefSession.company_id == company_id))
    await real_db_session.execute(delete(Company).where(Company.id == company_id))
    await real_db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ensure_valid_session_real_api(test_company: int, real_db_session: AsyncSession):
    """
    Integration test connecting to actual KSeF API (test/demo environment)
    and making real assertions against the test database.
    """
    service = KsefAuthService(settings=settings)

    # ACTION: Should deserialize from DB, decrypt, send request to API, and save to DB
    token = await service.ensure_valid_session(test_company, real_db_session)

    # ASSERTIONS
    # 1. Returned token is a valid non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # 2. Check if the session is functionally saved in the database
    stmt = select(KsefSession).where(KsefSession.company_id == test_company)
    result = await real_db_session.execute(stmt)
    ksef_session = result.scalar_one_or_none()

    assert ksef_session is not None
    assert ksef_session.company_id == test_company
    assert ksef_session.access_token == token
    assert ksef_session.refresh_token is not None
    assert ksef_session.expires_at is not None
