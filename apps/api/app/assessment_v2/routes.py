"""Typed HTTP routes for the additive assessment v2 foundation slice."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    AttestTranscriptSegmentSet,
    AttestTranscript,
    CreateChild,
    CreateRecording,
    CreateTranscriptRevision,
    CreateTranscriptSegmentSet,
    RecordConsent,
    RecordingQualityStatus,
    StartAssessment,
    TransitionAssessment,
)
from app.assessment_v2.domain.segments import TranscriptSegment
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
    EvidenceProcessingResponse,
    EvidenceProfileResponse,
    EvidenceProvenanceResponse,
    MeasuredFeatureResponse,
    ProcessingRunResponse,
    ProcessingRunActionRequest,
    ProtocolActivityResponse,
    ProtocolSelectionRequest,
    ProtocolSelectionResponse,
    RecordingCreateRequest,
    RecordingIntentResponse,
    RecordingQualityResponse,
    RecordingResponse,
    TranscriptAttestRequest,
    TranscriptSegmentReplayGrantResponse,
    TranscriptSegmentResponse,
    TranscriptSegmentSetCreateRequest,
    TranscriptSegmentSetResponse,
    TranscriptRevisionCreateRequest,
    TranscriptRevisionResponse,
    UploadGrantResponse,
    UploadIntentResponse,
    ComparisonCreateRequest,
    FeatureComparisonItemResponse,
    ComparisonResponse,
    ChildAssessmentHistoryItemResponse,
    AttentionCueReviewRequest,
    AttentionCueResponse,
    ClinicalDispositionRequest,
    ClinicalReviewResponse,
    FollowUpPlanSchema,
    ReportDraftCreateRequest,
    ReportDraftUpdateRequest,
    ReportSignOffRequest,
    ReportAmendmentCreateRequest,
    ReportResponse,
    ReportExportResponse,
)
from app.assessment_v2.clinical_review import (
    AttentionCue,
    ClinicalReviewSession,
    FollowUpPlan,
)
from app.assessment_v2.db.models import (
    AssessmentComparisonRecord,
    AssessmentReportRecord,
)
from app.assessment_v2.reports import ReportStatus
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
        max_attempts=value.max_attempts,
        available_at=value.available_at,
        error_code=value.error_code,
        result_available=value.result_available,
        can_retry=value.can_retry,
        can_cancel=value.can_cancel,
        version=value.version,
    )


def _evidence_processing_response(value) -> EvidenceProcessingResponse:
    return EvidenceProcessingResponse(processing_run=_processing_run_response(value))


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


def _transcript_segment_response(value) -> TranscriptSegmentResponse:
    return TranscriptSegmentResponse(
        id=value.id,
        ordinal=value.ordinal,
        start_ms=value.start_ms,
        end_ms=value.end_ms,
        speaker_role=value.speaker_role,
        text=value.text,
        confidence=value.confidence,
        uncertainty_reason=value.uncertainty_reason,
        created_at=value.created_at,
    )


def _transcript_segment_set_response(value) -> TranscriptSegmentSetResponse:
    return TranscriptSegmentSetResponse(
        id=value.id,
        assessment_id=value.assessment_id,
        transcript_revision_id=value.transcript_revision_id,
        transcript_content_sha256=value.transcript_content_sha256,
        recording_id=value.recording_id,
        revision=value.revision,
        source=value.source,
        review_state=value.review_state,
        segments_sha256=value.segments_sha256,
        segments=[_transcript_segment_response(segment) for segment in value.segments],
        created_at=value.created_at,
        attested_at=value.attested_at,
        version=value.version,
    )


def _transcript_segment_replay_response(value) -> TranscriptSegmentReplayGrantResponse:
    return TranscriptSegmentReplayGrantResponse(
        segment_id=value.segment_id,
        start_ms=value.start_ms,
        end_ms=value.end_ms,
        available=value.available,
        url=value.url,
        expires_at=value.expires_at,
        expires_in_seconds=value.expires_in_seconds,
    )


def _evidence_response(value) -> EvidenceProfileResponse:
    profile = value.profile
    return EvidenceProfileResponse(
        evidence_run_id=value.id,
        assessment_id=value.assessment_id,
        transcript_revision_id=value.transcript_revision_id,
        segment_set_id=value.segment_set_id,
        segment_set_sha256=value.segment_set_sha256,
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
    response_model=EvidenceProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_V2_ERROR_RESPONSES,
)
def create_current_evidence(
    assessment_id: str,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> EvidenceProcessingResponse:
    return _evidence_processing_response(
        service.enqueue_current_evidence_processing(assessment_id, _correlation_id(request))
    )


@router.get(
    "/assessments/{assessment_id}/evidence-processing-run",
    response_model=EvidenceProcessingResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_current_evidence_processing_run(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> EvidenceProcessingResponse:
    return _evidence_processing_response(
        service.get_current_evidence_processing_run(assessment_id)
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
    "/assessments/{assessment_id}/transcript-segment-set",
    response_model=TranscriptSegmentSetResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_current_transcript_segment_set(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptSegmentSetResponse:
    return _transcript_segment_set_response(
        service.get_current_transcript_segment_set(assessment_id)
    )


@router.post(
    "/assessments/{assessment_id}/transcript-segment-sets",
    response_model=TranscriptSegmentSetResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_transcript_segment_set(
    assessment_id: str,
    payload: TranscriptSegmentSetCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptSegmentSetResponse:
    value = service.create_transcript_segment_set(
        assessment_id,
        CreateTranscriptSegmentSet(
            assessment_id=assessment_id,
            transcript_revision_id=payload.transcript_revision_id,
            segments=tuple(
                TranscriptSegment(
                    ordinal=segment.ordinal,
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                    speaker_role=segment.speaker_role,
                    text=segment.text,
                    confidence=segment.confidence,
                    uncertainty_reason=segment.uncertainty_reason,
                )
                for segment in payload.segments
            ),
            source=payload.source,
            recording_id=payload.recording_id,
            expected_revision=payload.expected_revision,
            expected_version=payload.expected_version,
            client_checksum=payload.client_checksum,
        ),
        _correlation_id(request),
    )
    return _transcript_segment_set_response(value)


@router.post(
    "/transcript-segment-sets/{transcript_segment_set_id}/attest",
    response_model=TranscriptSegmentSetResponse,
    responses=_V2_ERROR_RESPONSES,
)
def attest_transcript_segment_set(
    transcript_segment_set_id: str,
    payload: TranscriptAttestRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptSegmentSetResponse:
    value = service.attest_transcript_segment_set(
        transcript_segment_set_id,
        AttestTranscriptSegmentSet(
            transcript_segment_set_id=transcript_segment_set_id,
            expected_version=payload.expected_version,
        ),
        _correlation_id(request),
    )
    return _transcript_segment_set_response(value)


@router.post(
    "/transcript-segments/{transcript_segment_id}/audio-replay-grant",
    response_model=TranscriptSegmentReplayGrantResponse,
    responses=_V2_ERROR_RESPONSES,
)
def create_transcript_segment_audio_replay_grant(
    transcript_segment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> TranscriptSegmentReplayGrantResponse:
    return _transcript_segment_replay_response(
        service.create_transcript_segment_audio_replay_grant(transcript_segment_id)
    )


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


@router.post(
    "/processing-runs/{processing_run_id}/retry",
    response_model=ProcessingRunResponse,
    responses=_V2_ERROR_RESPONSES,
)
def retry_processing_run(
    processing_run_id: str,
    payload: ProcessingRunActionRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ProcessingRunResponse:
    return _processing_run_response(
        service.retry_processing_run(
            processing_run_id,
            payload.expected_version,
            _correlation_id(request),
        )
    )


@router.post(
    "/processing-runs/{processing_run_id}/cancel",
    response_model=ProcessingRunResponse,
    responses=_V2_ERROR_RESPONSES,
)
def cancel_processing_run(
    processing_run_id: str,
    payload: ProcessingRunActionRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ProcessingRunResponse:
    return _processing_run_response(
        service.cancel_processing_run(
            processing_run_id,
            payload.expected_version,
            _correlation_id(request),
        )
    )


def _comparison_response(record: AssessmentComparisonRecord) -> ComparisonResponse:
    features = [
        FeatureComparisonItemResponse(
            feature_key=f.feature_key,
            unit=f.unit,
            status=f.status,
            incompatibility_reasons=f.incompatibility_reasons_json or [],
            baseline_value=f.baseline_value,
            current_value=f.current_value,
            absolute_delta=f.absolute_delta,
            percent_change=f.percent_change,
            percent_change_limitation=f.percent_change_limitation,
            numerical_trend=f.numerical_trend,
            clinical_interpretation=f.clinical_interpretation,
        )
        for f in getattr(record, "features", [])
    ]
    return ComparisonResponse(
        comparison_id=record.comparison_id,
        baseline_assessment_id=record.baseline_assessment_id,
        current_assessment_id=record.current_assessment_id,
        baseline_evidence_run_id=record.baseline_evidence_run_id,
        current_evidence_run_id=record.current_evidence_run_id,
        baseline_evidence_sha256=record.baseline_evidence_sha256,
        current_evidence_sha256=record.current_evidence_sha256,
        policy_version=record.policy_version,
        status=record.status,
        is_stale=record.is_stale,
        created_at=record.created_at,
        features=features,
    )


@router.post(
    "/assessments/{assessment_id}/comparisons",
    response_model=ComparisonResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_assessment_comparison(
    assessment_id: str,
    payload: ComparisonCreateRequest,
    request: Request,
    service: AssessmentService = Depends(get_assessment_service),
) -> ComparisonResponse:
    record = service.compare_assessments(
        assessment_id=assessment_id,
        baseline_assessment_id=payload.baseline_assessment_id,
        policy_version=payload.policy_version,
        correlation_id=_correlation_id(request),
    )
    return _comparison_response(record)


@router.get(
    "/assessments/{assessment_id}/comparisons",
    response_model=list[ComparisonResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_assessment_comparisons(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ComparisonResponse]:
    records = service.list_assessment_comparisons(assessment_id)
    return [_comparison_response(r) for r in records]


@router.get(
    "/assessments/{assessment_id}/comparisons/{comparison_id}",
    response_model=ComparisonResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_assessment_comparison(
    assessment_id: str,
    comparison_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ComparisonResponse:
    record = service.get_assessment_comparison(assessment_id, comparison_id)
    return _comparison_response(record)


@router.get(
    "/children/{child_id}/assessments/history",
    response_model=list[ChildAssessmentHistoryItemResponse],
    responses=_V2_ERROR_RESPONSES,
)
def list_child_assessment_history(
    child_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ChildAssessmentHistoryItemResponse]:
    items = service.list_child_assessment_history(child_id)
    return [
        ChildAssessmentHistoryItemResponse(
            assessment_id=item["assessment_id"],
            created_at=item["created_at"],
            purpose=item["purpose"],
            state=item["state"],
            age_months=item["age_months"],
            protocol_version_key=item.get("protocol_version_key"),
            language=item.get("language", "th"),
            evidence_run_id=item.get("evidence_run_id"),
            is_comparable=item["is_comparable"],
        )
        for item in items
    ]


def _cue_response(cue: AttentionCue) -> AttentionCueResponse:
    return AttentionCueResponse(
        cue_id=cue.cue_id,
        cue_type=cue.cue_type,
        title=cue.title,
        description=cue.description,
        policy_version=cue.policy_version,
        evidence_run_id=cue.evidence_run_id,
        supporting_feature_keys=cue.supporting_feature_keys,
        conflicting_feature_keys=cue.conflicting_feature_keys,
        limitations=cue.limitations,
        status=cue.status,
        reviewer_id=cue.clinician_feedback.reviewer_id if cue.clinician_feedback else None,
        reviewed_at=cue.clinician_feedback.reviewed_at if cue.clinician_feedback else None,
        rationale=cue.clinician_feedback.rationale if cue.clinician_feedback else None,
    )


def _clinical_review_response(session: ClinicalReviewSession) -> ClinicalReviewResponse:
    fp = None
    if session.follow_up:
        fp = FollowUpPlanSchema(
            target_date=session.follow_up.target_date,
            recommended_protocol=session.follow_up.recommended_protocol,
            focus_areas=session.follow_up.focus_areas,
            monitoring_notes=session.follow_up.monitoring_notes,
        )
    return ClinicalReviewResponse(
        review_id=session.review_id,
        assessment_id=session.assessment_id,
        child_id=session.child_id,
        evidence_run_id=session.evidence_run_id,
        version=session.version,
        status="completed" if session.disposition else "in_progress",
        cues=[_cue_response(c) for c in session.cues],
        disposition=session.disposition,
        disposition_notes=session.disposition_notes,
        follow_up_plan=fp,
        reviewed_by=session.reviewed_by,
        reviewed_at=session.reviewed_at,
        is_stale=session.is_stale,
    )


def _report_response(rec: AssessmentReportRecord) -> ReportResponse:
    return ReportResponse(
        report_id=rec.report_id,
        assessment_id=rec.assessment_id,
        child_id=rec.child_id,
        evidence_run_id=rec.evidence_run_id,
        comparison_id=rec.comparison_id,
        review_id=rec.review_id,
        amends_report_id=rec.amends_report_id,
        amendment_sequence=rec.amendment_sequence,
        version=rec.version,
        status=ReportStatus(rec.status),
        title=rec.title,
        purpose=rec.purpose,
        content_markdown=rec.content_markdown,
        limitations=list(rec.limitations_json or []),
        signed_by=rec.signed_by,
        signed_at=rec.signed_at,
        signed_snapshot_hash=rec.signed_snapshot_hash,
        is_stale=rec.is_stale,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


@router.get(
    "/assessments/{assessment_id}/clinical-review",
    response_model=ClinicalReviewResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_or_create_clinical_review(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ClinicalReviewResponse:
    session = service.get_or_create_clinical_review(assessment_id)
    return _clinical_review_response(session)


@router.post(
    "/assessments/{assessment_id}/clinical-review/cues/{cue_id}",
    response_model=AttentionCueResponse,
    responses=_V2_ERROR_RESPONSES,
)
def review_attention_cue(
    assessment_id: str,
    cue_id: str,
    payload: AttentionCueReviewRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> AttentionCueResponse:
    cue = service.review_attention_cue(
        assessment_id=assessment_id,
        cue_id=cue_id,
        status=payload.status,
        rationale=payload.rationale,
    )
    return _cue_response(cue)


@router.put(
    "/assessments/{assessment_id}/clinical-review/disposition",
    response_model=ClinicalReviewResponse,
    responses=_V2_ERROR_RESPONSES,
)
def update_clinical_disposition(
    assessment_id: str,
    payload: ClinicalDispositionRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> ClinicalReviewResponse:
    follow_up = None
    if payload.follow_up_plan:
        follow_up = FollowUpPlan(
            target_date=payload.follow_up_plan.target_date,
            recommended_protocol=payload.follow_up_plan.recommended_protocol,
            focus_areas=payload.follow_up_plan.focus_areas,
            monitoring_notes=payload.follow_up_plan.monitoring_notes,
        )
    session = service.update_clinical_disposition(
        assessment_id=assessment_id,
        disposition=payload.disposition,
        disposition_notes=payload.disposition_notes,
        follow_up=follow_up,
        expected_version=payload.expected_version,
    )
    return _clinical_review_response(session)


@router.post(
    "/assessments/{assessment_id}/reports/draft",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_report_draft(
    assessment_id: str,
    payload: ReportDraftCreateRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.create_report_draft(
        assessment_id=assessment_id,
        purpose=payload.purpose,
        comparison_id=payload.comparison_id,
    )
    return _report_response(rec)


@router.get(
    "/assessments/{assessment_id}/reports/current",
    response_model=ReportResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_current_report(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.get_current_report(assessment_id)
    return _report_response(rec)


@router.get(
    "/assessments/{assessment_id}/reports/{report_id}",
    response_model=ReportResponse,
    responses=_V2_ERROR_RESPONSES,
)
def get_report(
    assessment_id: str,
    report_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.get_report(assessment_id, report_id)
    return _report_response(rec)


@router.put(
    "/assessments/{assessment_id}/reports/{report_id}",
    response_model=ReportResponse,
    responses=_V2_ERROR_RESPONSES,
)
def update_report_draft(
    assessment_id: str,
    report_id: str,
    payload: ReportDraftUpdateRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.update_report_draft(
        assessment_id=assessment_id,
        report_id=report_id,
        title=payload.title,
        purpose=payload.purpose,
        content_markdown=payload.content_markdown,
        limitations=payload.limitations,
        expected_version=payload.expected_version,
    )
    return _report_response(rec)


@router.post(
    "/assessments/{assessment_id}/reports/{report_id}/sign",
    response_model=ReportResponse,
    responses=_V2_ERROR_RESPONSES,
)
def sign_off_report(
    assessment_id: str,
    report_id: str,
    payload: ReportSignOffRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.sign_off_report(
        assessment_id=assessment_id,
        report_id=report_id,
        expected_version=payload.expected_version,
    )
    return _report_response(rec)


@router.post(
    "/assessments/{assessment_id}/reports/{report_id}/amend",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_V2_ERROR_RESPONSES,
)
def create_report_amendment(
    assessment_id: str,
    report_id: str,
    payload: ReportAmendmentCreateRequest,
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportResponse:
    rec = service.create_report_amendment(
        assessment_id=assessment_id,
        report_id=report_id,
        title=payload.title,
        purpose=payload.purpose,
        content_markdown=payload.content_markdown,
    )
    return _report_response(rec)


@router.get(
    "/assessments/{assessment_id}/reports/{report_id}/export",
    response_model=ReportExportResponse,
    responses=_V2_ERROR_RESPONSES,
)
def export_report(
    assessment_id: str,
    report_id: str,
    format: str = "markdown",
    service: AssessmentService = Depends(get_assessment_service),
) -> ReportExportResponse:
    exp = service.export_report(
        assessment_id=assessment_id,
        report_id=report_id,
        export_format=format,
    )
    return ReportExportResponse(
        report_id=exp["report_id"],
        format=exp["format"],
        content_type=exp["content_type"],
        filename=exp["filename"],
        content=exp.get("content"),
        base64_content=exp.get("base64_content"),
        report_hash=exp.get("report_hash"),
        signed_by=exp.get("signed_by"),
        export_timestamp=exp["export_timestamp"],
    )


@router.get(
    "/assessments/{assessment_id}/reports/{report_id}/history",
    response_model=list[ReportResponse],
    responses=_V2_ERROR_RESPONSES,
)
def get_report_lineage(
    assessment_id: str,
    report_id: str,
    service: AssessmentService = Depends(get_assessment_service),
) -> list[ReportResponse]:
    records = service.get_report_lineage(assessment_id, report_id)
    return [_report_response(r) for r in records]

