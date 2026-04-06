"""Background tasks for KSeF synchronization."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.db.database import create_worker_engine
from app.services.invoice_sync import (
    InvoiceSyncPermanentError,
    InvoiceSyncService,
)
from app.worker import celery_app

logger = logging.getLogger(__name__)


async def _run_sync(company_id: int) -> dict:
    """Async proxy function to execute the KSeF sync for a specific company.

    Creates a fresh NullPool engine per invocation so that asyncio.run()'s
    event-loop teardown cannot corrupt a shared connection pool.
    """
    logger.info("Starting async KSeF sync for company_id: %d", company_id)
    engine = create_worker_engine()
    try:
        factory = async_sessionmaker(
            engine, autoflush=False, autocommit=False, expire_on_commit=False
        )
        service = InvoiceSyncService(settings=settings)

        async with factory() as session:
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
                if unclassified:
                    from app.tasks.classification_tasks import classify_company_task

                    classify_company_task.delay(company_id)
                    logger.info("Triggered classify_company_task for company_id=%d", company_id)
            except Exception:
                logger.exception("Failed to retrieve unclassified payload count")

        return result
    finally:
        await engine.dispose()


@celery_app.task(bind=True, max_retries=5, name="sync_company_task")
def sync_company_task(self, company_id: int) -> dict | None:
    """Celery task to run background synchronization for a given company.

    Permanent errors (bad config, missing company, wrong key) are raised
    immediately without retry. Transient errors (network, API timeouts) are
    retried up to max_retries times with minutes-scale exponential backoff.

    Args:
        company_id: The local database ID of the company to sync.

    Returns:
        A dictionary summarising the sync run, or None if retrying.
    """
    try:
        return asyncio.run(_run_sync(company_id))

    except InvoiceSyncPermanentError:
        logger.error(
            "sync_company_task permanently failed for company_id=%d (no retry)",
            company_id,
        )
        raise

    except Exception as exc:
        logger.error(
            "sync_company_task failed for company_id=%d: %s. Retrying...",
            company_id,
            type(exc).__name__,
        )
        # Minutes-scale exponential backoff capped at 1 hour:
        # retries 0-5 → 60s, 120s, 240s, 480s, 960s, 1920s (capped at 3600s)
        countdown = min(2**self.request.retries * 60, 3600)

        try:
            self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                "sync_company_task reached max retries (%d) for company_id=%d",
                self.max_retries,
                company_id,
            )
            raise
    return None
