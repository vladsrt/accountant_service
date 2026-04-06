"""FastAPI endpoints for bank statement CSV upload and ingestion."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.services.auth_service import get_current_user
from app.services.bank_statement_service import (
    BankStatementParseError,
    BankStatementService,
    BankStatementValidationError,
)

router = APIRouter(prefix="/api/v1/bank", tags=["Bank Statements"])


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
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload a bank statement CSV and ingest transactions",
)
@limiter.limit("10/minute")
async def upload_bank_statement(
    request: Request,
    file: UploadFile = File(...),
    company_registration_date: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parse, validate, filter, deduplicate, and persist bank transactions.

    Accepts a raw CSV bank statement export (mBank, PKO BP, Pekao, Alior, etc.).
    The bank format is auto-detected from the filename.

    The company_id is derived from the authenticated user's company profile,
    not from user input, preventing IDOR attacks.
    """
    # Derive company_id from authenticated user — NOT from form data
    company = await _get_user_company(current_user, db)

    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    service = BankStatementService()

    try:
        summary = await service.process_statement(
            company_id=company.id,
            company_registration_date=company_registration_date,
            file_content=file_content,
            filename=file.filename or "unknown.csv",
            db=db,
        )
    except BankStatementValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except BankStatementParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return summary
