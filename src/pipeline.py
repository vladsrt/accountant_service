"""
Multi-step classification pipeline (Round 8.5).

Step 1: Sanitizer + Classifiability check (LLM)
Step 2: PKWiU Classifier (LLM)
Step 3: Wolny Zawód Detector (LLM)
Step 4: Ambiguity Auditor (DETERMINISTIC CODE — no LLM)
Then: deterministic rate_lookup + revenue threshold → ACCEPTED / NEEDS_CLARIFICATION
"""

from __future__ import annotations

from app.core.config import settings
from src.auditor import audit as code_audit
from src.cache import ClassificationCache
from src.llm_client import call_llm
from src.models import ClassificationResult, Verdict
from src.prompts.step1_sanitizer import SYSTEM_PROMPT as STEP1_PROMPT
from src.prompts.step2_classifier import build_classifier_prompt
from src.prompts.step3_wolny_zawod import SYSTEM_PROMPT as STEP3_PROMPT
from src.rate_lookup import lookup_rate
from src.schemas.step_schemas import (
    STEP1_SANITIZER_SCHEMA,
    STEP2_CLASSIFIER_SCHEMA,
    STEP3_WOLNY_ZAWOD_SCHEMA,
)
from src.validator import validate_pkwiu

_cache = ClassificationCache()
_classifier_prompt = None


def _get_classifier_prompt() -> str:
    global _classifier_prompt
    if _classifier_prompt is None:
        _classifier_prompt = build_classifier_prompt()
    return _classifier_prompt


def _build_clarification(
    reason: str,
    question: str | None,
    steps: list[dict],
    confidence: float = 0.0,
    reasoning: str = "",
    ambiguity_flags: list[str] | None = None,
    pkwiu_code: str | None = None,
) -> ClassificationResult:
    """Build NEEDS_CLARIFICATION result."""
    if not question:
        question = "Opis na fakturze jest niejednoznaczny. Jaki konkretny rodzaj usługi lub produktu obejmuje ta faktura?"

    return ClassificationResult(
        verdict=Verdict.NEEDS_CLARIFICATION,
        rate_percent=None,
        pkwiu_code=pkwiu_code,
        pkwiu_description=None,
        confidence=confidence,
        reasoning=reasoning,
        ambiguity_flags=ambiguity_flags or [],
        rejection_reason=reason,
        corridor="CLARIFICATION",
        clarification_question=question,
        total_tokens=sum(s.get("tokens", 0) for s in steps),
        total_latency_ms=sum(s.get("latency_ms", 0) for s in steps),
        llm_calls_count=len(steps),
        steps=steps,
    )


