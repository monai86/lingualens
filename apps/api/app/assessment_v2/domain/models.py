from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


class ConsentPurpose(StrEnum):
    CLINICAL_ASSESSMENT = "clinical_assessment"
    RESEARCH_REUSE = "research_reuse"


class ConsentStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class RecordingUploadState(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"


class ProcessingRunStage(StrEnum):
    UPLOAD_VERIFICATION = "upload_verification"
    QUALITY_ANALYSIS = "quality_analysis"


class ProcessingRunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecordingQualityStatus(StrEnum):
    USABLE = "usable"
    NEEDS_ADDITIONAL_SAMPLE = "needs_additional_sample"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProtocolActivity:
    activity_key: str
    required: bool
    target_duration_seconds: int
    minimum_duration_seconds: int


@dataclass(frozen=True, slots=True)
class ProtocolVersion:
    protocol_version_key: str
    primary_language: str
    minimum_age_months: int
    maximum_age_months: int
    supported_purposes: tuple[AssessmentPurpose, ...]
    activities: tuple[ProtocolActivity, ...]


@dataclass(frozen=True, slots=True)
class AssessmentSnapshot:
    id: str
    organization_id: str
    child_id: str
    purpose: AssessmentPurpose
    state: AssessmentState
    assigned_clinician_id: str
    version: int
    age_months: int
    language_context: dict[str, object]


@dataclass(frozen=True, slots=True)
class AccessScope:
    user_id: str
    organization_id: str
    role: str


@dataclass(frozen=True, slots=True)
class CreateChild:
    display_code: str
    birth_year: int
    birth_month: int
    language_context: dict[str, object]


@dataclass(frozen=True, slots=True)
class ChildSnapshot:
    id: str
    organization_id: str
    display_code: str
    birth_year: int
    birth_month: int
    language_context: dict[str, object]
    version: int


@dataclass(frozen=True, slots=True)
class RecordConsent:
    purpose: ConsentPurpose
    scope_version: str
    status: ConsentStatus


@dataclass(frozen=True, slots=True)
class ConsentSnapshot:
    id: str
    organization_id: str
    child_id: str
    purpose: ConsentPurpose
    scope_version: str
    status: ConsentStatus
    granted_at: datetime
    withdrawn_at: datetime | None
    recorded_by_user_id: str
    version: int


@dataclass(frozen=True, slots=True)
class CreateAssessment:
    child_id: str
    purpose: AssessmentPurpose
    age_months: int
    language_context: dict[str, object]
    assigned_clinician_id: str


@dataclass(frozen=True, slots=True)
class StartAssessment:
    purpose: AssessmentPurpose
    assigned_clinician_id: str | None = None


@dataclass(frozen=True, slots=True)
class TransitionAssessment:
    assessment_id: str
    target_state: AssessmentState
    expected_version: int


@dataclass(frozen=True, slots=True)
class ProtocolSelectionSnapshot:
    assessment_id: str
    protocol_version_key: str
    selected_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class RecordingSnapshot:
    id: str
    organization_id: str
    assessment_id: str
    protocol_version_key: str
    activity_code: str
    declared_content_type: str
    declared_size_bytes: int
    declared_checksum: str
    object_key: str
    upload_state: RecordingUploadState
    expires_at: datetime
    verified_content_type: str | None
    verified_size_bytes: int | None
    verified_checksum: str | None
    verified_at: datetime | None
    version: int


@dataclass(frozen=True, slots=True)
class ProcessingRunSnapshot:
    id: str
    organization_id: str
    recording_id: str
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int
    available_at: datetime
    error_code: str | None


@dataclass(frozen=True, slots=True)
class RecordingQualitySnapshot:
    id: str
    organization_id: str
    recording_id: str
    status: RecordingQualityStatus
    measured_duration_seconds: float | None
    measured_loudness_db: float | None
    measured_silence_ratio: float | None
    measured_decodability: float | None
    unavailable_checks: tuple[str, ...]
    provenance: str
    evaluated_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class CaptureSnapshot:
    assessment: AssessmentSnapshot
    protocol_selection: ProtocolSelectionSnapshot | None
    activities: tuple[ProtocolActivity, ...]
    recordings: tuple[RecordingSnapshot, ...]
    quality_results: tuple[RecordingQualitySnapshot, ...]


@dataclass(frozen=True, slots=True)
class RecordingIntentSnapshot:
    recording: RecordingSnapshot
    processing_run: ProcessingRunSnapshot


@dataclass(frozen=True, slots=True)
class SelectProtocol:
    assessment_id: str
    protocol_version_key: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class StartCapture:
    assessment_id: str


@dataclass(frozen=True, slots=True)
class CreateRecording:
    assessment_id: str
    activity_code: str
    content_type: str
    size_bytes: int
    checksum: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class MarkRecordingUploading:
    recording_id: str
    expected_version: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CompleteRecordingUpload:
    recording_id: str
    expected_version: int
    observed_content_type: str
    observed_size_bytes: int
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class VerifyRecordingUpload:
    """Worker-owned authoritative verification, including a computed checksum."""

    recording_id: str
    expected_version: int
    verified_content_type: str
    verified_size_bytes: int
    server_computed_checksum: str
    verified_at: datetime


@dataclass(frozen=True, slots=True)
class CompleteCapture:
    assessment_id: str
    expected_version: int
