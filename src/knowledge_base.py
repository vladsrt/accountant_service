from __future__ import annotations

import json
from pathlib import Path

from src.config import KB_PATH


def load_knowledge_base(path: Path = KB_PATH) -> dict:
    """Load raw knowledge base from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_pkwiu_index(kb: dict) -> dict[str, list[float]]:
    """
    Build index: PKWiU code -> list of valid rates.
    Handles 'ex ' prefix by indexing both with and without it.
    """
    index: dict[str, list[float]] = {}
    for rate_obj in kb["rates"]:
        rate = rate_obj["rate_percent"]
        for entry in rate_obj["entries"]:
            code = entry["pkwiu"]
            if code is None:
                continue
            if code not in index:
                index[code] = []
            if rate not in index[code]:
                index[code].append(rate)
            # Also index without 'ex ' prefix
            normalized = code.replace("ex ", "")
            if normalized != code:
                if normalized not in index:
                    index[normalized] = []
                if rate not in index[normalized]:
                    index[normalized].append(rate)
    return index


def build_rate_entries(kb: dict) -> dict[float, list[dict]]:
    """Build index: rate -> list of entries (for validation)."""
    result = {}
    for rate_obj in kb["rates"]:
        rate = rate_obj["rate_percent"]
        result[rate] = rate_obj["entries"]
    return result


def generate_compact_kb_text(kb: dict) -> str:
    """
    Generate compacted knowledge base for system prompt.
    Groups entries by rate, ~2300 tokens.
    """
    lines = ["=== BAZA STAWEK RYCZAŁTU (PKWiU 2015) ===\n"]
    for rate_obj in kb["rates"]:
        rate = rate_obj["rate_percent"]
        desc = rate_obj["rate_description"]
        basis = rate_obj["legal_basis"]
        lines.append(f"## {rate}% — {desc} ({basis})")
        for entry in rate_obj["entries"]:
            code = entry["pkwiu"] or "-"
            lines.append(f"  {code}: {entry['description']}")
        lines.append("")
    return "\n".join(lines)


# Module-level singletons
_kb = None
_pkwiu_index = None
_rate_entries = None
_compact_text = None


def get_kb() -> dict:
    global _kb
    if _kb is None:
        _kb = load_knowledge_base()
    return _kb


def get_pkwiu_index() -> dict[str, list[float]]:
    global _pkwiu_index
    if _pkwiu_index is None:
        _pkwiu_index = build_pkwiu_index(get_kb())
    return _pkwiu_index


def get_rate_entries() -> dict[float, list[dict]]:
    global _rate_entries
    if _rate_entries is None:
        _rate_entries = build_rate_entries(get_kb())
    return _rate_entries


def get_compact_kb_text() -> str:
    global _compact_text
    if _compact_text is None:
        _compact_text = generate_compact_kb_text(get_kb())
    return _compact_text
