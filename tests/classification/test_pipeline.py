"""Regression tests for the AI classification pipeline.

Covers:
1. Deterministic auditor (src.auditor) — gastronomia + clean pass
2. Full classify() pipeline with mocked LLM calls
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.auditor import audit
from src.models import ClassificationResult, Verdict

# ---------------------------------------------------------------------------
# Test 1: Auditor — gastronomia without alcohol info → REJECTED
# ---------------------------------------------------------------------------


def test_auditor_gastro_no_alcohol():
    """When PKWiU 56.10 is gastro and P_7 doesn't mention alcohol,
    the auditor must flag 'alcohol_threshold_unknown' and reject.
    """
    result = audit(
        p7_text="Usługa cateringowa — obiad dla 30 osób",
        pkwiu_code="56.10.11.0",
        is_wolny_zawod=False,
        marker_found=None,
    )

    assert result["approved"] is False
    assert "alcohol_threshold_unknown" in result["ambiguity_flags"]
    assert result["clarification_question"] is not None
    assert result["confidence"] < 0.90


# ---------------------------------------------------------------------------
# Test 2: Auditor — clean IT services → APPROVED
# ---------------------------------------------------------------------------


def test_auditor_clean_pass():
    """A clean IT-services P_7 (no ambiguities) should be approved
    with high confidence and no flags.
    """
    result = audit(
        p7_text="Tworzenie oprogramowania na zamówienie",
        pkwiu_code="62.01.11.0",
        is_wolny_zawod=False,
        marker_found=None,
    )

    assert result["approved"] is True
    assert result["ambiguity_flags"] == []
    assert result["confidence"] >= 0.90


# ---------------------------------------------------------------------------
# Test 3: Full classify() with mocked LLM → ACCEPTED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_accepted_with_mocked_llm():
    """Mock all three LLM calls and verify the pipeline returns
    a valid ACCEPTED ClassificationResult with correct rate and PKWiU.
    """
    # Step 1: Sanitizer response
    s1_data = {
        "sanitized_p7": "Tworzenie oprogramowania na zamówienie",
        "is_classifiable": True,
        "rejection_reason": None,
        "clarification_question": None,
    }
    s1_meta = {"model": "gpt-4o-mini", "tokens": 100, "latency_ms": 200}

    # Step 2: Classifier response — PKWiU 62.01.11.0 → 12% rate
    s2_data = {
        "pkwiu_code": "62.01.11.0",
        "null_pkwiu_category": None,
        "pkwiu_description": "Usługi związane z projektowaniem, programowaniem i rozwojem oprogramowania",
        "reasoning": "P_7 describes custom software development → PKWiU 62.01.11.0",
    }
    s2_meta = {"model": "gpt-4o-mini", "tokens": 150, "latency_ms": 300}

    # Step 3: Wolny zawód — not wolny zawód
    s3_data = {
        "is_wolny_zawod": False,
        "marker_found": None,
        "reasoning": "No wolny zawód marker found in P_7",
    }
    s3_meta = {"model": "gpt-4o-mini", "tokens": 80, "latency_ms": 150}

    # Sequence of mock returns for the 3 LLM calls
    mock_returns = [
        (s1_data, s1_meta),
        (s2_data, s2_meta),
        (s3_data, s3_meta),
    ]

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.put = AsyncMock()

    with (
        patch("src.pipeline.call_llm", new_callable=AsyncMock, side_effect=mock_returns),
        patch("src.pipeline._cache", mock_cache),
    ):
        from src.pipeline import classify

        result = await classify("Tworzenie oprogramowania na zamówienie", use_cache=True)

    assert isinstance(result, ClassificationResult)
    assert result.verdict == Verdict.ACCEPTED
    assert result.rate_percent == 12
    assert result.pkwiu_code == "62.01.11.0"
    assert result.confidence >= 0.90
    assert result.corridor == "GREEN"
    assert result.llm_calls_count == 4  # 3 LLM steps + 1 deterministic auditor step
    assert result.total_tokens == 330  # 100 + 150 + 80

    # Verify cache was called
    mock_cache.get.assert_awaited_once()
    mock_cache.put.assert_awaited_once()
