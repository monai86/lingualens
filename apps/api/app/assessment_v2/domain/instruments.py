"""Domain contracts for generic instrument administrations and responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping


class InstrumentRespondentType(StrEnum):
    CAREGIVER = "caregiver"
    CLINICIAN = "clinician"
    TEACHER = "teacher"


def _require_clean_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n"):
        raise ValueError(f"{field_name} must be a non-empty string without newlines")


def _require_utc(dt: datetime, field_name: str) -> None:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime")


@dataclass(frozen=True, slots=True)
class InstrumentItemResponse:
    """A response to an individual item in a standardized instrument."""

    item_key: str
    prompt_label: str
    response_value: str | int | float | bool
    score: float | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_clean_text(self.item_key, "item_key")
        _require_clean_text(self.prompt_label, "prompt_label")
        if not isinstance(self.response_value, (str, int, float, bool)):
            raise ValueError("response_value must be a scalar")
        if self.notes is not None and not isinstance(self.notes, str):
            raise ValueError("notes must be a string if provided")

    def to_dict(self) -> dict[str, object]:
        return {
            "item_key": self.item_key,
            "prompt_label": self.prompt_label,
            "response_value": self.response_value,
            "score": self.score,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class InstrumentAdministration:
    """An administered screening or assessment instrument snapshot."""

    administration_id: str
    organization_id: str
    assessment_id: str
    instrument_name: str
    instrument_version: str
    respondent_type: InstrumentRespondentType
    administered_by_user_id: str
    administered_at: datetime
    licensing_verified: bool
    summary_scores: Mapping[str, float] = field(default_factory=dict)
    items: tuple[InstrumentItemResponse, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_clean_text(self.administration_id, "administration_id")
        _require_clean_text(self.organization_id, "organization_id")
        _require_clean_text(self.assessment_id, "assessment_id")
        _require_clean_text(self.instrument_name, "instrument_name")
        _require_clean_text(self.instrument_version, "instrument_version")
        _require_clean_text(self.administered_by_user_id, "administered_by_user_id")
        _require_utc(self.administered_at, "administered_at")
        _require_utc(self.created_at, "created_at")

        for k, v in self.summary_scores.items():
            _require_clean_text(k, "summary score key")
            if not isinstance(v, (int, float)):
                raise ValueError("summary score value must be a number")

    def to_dict(self) -> dict[str, object]:
        return {
            "administration_id": self.administration_id,
            "organization_id": self.organization_id,
            "assessment_id": self.assessment_id,
            "instrument_name": self.instrument_name,
            "instrument_version": self.instrument_version,
            "respondent_type": self.respondent_type.value,
            "administered_by_user_id": self.administered_by_user_id,
            "administered_at": self.administered_at.astimezone(timezone.utc).isoformat(),
            "licensing_verified": self.licensing_verified,
            "summary_scores": dict(self.summary_scores),
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
        }
