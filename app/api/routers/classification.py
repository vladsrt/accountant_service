"""FastAPI endpoints for AI invoice classification."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models.company import Company
from app.db.models.invoice import Invoice
from app.db.models.invoice_line_classification import InvoiceLineClassification
from app.db.models.user import User
from app.schemas.classification import (
    ClarificationResolveRequest,
    ClassificationTriggerResponse,
    InvoiceClassificationResponse,
    LineClassificationResponse,
    PendingInvoiceResponse,
    PendingLineResponse,
)
from app.services.auth_service import get_current_user
from app.services.classification_service import ClassificationService
from app.tasks.classification_tasks import classify_company_task

router = APIRouter(prefix="/api/v1/classification", tags=["Classification"])


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
    "/trigger",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ClassificationTriggerResponse,
    summary="Trigger AI classification for all unclassified invoices",
)
@limiter.limit("5/minute")
async def trigger_classification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClassificationTriggerResponse:
    """Enqueue a background task to classify all unclassified invoices."""
    company = await _get_user_company(current_user, db)
    task = classify_company_task.delay(company_id=company.id)
    return ClassificationTriggerResponse(
        status="Classification triggered in background",
        task_id=task.id,
    )


@router.get(
    "/invoice/{invoice_id}",
    response_model=InvoiceClassificationResponse,
    summary="Get classification results for a specific invoice",
)
async def get_invoice_classification(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceClassificationResponse:
    """Return all line classification results for a given invoice."""
    company = await _get_user_company(current_user, db)

    # Verify invoice belongs to the user's company
    inv_stmt = select(Invoice).where(
        Invoice.id == invoice_id,
        Invoice.company_id == company.id,
    )
    inv_result = await db.execute(inv_stmt)
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found or access denied",
        )

    # Fetch line classifications
    lines_stmt = (
        select(InvoiceLineClassification)
        .where(InvoiceLineClassification.invoice_id == invoice_id)
        .order_by(InvoiceLineClassification.line_index)
    )
    lines_result = await db.execute(lines_stmt)
    lines = lines_result.scalars().all()

    return InvoiceClassificationResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        is_classified=invoice.is_classified,
        tax_rate=invoice.tax_rate,
        lines=[LineClassificationResponse.model_validate(line) for line in lines],
    )


@router.get(
    "/pending",
    response_model=list[PendingInvoiceResponse],
    summary="List invoices with NEEDS_CLARIFICATION lines",
)
async def get_pending_clarifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PendingInvoiceResponse]:
    """Return invoices that have lines requiring user clarification."""
    company = await _get_user_company(current_user, db)

    # Find all NEEDS_CLARIFICATION lines for this company's invoices
    stmt = (
        select(InvoiceLineClassification, Invoice.invoice_number)
        .join(Invoice, InvoiceLineClassification.invoice_id == Invoice.id)
        .where(
            Invoice.company_id == company.id,
            InvoiceLineClassification.verdict == "NEEDS_CLARIFICATION",
        )
        .order_by(InvoiceLineClassification.invoice_id, InvoiceLineClassification.line_index)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Group by invoice
    invoices_map: dict[int, PendingInvoiceResponse] = {}
    for line, inv_number in rows:
        if line.invoice_id not in invoices_map:
            invoices_map[line.invoice_id] = PendingInvoiceResponse(
                invoice_id=line.invoice_id,
                invoice_number=inv_number,
                questions=[],
            )
        invoices_map[line.invoice_id].questions.append(
            PendingLineResponse(
                line_index=line.line_index,
                p7_text=line.p7_text,
                clarification_question=line.clarification_question,
                ambiguity_flags=line.ambiguity_flags,
            )
        )

    return list(invoices_map.values())


@router.post(
    "/invoice/{invoice_id}/reclassify",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ClassificationTriggerResponse,
    summary="Reclassify a single invoice",
)
@limiter.limit("10/minute")
async def reclassify_invoice(
    request: Request,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClassificationTriggerResponse:
    """Delete existing classification results and reclassify the invoice."""
    company = await _get_user_company(current_user, db)

    # Verify invoice belongs to the user's company
    inv_stmt = select(Invoice).where(
        Invoice.id == invoice_id,
        Invoice.company_id == company.id,
    )
    inv_result = await db.execute(inv_stmt)
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found or access denied",
        )

    # Clear existing classifications
    from sqlalchemy import delete

    await db.execute(
        delete(InvoiceLineClassification).where(InvoiceLineClassification.invoice_id == invoice_id)
    )
    invoice.is_classified = False
    invoice.tax_rate = None
    await db.commit()

    # Trigger classification for the company (will pick up this invoice)
    task = classify_company_task.delay(company_id=company.id)
    return ClassificationTriggerResponse(
        status="Reclassification triggered",
        task_id=task.id,
    )


@router.post(
    "/resolve",
    summary="Resolve a NEEDS_CLARIFICATION line with user's answer",
)
@limiter.limit("10/minute")
async def resolve_pending_classification(
    request: Request,
    body: ClarificationResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-classify a pending line using the user's clarification answer."""
    company = await _get_user_company(current_user, db)

    result = await ClassificationService.resolve_classification(
        db=db,
        company_id=company.id,
        invoice_id=body.invoice_id,
        line_index=body.line_index,
        user_answer=body.user_answer,
    )

    if result["status"] == "NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["detail"],
        )

    return result
