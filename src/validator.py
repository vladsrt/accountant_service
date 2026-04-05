from __future__ import annotations

from src.knowledge_base import get_pkwiu_index


_VALID_NULL_CATEGORIES = {"wlasna_produkcja", "dzialalnosc_wytworcza", "sprzedaz"}


def validate_pkwiu(
    pkwiu_code: str | None,
    is_wolny_zawod: bool,
    reasoning: str,
    null_pkwiu_category: str | None = None,
) -> tuple[bool, str | None]:
    """
    Validate PKWiU code exists in knowledge base.
    Returns (is_valid, rejection_reason).
    """
    # Wolny zawód with null PKWiU is always valid
    if is_wolny_zawod and pkwiu_code is None:
        return True, None

    # Null PKWiU — valid if category is specified
    if not is_wolny_zawod and pkwiu_code is None:
        if null_pkwiu_category in _VALID_NULL_CATEGORIES:
            return True, None
        return False, "No PKWiU code and no valid null_pkwiu_category."

    # Check PKWiU exists in KB
    if pkwiu_code is not None:
        index = get_pkwiu_index()
        normalized = pkwiu_code.replace("ex ", "")
        for kb_code in index:
            kb_norm = kb_code.replace("ex ", "")
            if (kb_norm == normalized
                    or normalized.startswith(kb_norm)
                    or kb_norm.startswith(normalized)):
                return True, None
        return False, f"PKWiU {pkwiu_code} not found in knowledge base"

    return True, None
