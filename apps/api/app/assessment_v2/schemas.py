"""Strict transport contracts for the assessment v2 API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentState,
    ConsentPurpose,
    ConsentStatus,
    ProcessingRunStage,
    ProcessingRunState,
    RecordingQualityStatus,
    RecordingUploadState,
    TranscriptReviewState,
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptSource,
)
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DomainProfileStatus,
    EvidenceSource,
    EvidenceState,
)
from app.assessment_v2.storage import CAPTURE_ALLOWED_MIME_TYPES
from app.core.config import MAX_CAPTURE_UPLOAD_SIZE_BYTES


_LANGUAGE_CODE = re.compile(r"^[A-Za-z]{2}$")
_CAPTURE_CONTENT_TYPE = re.compile(
    r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:;[A-Za-z0-9!#$&^_.+-]+=[A-Za-z0-9!#$&^_.+-]+)*$"
)
_CHECKSUM = re.compile(r"^sha256:[0-9a-f]{64}$")


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


class TranscriptRevisionCreateRequest(_StrictModel):
    # Transcript content is hashed and reviewed as an exact artifact. Do not
    # inherit the API-wide whitespace normalization for this field.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    source: TranscriptSource
    content: str = Field(min_length=1, max_length=2_000_000)
    expected_revision: int | None = Field(default=None, strict=True, ge=1)
    expected_version: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def validate_expected_current_pair(self) -> "TranscriptRevisionCreateRequest":
        if (self.expected_revision is None) != (self.expected_version is None):
            raise ValueError("expected_revision and expected_version must be provided together")
        return self


class TranscriptAttestRequest(_StrictModel):
    expected_version: int = Field(strict=True, ge=1)


class TranscriptRevisionResponse(_StrictModel):
    # Preserve trailing newlines and other intentional formatting in the
    # reviewed transcript returned to the client.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    id: str = Field(min_length=1, max_length=64)
    assessment_id: str = Field(min_length=1, max_length=64)
    revision: int = Field(strict=True, ge=1)
    source: TranscriptSource
    review_state: TranscriptReviewState
    content: str = Field(min_length=1, max_length=2_000_000)
    content_sha256: str = Field(strict=True, min_length=64, max_length=64)
    created_at: datetime
    attested_at: datetime | None
    version: int = Field(strict=True, ge=1)


class TranscriptSegmentCreateRequest(_StrictModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    ordinal: int = Field(strict=True, ge=1, le=100_000)
    start_ms: int = Field(strict=True, ge=0, le=86_400_000)
    end_ms: int = Field(strict=True, ge=1, le=86_400_000)
    speaker_role: TranscriptSegmentSpeakerRole
    text: str = Field(min_length=1, max_length=20_000)
    confidence: float | None = Field(default=None, strict=True, ge=0, le=1)
    uncertainty_reason: TranscriptSegmentUncertaintyReason = (
        TranscriptSegmentUncertaintyReason.NONE
    )

    @model_validator(mode="after")
    def validate_offsets(self) -> "TranscriptSegmentCreateRequest":
        if not self.text.strip():
            raise ValueError("text must be a non-empty value")
        if any(character in self.text for character in "\r\n"):
            raise ValueError("text must not contain newline characters")
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class TranscriptSegmentSetCreateRequest(_StrictModel):
    transcript_revision_id: str = Field(min_length=1, max_length=64)
    source: TranscriptSource
    segments: list[TranscriptSegmentCreateRequest] = Field(min_length=1, max_length=100_000)
    recording_id: str | None = Field(default=None, min_length=1, max_length=64)
    expected_revision: int | None = Field(default=None, strict=True, ge=1)
    expected_version: int | None = Field(default=None, strict=True, ge=1)
    client_checksum: str | None = Field(default=None, strict=True, min_length=64, max_length=64)

    @field_validator("client_checksum")
    @classmethod
    def validate_client_checksum(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("client_checksum must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def validate_expected_current_pair(self) -> "TranscriptSegmentSetCreateRequest":
        if (self.expected_revision is None) != (self.expected_version is None):
            raise ValueError("expected_revision and expected_version must be provided together")
        ordinals = [segment.ordinal for segment in self.segments]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise ValueError("segment ordinals must be contiguous starting at 1")
        return self


class TranscriptSegmentResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    ordinal: int = Field(strict=True, ge=1)
    start_ms: int = Field(strict=True, ge=0)
    end_ms: int = Field(strict=True, ge=1)
    speaker_role: TranscriptSegmentSpeakerRole
    text: str = Field(min_length=1, max_length=20_000)
    confidence: float | None = Field(default=None, strict=True, ge=0, le=1)
    uncertainty_reason: TranscriptSegmentUncertaintyReason
    created_at: datetime


class TranscriptSegmentSetResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    assessment_id: str = Field(min_length=1, max_length=64)
    transcript_revision_id: str = Field(min_length=1, max_length=64)
    transcript_content_sha256: str = Field(strict=True, min_length=64, max_length=64)
    recording_id: str | None = Field(default=None, min_length=1, max_length=64)
    revision: int = Field(strict=True, ge=1)
    source: TranscriptSource
    review_state: TranscriptReviewState
    segments_sha256: str = Field(strict=True, min_length=64, max_length=64)
    segments: list[TranscriptSegmentResponse] = Field(min_length=1, max_length=100_000)
    created_at: datetime
    attested_at: datetime | None
    version: int = Field(strict=True, ge=1)


class TranscriptSegmentReplayGrantResponse(_StrictModel):
    segment_id: str = Field(min_length=1, max_length=64)
    start_ms: int = Field(strict=True, ge=0)
    end_ms: int = Field(strict=True, ge=1)
    available: bool
    url: str | None = Field(default=None, min_length=1, max_length=4096)
    expires_at: datetime | None = None
    expires_in_seconds: int | None = Field(default=None, strict=True, ge=1, le=900)

    @model_validator(mode="after")
    def validate_replay_grant(self) -> "TranscriptSegmentReplayGrantResponse":
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        if self.available:
            if self.url is None or self.expires_at is None or self.expires_in_seconds is None:
                raise ValueError("available replay requires a signed URL and expiry")
        elif self.url is not None or self.expires_at is not None or self.expires_in_seconds is not None:
            raise ValueError("unavailable replay cannot expose a signed grant")
        return self


class EvidenceProvenanceResponse(_StrictModel):
    input_ref: str = Field(min_length=1, max_length=256)
    input_sha256: str = Field(strict=True, min_length=64, max_length=64)
    protocol_version_key: str = Field(min_length=1, max_length=128)
    extractor: str = Field(min_length=1, max_length=128)
    pipeline_version: str = Field(min_length=1, max_length=128)
    feature_schema_version: str = Field(min_length=1, max_length=128)
    analyzed_at: datetime


class MeasuredFeatureResponse(_StrictModel):
    key: str = Field(min_length=1, max_length=128)
    value: bool | int | float | str | None
    unit: str = Field(min_length=1, max_length=64)
    source: EvidenceSource
    state: EvidenceState
    limitation: str | None = Field(default=None, min_length=1, max_length=2000)
    provenance: EvidenceProvenanceResponse


class DomainProfileResponse(_StrictModel):
    domain: DevelopmentalDomain
    status: DomainProfileStatus
    summary: str = Field(min_length=1, max_length=2000)
    feature_keys: list[str] = Field(max_length=128)
    supporting_features: list[str] = Field(max_length=128)
    conflicting_features: list[str] = Field(max_length=128)
    limitations: list[str] = Field(max_length=128)


class EvidenceProfileResponse(_StrictModel):
    evidence_run_id: str = Field(min_length=1, max_length=64)
    assessment_id: str = Field(min_length=1, max_length=64)
    transcript_revision_id: str = Field(min_length=1, max_length=64)
    segment_set_id: str | None = Field(default=None, min_length=1, max_length=64)
    segment_set_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    state: EvidenceState
    generated_at: datetime
    provenance: EvidenceProvenanceResponse
    features: list[MeasuredFeatureResponse]
    domains: list[DomainProfileResponse]
    limitations: list[str] = Field(max_length=128)
    not_diagnostic: Literal[True] = True
    decision_support_only: Literal[True] = True
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


class ProtocolSelectionRequest(_StrictModel):
    """An intentionally empty request: selection is derived server-side."""


class RecordingCreateRequest(_StrictModel):
    content_type: str = Field(strict=True, min_length=3, max_length=128)
    size_bytes: int = Field(strict=True, ge=1, le=MAX_CAPTURE_UPLOAD_SIZE_BYTES)
    checksum: str = Field(strict=True, min_length=8, max_length=128, pattern=_CHECKSUM.pattern)

    @field_validator("content_type")
    @classmethod
    def normalize_content_type(cls, value: str) -> str:
        normalized = value.lower()
        if _CAPTURE_CONTENT_TYPE.fullmatch(normalized) is None or normalized not in CAPTURE_ALLOWED_MIME_TYPES:
            raise ValueError("content_type must be a media type")
        return normalized


class ProtocolActivityResponse(_StrictModel):
    activity_code: str = Field(min_length=1, max_length=64)
    required: bool
    target_duration_seconds: int = Field(strict=True, ge=1, le=3600)
    minimum_duration_seconds: int = Field(strict=True, ge=1, le=3600)


class ProtocolSelectionResponse(_StrictModel):
    protocol_version_key: str = Field(min_length=1, max_length=128)
    selected_at: datetime
    version: int = Field(strict=True, ge=1)


class RecordingResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    activity_code: str = Field(min_length=1, max_length=64)
    content_type: str = Field(min_length=3, max_length=128)
    size_bytes: int = Field(strict=True, ge=1, le=MAX_CAPTURE_UPLOAD_SIZE_BYTES)
    upload_state: RecordingUploadState
    expires_at: datetime
    verified_at: datetime | None
    version: int = Field(strict=True, ge=1)


class CaptureProgressResponse(_StrictModel):
    required_activities_total: int = Field(strict=True, ge=0, le=32)
    required_activities_verified: int = Field(strict=True, ge=0, le=32)
    required_activities_usable: int = Field(strict=True, ge=0, le=32)


class CaptureResponse(_StrictModel):
    assessment_id: str = Field(min_length=1, max_length=64)
    state: AssessmentState
    protocol: ProtocolSelectionResponse | None
    activities: list[ProtocolActivityResponse]
    recordings: list[RecordingResponse]
    progress: CaptureProgressResponse


class CaptureStateResponse(_StrictModel):
    assessment_id: str = Field(min_length=1, max_length=64)
    state: AssessmentState
    version: int = Field(strict=True, ge=1)


class UploadGrantResponse(_StrictModel):
    # The browser receives only a short-lived provider URL. Permanent bucket
    # and object locators remain server-side so API responses cannot become a
    # storage inventory or a reusable path oracle.
    url: str = Field(min_length=1, max_length=4096)
    expires_at: datetime
    expires_in_seconds: int = Field(strict=True, ge=1, le=7200)
    chunk_size_bytes: int = Field(strict=True, ge=1, le=MAX_CAPTURE_UPLOAD_SIZE_BYTES)
    upload_length_bytes: int = Field(strict=True, ge=1, le=MAX_CAPTURE_UPLOAD_SIZE_BYTES)
    content_type: str = Field(min_length=3, max_length=128)
    upsert: bool


class UploadIntentResponse(_StrictModel):
    recording: RecordingResponse
    upload: UploadGrantResponse


class ProcessingRunActionRequest(_StrictModel):
    expected_version: int = Field(strict=True, ge=1)


class ProcessingRunResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int = Field(strict=True, ge=0, le=1000)
    max_attempts: int = Field(strict=True, ge=1, le=1000)
    available_at: datetime
    error_code: str | None = Field(default=None, min_length=1, max_length=64)
    result_available: bool
    can_retry: bool
    can_cancel: bool
    version: int = Field(strict=True, ge=1)


class EvidenceProcessingResponse(_StrictModel):
    processing_run: ProcessingRunResponse


class RecordingIntentResponse(_StrictModel):
    recording: RecordingResponse
    processing_run: ProcessingRunResponse


class CompleteUploadResponse(_StrictModel):
    recording: RecordingResponse
    processing_run: ProcessingRunResponse


class RecordingQualityResponse(_StrictModel):
    status: RecordingQualityStatus
    evaluated_at: datetime
    version: int = Field(strict=True, ge=1)


class DownloadGrantResponse(_StrictModel):
    url: str = Field(min_length=1, max_length=2048)
    expires_at: datetime
    expires_in_seconds: int = Field(strict=True, ge=1, le=900)


class DownloadIntentResponse(_StrictModel):
    recording: RecordingResponse
    download: DownloadGrantResponse


class DeleteRecordingResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    deleted: bool


# Longitudinal comparison schemas (B2)
from app.assessment_v2.longitudinal import (
    CompatibilityStatus,
    IncompatibilityReason,
    NumericalTrend,
)


class ComparisonCreateRequest(_StrictModel):
    baseline_assessment_id: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(default="longitudinal_v1", min_length=1, max_length=64)


class FeatureComparisonItemResponse(_StrictModel):
    feature_key: str = Field(min_length=1, max_length=128)
    unit: str | None = Field(default=None, max_length=64)
    status: CompatibilityStatus
    incompatibility_reasons: list[IncompatibilityReason]
    baseline_value: float | int | None = None
    current_value: float | int | None = None
    absolute_delta: float | None = None
    percent_change: float | None = None
    percent_change_limitation: str | None = Field(default=None, max_length=64)
    numerical_trend: NumericalTrend
    clinical_interpretation: str = Field(min_length=1, max_length=64)


class ComparisonResponse(_StrictModel):
    comparison_id: str = Field(min_length=1, max_length=64)
    baseline_assessment_id: str = Field(min_length=1, max_length=64)
    current_assessment_id: str = Field(min_length=1, max_length=64)
    baseline_evidence_run_id: str = Field(min_length=1, max_length=64)
    current_evidence_run_id: str = Field(min_length=1, max_length=64)
    baseline_evidence_sha256: str = Field(min_length=64, max_length=64)
    current_evidence_sha256: str = Field(min_length=64, max_length=64)
    policy_version: str = Field(min_length=1, max_length=64)
    status: CompatibilityStatus
    is_stale: bool
    features: list[FeatureComparisonItemResponse]
    created_at: datetime


class ChildAssessmentHistoryItemResponse(_StrictModel):
    assessment_id: str = Field(min_length=1, max_length=64)
    created_at: datetime
    purpose: str = Field(min_length=1, max_length=64)
    state: str = Field(min_length=1, max_length=64)
    age_months: int = Field(ge=0, le=240)
    protocol_version_key: str | None = Field(default=None, max_length=128)
    language: str = Field(min_length=1, max_length=64)
    evidence_run_id: str | None = Field(default=None, max_length=64)
    is_comparable: bool


# Clinical Review & Reports Schemas (C1 & C2)
from app.assessment_v2.clinical_review import (
    AttentionCueType,
    ClinicalDispositionType,
    CueStatus,
)
from app.assessment_v2.reports import ReportStatus


class AttentionCueReviewRequest(_StrictModel):
    status: CueStatus
    rationale: str | None = Field(default=None, max_length=2048)


class FollowUpPlanSchema(_StrictModel):
    target_date: str | None = Field(default=None, max_length=64)
    recommended_protocol: str | None = Field(default=None, max_length=128)
    focus_areas: list[str] = Field(default_factory=list)
    monitoring_notes: str | None = Field(default=None, max_length=2048)


class ClinicalDispositionRequest(_StrictModel):
    disposition: ClinicalDispositionType
    disposition_notes: str | None = Field(default=None, max_length=4096)
    follow_up_plan: FollowUpPlanSchema | None = None
    expected_version: int | None = Field(default=None, ge=1)


class AttentionCueResponse(_StrictModel):
    cue_id: str = Field(min_length=1, max_length=64)
    cue_type: AttentionCueType
    title: str = Field(min_length=1, max_length=255)
    description: str
    policy_version: str = Field(min_length=1, max_length=64)
    evidence_run_id: str = Field(min_length=1, max_length=64)
    supporting_feature_keys: list[str]
    conflicting_feature_keys: list[str]
    limitations: list[str]
    status: CueStatus
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    rationale: str | None = None


class ClinicalReviewResponse(_StrictModel):
    review_id: str = Field(min_length=1, max_length=64)
    assessment_id: str = Field(min_length=1, max_length=64)
    child_id: str = Field(min_length=1, max_length=64)
    evidence_run_id: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=32)
    cues: list[AttentionCueResponse]
    disposition: ClinicalDispositionType | None = None
    disposition_notes: str | None = None
    follow_up_plan: FollowUpPlanSchema | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    is_stale: bool


class ReportDraftCreateRequest(_StrictModel):
    purpose: str | None = Field(default=None, max_length=1024)
    comparison_id: str | None = Field(default=None, max_length=64)


class ReportDraftUpdateRequest(_StrictModel):
    title: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=1024)
    content_markdown: str = Field(min_length=1)
    limitations: list[str] | None = None
    expected_version: int | None = Field(default=None, ge=1)


class ReportSignOffRequest(_StrictModel):
    expected_version: int | None = Field(default=None, ge=1)


class ReportAmendmentCreateRequest(_StrictModel):
    title: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=1, max_length=1024)
    content_markdown: str = Field(min_length=1)


class ReportResponse(_StrictModel):
    report_id: str = Field(min_length=1, max_length=64)
    assessment_id: str = Field(min_length=1, max_length=64)
    child_id: str = Field(min_length=1, max_length=64)
    evidence_run_id: str = Field(min_length=1, max_length=64)
    comparison_id: str | None = None
    review_id: str = Field(min_length=1, max_length=64)
    amends_report_id: str | None = None
    amendment_sequence: int = Field(ge=0)
    version: int = Field(ge=1)
    status: ReportStatus
    title: str = Field(min_length=1, max_length=255)
    purpose: str
    content_markdown: str
    limitations: list[str]
    signed_by: str | None = None
    signed_at: datetime | None = None
    signed_snapshot_hash: str | None = None
    is_stale: bool
    created_at: datetime
    updated_at: datetime


class ReportExportResponse(_StrictModel):
    report_id: str = Field(min_length=1, max_length=64)
    format: str = Field(min_length=1, max_length=16)
    content_type: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content: str | None = None
    base64_content: str | None = None
    report_hash: str | None = None
    signed_by: str | None = None
    export_timestamp: datetime


