"""FastAPI endpoints for bank statement CSV upload and ingestion."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.bank_statement_service import (
    BankStatementParseError,
    BankStatementService,
    BankStatementValidationError,
)

router = APIRouter(prefix="/api/v1/bank", tags=["Bank Statements"])


@router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload a bank statement CSV and ingest transactions",
)
async def upload_bank_statement(
    file: UploadFile = File(...),
    company_id: int = Form(...),
    company_registration_date: date | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Parse, validate, filter, deduplicate, and persist bank transactions.

    Accepts a raw CSV bank statement export (mBank, PKO BP, Pekao, Alior, etc.).
    The bank format is auto-detected from the filename.

    Pipeline:
      1. Parse CSV via bank2ynab.
      2. Validate YTD coverage (statement must start from Jan 1 or company registration date).
      3. Filter to keep only positive inflows.
      4. SHA-256 hash each row for idempotent deduplication.
      5. Bulk upsert into ``bank_transactions`` table.

    Returns:
        JSON summary with ``total_parsed``, ``new_inserted``, ``duplicates_ignored``.
    """
    file_content = await file.read()

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    service = BankStatementService()

    try:
        summary = await service.process_statement(
            company_id=company_id,
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
