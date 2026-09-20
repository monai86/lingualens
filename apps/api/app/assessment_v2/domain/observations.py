"""Domain contracts for versioned clinician and caregiver observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import re


class ObservationSource(StrEnum):
    CLINICIAN = "clinician"
    CAREGIVER = "caregiver"
    EDUCATOR = "educator"


class ObservationCategory(StrEnum):
    COMMUNICATION = "communication"
    SOCIAL_ENGAGEMENT = "social_engagement"
    PLAY_BEHAVIOR = "play_behavior"
    SENSORY_MOTOR = "sensory_motor"
    EMOTIONAL_REGULATION = "emotional_regulation"


def _require_clean_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n"):
        raise ValueError(f"{field_name} must be a non-empty string without newlines")


def _require_utc(dt: datetime, field_name: str) -> None:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime")


@dataclass(frozen=True, slots=True)
class ObservationRecordValue:
    """An immutable, versioned clinical or caregiver observation snapshot."""

    observation_id: str
    organization_id: str
    assessment_id: str
    category: ObservationCategory
    source: ObservationSource
    observer_name: str
    observer_role: str
    observed_at: datetime
    activity_context: str
    notes: str
    structured_flags: tuple[str, ...] = field(default_factory=tuple)
    is_amendment: bool = False
    amends_observation_id: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_clean_text(self.observation_id, "observation_id")
        _require_clean_text(self.organization_id, "organization_id")
        _require_clean_text(self.assessment_id, "assessment_id")
        _require_clean_text(self.observer_name, "observer_name")
        _require_clean_text(self.observer_role, "observer_role")
        _require_clean_text(self.activity_context, "activity_context")
        _require_utc(self.observed_at, "observed_at")
        _require_utc(self.created_at, "created_at")

        if not isinstance(self.notes, str) or not self.notes.strip():
            raise ValueError("notes must be non-empty text")

        for flag in self.structured_flags:
            _require_clean_text(flag, "structured_flag")

        if self.is_amendment:
            if not self.amends_observation_id:
                raise ValueError("amendment must specify amends_observation_id")
            _require_clean_text(self.amends_observation_id, "amends_observation_id")
            if self.version < 2:
                raise ValueError("amendment version must be >= 2")
        else:
            if self.amends_observation_id is not None:
                raise ValueError("non-amendment observation must not set amends_observation_id")
            if self.version != 1:
                raise ValueError("initial observation version must be 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "organization_id": self.organization_id,
            "assessment_id": self.assessment_id,
            "category": self.category.value,
            "source": self.source.value,
            "observer_name": self.observer_name,
            "observer_role": self.observer_role,
            "observed_at": self.observed_at.astimezone(timezone.utc).isoformat(),
            "activity_context": self.activity_context,
            "notes": self.notes,
            "structured_flags": list(self.structured_flags),
            "is_amendment": self.is_amendment,
            "amends_observation_id": self.amends_observation_id,
            "version": self.version,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
        }
