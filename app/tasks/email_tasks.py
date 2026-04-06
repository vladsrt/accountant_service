import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="send_verification_email_task", max_retries=3)
def send_verification_email_task(email: str, token: str) -> None:
    """Simulate sending an email asynchronously with Celery."""
    verification_link = f"http://localhost:8000/api/v1/auth/verify-email?token={token}"
    logger.info("--- EMAIL SIMULATION ---")
    logger.info("To: %s", email)
    logger.info("Subject: Verify your email address")
    logger.info("Verification email dispatched (link redacted from logs)")
    logger.info("------------------------")
