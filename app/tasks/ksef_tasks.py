"""Background tasks for KSeF synchronization."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.db.database import async_session_factory
from app.services.invoice_sync import InvoiceSyncError, InvoiceSyncService
from app.worker import celery_app

logger = logging.getLogger(__name__)


async def _run_sync(company_id: int) -> dict:
    """Async proxy function to execute the KSeF sync for a specific company."""
    logger.info("Starting async KSeF sync for company_id: %d", company_id)
    service = InvoiceSyncService(settings=settings)

    async with async_session_factory() as session:
        result = await service.sync_company(company_id=company_id, db=session)

        # Post-sync metadata hook for RAG/LLM pipelines
        try:
            from app.services.llm_payload_service import LLMPayloadService

            unclassified = await LLMPayloadService.get_unclassified_payload(
                company_id=company_id, db=session
            )
            logger.info(
                "AI Classification Prep: %d unclassified invoices ready for company_id: %d",
                len(unclassified),
                company_id,
            )
        except Exception as exc:
            logger.exception("Failed to retrieve unclassified payload count: %s", exc)

    logger.info("Completed async KSeF sync for company_id: %d", company_id)
    return result


@celery_app.task(bind=True, max_retries=5, name="sync_company_task")
def sync_company_task(self, company_id: int) -> dict | None:
    """Celery task to run background synchronization for a given company.

    Automatically handles retries with exponential backoff on failure.

    Args:
        company_id: The local database ID of the company to sync.

    Returns:
        A dictionary summarizing the sync run, or None if retrying.
    """
    try:
        # Bridge sync Celery to async InvoiceSyncService
        return asyncio.run(_run_sync(company_id))

    except (InvoiceSyncError, Exception) as exc:
        logger.error(
            "sync_company_task failed for company_id %d: %s. Retrying...", company_id, str(exc)
        )
        # Exponential backoff: 2^retries
        countdown = 2**self.request.retries

        try:
            self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                "sync_company_task reached max retries (%d) for company_id %d",
                self.max_retries,
                company_id,
            )
            raise
    return None
