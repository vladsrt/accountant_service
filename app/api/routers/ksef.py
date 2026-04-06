"""FastAPI endpoints for managing KSeF integrations."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.schemas.ksef import KsefSetupRequest
from app.services.auth_service import get_current_user
from app.services.ksef_auth import CryptoUtil
from app.tasks.ksef_tasks import sync_company_task

router = APIRouter(prefix="/api/v1/ksef", tags=["KSeF"])


async def _get_user_company(current_user: User, db: AsyncSession) -> Company:
    """Fetch the company belonging to the current user, or raise 404."""
    result = await db.execute(select(Company).where(Company.user_id == current_user.id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have a company profile",
        )
    return company


@router.post(
    "/setup",
    status_code=status.HTTP_200_OK,
    summary="Configure KSeF credentials and trigger initial sync",
)
@limiter.limit("5/minute")
async def setup_ksef(
    request: Request,
    payload: KsefSetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Encrypt and save a company's KSeF token, then trigger a background sync."""
    company = await _get_user_company(current_user, db)

    # Encrypt the token securely
    try:
        encrypted_token = CryptoUtil.encrypt(payload.ksef_token, settings.ENCRYPTION_MASTER_KEY)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt KSeF token",
        ) from exc

    # Update company record
    company.nip = payload.nip
    company.ksef_token = encrypted_token
    await db.commit()

    # Fire-and-forget Celery task
    sync_company_task.delay(company_id=company.id)

    return {"status": "KSeF credentials saved and initial sync triggered"}


@router.post(
    "/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a background KSeF synchronization",
)
@limiter.limit("5/minute")
async def trigger_ksef_sync(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a Celery task to synchronize invoices for the current user's company."""
    company = await _get_user_company(current_user, db)

    if not company.ksef_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KSeF credentials not configured for this company",
        )

    sync_company_task.delay(company_id=company.id)

    return {"status": "Sync triggered in background"}


@router.delete(
    "/token",
    status_code=status.HTTP_200_OK,
    summary="Revoke stored KSeF token",
)
async def delete_ksef_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove the stored KSeF token for the current user's company."""
    company = await _get_user_company(current_user, db)

    company.ksef_token = None
    await db.commit()

    return {"status": "KSeF token removed"}
