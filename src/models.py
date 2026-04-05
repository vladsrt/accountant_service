from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(Enum):
    ACCEPTED = "ACCEPTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


@dataclass
class LLMResult:
    """Raw structured output from Front Desk."""
    sanitized_p7: str
    is_classifiable: bool
    rejection_reason: str | None
    is_wolny_zawod: bool
    pkwiu_code: str | None
    pkwiu_description: str | None
    confidence: float
    reasoning: str
    ambiguity_flags: list[str] = field(default_factory=list)
    clarification_question: str | None = None


@dataclass
class ClassificationResult:
    """Final result after full pipeline (LLM + validation)."""
    verdict: Verdict
    rate_percent: float | None
    pkwiu_code: str | None
    pkwiu_description: str | None
    confidence: float
    reasoning: str
    ambiguity_flags: list[str]
    rejection_reason: str | None
    # Pipeline metadata
    corridor: str  # "GREEN" or "CLARIFICATION"
    clarification_question: str | None = None
    is_threshold_dependent: bool = False  # True if PKWiU subject to 100k revenue threshold (8.5%/12.5%)
    total_tokens: int = 0
    total_latency_ms: int = 0
    llm_calls_count: int = 0
    steps: list[dict] = field(default_factory=list)


@dataclass
class TestCaseResult:
    """Result of running one test case."""
    test_id: int
    p7_value: str
    difficulty: str
    expected_rate: float | None
    expected_pkwiu: str | None
    result: ClassificationResult
    rate_correct: bool = False
    pkwiu_correct: bool = False
    false_positive: bool = False
    false_negative: bool = False
    wrong_rate: bool = False
