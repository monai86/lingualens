from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AssessmentPurpose(StrEnum):
    INITIAL = "initial"
    DEVELOPMENTAL_FOLLOW_UP = "developmental_follow_up"
    POST_INTERVENTION_FOLLOW_UP = "post_intervention_follow_up"
    ADDITIONAL_EVIDENCE = "additional_evidence"


class AssessmentState(StrEnum):
    DRAFT = "draft"
    READY_FOR_CAPTURE = "ready_for_capture"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    READY_FOR_CLINICIAN = "ready_for_clinician"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AssessmentSnapshot:
    id: str
    organization_id: str
    child_id: str
    purpose: AssessmentPurpose
    state: AssessmentState
    assigned_clinician_id: str
    version: int
