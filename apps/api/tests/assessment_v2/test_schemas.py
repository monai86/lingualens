from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module

import pytest
from pydantic import ValidationError

from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentState,
    ProcessingRunStage,
    ProcessingRunState,
    RecordingQualityStatus,
    RecordingUploadState,
)
from app.assessment_v2.schemas import (
    AssessmentCreateRequest,
    AssessmentResponse,
    AssessmentTransitionRequest,
    ChildCreateRequest,
    ChildResponse,
    ConsentCreateRequest,
    ConsentResponse,
)


def language_context() -> dict[str, object]:
    return {"primary": "TH", "additional": ["en"]}


def test_child_request_is_strict_and_normalizes_language_codes() -> None:
    request = ChildCreateRequest(
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context=language_context(),
    )

    assert request.language_context == {"primary": "th", "additional": ["en"]}

    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context=language_context(),
            name="real child",
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "child"},
        {"date_of_birth": "2021-06-01"},
        {"organization_id": "org_alpha"},
        {"state": "finalized"},
    ],
)
def test_request_models_reject_identifiers_dates_organization_and_state(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context=language_context(),
            **payload,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("birth_month", 0),
        ("birth_month", 13),
        ("birth_year", 1899),
        ("birth_year", 2101),
    ],
)
def test_child_birth_fields_are_constrained(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=value if field == "birth_year" else 2021,
            birth_month=value if field == "birth_month" else 6,
            language_context=language_context(),
        )


def test_language_context_requires_two_letter_primary_and_additional_codes() -> None:
    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "thai", "additional": []},
        )

    with pytest.raises(ValidationError):
        ChildCreateRequest(
            display_code="LL-0001",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": ["english"]},
        )


def test_consent_request_is_strict_and_has_explicit_enums() -> None:
    request = ConsentCreateRequest(
        purpose="clinical_assessment",
        scope_version="clinical-v1",
        status="active",
    )

    assert request.purpose.value == "clinical_assessment"
    assert request.status.value == "active"

    with pytest.raises(ValidationError):
        ConsentCreateRequest(
            purpose="clinical_assessment",
            scope_version="clinical-v1",
            status="active",
            organization_id="org_alpha",
        )


def test_assessment_create_and_transition_requests_cannot_supply_state_or_negative_version() -> None:
    request = AssessmentCreateRequest(purpose=AssessmentPurpose.INITIAL)
    assert request.assigned_clinician_id is None

    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="not-a-purpose")
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(purpose="initial", state="finalized")
    with pytest.raises(ValidationError):
        AssessmentTransitionRequest(target_state=AssessmentState.DRAFT, expected_version=-1)


def test_responses_expose_safe_clinical_fields_without_child_name_or_exact_dob() -> None:
    child_fields = set(ChildResponse.model_fields)
    assessment_fields = set(AssessmentResponse.model_fields)
    consent_fields = set(ConsentResponse.model_fields)

    assert {"display_code", "birth_year", "birth_month", "language_context"} <= child_fields
    assert "name" not in child_fields and "date_of_birth" not in child_fields
    assert "age_months" in assessment_fields and "language_context" in assessment_fields
    assert "name" not in assessment_fields and "date_of_birth" not in assessment_fields
    assert {"purpose", "scope_version", "status", "version"} <= consent_fields

    response = ChildResponse(
        id="child_01",
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context={"primary": "th", "additional": []},
        version=1,
    )
    assert response.model_dump()["display_code"] == "LL-0001"

    assessment = AssessmentResponse(
        id="assessment_01",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=AssessmentState.DRAFT,
        age_months=63,
        language_context={"primary": "th", "additional": []},
        assigned_clinician_id="therapist_01",
        version=1,
    )
    assert assessment.state is AssessmentState.DRAFT

    consent = ConsentResponse(
        id="consent_01",
        child_id="child_01",
        purpose="clinical_assessment",
        scope_version="clinical-v1",
        status="active",
        granted_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        withdrawn_at=None,
        version=1,
    )
    assert consent.status.value == "active"


