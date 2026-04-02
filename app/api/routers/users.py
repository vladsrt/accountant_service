"""FastAPI endpoints for managing users."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.user import User
from app.schemas.user import UserDeleteRequest
from app.services.auth_service import get_current_user, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Permanently delete user account",
)
async def delete_my_account(
    payload: UserDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Execute a GDPR hard delete of the user account and all connected data.
    Requires password confirmation for safety.
    """
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password",
        )

    await db.delete(current_user)
    await db.commit()

    return {"status": "Account and all associated data permanently deleted"}
