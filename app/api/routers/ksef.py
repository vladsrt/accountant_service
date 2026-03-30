"""FastAPI endpoints for managing KSeF integrations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models.company import Company
from app.schemas.ksef import KsefSetupRequest, KsefSyncRequest
from app.services.ksef_auth import CryptoUtil
from app.tasks.ksef_tasks import sync_company_task

router = APIRouter(prefix="/api/v1/ksef", tags=["KSeF"])


@router.post(
    "/setup",
    status_code=status.HTTP_200_OK,
    summary="Configure KSeF credentials and trigger initial sync",
)
async def setup_ksef(
    payload: KsefSetupRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Encrypt and save a company's KSeF token, then trigger a background sync.

    Upserts the Company record with the new NIP and encrypted token.
    Then immediately enqueues `sync_company_task` in Celery to backfill historical data.
    """
    # 1. Encrypt the token securely
    try:
        encrypted_token = CryptoUtil.encrypt(payload.ksef_token, settings.ENCRYPTION_MASTER_KEY)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt KSeF token",
        ) from exc

    # 2. Upsert Company in the local DB
    company = await db.get(Company, payload.company_id)
    if company:
        company.nip = payload.nip
        company.ksef_token = encrypted_token
    else:
        # Create new company
        company = Company(
            id=payload.company_id,
            nip=payload.nip,
            ksef_token=encrypted_token,
        )
        db.add(company)

    await db.commit()

    # 3. Fire-and-forget Celery task
    sync_company_task.delay(company_id=payload.company_id)

    return {"status": "KSeF credentials saved and initial sync triggered"}


@router.post(
    "/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a background KSeF synchronization",
)
async def trigger_ksef_sync(
    payload: KsefSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue a Celery task to synchronize invoices for a company.

    Verifies the company exists and has KSeF credentials configured before proceeding.
    """
    # Verify company exists
    company = await db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {payload.company_id} not found",
        )

    if not company.ksef_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KSeF credentials not configured for this company",
        )

    # Fire-and-forget Celery task
    sync_company_task.delay(company_id=payload.company_id)

    return {"status": "Sync triggered in background"}
