from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from ksef2 import Environment

from app.services.ksef_auth import (
    CryptoUtil,
    KsefAuthError,
    KsefAuthService,
    KsefEncryptionError,
    KsefSessionNotFoundError,
    _resolve_environment,
)


@pytest.mark.asyncio
class TestCryptoUtilAndEnv:
    def test_encrypt_decrypt_success(self, master_key: str):
        plaintext = "secret_ksef_token_123!"
        encrypted = CryptoUtil.encrypt(plaintext, master_key)

        assert encrypted != plaintext
        assert isinstance(encrypted, str)

        decrypted = CryptoUtil.decrypt(encrypted, master_key)
        assert decrypted == plaintext

    def test_decrypt_invalid_key(self):
        wrong_key = Fernet.generate_key().decode()
        encrypted = CryptoUtil.encrypt("test_data", wrong_key)

        # Now try to decrypt with a new, different key
        another_key = Fernet.generate_key().decode()
        with pytest.raises(KsefEncryptionError, match="Decryption failed: invalid token"):
            CryptoUtil.decrypt(encrypted, another_key)

    @pytest.mark.parametrize(
        "url, expected_env",
        [
            ("https://api.ksef.mf.gov.pl", Environment.PRODUCTION),
            ("https://api-test.ksef.mf.gov.pl", Environment.TEST),
            ("https://api-demo.ksef.mf.gov.pl", Environment.DEMO),
            ("https://api-test.ksef.mf.gov.pl/", Environment.TEST),
            ("https://api-test.ksef.mf.gov.pl/api/online/", Environment.TEST),
        ],
    )
    def test_resolve_environment_success(self, url: str, expected_env: Environment):
        assert _resolve_environment(url) is expected_env

    def test_resolve_environment_error(self):
        with pytest.raises(KsefAuthError, match="Cannot resolve KSeF environment from URL"):
            _resolve_environment("https://invalid.url.com")


@pytest.mark.asyncio
class TestKsefAuthService:
    async def test_ensure_valid_session_existing_valid(
        self,
        ksef_auth_service: KsefAuthService,
        mock_db_session: AsyncMock,
    ):
        """1. Valid Session: db returns a session expiring in 2 hours."""
        company_id = 1
        valid_until = datetime.now(timezone.utc) + timedelta(hours=2)

        # Mock result for the first select (ksef session)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("access_123", "refresh_123", valid_until)
        mock_db_session.execute.return_value = mock_result

        with patch("app.services.ksef_auth.Client") as sdk_mock:
            token = await ksef_auth_service.ensure_valid_session(company_id, mock_db_session)

            assert token == "access_123"
            # Ensured that execute was called only once (for session lookup)
            assert mock_db_session.execute.call_count == 1
            sdk_mock.assert_not_called()

    async def test_ensure_valid_session_refresh(
        self,
        ksef_auth_service: KsefAuthService,
        mock_db_session: AsyncMock,
    ):
        """2. Refresh Session: session is about to expire, sdk is called to refresh."""
        company_id = 1
        # Expiring in 1 minute (< 5 minutes threshold)
        expiring_soon = datetime.now(timezone.utc) + timedelta(minutes=1)
        new_valid_until = datetime.now(timezone.utc) + timedelta(hours=2)

        # Setup db interactions
        # 1st call: select ksef session (ensure_valid_session)
        # 2nd call: select refresh token (inside _refresh_session)
        # 3rd call: update session table
        mock_result_1 = MagicMock()
        mock_result_1.fetchone.return_value = ("old_access", "old_refresh", expiring_soon)

        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = "old_refresh"

        mock_db_session.execute.side_effect = [mock_result_1, mock_result_2, MagicMock()]

        with patch("app.services.ksef_auth.Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.__enter__.return_value = mock_client

            # Mocking the refresh response
            mock_refresh_response = MagicMock()
            mock_refresh_response.access_token.token = "new_access_123"
            mock_refresh_response.access_token.valid_until = new_valid_until
            mock_client.authentication.refresh.return_value = mock_refresh_response

            token = await ksef_auth_service.ensure_valid_session(company_id, mock_db_session)

            assert token == "new_access_123"
            assert mock_db_session.execute.call_count == 3
            mock_client.authentication.refresh.assert_called_once_with(refresh_token="old_refresh")
            mock_db_session.commit.assert_called_once()

    async def test_ensure_valid_session_full_auth(
        self,
        ksef_auth_service: KsefAuthService,
        mock_db_session: AsyncMock,
        master_key: str,
    ):
        """3. Full Auth: no existing session, full sdk authentication performed."""
        company_id = 1
        nip = "1112223344"
        raw_ksef_token = "secret_ksef_token"
        encrypted_ksef_token = CryptoUtil.encrypt(raw_ksef_token, master_key)
        new_valid_until = datetime.now(timezone.utc) + timedelta(hours=2)

        # 1st execution: checking for existing session -> returns None
        mock_result_1 = MagicMock()
        mock_result_1.fetchone.return_value = None

        # 2nd execution: fetching company nip & ksef_token
        mock_result_2 = MagicMock()
        mock_result_2.fetchone.return_value = (nip, encrypted_ksef_token)

        # 3rd execution: inserting new ksef session
        mock_result_3 = MagicMock()

        mock_db_session.execute.side_effect = [mock_result_1, mock_result_2, mock_result_3]

        with patch("app.services.ksef_auth.Client") as MockClient:
            mock_client = MockClient.return_value
            mock_client.__enter__.return_value = mock_client

            # Mocking the auth response
            mock_auth_response = MagicMock()
            mock_auth_response.auth_tokens.access_token.token = "new_full_access"
            mock_auth_response.auth_tokens.refresh_token.token = "new_full_refresh"
            mock_auth_response.auth_tokens.access_token.valid_until = new_valid_until
            mock_client.authentication.with_token.return_value = mock_auth_response

            token = await ksef_auth_service.ensure_valid_session(company_id, mock_db_session)

            assert token == "new_full_access"
            assert mock_db_session.execute.call_count == 3
            mock_db_session.commit.assert_called_once()
            mock_client.authentication.with_token.assert_called_once_with(
                ksef_token=raw_ksef_token, nip=nip
            )

    async def test_ensure_valid_session_company_not_found(
        self,
        ksef_auth_service: KsefAuthService,
        mock_db_session: AsyncMock,
    ):
        """4. Error Handling: company not found in DB during full auth."""
        company_id = 999

        # 1st call: session lookup -> None
        mock_result_1 = MagicMock()
        mock_result_1.fetchone.return_value = None

        # 2nd call: company lookup -> None
        mock_result_2 = MagicMock()
        mock_result_2.fetchone.return_value = None

        mock_db_session.execute.side_effect = [mock_result_1, mock_result_2]

        with pytest.raises(
            KsefSessionNotFoundError, match=f"Company with id={company_id} not found"
        ):
            await ksef_auth_service.ensure_valid_session(company_id, mock_db_session)
