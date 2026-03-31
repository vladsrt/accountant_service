"""
KSeF 2.0 Authentication Service.

Uses the ksef2 SDK for the authorization flow and Fernet symmetric encryption
for storing ksef_token at rest in the database.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from ksef2 import Client, Environment
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Company, KsefSession

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KsefAuthError(Exception):
    """Base exception for all KSeF authentication errors."""


class KsefSessionNotFoundError(KsefAuthError):
    """Raised when no KSeF session is found for a given company."""


class KsefEncryptionError(KsefAuthError):
    """Raised when token encryption or decryption fails."""


# ---------------------------------------------------------------------------
# Fernet crypto utilities
# ---------------------------------------------------------------------------


class CryptoUtil:
    """Symmetric encrypt / decrypt helpers using Fernet (AES-128-CBC + HMAC)."""

    @staticmethod
    def encrypt(plaintext: str, master_key: str) -> str:
        """Encrypt a plaintext string and return a URL-safe base64 ciphertext."""
        try:
            f = Fernet(master_key.encode())
            return f.encrypt(plaintext.encode()).decode()
        except Exception as exc:
            raise KsefEncryptionError(f"Encryption failed: {exc}") from exc

    @staticmethod
    def decrypt(ciphertext: str, master_key: str) -> str:
        """Decrypt a Fernet ciphertext back to the original string."""
        try:
            f = Fernet(master_key.encode())
            return f.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise KsefEncryptionError(
                "Decryption failed: invalid token or wrong master key"
            ) from exc
        except Exception as exc:
            raise KsefEncryptionError(f"Decryption failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Environment resolver
# ---------------------------------------------------------------------------

_URL_TO_ENV: dict[str, Environment] = {
    "https://api.ksef.mf.gov.pl": Environment.PRODUCTION,
    "https://api-test.ksef.mf.gov.pl": Environment.TEST,
    "https://api-demo.ksef.mf.gov.pl": Environment.DEMO,
}


def _resolve_environment(base_url: str) -> Environment:
    """Map a KSeF base URL to the corresponding SDK Environment enum."""
    normalized = base_url.rstrip("/").split("/v2")[0].split("/api/")[0]
    env = _URL_TO_ENV.get(normalized)
    if env is None:
        raise KsefAuthError(
            f"Cannot resolve KSeF environment from URL: {base_url!r}. "
            f"Expected one of: {list(_URL_TO_ENV.keys())}"
        )
    return env


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class KsefAuthService:
    """Async service for KSeF 2.0 authentication via the ksef2 SDK."""

    _REFRESH_THRESHOLD: timedelta = timedelta(minutes=5)

    def __init__(self, settings: Settings) -> None:
        self._master_key: str = settings.ENCRYPTION_MASTER_KEY
        self._environment: Environment = _resolve_environment(settings.KSEF_BASE_URL)
        self.logger: logging.Logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # SDK wrappers (sync → async via to_thread)
    # ------------------------------------------------------------------

    def _sdk_authenticate(self, ksef_token: str, nip: str) -> dict[str, str]:
        """Run the full SDK token auth flow (synchronous, called in a thread).

        Returns:
            Dict with access_token, refresh_token, expires_at.
        """
        with Client(environment=self._environment) as client:
            authenticated = client.authentication.with_token(
                ksef_token=ksef_token,
                nip=nip,
            )
            return {
                "access_token": authenticated.auth_tokens.access_token.token,
                "refresh_token": authenticated.auth_tokens.refresh_token.token,
                "expires_at": authenticated.auth_tokens.access_token.valid_until.isoformat(),
            }

    def _sdk_refresh(self, refresh_token: str) -> dict[str, str]:
        """Refresh an access token via SDK (synchronous, called in a thread).

        Returns:
            Dict with access_token and expires_at.
        """
        with Client(environment=self._environment) as client:
            refreshed = client.authentication.refresh(refresh_token=refresh_token)
            return {
                "access_token": refreshed.access_token.token,
                "expires_at": refreshed.access_token.valid_until.isoformat(),
            }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _save_session(
        self,
        company_id: int,
        tokens: dict[str, str],
        db: AsyncSession,
    ) -> None:
        """Upsert a KSeF session row for the given company.

        Both access_token and refresh_token are encrypted at rest with Fernet
        before being persisted, matching the protection applied to ksef_token.
        """
        self.logger.info("Saving KSeF session for company_id=%d", company_id)

        encrypted_access = CryptoUtil.encrypt(tokens["access_token"], self._master_key)
        encrypted_refresh = CryptoUtil.encrypt(tokens["refresh_token"], self._master_key)

        stmt = text("""
            INSERT INTO ksef_sessions (company_id, access_token, refresh_token, expires_at)
            VALUES (:company_id, :access_token, :refresh_token, :expires_at)
            ON CONFLICT (company_id) DO UPDATE SET
                access_token  = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at    = EXCLUDED.expires_at
        """)

        await db.execute(
            stmt,
            {
                "company_id": company_id,
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "expires_at": tokens["expires_at"],
            },
        )
        await db.commit()

        self.logger.info("KSeF session saved for company_id=%d", company_id)

    async def _refresh_session(
        self,
        company_id: int,
        db: AsyncSession,
    ) -> str:
        """Refresh an existing KSeF session via SDK and persist new tokens.

        Decrypts the stored refresh_token before passing it to the SDK, and
        re-encrypts the new access_token before writing it back.

        Returns:
            The new plaintext access_token (for immediate in-memory use).
        """
        # Load current session from DB via SQLAlchemy ORM
        stmt = select(KsefSession.refresh_token).where(KsefSession.company_id == company_id)
        result = await db.execute(stmt)
        encrypted_refresh = result.scalar_one_or_none()

        if encrypted_refresh is None:
            raise KsefSessionNotFoundError(f"No KSeF session found for company_id={company_id}")

        refresh_token = CryptoUtil.decrypt(encrypted_refresh, self._master_key)

        self.logger.info("Refreshing session via SDK (company_id=%d)", company_id)
        refreshed = await asyncio.to_thread(self._sdk_refresh, refresh_token)

        encrypted_new_access = CryptoUtil.encrypt(refreshed["access_token"], self._master_key)

        # Update only access_token and expires_at; refresh_token stays unchanged
        update_stmt = (
            update(KsefSession)
            .where(KsefSession.company_id == company_id)
            .values(access_token=encrypted_new_access, expires_at=refreshed["expires_at"])
        )
        await db.execute(update_stmt)
        await db.commit()

        self.logger.info("Session refreshed for company_id=%d", company_id)
        return refreshed["access_token"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ensure_valid_session(
        self,
        company_id: int,
        db: AsyncSession,
    ) -> str:
        """Return a valid KSeF access token for the given company.

        1. If a valid session exists (> 5 min to expiry) → return stored access_token.
        2. If expiring soon → refresh via SDK.
        3. If no session → full auth flow via SDK (decrypt ksef_token first).

        Returns:
            A valid KSeF access_token string.
        """
        self.logger.info("Ensuring valid KSeF session for company_id=%d", company_id)

        # Check for an existing session
        stmt = select(
            KsefSession.access_token, KsefSession.refresh_token, KsefSession.expires_at
        ).where(KsefSession.company_id == company_id)

        result = await db.execute(stmt)
        row = result.fetchone()

        if row is not None:
            encrypted_access, _encrypted_refresh, expires_at = row

            # Ensure expires_at is offset-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            time_left = expires_at - datetime.now(timezone.utc)

            if time_left > self._REFRESH_THRESHOLD:
                self.logger.info("Existing session still valid (expires in %s)", time_left)
                return CryptoUtil.decrypt(encrypted_access, self._master_key)

            self.logger.info("Session expiring soon (in %s), refreshing…", time_left)
            return await self._refresh_session(company_id, db)

        # No session — run full auth flow
        self.logger.info("No existing session, starting full auth flow via SDK")

        # Fetch company credentials (ksef_token is encrypted in DB)
        comp_stmt = select(Company.nip, Company.ksef_token).where(Company.id == company_id)
        comp_result = await db.execute(comp_stmt)
        company_row = comp_result.fetchone()

        if company_row is None:
            raise KsefSessionNotFoundError(f"Company with id={company_id} not found")

        nip, encrypted_ksef_token = company_row

        # Decrypt the ksef_token
        self.logger.info("Decrypting ksef_token for company_id=%d", company_id)
        decrypted_token = CryptoUtil.decrypt(encrypted_ksef_token, self._master_key)

        # Authenticate via SDK (sync → thread)
        self.logger.info(
            "Authenticating via ksef2 SDK (NIP=%s, env=%s)",
            nip,
            self._environment.name,
        )
        tokens = await asyncio.to_thread(self._sdk_authenticate, decrypted_token, nip)

        # Persist session
        await self._save_session(company_id, tokens, db)

        self.logger.info("Full auth flow completed for company_id=%d", company_id)
        return tokens["access_token"]
