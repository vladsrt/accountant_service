"""
Deterministic PKWiU → ryczałt rate lookup.

LLM determines the PKWiU code, this module determines the rate.
Zero guessing — if PKWiU maps to one rate, return it.
If ambiguous (multiple rates possible), return all candidates.
"""
from __future__ import annotations

from src.knowledge_base import get_pkwiu_index
from src.config import THRESHOLD_PKWIU_PREFIXES


def lookup_rate(pkwiu_code: str | None, is_wolny_zawod: bool, null_pkwiu_category: str | None = None) -> dict:
    """
    Determine ryczałt rate from PKWiU code.

    Returns dict:
        {
            "rate": float | None,        # determined rate, or None if ambiguous
            "rates_candidates": list[float],  # all possible rates
            "needs_clarification": bool,  # True if can't determine single rate
            "reason": str,               # explanation
        }
    """
    # Wolny zawód always = 17%, regardless of PKWiU
    if is_wolny_zawod:
        return {
            "rate": 17,
            "rates_candidates": [17],
            "needs_clarification": False,
            "is_threshold_dependent": False,
            "reason": "Wolny zawód — stawka 17%",
        }

    # No PKWiU — use null_pkwiu_category to determine rate
    if pkwiu_code is None:
        category_rates = {
            "wlasna_produkcja": 2,       # own farm products
            "dzialalnosc_wytworcza": 5.5, # manufacturing
            "sprzedaz": 3,               # sale of goods/assets
        }
        if null_pkwiu_category and null_pkwiu_category in category_rates:
            rate = category_rates[null_pkwiu_category]
            return {
                "rate": rate,
                "rates_candidates": [rate],
                "needs_clarification": False,
                "is_threshold_dependent": False,
                "reason": f"Brak PKWiU, kategoria: {null_pkwiu_category} — stawka {rate}%",
            }
        return {
            "rate": None,
            "rates_candidates": [2, 3, 5.5],
            "needs_clarification": True,
            "is_threshold_dependent": False,
            "reason": "Brak kodu PKWiU i nie określono kategorii",
        }

    index = get_pkwiu_index()
    normalized = pkwiu_code.replace("ex ", "")

    # Collect matches by type: exact > child (LLM more specific) > parent (KB more specific)
    exact_matches = []
    child_matches = []   # LLM code is more specific than KB
    parent_matches = []  # KB code is more specific than LLM

    for kb_code, rates in index.items():
        kb_norm = kb_code.replace("ex ", "")

        # Exact match — highest priority
        if kb_norm == normalized:
            exact_matches.append((kb_code, rates))
        # LLM code is more specific than KB (child)
        elif normalized.startswith(kb_norm + ".") or (
            normalized.startswith(kb_norm) and len(normalized) > len(kb_norm)
        ):
            child_matches.append((len(kb_norm), kb_code, rates))
        # KB code is more specific than LLM (parent)
        elif kb_norm.startswith(normalized + ".") or (
            kb_norm.startswith(normalized) and len(kb_norm) > len(normalized)
        ):
            parent_matches.append((len(kb_norm), kb_code, rates))

    # Priority: exact match > child match (longest) > parent match (longest)
    if exact_matches:
        # Merge rates from all exact matches (with/without "ex " prefix)
        best_rates = set()
        for _, rates in exact_matches:
            best_rates.update(rates)
        all_rates = set(best_rates)
        for _, _, rates in child_matches:
            all_rates.update(rates)
        for _, _, rates in parent_matches:
            all_rates.update(rates)
    elif child_matches:
        # LLM code is more specific — use the longest (most specific) KB match
        child_matches.sort(key=lambda x: x[0], reverse=True)
        best_rates = set(child_matches[0][2])
        all_rates = set()
        for _, _, rates in child_matches:
            all_rates.update(rates)
        for _, _, rates in parent_matches:
            all_rates.update(rates)
    elif parent_matches:
        # KB codes are more specific — collect all parent rates
        all_rates = set()
        for _, _, rates in parent_matches:
            all_rates.update(rates)
        best_rates = all_rates
    else:
        return {
            "rate": None,
            "rates_candidates": [],
            "needs_clarification": True,
            "is_threshold_dependent": False,
            "reason": f"PKWiU {pkwiu_code} nie znaleziono w bazie wiedzy",
        }

    if len(best_rates) == 1:
        rate = list(best_rates)[0]
        threshold = _is_threshold_dependent(pkwiu_code, rate)
        return {
            "rate": rate,
            "rates_candidates": sorted(all_rates),
            "needs_clarification": False,
            "is_threshold_dependent": threshold,
            "reason": f"PKWiU {pkwiu_code} → stawka {rate}%",
        }

    # Multiple rates — ambiguous
    return {
        "rate": None,
        "rates_candidates": sorted(all_rates),
        "needs_clarification": True,
        "is_threshold_dependent": False,
        "reason": (
            f"PKWiU {pkwiu_code} ma kilka możliwych stawek: "
            f"{sorted(best_rates)}. Potrzebne uściślenie."
        ),
    }


def _is_threshold_dependent(pkwiu_code: str | None, rate: float) -> bool:
    """
    Check if PKWiU is subject to Art. 12 ust. 1 pkt 4 revenue threshold.
    These codes have base rate 8.5%, but 12.5% when annual revenue > 100k PLN.
    The actual split calculation is done by Math Engine, not the classifier.
    """
    if pkwiu_code is None or rate != 8.5:
        return False
    pkwiu_norm = pkwiu_code.replace("ex ", "")
    return any(
        pkwiu_norm.startswith(prefix) or pkwiu_norm == prefix
        for prefix in THRESHOLD_PKWIU_PREFIXES
    )
