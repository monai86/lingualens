"""Strict transport contracts for the assessment v2 API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentState,
    ConsentPurpose,
    ConsentStatus,
)


_LANGUAGE_CODE = re.compile(r"^[A-Za-z]{2}$")


def _normalize_language_context(value: Any) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("language_context must be an object")
    unknown = set(value) - {"primary", "additional"}
    if unknown:
        raise ValueError("language_context contains unsupported fields")

    primary = value.get("primary")
    if not isinstance(primary, str) or not _LANGUAGE_CODE.fullmatch(primary.strip()):
        raise ValueError("primary language must be a two-letter code")

    additional = value.get("additional", [])
    if not isinstance(additional, list):
        raise ValueError("additional languages must be a list")
    normalized_additional: list[str] = []
    for code in additional:
        if not isinstance(code, str) or not _LANGUAGE_CODE.fullmatch(code.strip()):
            raise ValueError("additional languages must use two-letter codes")
        normalized_additional.append(code.strip().lower())

    return {"primary": primary.strip().lower(), "additional": normalized_additional}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChildCreateRequest(_StrictModel):
    display_code: str = Field(min_length=1, max_length=64)
    birth_year: int = Field(strict=True, ge=1900, le=2100)
    birth_month: int = Field(strict=True, ge=1, le=12)
    language_context: dict[str, object]

    @field_validator("language_context")
    @classmethod
    def normalize_language_context(cls, value: dict[str, object]) -> dict[str, object]:
        return _normalize_language_context(value)


class ChildResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    display_code: str = Field(min_length=1, max_length=64)
    birth_year: int = Field(strict=True, ge=1900, le=2100)
    birth_month: int = Field(strict=True, ge=1, le=12)
    language_context: dict[str, object]
    version: int = Field(strict=True, ge=1)

    @field_validator("language_context")
    @classmethod
    def normalize_language_context(cls, value: dict[str, object]) -> dict[str, object]:
        return _normalize_language_context(value)


class ConsentCreateRequest(_StrictModel):
    purpose: ConsentPurpose
    scope_version: str = Field(min_length=1, max_length=64)
    status: ConsentStatus


class ConsentResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    child_id: str = Field(min_length=1, max_length=64)
    purpose: ConsentPurpose
    scope_version: str = Field(min_length=1, max_length=64)
    status: ConsentStatus
    granted_at: datetime
    withdrawn_at: datetime | None
    version: int = Field(strict=True, ge=1)


class AssessmentCreateRequest(_StrictModel):
    purpose: AssessmentPurpose
    assigned_clinician_id: str | None = Field(default=None, min_length=1, max_length=128)


class AssessmentTransitionRequest(_StrictModel):
    target_state: AssessmentState
    expected_version: int = Field(strict=True, ge=1)


class AssessmentResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    child_id: str = Field(min_length=1, max_length=64)
    purpose: AssessmentPurpose
    state: AssessmentState
    age_months: int = Field(strict=True, ge=0, le=216)
    language_context: dict[str, object]
    assigned_clinician_id: str = Field(min_length=1, max_length=128)
    version: int = Field(strict=True, ge=1)

    @field_validator("language_context")
    @classmethod
    def normalize_language_context(cls, value: dict[str, object]) -> dict[str, object]:
        return _normalize_language_context(value)


class ErrorBody(_StrictModel):
    code: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=512)
    details: dict[str, object] = Field(default_factory=dict)
    correlation_id: str = Field(min_length=1, max_length=128)


class ErrorEnvelope(_StrictModel):
    error: ErrorBody

