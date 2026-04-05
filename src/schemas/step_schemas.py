"""JSON Schema definitions for each pipeline step (OpenAI strict mode)."""

STEP1_SANITIZER_SCHEMA = {
    "name": "sanitizer_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "sanitized_p7": {
                "type": "string",
                "description": "P_7 with PII replaced by [REDACTED]. Keep service description intact.",
            },
            "is_classifiable": {
                "type": "boolean",
                "description": "false if P_7 is too vague to determine service type.",
            },
            "rejection_reason": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Why not classifiable. null if classifiable.",
            },
            "clarification_question": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Question in Polish if not classifiable. null if classifiable.",
            },
        },
        "required": [
            "sanitized_p7",
            "is_classifiable",
            "rejection_reason",
            "clarification_question",
        ],
        "additionalProperties": False,
    },
}

STEP2_CLASSIFIER_SCHEMA = {
    "name": "classifier_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "pkwiu_code": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": (
                    "Most specific PKWiU 2015 code. "
                    "null ONLY for: manufacturing (działalność wytwórcza), "
                    "own production (własna uprawa/hodowla), or asset sale (zbycie środka trwałego)."
                ),
            },
            "null_pkwiu_category": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": (
                    "REQUIRED when pkwiu_code is null. Category of null-PKWiU activity: "
                    "'wlasna_produkcja' (own farm: honey, eggs, vegetables = 2%), "
                    "'dzialalnosc_wytworcza' (manufacturing: furniture, clothes, pallets = 5.5%), "
                    "'sprzedaz' (sale of goods/assets: used laptop, flowers, equipment = 3%). "
                    "null if pkwiu_code is not null."
                ),
            },
            "pkwiu_description": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Polish description of the PKWiU category. null if pkwiu_code is null.",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation: what service/product, which PKWiU, why.",
            },
        },
        "required": ["pkwiu_code", "null_pkwiu_category", "pkwiu_description", "reasoning"],
        "additionalProperties": False,
    },
}

STEP3_WOLNY_ZAWOD_SCHEMA = {
    "name": "wolny_zawod_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "is_wolny_zawod": {
                "type": "boolean",
                "description": "true ONLY if explicit marker from the closed list was found in P_7.",
            },
            "marker_found": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "The exact marker text found in P_7 (e.g. 'adwokat', 'dr med.'). null if none.",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of which marker was or wasn't found.",
            },
        },
        "required": ["is_wolny_zawod", "marker_found", "reasoning"],
        "additionalProperties": False,
    },
}

STEP4_AUDITOR_SCHEMA = {
    "name": "auditor_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "approved": {
                "type": "boolean",
                "description": "true if classification is correct and unambiguous. false if issues found.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence 0.0-1.0. Only meaningful when approved=true. 0.90+ for clear cases.",
            },
            "corrected_pkwiu": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "If classifier made a known mistake, provide the correct PKWiU. null if no correction.",
            },
            "ambiguity_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Flags: 'alcohol_threshold_unknown' (fatal), "
                    "'wolny_zawod_vs_regular', 'najem_vs_zakwaterowanie', "
                    "'healthcare_practice_type_unknown', 'pkwiu_hierarchy_ambiguous', "
                    "'multiple_services', 'rd_vs_manufacturing'. Empty if no issues."
                ),
            },
            "clarification_question": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Specific question in Polish with options. Required when approved=false.",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of what was checked and why approved or not.",
            },
        },
        "required": [
            "approved",
            "confidence",
            "corrected_pkwiu",
            "ambiguity_flags",
            "clarification_question",
            "reasoning",
        ],
        "additionalProperties": False,
    },
}
