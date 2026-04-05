from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from src.config import CACHE_DB_PATH, CACHE_TTL_DAYS
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


class ClassificationCache:
    def __init__(self, db_path: Path = CACHE_DB_PATH):
        self._memory: dict[str, ClassificationResult] = {}
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS classification_cache (
                cache_key     TEXT PRIMARY KEY,
                p7_original   TEXT NOT NULL,
                rate_percent  REAL,
                pkwiu_code    TEXT,
                pkwiu_desc    TEXT,
                confidence    REAL NOT NULL,
                reasoning     TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get(self, p7_text: str) -> ClassificationResult | None:
        key = normalize_for_cache(p7_text)

        # Tier 1: in-memory
        if key in self._memory:
            return self._memory[key]

        # Tier 2: SQLite
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            row = conn.execute(
                "SELECT rate_percent, pkwiu_code, pkwiu_desc, confidence, reasoning, created_at "
                "FROM classification_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            conn.close()

        if row is None:
            return None

        rate, pkwiu, pkwiu_desc, conf, reasoning, created_at = row

        # Check TTL
        created = datetime.fromisoformat(created_at)
        if datetime.now() - created > timedelta(days=CACHE_TTL_DAYS):
            self._evict(key)
            return None

        result = ClassificationResult(
            verdict=Verdict.ACCEPTED,
            rate_percent=rate,
            pkwiu_code=pkwiu,
            pkwiu_description=pkwiu_desc,
            confidence=conf,
            reasoning=reasoning,
            ambiguity_flags=[],
            rejection_reason=None,
            corridor="CACHE",
            is_threshold_dependent=_is_threshold_dependent(pkwiu, rate) if rate else False,
        )
        # Promote to memory
        self._memory[key] = result
        return result

    def put(self, p7_text: str, result: ClassificationResult):
        """Cache only ACCEPTED results."""
        if result.verdict != Verdict.ACCEPTED:
            return

        key = normalize_for_cache(p7_text)
        self._memory[key] = result

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT OR REPLACE INTO classification_cache "
                "(cache_key, p7_original, rate_percent, pkwiu_code, pkwiu_desc, "
                "confidence, reasoning, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    key,
                    p7_text,
                    result.rate_percent,
                    result.pkwiu_code,
                    result.pkwiu_description,
                    result.confidence,
                    result.reasoning,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()

    def _evict(self, key: str):
        self._memory.pop(key, None)
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM classification_cache WHERE cache_key = ?", (key,))
            conn.commit()
            conn.close()

    def clear(self):
        self._memory.clear()
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM classification_cache")
            conn.commit()
            conn.close()
