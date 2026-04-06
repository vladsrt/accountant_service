from __future__ import annotations

import hashlib
import json
import re
import unicodedata

import redis.asyncio as aioredis

from app.core.config import settings
from src.models import ClassificationResult, Verdict
from src.rate_lookup import _is_threshold_dependent


def normalize_for_cache(p7_text: str) -> str:
    """
    Normalize P_7 text to create a stable cache key.
    Removes dates, contract numbers, quantities so that
    the same service with different metadata hits cache.
    """
    text = p7_text.strip().lower()

    # Remove dates
    text = re.sub(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", "", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}", "", text)
    text = re.sub(
        r"(styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|"
        r"wrzesień|październik|listopad|grudzień)\s*\d{0,4}",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove contract/invoice references
    text = re.sub(
        r"(nr|numer|umowa|faktura|kontrakt|contract)\s*[:.#]?\s*[\w/-]+",
        "",
        text,
    )

    # Remove quantities
    text = re.sub(r"\d+\s*(szt|kg|m2|m3|godz|h|dni|osób|słoików)", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove diacritics for key stability
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))

    return hashlib.sha256(ascii_text.encode()).hexdigest()


def _serialize_result(result: ClassificationResult) -> str:
    """Serialize a ClassificationResult to JSON for Redis storage."""
    return json.dumps({
        "rate_percent": result.rate_percent,
        "pkwiu_code": result.pkwiu_code,
        "pkwiu_description": result.pkwiu_description,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "is_threshold_dependent": result.is_threshold_dependent,
    })


def _deserialize_result(data: str) -> ClassificationResult:
    """Deserialize a ClassificationResult from JSON stored in Redis."""
    d = json.loads(data)
    return ClassificationResult(
        verdict=Verdict.ACCEPTED,
        rate_percent=d["rate_percent"],
        pkwiu_code=d["pkwiu_code"],
        pkwiu_description=d["pkwiu_description"],
        confidence=d["confidence"],
        reasoning=d["reasoning"],
        ambiguity_flags=[],
        rejection_reason=None,
        corridor="CACHE",
        is_threshold_dependent=d.get("is_threshold_dependent", False),
    )


class ClassificationCache:
    """Async Redis-backed classification cache.

    Replaces the former SQLite + threading.Lock implementation to avoid
    'database is locked' errors in Celery workers.
    """

    _PREFIX = "clf:"

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.REDIS_URL
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._ttl_seconds = settings.CACHE_TTL_DAYS * 86400

    async def get(self, p7_text: str) -> ClassificationResult | None:
        key = self._PREFIX + normalize_for_cache(p7_text)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return _deserialize_result(raw)

    async def put(self, p7_text: str, result: ClassificationResult) -> None:
        """Cache only ACCEPTED results."""
        if result.verdict != Verdict.ACCEPTED:
            return
        key = self._PREFIX + normalize_for_cache(p7_text)
        await self._redis.set(key, _serialize_result(result), ex=self._ttl_seconds)

    async def clear(self) -> None:
        """Remove all classification cache keys."""
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{self._PREFIX}*", count=500)
            if keys:
                await self._redis.delete(*keys)
            if cursor == 0:
                break
