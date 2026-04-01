from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import (
    create_verification_token,
    decode_verification_token,
    get_password_hash,
)
from app.tasks.email_tasks import send_verification_email_task

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user with an email and a strong password.
    Returns the user data (without password) and triggers an asynchronous email validation task.
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Hash password (raw password is not saved or logged anywhere)
    hashed_password = get_password_hash(user_data.password)

    # Create user
    new_user = User(email=user_data.email, hashed_password=hashed_password, is_verified=False)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate verification token
    token = create_verification_token(user_data.email)

    # Dispatch Celery task asynchronously
    send_verification_email_task.delay(user_data.email, token)

    return new_user


@router.get("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify an email address using the token sent securely.
    """
    email = decode_verification_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Find user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    # Mark as verified
    user.is_verified = True
    db.add(user)
    await db.commit()

    return {"message": "Email verified successfully"}
