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


class ProcessingRunResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int = Field(strict=True, ge=0, le=1000)
    error_code: str | None = Field(default=None, min_length=1, max_length=64)


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
