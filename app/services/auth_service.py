from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklist (shared across requests)
_blacklist_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
_BLACKLIST_PREFIX = "token_blacklist:"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_verification_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    to_encode = {"exp": expire, "sub": email, "type": "email_verification"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_verification_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "email_verification":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def create_access_token(subject: str) -> str:
    """Create an access token with user.id as the subject."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": subject, "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    """Create a refresh token with user.id as the subject."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": subject, "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


async def blacklist_token(token: str) -> None:
    """Add a token to the Redis blacklist with TTL = remaining token lifetime."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        exp = payload.get("exp")
        if exp is None:
            return
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        if remaining > 0:
            await _blacklist_redis.set(
                f"{_BLACKLIST_PREFIX}{token}", "1", ex=remaining
            )
    except JWTError:
        pass  # Invalid token — nothing to blacklist


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token is in the Redis blacklist."""
    return await _blacklist_redis.exists(f"{_BLACKLIST_PREFIX}{token}") > 0


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check blacklist first
    if await is_token_blacklisted(token):
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Lookup by user.id instead of email
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
