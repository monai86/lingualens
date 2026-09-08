"""Typed HTTP routes for the additive assessment v2 foundation slice."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    AttestTranscript,
    CreateChild,
    CreateRecording,
    CreateTranscriptRevision,
    RecordConsent,
    RecordingQualityStatus,
    StartAssessment,
    TransitionAssessment,
)
from app.assessment_v2.schemas import (
    AssessmentCreateRequest,
    AssessmentResponse,
    AssessmentTransitionRequest,
    CaptureProgressResponse,
    CaptureResponse,
    CaptureStateResponse,
    ChildCreateRequest,
    ChildResponse,
    ConsentCreateRequest,
    ConsentResponse,
    CompleteUploadResponse,
    DeleteRecordingResponse,
    DownloadGrantResponse,
    DownloadIntentResponse,
    DomainProfileResponse,
    ErrorEnvelope,
    EvidenceProfileResponse,
    EvidenceProvenanceResponse,
    MeasuredFeatureResponse,
    ProcessingRunResponse,
    ProtocolActivityResponse,
    ProtocolSelectionRequest,
    ProtocolSelectionResponse,
    RecordingCreateRequest,
    RecordingIntentResponse,
    RecordingQualityResponse,
    RecordingResponse,
    TranscriptAttestRequest,
    TranscriptRevisionCreateRequest,
    TranscriptRevisionResponse,
    UploadGrantResponse,
    UploadIntentResponse,
)
from app.assessment_v2.services import AssessmentService


_V2_ERROR_RESPONSES = {
    400: {"model": ErrorEnvelope},
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    405: {"model": ErrorEnvelope},
    409: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    429: {"model": ErrorEnvelope},
    500: {"model": ErrorEnvelope},
    503: {"model": ErrorEnvelope},
}

router = APIRouter(tags=["assessment-v2"])


def _correlation_id(request: Request) -> str:
    return request.state.request_id


def _child_response(value) -> ChildResponse:
    return ChildResponse(
        id=value.id,
        display_code=value.display_code,
        birth_year=value.birth_year,
        birth_month=value.birth_month,
        language_context=value.language_context,
        version=value.version,
    )


def _consent_response(value) -> ConsentResponse:
    return ConsentResponse(
        id=value.id,
        child_id=value.child_id,
        purpose=value.purpose,
        scope_version=value.scope_version,
        status=value.status,
        granted_at=value.granted_at,
        withdrawn_at=value.withdrawn_at,
        version=value.version,
    )


def _assessment_response(value) -> AssessmentResponse:
    return AssessmentResponse(
        id=value.id,
        child_id=value.child_id,
        purpose=value.purpose,
        state=value.state,
        age_months=value.age_months,
        language_context=value.language_context,
        assigned_clinician_id=value.assigned_clinician_id,
        version=value.version,
    )


def _recording_response(value) -> RecordingResponse:
    return RecordingResponse(
        id=value.id,
        activity_code=value.activity_code,
        content_type=value.declared_content_type,
        size_bytes=value.declared_size_bytes,
        upload_state=value.upload_state,
        expires_at=value.expires_at,
        verified_at=value.verified_at,
        version=value.version,
    )


def _processing_run_response(value) -> ProcessingRunResponse:
    return ProcessingRunResponse(
        id=value.id,
        stage=value.stage,
        state=value.state,
        attempt_count=value.attempt_count,
        error_code=value.error_code,
    )


def _capture_response(value) -> CaptureResponse:
    quality_by_recording = {quality.recording_id: quality for quality in value.quality_results}
    activities = [
        ProtocolActivityResponse(
            activity_code=activity.activity_key,
            required=activity.required,
            target_duration_seconds=activity.target_duration_seconds,
            minimum_duration_seconds=activity.minimum_duration_seconds,
        )
        for activity in value.activities
    ]
    required_activities = [activity for activity in value.activities if activity.required]
    verified_activity_codes = {
        recording.activity_code
        for recording in value.recordings
        if recording.upload_state.value == "verified"
    }
    usable_activity_codes = {
        recording.activity_code
        for recording in value.recordings
        if recording.upload_state.value == "verified"
        and quality_by_recording.get(recording.id) is not None
        and quality_by_recording[recording.id].status is RecordingQualityStatus.USABLE
    }
    protocol = value.protocol_selection
    return CaptureResponse(
        assessment_id=value.assessment.id,
        state=value.assessment.state,
        protocol=(
            ProtocolSelectionResponse(
                protocol_version_key=protocol.protocol_version_key,
                selected_at=protocol.selected_at,
                version=protocol.version,
            )
            if protocol is not None
            else None
        ),
        activities=activities,
        recordings=[_recording_response(recording) for recording in value.recordings],
        progress=CaptureProgressResponse(
            required_activities_total=len(required_activities),
            required_activities_verified=sum(
                activity.activity_key in verified_activity_codes for activity in required_activities
            ),
            required_activities_usable=sum(
                activity.activity_key in usable_activity_codes for activity in required_activities
            ),
        ),
    )


def _quality_response(value) -> RecordingQualityResponse:
    return RecordingQualityResponse(
        status=value.status,
        evaluated_at=value.evaluated_at,
        version=value.version,
    )


def _transcript_response(value) -> TranscriptRevisionResponse:
    return TranscriptRevisionResponse(
        id=value.id,
        assessment_id=value.assessment_id,
        revision=value.revision,
        source=value.source,
        review_state=value.review_state,
        content=value.content,
        content_sha256=value.content_sha256,
        created_at=value.created_at,
        attested_at=value.attested_at,
        version=value.version,
    )


def _evidence_response(value) -> EvidenceProfileResponse:
    profile = value.profile
    return EvidenceProfileResponse(
        evidence_run_id=value.id,
        assessment_id=value.assessment_id,
        transcript_revision_id=value.transcript_revision_id,
        state=value.state,
        generated_at=profile.generated_at,
        provenance=EvidenceProvenanceResponse(**value.provenance.to_dict()),
        features=[
            MeasuredFeatureResponse(
                key=feature.key,
                value=feature.value,
                unit=feature.unit,
                source=feature.source,
                state=feature.state,
                limitation=feature.limitation,
                provenance=EvidenceProvenanceResponse(**feature.provenance.to_dict()),
            )
            for feature in profile.features
        ],
        domains=[
            DomainProfileResponse(
                domain=domain.domain,
                status=domain.status,
                summary=domain.summary,
                feature_keys=list(domain.feature_keys),
                supporting_features=list(domain.supporting_features),
                conflicting_features=list(domain.conflicting_features),
                limitations=list(domain.limitations),
            )
            for domain in profile.domains
        ],
        limitations=list(profile.limitations),
        not_diagnostic=profile.not_diagnostic,
        decision_support_only=profile.decision_support_only,
        version=value.version,
    )


@router.post(
    "/children",
    response_model=ChildResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_child(
    payload: ChildCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ChildResponse:
    value = service.create_child(
        CreateChild(
            display_code=payload.display_code,
            birth_year=payload.birth_year,
            birth_month=payload.birth_month,
            language_context=payload.language_context,
        ),
        _correlation_id(request),
    )
    return _child_response(value)


@router.get(
    "/children",
    response_model=list[ChildResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_children(
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ChildResponse]:
    return [_child_response(value) for value in service.list_children()]


@router.get(
    "/children/{child_id}",
    response_model=ChildResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_child(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ChildResponse:
    return _child_response(service.get_child(child_id))


@router.post(
    "/children/{child_id}/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_consent(
    child_id: str,
    payload: ConsentCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ConsentResponse:
    value = service.grant_consent(
        child_id,
        RecordConsent(
            purpose=payload.purpose,
            scope_version=payload.scope_version,
            status=payload.status,
        ),
        _correlation_id(request),
    )
    return _consent_response(value)


@router.get(
    "/children/{child_id}/consents",
    response_model=list[ConsentResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_consents(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ConsentResponse]:
    return [_consent_response(value) for value in service.list_consents(child_id)]


@router.post(
    "/children/{child_id}/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_assessment(
    child_id: str,
    payload: AssessmentCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    value = service.create_assessment(
        child_id,
        StartAssessment(
            purpose=payload.purpose,
            assigned_clinician_id=payload.assigned_clinician_id,
        ),
        _correlation_id(request),
    )
    return _assessment_response(value)


@router.get(
    "/children/{child_id}/assessments",
    response_model=list[AssessmentResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_assessments(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[AssessmentResponse]:
    return [_assessment_response(value) for value in service.list_assessments(child_id)]


@router.get(
    "/assessments/{assessment_id}/transcript",
    response_model=TranscriptRevisionResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_current_transcript(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptRevisionResponse:
    return _transcript_response(service.get_current_transcript(assessment_id))


@router.get(
    "/assessments/{assessment_id}/evidence",
    response_model=EvidenceProfileResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_current_evidence(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> EvidenceProfileResponse:
    return _evidence_response(service.get_current_evidence(assessment_id))


@router.post(
    "/assessments/{assessment_id}/evidence-runs",
    response_model=EvidenceProfileResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_current_evidence(
    assessment_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> EvidenceProfileResponse:
    return _evidence_response(
        service.create_current_evidence_run(assessment_id, _correlation_id(request))
    )


@router.post(
    "/assessments/{assessment_id}/transcript-revisions",
    response_model=TranscriptRevisionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_transcript_revision(
    assessment_id: str,
    payload: TranscriptRevisionCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptRevisionResponse:
    value = service.create_transcript_revision(
        assessment_id,
        CreateTranscriptRevision(
            assessment_id=assessment_id,
            content=payload.content,
            source=payload.source,
            expected_revision=payload.expected_revision,
            expected_version=payload.expected_version,
        ),
        _correlation_id(request),
    )
    return _transcript_response(value)


@router.post(
    "/transcript-revisions/{transcript_revision_id}/attest",
    response_model=TranscriptRevisionResponse,
    responses=_V2_ERROR_RESPONSES,
)
def attest_transcript(
    transcript_revision_id: str,
    payload: TranscriptAttestRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptRevisionResponse:
    value = service.attest_transcript(
        transcript_revision_id,
        AttestTranscript(
            transcript_revision_id=transcript_revision_id,
            expected_version=payload.expected_version,
        ),
        _correlation_id(request),
    )
    return _transcript_response(value)


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_assessment(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    return _assessment_response(service.get_assessment(assessment_id))


@router.post(
    "/assessments/{assessment_id}/transitions",
    response_model=AssessmentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def transition_assessment(
    assessment_id: str,
    payload: AssessmentTransitionRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentResponse:
    value = service.transition_assessment(
        assessment_id,
        TransitionAssessment(
            assessment_id=assessment_id,
            target_state=payload.target_state,
            expected_version=payload.expected_version,
        ),
        _correlation_id(request),
    )
    return _assessment_response(value)


@router.post(
    "/assessments/{assessment_id}/protocol-selection",
    response_model=CaptureResponse,
    responses=_V2_ERROR_RESPONSES,
)
def select_capture_protocol(
    assessment_id: str,
    payload: ProtocolSelectionRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> CaptureResponse:
    del payload
    return _capture_response(service.select_protocol(assessment_id, _correlation_id(request)))


@router.get(
    "/assessments/{assessment_id}/capture",
    response_model=CaptureResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_capture(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> CaptureResponse:
    return _capture_response(service.get_capture(assessment_id))


@router.post(
    "/assessments/{assessment_id}/capture/start",
    response_model=CaptureStateResponse,
    responses=_V2_ERROR_RESPONSES,
)
def start_capture(
    assessment_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> CaptureStateResponse:
    value = service.start_capture(assessment_id, _correlation_id(request))
    return CaptureStateResponse(
        assessment_id=value.id,
        state=value.state,
        version=value.version,
    )


@router.post(
    "/assessments/{assessment_id}/activities/{activity_code}/recordings",
    response_model=RecordingIntentResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_recording(
    assessment_id: str,
    activity_code: str,
    payload: RecordingCreateRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=r".*\S.*",
        ),
    ],
    service: AssessmentService = Depends(get_assessment_service),
) -> RecordingIntentResponse:
    value = service.create_recording(
        CreateRecording(
            assessment_id=assessment_id,
            activity_code=activity_code,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            checksum=payload.checksum,
            idempotency_key=idempotency_key.strip(),
        ),
        _correlation_id(request),
    )
    return RecordingIntentResponse(
        recording=_recording_response(value.recording),
        processing_run=_processing_run_response(value.processing_run),
    )


@router.post(
    "/recordings/{recording_id}/upload-intent",
    response_model=UploadIntentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def create_upload_intent(
    recording_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> UploadIntentResponse:
    recording, grant = service.create_upload_intent(recording_id, _correlation_id(request))
    return UploadIntentResponse(
        recording=_recording_response(recording),
        upload=UploadGrantResponse(
            url=grant.url,
            expires_at=grant.expires_at,
            expires_in_seconds=grant.expires_in_seconds,
            chunk_size_bytes=grant.chunk_size_bytes,
            upload_length_bytes=grant.upload_length_bytes,
            content_type=grant.content_type,
            upsert=grant.upsert,
        ),
    )


@router.post(
    "/recordings/{recording_id}/complete-upload",
    response_model=CompleteUploadResponse,
    responses=_V2_ERROR_RESPONSES,
)
def complete_upload(
    recording_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> CompleteUploadResponse:
    value = service.complete_upload(recording_id, _correlation_id(request))
    return CompleteUploadResponse(
        recording=_recording_response(value.recording),
        processing_run=_processing_run_response(value.processing_run),
    )


@router.get(
    "/recordings/{recording_id}",
    response_model=RecordingResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_recording(
    recording_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> RecordingResponse:
    return _recording_response(service.get_recording(recording_id))


@router.get(
    "/recordings/{recording_id}/quality",
    response_model=RecordingQualityResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_recording_quality(
    recording_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> RecordingQualityResponse:
    return _quality_response(service.get_recording_quality(recording_id))


@router.post(
    "/recordings/{recording_id}/download-intent",
    response_model=DownloadIntentResponse,
    responses=_V2_ERROR_RESPONSES,
)
def create_download_intent(
    recording_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> DownloadIntentResponse:
    recording, grant = service.download_intent(recording_id)
    return DownloadIntentResponse(
        recording=_recording_response(recording),
        download=DownloadGrantResponse(
            url=grant.url,
            expires_at=grant.expires_at,
            expires_in_seconds=grant.expires_in_seconds,
        ),
    )


@router.delete(
    "/recordings/{recording_id}",
    response_model=DeleteRecordingResponse,
    responses=_V2_ERROR_RESPONSES,
)
def delete_recording(
    recording_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> DeleteRecordingResponse:
    return DeleteRecordingResponse(
        id=recording_id,
        deleted=service.delete_recording(recording_id, _correlation_id(request)),
    )


@router.post(
    "/assessments/{assessment_id}/capture/complete",
    response_model=CaptureStateResponse,
    responses=_V2_ERROR_RESPONSES,
)
def complete_capture(
    assessment_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> CaptureStateResponse:
    value = service.complete_capture(assessment_id, _correlation_id(request))
    return CaptureStateResponse(
        assessment_id=value.id,
        state=value.state,
        version=value.version,
    )


@router.get(
    "/processing-runs/{processing_run_id}",
    response_model=ProcessingRunResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_processing_run(
    processing_run_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ProcessingRunResponse:
    return _processing_run_response(service.get_processing_run(processing_run_id))
