"""Background tasks for AI invoice classification."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.database import create_worker_engine
from app.worker import celery_app

logger = logging.getLogger(__name__)


async def _run_classify(company_id: int) -> dict:
    """Async proxy to run classification for a company.

    Creates a fresh NullPool engine per invocation (same pattern as ksef_tasks).
    """
    from app.services.classification_service import ClassificationService

    logger.info("Starting AI classification for company_id: %d", company_id)
    engine = create_worker_engine()
    try:
        factory = async_sessionmaker(
            engine, autoflush=False, autocommit=False, expire_on_commit=False
        )
        async with factory() as session:
            result = await ClassificationService.classify_company_invoices(
                company_id=company_id, db=session
            )
        return result
    finally:
        await engine.dispose()


@celery_app.task(bind=True, max_retries=3, name="classify_company_task")
def classify_company_task(self, company_id: int) -> dict | None:
    """Celery task to classify all unclassified invoices for a company.

    Transient errors (OpenAI timeouts, rate limits) are retried with
    exponential backoff. Max 3 retries: 60s, 120s, 240s.
    """
    try:
        return asyncio.run(_run_classify(company_id))

    except Exception as exc:
        logger.error(
            "classify_company_task failed for company_id=%d: %s. Retrying...",
            company_id,
            type(exc).__name__,
        )
        countdown = min(2**self.request.retries * 60, 1800)

        try:
            self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(
                "classify_company_task reached max retries (%d) for company_id=%d",
                self.max_retries,
                company_id,
            )
            raise
    return None
