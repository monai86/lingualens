"""Canonical V2 constraints and input validators for desktop client (GUI/TUI).

Provides shared validation seam without introducing backend runtime dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


class LinguaLensValidationError(ValueError):
    """Raised when client-side or canonical schema validation fails."""
    pass


_LANGUAGE_CODE = re.compile(r"^[A-Za-z]{2}$")

VALID_ASSESSMENT_PURPOSES = frozenset({
    "initial",
    "developmental_follow_up",
    "post_intervention_follow_up",
    "additional_evidence",
})

VALID_CONSENT_PURPOSES = frozenset({
    "clinical_assessment",
    "research_reuse",
})

VALID_CONSENT_STATUSES = frozenset({
    "active",
    "withdrawn",
})

MAX_ASSESSMENT_AGE_MONTHS = 216


def normalize_language_context(value: Any) -> dict[str, Any]:
    """Validate and normalize language context per canonical schema."""
    if value is None:
        return {"primary": "th", "additional": []}
    if not isinstance(value, dict):
        raise ValueError("language_context must be a dictionary")
    unknown = set(value) - {"primary", "additional"}
    if unknown:
        raise ValueError(f"language_context contains unsupported fields: {', '.join(sorted(unknown))}")

    primary = value.get("primary")
    if not isinstance(primary, str) or not _LANGUAGE_CODE.fullmatch(primary.strip()):
        raise ValueError("primary language must be a two-letter ISO code")

    additional = value.get("additional", [])
    if not isinstance(additional, list):
        raise ValueError("additional languages must be a list")

    normalized_additional: list[str] = []
    for code in additional:
        if not isinstance(code, str) or not _LANGUAGE_CODE.fullmatch(code.strip()):
            raise ValueError("additional languages must use two-letter ISO codes")
        normalized_additional.append(code.strip().lower())

    return {"primary": primary.strip().lower(), "additional": normalized_additional}


def validate_child_input(
    display_code: Any,
    birth_year: Any,
    birth_month: Any,
    language_context: Any = None,
) -> dict[str, Any]:
    """Validate child intake inputs per canonical ChildCreateRequest contract."""
    if not isinstance(display_code, str):
        raise ValueError("display_code must be a non-empty string")
    trimmed_code = display_code.strip()
    if not (1 <= len(trimmed_code) <= 64):
        raise ValueError("display_code must be between 1 and 64 characters")

    # Strict integer check: bool is an int subclass in Python, so exclude bool explicitly
    if isinstance(birth_year, bool) or not isinstance(birth_year, int):
        raise ValueError("birth_year must be a strict integer")
    if not (1900 <= birth_year <= 2100):
        raise ValueError("birth_year must be between 1900 and 2100")

    if isinstance(birth_month, bool) or not isinstance(birth_month, int):
        raise ValueError("birth_month must be a strict integer")
    if not (1 <= birth_month <= 12):
        raise ValueError("birth_month must be between 1 and 12")

    norm_lang = normalize_language_context(language_context)
    return {
        "display_code": trimmed_code,
        "birth_year": birth_year,
        "birth_month": birth_month,
        "language_context": norm_lang,
    }


def validate_consent_input(
    child_id: Any,
    purpose: Any,
    scope_version: Any,
    status: Any,
) -> dict[str, Any]:
    """Validate consent recording input per canonical ConsentCreateRequest contract."""
    if not isinstance(child_id, str):
        raise ValueError("child_id must be a non-empty string")
    clean_child = child_id.strip()
    if not (1 <= len(clean_child) <= 64):
        raise ValueError("child_id must be between 1 and 64 characters")

    if not isinstance(purpose, str) or purpose not in VALID_CONSENT_PURPOSES:
        raise ValueError(f"purpose must be one of: {', '.join(sorted(VALID_CONSENT_PURPOSES))}")

    if not isinstance(scope_version, str):
        raise ValueError("scope_version must be a non-empty string")
    clean_scope = scope_version.strip()
    if not (1 <= len(clean_scope) <= 64):
        raise ValueError("scope_version must be between 1 and 64 characters")

    if not isinstance(status, str) or status not in VALID_CONSENT_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_CONSENT_STATUSES))}")

    return {
        "child_id": clean_child,
        "purpose": purpose,
        "scope_version": clean_scope,
        "status": status,
    }


def validate_assessment_input(
    child_id: Any,
    purpose: Any,
    assigned_clinician_id: Any = None,
) -> dict[str, Any]:
    """Validate assessment creation input per canonical AssessmentCreateRequest contract."""
    if not isinstance(child_id, str):
        raise ValueError("child_id must be a non-empty string")
    clean_child = child_id.strip()
    if not (1 <= len(clean_child) <= 64):
        raise ValueError("child_id must be between 1 and 64 characters")

    if not isinstance(purpose, str) or purpose not in VALID_ASSESSMENT_PURPOSES:
        raise ValueError(f"purpose must be one of: {', '.join(sorted(VALID_ASSESSMENT_PURPOSES))}")

    clean_clinician: str | None = None
    if assigned_clinician_id is not None:
        if not isinstance(assigned_clinician_id, str):
            raise ValueError("assigned_clinician_id must be a string")
        clean_clinician = assigned_clinician_id.strip()
        if not (1 <= len(clean_clinician) <= 128):
            raise ValueError("assigned_clinician_id must be between 1 and 128 characters")

    return {
        "child_id": clean_child,
        "purpose": purpose,
        "assigned_clinician_id": clean_clinician,
    }


def calculate_age_in_months(
    birth_year: int,
    birth_month: int,
    current_date: datetime | None = None,
) -> int:
    """Calculate age in months relative to current_date per canonical backend rule."""
    now = current_date or datetime.now(timezone.utc)
    age_months = (now.year - birth_year) * 12 + now.month - birth_month
    if not (0 <= age_months <= MAX_ASSESSMENT_AGE_MONTHS):
        raise ValueError(
            f"Calculated age ({age_months} months) is out of range (0-{MAX_ASSESSMENT_AGE_MONTHS} months)."
        )
    return age_months
