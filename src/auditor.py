"""
Deterministic auditor — replaces LLM Step 4.

Checks for known ambiguity patterns using code rules, not LLM.
Returns audit result with flags and optional clarification question.
"""
from __future__ import annotations

import re


# Healthcare PKWiU codes where wolny zawód status matters for rate
_HEALTHCARE_PKWIU = ("86",)

# Professions that could be wolny zawód — need marker to confirm
_WOLNY_ZAWOD_SUSPICIOUS = [
    (r"reprezentacj\w*\s+prawn", "Czy usługodawca jest adwokatem lub radcą prawnym?"),
    (r"obsług\w*\s+prawn", "Czy usługodawca jest adwokatem lub radcą prawnym?"),
    (r"nadzór\s+(budowlan|inwestorsk)", "Czy usługodawca posiada uprawnienia budowlane?"),
    (r"psychoterapi", "Czy usługodawca jest psychologiem (mgr psychologii)?"),
    (r"terapi\w*\s+psycholog", "Czy usługodawca jest psychologiem (mgr psychologii)?"),
    (r"fizjoterapi", "Czy usługodawca posiada tytuł zawodowy (fizjoterapeuta)?"),
    (r"konsultacj\w*\s+lekars", "Czy usługodawca jest lekarzem (dr med., lek.)?"),
    (r"us[łl]ug\w*\s+(medyczn|zdrowotn)", "Czy usługodawca jest lekarzem lub posiada tytuł zawodowy?"),
    (r"stomatolog", "Czy usługodawca jest lekarzem dentystą?"),
    (r"badani\w*\s+laborator", "Jakiego rodzaju badania — medyczne czy naukowe (R&D)?"),
]

# Gastronomia keywords — catches catering, bar, kantyna etc
_GASTRO_KEYWORDS = [
    r"catering", r"gastronom", r"kantyn", r"kelners",
    r"\bbar\b", r"food\s*truck",
]


def audit(
    p7_text: str,
    pkwiu_code: str | None,
    is_wolny_zawod: bool,
    marker_found: str | None,
) -> dict:
    """
    Deterministic ambiguity check.
    """
    flags = []
    question = None
    reasoning_parts = []
    p7_lower = p7_text.lower()
    pkwiu_norm = (pkwiu_code or "").replace("ex ", "")

    # === 1. Gastronomia (PKWiU 56) — check alcohol info in P_7 ===
    is_gastro = pkwiu_norm.startswith("56") or any(
        re.search(p, p7_lower) for p in _GASTRO_KEYWORDS
    )
    if is_gastro:
        has_no_alcohol = bool(re.search(r"bez alkohol", p7_lower))
        has_alcohol = bool(re.search(r"alkohol", p7_lower)) and not has_no_alcohol
        if not has_no_alcohol and not has_alcohol:
            # No alcohol info → can't determine rate
            flags.append("alcohol_threshold_unknown")
            question = (
                "Czy w ramach usługi gastronomicznej podawane są napoje "
                "o zawartości alkoholu powyżej 1,5%?"
            )
            reasoning_parts.append("Gastronomia — brak info o alkoholu")

    # === 2. Najem without period — najem vs zakwaterowanie ===
    # Only for residential (68.20.1). Commercial (68.20.2) is always long-term, no ambiguity.
    is_commercial = bool(re.search(
        r"magazyn|hal[aei]|biur|lokal\s*u[żz]ytkow|komercyjn|przemysłow|handlow",
        p7_lower,
    ))
    if pkwiu_norm.startswith("68.20") and not is_commercial:
        # Explicit period TYPE patterns (long-term vs short-term)
        explicit_type_patterns = [
            r"miesi",          # miesięczny/miesiąc
            r"rok\b|roczn",    # roczny
            r"\d+\s*dob",      # N dób
            r"na doby|na dobę",
            r"airbnb|booking",
        ]
        # Weak period patterns (month name, year) — not enough for "pokój/pokoju"
        weak_period_patterns = [
            r"stycz|luty|marz|kwiet|maj|czerw|lip|sierp|wrzesi|paźdz|listop|grudz",
            r"\d{4}",          # year like 2026
        ]
        has_explicit_type = any(re.search(p, p7_lower) for p in explicit_type_patterns)
        has_weak_period = any(re.search(p, p7_lower) for p in weak_period_patterns)
        is_room_rental = bool(re.search(r"pokoj|pokój", p7_lower))

        # "najem pokoju — luty 2026" → month alone doesn't clarify if it's nightly or monthly
        # "najem lokalu mieszkalnego — luty 2026" → month + lokal = long-term, OK
        has_period = has_explicit_type or (has_weak_period and not is_room_rental)
        if not has_period:
            flags.append("najem_vs_zakwaterowanie")
            question = (
                "Czy to jest wynajem długoterminowy (najem miesięczny) "
                "czy krótkoterminowe zakwaterowanie (na doby)?"
            )
            reasoning_parts.append("Najem bez okresu")

    # === 3. Wolny zawód suspicion — professions without marker ===
    if not is_wolny_zawod and not marker_found:
        for pattern, q in _WOLNY_ZAWOD_SUSPICIOUS:
            if re.search(pattern, p7_lower):
                flags.append("wolny_zawod_vs_regular")
                question = q
                reasoning_parts.append(f"Podejrzenie wolnego zawodu bez markera")
                break

    # === 4. Ambiguous null-PKWiU categories ===
    if pkwiu_code is None and not flags:
        ambiguous_null_patterns = [
            (r"prototyp", "rd_vs_manufacturing",
             "Czy to jest prototypowanie (R&D) czy produkcja seryjna?"),
            (r"druk\s*3d", "rd_vs_manufacturing",
             "Czy druk 3D dotyczy prototypowania (R&D) czy produkcji?"),
        ]
        for pattern, flag, q in ambiguous_null_patterns:
            if re.search(pattern, p7_lower):
                flags.append(flag)
                question = q
                reasoning_parts.append("Dwuznaczna kategoria bez PKWiU")
                break

    # === Build result ===
    if not flags:
        return {
            "approved": True,
            "confidence": 0.92,
            "ambiguity_flags": [],
            "clarification_question": None,
            "reasoning": "Brak dwuznaczności",
        }

    return {
        "approved": False,
        "confidence": 0.70,
        "ambiguity_flags": flags,
        "clarification_question": question,
        "reasoning": "; ".join(reasoning_parts),
    }