async def classify(
    p7_text: str,
    use_cache: bool = True,
) -> ClassificationResult:
    """
    Stateless classification pipeline.
    Returns base rate + is_threshold_dependent flag.
    Revenue threshold split is Math Engine's responsibility.
    """
    steps = []

    # Cache lookup
    if use_cache:
        cached = await _cache.get(p7_text)
        if cached is not None:
            cached.corridor = "CACHE"
            return cached

    # === Step 1: Sanitizer + Classifiability ===
    s1_data, s1_meta = await call_llm(
        STEP1_PROMPT,
        f"P_7: {p7_text}",
        STEP1_SANITIZER_SCHEMA,
    )
    steps.append({"step": "sanitizer", **s1_meta})

    sanitized = s1_data["sanitized_p7"]

    if not s1_data["is_classifiable"]:
        return _build_clarification(
            reason=s1_data.get("rejection_reason") or "P_7 too vague",
            question=s1_data.get("clarification_question"),
            steps=steps,
        )

    # === Step 2: PKWiU Classifier ===
    s2_data, s2_meta = await call_llm(
        _get_classifier_prompt(),
        f"P_7: {sanitized}",
        STEP2_CLASSIFIER_SCHEMA,
    )
    steps.append({"step": "classifier", **s2_meta})

    pkwiu_code = s2_data["pkwiu_code"]
    if pkwiu_code == "null":
        pkwiu_code = None
    null_pkwiu_category = s2_data.get("null_pkwiu_category")
    if null_pkwiu_category == "null":
        null_pkwiu_category = None
    pkwiu_description = s2_data.get("pkwiu_description")
    classifier_reasoning = s2_data.get("reasoning", "")

    # === Step 3: Wolny Zawód Detector ===
    s3_data, s3_meta = await call_llm(
        STEP3_PROMPT,
        f"P_7: {sanitized}",
        STEP3_WOLNY_ZAWOD_SCHEMA,
    )
    steps.append({"step": "wolny_zawod", **s3_meta})

    is_wolny_zawod = s3_data["is_wolny_zawod"]

    # === Step 4: Deterministic Auditor (code, no LLM) ===
    s4_data = code_audit(
        p7_text=sanitized,
        pkwiu_code=pkwiu_code,
        is_wolny_zawod=is_wolny_zawod,
        marker_found=s3_data.get("marker_found"),
    )
    steps.append({"step": "auditor", "tokens": 0, "latency_ms": 0})

    ambiguity_flags = s4_data.get("ambiguity_flags", [])
    confidence = s4_data.get("confidence", 0.92)
    auditor_reasoning = s4_data.get("reasoning", "")
    combined_reasoning = f"{classifier_reasoning} | Auditor: {auditor_reasoning}"

    # Check fatal ambiguities
    if settings.FATAL_AMBIGUITIES.intersection(set(ambiguity_flags)):
        return _build_clarification(
            reason="Fatal ambiguity: " + ", ".join(ambiguity_flags),
            question=s4_data.get("clarification_question"),
            steps=steps,
            confidence=confidence,
            reasoning=combined_reasoning,
            ambiguity_flags=ambiguity_flags,
            pkwiu_code=pkwiu_code,
        )

    # Auditor rejected
    if not s4_data["approved"]:
        return _build_clarification(
            reason="Auditor: " + auditor_reasoning,
            question=s4_data.get("clarification_question"),
            steps=steps,
            confidence=confidence,
            reasoning=combined_reasoning,
            ambiguity_flags=ambiguity_flags,
            pkwiu_code=pkwiu_code,
        )

    # === Validation: PKWiU exists in KB ===
    is_valid, validation_error = validate_pkwiu(
        pkwiu_code, is_wolny_zawod, classifier_reasoning, null_pkwiu_category
    )
    if not is_valid:
        return _build_clarification(
            reason=f"Validation: {validation_error}",
            question=None,
            steps=steps,
            confidence=confidence,
            reasoning=combined_reasoning,
            ambiguity_flags=ambiguity_flags,
        )

    # === Deterministic rate lookup ===
    rate_info = lookup_rate(pkwiu_code, is_wolny_zawod, null_pkwiu_category)

    if rate_info["needs_clarification"]:
        return _build_clarification(
            reason=f"Rate lookup: {rate_info['reason']}",
            question=None,
            steps=steps,
            confidence=confidence,
            reasoning=combined_reasoning,
            ambiguity_flags=ambiguity_flags,
            pkwiu_code=pkwiu_code,
        )

    rate = rate_info["rate"]

    # === ACCEPTED ===
    result = ClassificationResult(
        verdict=Verdict.ACCEPTED,
        rate_percent=rate,
        pkwiu_code=pkwiu_code,
        pkwiu_description=pkwiu_description,
        confidence=confidence,
        reasoning=combined_reasoning,
        ambiguity_flags=ambiguity_flags,
        rejection_reason=None,
        corridor="GREEN",
        clarification_question=None,
        is_threshold_dependent=rate_info.get("is_threshold_dependent", False),
        total_tokens=sum(s.get("tokens", 0) for s in steps),
        total_latency_ms=sum(s.get("latency_ms", 0) for s in steps),
        llm_calls_count=len(steps),
        steps=steps,
    )

    if use_cache:
        await _cache.put(p7_text, result)

    return result


async def clear_cache():
    """Clear classification cache."""
    await _cache.clear()
