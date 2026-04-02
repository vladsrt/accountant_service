import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
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
    # Ensure settings actually have values so we don't insert empty credentials
    if not settings.KSEF_NIP or not settings.KSEF_TOKEN or not settings.ENCRYPTION_MASTER_KEY:
        pytest.skip(
            "Skipping integration test: Missing KSEF_NIP, KSEF_TOKEN or ENCRYPTION_MASTER_KEY in settings."
        )

    # Pre-cleanup by NIP in case a previous test run failed mid-execution
    existing = await real_db_session.execute(
        select(Company.id).where(Company.nip == settings.KSEF_NIP)
    )
    existing_id = existing.scalar_one_or_none()
    if existing_id is not None:
        await real_db_session.execute(
            delete(KsefSession).where(KsefSession.company_id == existing_id)
        )
        await real_db_session.execute(delete(Company).where(Company.id == existing_id))
        await real_db_session.commit()

    # Encrypt the real (test environment) token using the master key
    encrypted_token = CryptoUtil.encrypt(settings.KSEF_TOKEN, settings.ENCRYPTION_MASTER_KEY)

    # Insert test company; let PostgreSQL GENERATED ALWAYS AS IDENTITY assign the id
    user_email = "integration_ksef@example.com"
    user_res = await real_db_session.execute(select(User.id).where(User.email == user_email))
    user_id = user_res.scalar_one_or_none()
    
    if not user_id:
        new_user = await real_db_session.execute(
            insert(User).values(email=user_email, hashed_password="fake", is_verified=True).returning(User.id)
        )
        user_id = new_user.scalar_one()
    # ------------------------------------------

    # Insert test company WITH user_id
    result = await real_db_session.execute(
        insert(Company)
        .values(user_id=user_id, nip=settings.KSEF_NIP, ksef_token=encrypted_token)
        .returning(Company.id)
    )
    company_id = result.scalar_one()
    await real_db_session.commit()

    yield company_id

    # Teardown
    from sqlalchemy import delete
    await real_db_session.execute(delete(Company).where(Company.id == company_id))
    await real_db_session.execute(delete(User).where(User.id == user_id))
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
    # access_token is stored encrypted; decrypt before comparing to the returned plaintext token
    assert CryptoUtil.decrypt(ksef_session.access_token, settings.ENCRYPTION_MASTER_KEY) == token
    assert ksef_session.refresh_token is not None
    assert ksef_session.expires_at is not None
