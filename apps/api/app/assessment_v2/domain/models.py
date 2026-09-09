from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re


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
    CLEANUP = "cleanup"
    EVIDENCE_EXTRACTION = "evidence_extraction"


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


class TranscriptSource(StrEnum):
    MANUAL = "manual"
    ASR_DRAFT = "asr_draft"
    IMPORTED = "imported"


class TranscriptReviewState(StrEnum):
    DRAFT = "draft"
    ATTESTED = "attested"
    SUPERSEDED = "superseded"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n"):
        raise ValueError(f"{field_name} must be a non-empty value without newlines")


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
    recording_id: str | None
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int
    available_at: datetime
    error_code: str | None
    assessment_id: str | None = None
    transcript_revision_id: str | None = None
    max_attempts: int = 3
    result_available: bool = False
    can_retry: bool = False
    can_cancel: bool = False
    version: int = 1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.version < 1:
            raise ValueError("version must be positive")

        has_recording_target = self.recording_id is not None
        has_evidence_target = (
            self.assessment_id is not None or self.transcript_revision_id is not None
        )
        if not has_recording_target and not has_evidence_target:
            raise ValueError("processing run requires a target")
        if has_recording_target and has_evidence_target:
            raise ValueError("processing run cannot mix recording and evidence targets")

        if self.stage is ProcessingRunStage.EVIDENCE_EXTRACTION:
            if (
                has_recording_target
                or self.assessment_id is None
                or self.transcript_revision_id is None
            ):
                raise ValueError(
                    "evidence extraction requires an assessment and transcript revision target"
                )
            return

        if self.stage not in {
            ProcessingRunStage.UPLOAD_VERIFICATION,
            ProcessingRunStage.QUALITY_ANALYSIS,
            ProcessingRunStage.CLEANUP,
        }:
            raise ValueError("processing run has an invalid target family")
        if not has_recording_target:
            raise ValueError("capture processing run requires a recording target")
        if self.result_available:
            raise ValueError("capture processing run cannot expose a result")
        if self.can_retry or self.can_cancel:
            raise ValueError("capture processing run cannot expose retry or cancel actions")


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


@dataclass(frozen=True, slots=True)
class TranscriptRevisionSnapshot:
    id: str
    organization_id: str
    assessment_id: str
    revision: int
    source: TranscriptSource
    review_state: TranscriptReviewState
    content: str
    content_sha256: str
    created_by_user_id: str
    created_at: datetime
    attested_by_user_id: str | None
    attested_at: datetime | None
    version: int

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.id, "transcript revision id"),
            (self.organization_id, "organization id"),
            (self.assessment_id, "assessment id"),
            (self.created_by_user_id, "created by user id"),
        ):
            _require_non_empty(value, field_name)
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("transcript content must be non-empty")
        if _SHA256.fullmatch(self.content_sha256) is None:
            raise ValueError("content_sha256 must be a 64-character lowercase SHA-256 digest")
        if self.revision < 1:
            raise ValueError("revision must be positive")
        if self.version < 1:
            raise ValueError("version must be positive")
        if (self.attested_by_user_id is None) != (self.attested_at is None):
            raise ValueError("attestation actor and timestamp must be provided together")
        if self.review_state is TranscriptReviewState.ATTESTED and self.attested_by_user_id is None:
            raise ValueError("attested transcript revision requires attestation metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "assessment_id": self.assessment_id,
            "revision": self.revision,
            "source": self.source.value,
            "review_state": self.review_state.value,
            "content": self.content,
            "content_sha256": self.content_sha256,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat(),
            "attested_by_user_id": self.attested_by_user_id,
            "attested_at": self.attested_at.isoformat() if self.attested_at else None,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class CreateTranscriptRevision:
    assessment_id: str
    content: str
    source: TranscriptSource
    expected_revision: int | None = None
    expected_version: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.assessment_id, "assessment id")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("transcript content must be non-empty")
        if (self.expected_revision is None) != (self.expected_version is None):
            raise ValueError("expected_revision and expected_version must be provided together")
        if self.expected_revision is not None and self.expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        if self.expected_version is not None and self.expected_version < 1:
            raise ValueError("expected_version must be positive")
@dataclass(frozen=True, slots=True)
class AttestTranscript:
    transcript_revision_id: str
    expected_version: int

    def __post_init__(self) -> None:
        _require_non_empty(self.transcript_revision_id, "transcript revision id")
        if self.expected_version < 1:
            raise ValueError("expected_version must be positive")
