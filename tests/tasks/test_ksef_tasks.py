"""Unit tests for the Celery tasks executing KSeF actions."""

from unittest.mock import AsyncMock, patch

from app.services.invoice_sync import InvoiceSyncError, InvoiceSyncPermanentError
from app.tasks.ksef_tasks import sync_company_task


def test_sync_company_task_success() -> None:
    """The task should call _run_sync and return the dictionary."""
    expected_response = {"company_id": 1, "seller_invoices": 10, "buyer_invoices": 0}

    # We mock the _run_sync inner coroutine inside the task
    with patch("app.tasks.ksef_tasks._run_sync", new_callable=AsyncMock) as mock_run_sync:
        mock_run_sync.return_value = expected_response

        result = sync_company_task(1)

        assert result == expected_response
        mock_run_sync.assert_called_once_with(1)


def test_sync_company_task_retry_on_failure() -> None:
    """The task should catch exceptions and retry with exponential backoff."""

    with patch("app.tasks.ksef_tasks._run_sync", new_callable=AsyncMock) as mock_run_sync:
        mock_error = InvoiceSyncError("KSeF SDK failed")
        mock_run_sync.side_effect = mock_error

        # We patch the retry method on the Celery Task class
        with patch("celery.app.task.Task.retry") as mock_retry:
            mock_retry.side_effect = Exception("Retry Halt")

            sync_company_task.push_request(retries=2)
            try:
                try:
                    sync_company_task(1)
                except Exception as e:
                    assert str(e) == "Retry Halt"

                # Verify self.retry was called
                mock_retry.assert_called_once()
                # Ensure countdown matches minutes-scale backoff: min(2**retries * 60, 3600)
                args, kwargs = mock_retry.call_args
                assert kwargs["exc"] == mock_error
                assert kwargs["countdown"] == 240  # min(2**2 * 60, 3600)
            finally:
                sync_company_task.pop_request()


def test_sync_company_task_max_retries() -> None:
    """The task should surface the MaxRetriesExceededError if retries run out."""

    with patch("app.tasks.ksef_tasks._run_sync", new_callable=AsyncMock) as mock_run_sync:
        mock_error = InvoiceSyncError("KSeF SDK failed")
        mock_run_sync.side_effect = mock_error

        with patch("celery.app.task.Task.retry") as mock_retry:
            mock_retry.side_effect = sync_company_task.MaxRetriesExceededError(
                "Max Retries Reached"
            )

            sync_company_task.push_request(retries=5)
            try:
                # We expect the error to bubble up
                try:
                    sync_company_task(1)
                    assert False, "Should have raised exception"
                except sync_company_task.MaxRetriesExceededError as e:
                    assert str(e) == "Max Retries Reached"
            finally:
                sync_company_task.pop_request()


def test_sync_company_task_permanent_error_no_retry() -> None:
    """InvoiceSyncPermanentError must propagate immediately without calling self.retry."""

    with patch("app.tasks.ksef_tasks._run_sync", new_callable=AsyncMock) as mock_run_sync:
        mock_run_sync.side_effect = InvoiceSyncPermanentError("Company not found")

        with patch("celery.app.task.Task.retry") as mock_retry:
            sync_company_task.push_request(retries=0)
            try:
                try:
                    sync_company_task(1)
                    assert False, "Should have raised InvoiceSyncPermanentError"
                except InvoiceSyncPermanentError:
                    pass

                mock_retry.assert_not_called()
            finally:
                sync_company_task.pop_request()