def test_capture_requests_are_strict_and_bound_upload_metadata() -> None:
    capture_schemas = import_module("app.assessment_v2.schemas")
    assert all(
        hasattr(capture_schemas, name)
        for name in ("ProtocolSelectionRequest", "RecordingCreateRequest")
    )
    RecordingCreateRequest = capture_schemas.RecordingCreateRequest
    ProtocolSelectionRequest = capture_schemas.ProtocolSelectionRequest

    request = RecordingCreateRequest(
        content_type="audio/webm",
        size_bytes=456,
        checksum="sha256:" + "0123456789abcdef" * 4,
    )

    assert request.content_type == "audio/webm"
    assert request.size_bytes == 456

    for unsafe_field in (
        {"filename": "sample.webm"},
        {"child_name": "Synthetic Child"},
        {"organization_id": "org_alpha"},
        {"state": "verified"},
    ):
        with pytest.raises(ValidationError):
            RecordingCreateRequest(
                content_type="audio/webm",
                size_bytes=456,
                checksum="sha256:" + "0123456789abcdef" * 4,
                **unsafe_field,
            )

    with pytest.raises(ValidationError):
        RecordingCreateRequest(content_type="audio/webm", size_bytes=0, checksum="sha256:abc")
    with pytest.raises(ValidationError):
        RecordingCreateRequest(
            content_type="audio/webm",
            size_bytes=456,
            checksum="checksum with whitespace",
        )
    with pytest.raises(ValidationError):
        RecordingCreateRequest(
            content_type="audio/flac",
            size_bytes=456,
            checksum="sha256:" + "0" * 64,
        )
    with pytest.raises(ValidationError):
        RecordingCreateRequest(
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:" + "0" * 32,
        )
    with pytest.raises(ValidationError):
        ProtocolSelectionRequest(unexpected="input")


def test_capture_responses_expose_only_safe_recording_and_processing_fields() -> None:
    capture_schemas = import_module("app.assessment_v2.schemas")
    expected_names = (
        "CaptureProgressResponse",
        "CaptureResponse",
        "ProcessingRunResponse",
        "ProtocolActivityResponse",
        "ProtocolSelectionResponse",
        "RecordingQualityResponse",
        "RecordingResponse",
    )
    assert all(hasattr(capture_schemas, name) for name in expected_names)
    CaptureProgressResponse = capture_schemas.CaptureProgressResponse
    CaptureResponse = capture_schemas.CaptureResponse
    ProcessingRunResponse = capture_schemas.ProcessingRunResponse
    ProtocolActivityResponse = capture_schemas.ProtocolActivityResponse
    ProtocolSelectionResponse = capture_schemas.ProtocolSelectionResponse
    RecordingQualityResponse = capture_schemas.RecordingQualityResponse
    RecordingResponse = capture_schemas.RecordingResponse

    recording_fields = set(RecordingResponse.model_fields)
    capture_fields = set(CaptureResponse.model_fields)
    processing_fields = set(ProcessingRunResponse.model_fields)
    quality_fields = set(RecordingQualityResponse.model_fields)

    assert {"id", "activity_code", "content_type", "size_bytes", "upload_state", "version"} <= recording_fields
    assert {"assessment_id", "state", "protocol", "activities", "recordings", "progress"} <= capture_fields
    assert processing_fields == {"id", "stage", "state", "attempt_count", "error_code"}
    assert quality_fields == {"status", "evaluated_at", "version"}
    assert {"object_key", "checksum", "filename", "child_name", "organization_id"}.isdisjoint(
        recording_fields | capture_fields | processing_fields | quality_fields
    )

    response = CaptureResponse(
        assessment_id="assessment_opaque_01",
        state=AssessmentState.CAPTURING,
        protocol=ProtocolSelectionResponse(
            protocol_version_key="thai_guided_language_sample:v0",
            selected_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
            version=1,
        ),
        activities=[
            ProtocolActivityResponse(
                activity_code="free_play",
                required=True,
                target_duration_seconds=180,
                minimum_duration_seconds=120,
            )
        ],
        recordings=[
            RecordingResponse(
                id="recording_opaque_01",
                activity_code="free_play",
                content_type="audio/webm",
                size_bytes=456,
                upload_state=RecordingUploadState.UPLOADING,
                expires_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
                verified_at=None,
                version=2,
            )
        ],
        progress=CaptureProgressResponse(
            required_activities_total=1,
            required_activities_verified=0,
            required_activities_usable=0,
        ),
    )
    processing = ProcessingRunResponse(
        id="run_opaque_01",
        stage=ProcessingRunStage.QUALITY_ANALYSIS,
        state=ProcessingRunState.QUEUED,
        attempt_count=0,
        error_code=None,
    )
    quality = RecordingQualityResponse(
        status=RecordingQualityStatus.USABLE,
        evaluated_at=datetime(2026, 9, 6, tzinfo=timezone.utc),
        version=1,
    )

    assert response.recordings[0].activity_code == "free_play"
    assert processing.stage is ProcessingRunStage.QUALITY_ANALYSIS
    assert quality.status is RecordingQualityStatus.USABLE
