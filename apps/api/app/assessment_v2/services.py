"""Clinical policy boundary for the assessment v2 persistence layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Protocol, TypeVar

from app.assessment_v2.db.repositories import RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AttestTranscript,
    AssessmentSnapshot,
    AssessmentState,
    CaptureSnapshot,
    ChildSnapshot,
    CompleteCapture,
    CompleteRecordingUpload,
    ConsentPurpose,
    CreateRecording,
    CreateAssessment,
    CreateChild,
    CreateTranscriptRevision,
    CreateTranscriptSegmentSet,
    AttestTranscriptSegmentSet,
    MarkRecordingUploading,
    RecordConsent,
    ProcessingRunSnapshot,
    RecordingQualitySnapshot,
    RecordingIntentSnapshot,
    RecordingSnapshot,
    RecordingUploadState,
    SelectProtocol,
    StartCapture,
    StartAssessment,
    TransitionAssessment,
    TranscriptRevisionSnapshot,
    VerifyRecordingUpload,
)
from app.assessment_v2.evidence import EvidenceRunSnapshot, EvidenceState
from app.assessment_v2.evidence_adapter import AdaptedEvidence
from app.assessment_v2.longitudinal import compare_evidence_runs
from app.assessment_v2.db.longitudinal_repository import LongitudinalRepository
from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    ClinicalReviewSession,
    CueStatus,
    FollowUpPlan,
    evaluate_attention_cues,
)
from app.assessment_v2.db.clinical_review_repository import ClinicalReviewRepository
from app.assessment_v2.reports import (
    ReportReadiness,
    ReportStatus,
    build_signed_report_snapshot,
    check_report_signoff_readiness,
    generate_report_draft_markdown,
    render_assessment_v2_pdf,
)
from app.assessment_v2.db.reports_repository import ReportsRepository
from app.assessment_v2.db.models import (
    AssessmentComparisonRecord,
    AssessmentClinicalReviewRecord,
    AssessmentAttentionCueRecord,
    AssessmentReportRecord,
)
from app.assessment_v2.domain.segments import (
    SegmentAudioReplayGrant,
    TranscriptSegmentSnapshot,
    TranscriptSegmentSetSnapshot,
)
from app.assessment_v2.protocols import ProtocolUnavailableError, select_protocol
from app.assessment_v2.storage import (
    CaptureStorageAdapter,
    SignedDownloadGrant,
    SignedUploadGrant,
    StorageInputError,
    StorageUnavailableError,
)
from app.core.security import CurrentUser


class AssessmentRepository(Protocol):
    def create_child(self, scope: AccessScope, command: CreateChild, correlation_id: str) -> ChildSnapshot: ...

    def get_child(self, scope: AccessScope, child_id: str) -> ChildSnapshot | None: ...

    def list_children(self, scope: AccessScope) -> list[ChildSnapshot]: ...

    def add_consent(
        self, scope: AccessScope, child_id: str, command: RecordConsent, correlation_id: str
    ): ...

    def list_consents(self, scope: AccessScope, child_id: str) -> list[ConsentSnapshot]: ...

    def has_active_consent(self, scope: AccessScope, child_id: str, purpose: ConsentPurpose) -> bool: ...

    def can_assign_clinician(self, scope: AccessScope, child_id: str, clinician_id: str) -> bool: ...

    def create_assessment_if_consented(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot: ...

    def create_assessment(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot: ...

    def get_assessment(self, scope: AccessScope, assessment_id: str) -> AssessmentSnapshot | None: ...

    def list_assessments(self, scope: AccessScope, child_id: str) -> list[AssessmentSnapshot]: ...

    def get_current_transcript(
        self, scope: AccessScope, assessment_id: str
    ) -> TranscriptRevisionSnapshot | None: ...

    def create_transcript_revision(
        self, scope: AccessScope, command: CreateTranscriptRevision, correlation_id: str
    ) -> TranscriptRevisionSnapshot: ...

    def attest_transcript(
        self, scope: AccessScope, command: AttestTranscript, correlation_id: str
    ) -> TranscriptRevisionSnapshot: ...

    def get_current_transcript_segment_set(
        self, scope: AccessScope, assessment_id: str
    ) -> TranscriptSegmentSetSnapshot | None: ...

    def create_transcript_segment_set(
        self,
        scope: AccessScope,
        command: CreateTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot: ...

    def attest_transcript_segment_set(
        self,
        scope: AccessScope,
        command: AttestTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot: ...

    def get_transcript_segment_replay_target(
        self,
        scope: AccessScope,
        transcript_segment_id: str,
    ) -> tuple[TranscriptSegmentSnapshot, RecordingSnapshot | None] | None: ...

    def get_current_evidence(
        self, scope: AccessScope, assessment_id: str
    ) -> EvidenceRunSnapshot | None: ...

    def create_evidence_run(
        self,
        scope: AccessScope,
        assessment_id: str,
        transcript_revision_id: str,
        adapted: AdaptedEvidence,
        correlation_id: str,
    ) -> EvidenceRunSnapshot: ...

    def transition_assessment(
        self, scope: AccessScope, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot: ...

    def select_protocol_and_ready(
        self, scope: AccessScope, command: SelectProtocol, correlation_id: str
    ) -> CaptureSnapshot: ...

    def get_recording_if_consented(
        self, scope: AccessScope, recording_id: str
    ) -> RecordingSnapshot | None: ...

    def get_recording_quality_if_consented(
        self, scope: AccessScope, recording_id: str
    ) -> RecordingQualitySnapshot | None: ...

    def get_processing_run_if_consented(
        self, scope: AccessScope, processing_run_id: str
    ) -> ProcessingRunSnapshot | None: ...

    def get_current_evidence_processing_run(
        self, scope: AccessScope, assessment_id: str
    ) -> ProcessingRunSnapshot | None: ...

    def enqueue_current_evidence_processing(
        self, scope: AccessScope, assessment_id: str, correlation_id: str
    ) -> ProcessingRunSnapshot: ...

    def retry_evidence_processing_run(
        self, scope: AccessScope, run_id: str, expected_version: int, correlation_id: str
    ) -> ProcessingRunSnapshot: ...

    def request_evidence_processing_cancellation(
        self, scope: AccessScope, run_id: str, expected_version: int, correlation_id: str
    ) -> ProcessingRunSnapshot: ...

    def mark_recording_deleted_if_consented(
        self,
        scope: AccessScope,
        recording_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> RecordingSnapshot | None: ...

    def expire_recording_upload_if_needed(
        self,
        scope: AccessScope,
        recording_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> RecordingSnapshot | None: ...

    def complete_cleanup_for_recording(self, scope: AccessScope, recording_id: str) -> None: ...

    def commit_transaction(self) -> None: ...

    def mark_recording_uploading_if_capture_active(
        self, scope: AccessScope, command: MarkRecordingUploading, correlation_id: str
    ) -> RecordingSnapshot: ...

    def complete_recording_upload_if_capture_active(
        self, scope: AccessScope, command: CompleteRecordingUpload, correlation_id: str
    ) -> RecordingIntentSnapshot: ...

    def verify_recording_upload(
        self, scope: AccessScope, command: VerifyRecordingUpload, correlation_id: str
    ) -> RecordingIntentSnapshot: ...

    def get_capture(self, scope: AccessScope, assessment_id: str) -> CaptureSnapshot | None: ...

    def start_capture_if_consented(
        self, scope: AccessScope, command: StartCapture, correlation_id: str
    ) -> AssessmentSnapshot: ...

    def create_recording_if_capture_active(
        self, scope: AccessScope, command: CreateRecording, correlation_id: str
    ) -> RecordingIntentSnapshot: ...

    def complete_capture_if_required_usable(
        self, scope: AccessScope, command: CompleteCapture, correlation_id: str
    ) -> AssessmentSnapshot: ...


class ClinicalPolicyError(Exception):
    """A safe, user-facing policy failure from the clinical service boundary."""

    def __init__(
        self,
        code: str,
        status_code: int,
        safe_message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.safe_message = safe_message
        self.details = dict(details) if details is not None else {}
        super().__init__(safe_message)


_CLINICAL_ROLES = frozenset({"therapist", "clinical_supervisor", "org_admin"})
_CLINICAL_MUTATION_ROLES = frozenset({"therapist", "clinical_supervisor"})
_OVERSIGHT_ROLES = frozenset({"clinical_supervisor"})
_TRANSCRIPT_EDITOR_ROLES = frozenset({"therapist", "clinical_supervisor"})
_EVIDENCE_RUN_ROLES = frozenset({"therapist", "clinical_supervisor"})
_TRANSCRIPT_ATTESTATION_ROLES = frozenset({"therapist"})
_MAX_ASSESSMENT_AGE_MONTHS = 216
_POLICY_MESSAGES: dict[str, tuple[int, str]] = {
    "inactive_membership": (403, "Active organization membership is required."),
    "role_not_permitted": (403, "This role is not permitted for the clinical workflow."),
    "child_not_found": (404, "Child was not found."),
    "assessment_not_found": (404, "Assessment was not found."),
    "active_consent_required": (409, "Active clinical-assessment consent is required."),
    "clinician_assignment_not_permitted": (403, "Clinician assignment is not permitted."),
    "age_out_of_range": (422, "Child age is outside the supported assessment range."),
    "workflow_stage_unavailable": (409, "This workflow stage is not yet available."),
    "stale_assessment_version": (409, "The assessment version is stale."),
    "invalid_assessment_transition": (409, "The assessment transition is not permitted."),
    "protocol_unavailable": (422, "A capture protocol is not available for this assessment."),
    "capture_not_ready": (409, "Capture is not ready to start."),
    "capture_not_active": (409, "Capture is not active."),
    "recording_activity_invalid": (422, "The recording activity is not available for this assessment."),
    "recording_not_found": (404, "Recording was not found."),
    "recording_not_verified": (409, "Recording upload has not been verified."),
    "upload_intent_expired": (409, "The upload intent has expired."),
    "upload_verification_failed": (409, "The upload could not be verified."),
    "capture_incomplete": (409, "Required capture activities are incomplete."),
    "required_activity_not_usable": (409, "A required recording is not usable."),
    "evidence_locked": (409, "Finalized evidence cannot be deleted."),
    "idempotency_conflict": (409, "The idempotency key was already used for a different request."),
    "consent_revoked": (409, "Active clinical-assessment consent is required."),
    "processing_run_not_found": (404, "Processing run was not found."),
    "processing_run_not_retryable": (409, "This processing run cannot be retried."),
    "processing_run_not_cancellable": (409, "This processing run cannot be cancelled."),
    "stale_processing_run_version": (409, "The processing run version is stale."),
    "transcript_not_found": (404, "Transcript was not found."),
    "transcript_not_reviewable": (409, "The transcript is not ready for this review action."),
    "stale_transcript_version": (409, "The transcript version is stale."),
    "segment_set_not_found": (404, "Transcript segments were not found."),
    "segment_not_found": (404, "Transcript segment was not found."),
    "segment_set_not_reviewable": (409, "The transcript segments are not ready for this review action."),
    "stale_segment_set_version": (409, "The transcript segment version is stale."),
    "segment_transcript_stale": (409, "The transcript segments are based on a stale transcript."),
    "segment_role_not_permitted": (403, "This role is not permitted to edit transcript segments."),
    "segment_set_integrity_error": (409, "The transcript segment snapshot is inconsistent."),
    "evidence_not_found": (404, "Evidence is not available for this assessment."),
    "evidence_provenance_required": (409, "Evidence provenance is required."),
    "evidence_segment_provenance_mismatch": (409, "Evidence segment provenance is inconsistent."),
    "evidence_protocol_mismatch": (409, "Evidence does not match the assessment protocol."),
    "evidence_provenance_mismatch": (409, "Evidence provenance is inconsistent."),
    "evidence_no_measurements": (409, "The completed evidence run contains no measurements."),
    "stale_evidence_input": (409, "The evidence input is stale."),
    "stale_segment_set_input": (409, "The transcript segment input is stale."),
    "storage_unavailable": (503, "Private storage is temporarily unavailable."),
    "different_child": (400, "Assessments belong to different children."),
    "tenant_mismatch": (403, "Assessments must belong to the caller organization."),
    "comparison_not_found": (404, "Assessment comparison was not found."),
    "comparison_save_failed": (500, "Failed to persist assessment comparison."),
    "clinical_review_not_found": (404, "Clinical review session was not found."),
    "attention_cue_not_found": (404, "Attention cue was not found."),
    "report_not_found": (404, "Assessment report was not found."),
    "report_not_ready": (409, "Report is not ready for sign-off."),
    "report_immutable": (409, "Signed reports are immutable."),
    "report_export_not_ready": (409, "Report must be signed off before export."),
    "stale_report_version": (409, "The report version is stale."),
}

_Result = TypeVar("_Result")


class AssessmentService:
    def __init__(
        self,
        repository: AssessmentRepository,
        user: CurrentUser,
        *,
        storage: CaptureStorageAdapter | None = None,
        authorized_role: str | None = None,
    ) -> None:
        self.repository = repository
        self.user = user
        self.storage = storage
        self.authorized_role = authorized_role or user.role
        self.now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def create_child(self, command: CreateChild, correlation_id: str) -> ChildSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        return self._repository_call(
            lambda: self.repository.create_child(self.scope, command, correlation_id)
        )

    def get_child(self, child_id: str) -> ChildSnapshot:
        self._require_clinical_role()
        child = self._repository_call(lambda: self.repository.get_child(self.scope, child_id))
        if child is None:
            raise self._policy_error("child_not_found")
        return child

    def list_children(self) -> list[ChildSnapshot]:
        self._require_clinical_role()
        return self._repository_call(lambda: self.repository.list_children(self.scope))

    def grant_consent(self, child_id: str, command: RecordConsent, correlation_id: str):
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        return self._repository_call(
            lambda: self.repository.add_consent(self.scope, child_id, command, correlation_id)
        )

    def list_consents(self, child_id: str) -> list[ConsentSnapshot]:
        self._require_clinical_role()
        self.get_child(child_id)
        return self._repository_call(lambda: self.repository.list_consents(self.scope, child_id))

    def create_assessment(
        self, child_id: str, command: StartAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        child = self.get_child(child_id)

        assigned_clinician_id = command.assigned_clinician_id or self.user.user_id
        if self.authorized_role not in _OVERSIGHT_ROLES and assigned_clinician_id != self.user.user_id:
            raise self._policy_error("clinician_assignment_not_permitted")

        if not self._repository_call(
            lambda: self.repository.can_assign_clinician(
                self.scope, child_id, assigned_clinician_id
            )
        ):
            raise self._policy_error("clinician_assignment_not_permitted")

        age_months = self._age_in_months(child)
        create_command = CreateAssessment(
            child_id=child_id,
            purpose=command.purpose,
            age_months=age_months,
            language_context=dict(child.language_context),
            assigned_clinician_id=assigned_clinician_id,
        )
        return self._repository_call(
            lambda: self.repository.create_assessment_if_consented(
                self.scope, create_command, correlation_id
            )
        )

    def get_assessment(self, assessment_id: str) -> AssessmentSnapshot:
        self._require_clinical_role()
        assessment = self._repository_call(
            lambda: self.repository.get_assessment(self.scope, assessment_id)
        )
        if assessment is None:
            raise self._policy_error("assessment_not_found")
        return assessment

    def list_assessments(self, child_id: str) -> list[AssessmentSnapshot]:
        self._require_clinical_role()
        self.get_child(child_id)
        return self._repository_call(lambda: self.repository.list_assessments(self.scope, child_id))

    def get_current_transcript(self, assessment_id: str) -> TranscriptRevisionSnapshot:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        transcript = self._repository_call(
            lambda: self.repository.get_current_transcript(self.scope, assessment_id)
        )
        if transcript is None:
            raise self._policy_error("transcript_not_found")
        return transcript

    def create_transcript_revision(
        self,
        assessment_id: str,
        command: CreateTranscriptRevision,
        correlation_id: str,
    ) -> TranscriptRevisionSnapshot:
        self._require_authorized_role(_TRANSCRIPT_EDITOR_ROLES)
        assessment = self.get_assessment(assessment_id)
        if command.assessment_id != assessment.id:
            raise self._policy_error("transcript_not_reviewable")
        return self._repository_call(
            lambda: self.repository.create_transcript_revision(
                self.scope, command, correlation_id
            )
        )

    def attest_transcript(
        self,
        transcript_revision_id: str,
        command: AttestTranscript,
        correlation_id: str,
    ) -> TranscriptRevisionSnapshot:
        self._require_authorized_role(_TRANSCRIPT_ATTESTATION_ROLES)
        if command.transcript_revision_id != transcript_revision_id:
            raise self._policy_error("transcript_not_reviewable")
        return self._repository_call(
            lambda: self.repository.attest_transcript(self.scope, command, correlation_id)
        )

    def get_current_transcript_segment_set(
        self,
        assessment_id: str,
    ) -> TranscriptSegmentSetSnapshot:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        segment_set = self._repository_call(
            lambda: self.repository.get_current_transcript_segment_set(
                self.scope,
                assessment_id,
            )
        )
        if segment_set is None:
            raise self._policy_error("segment_set_not_found")
        return segment_set

    def create_transcript_segment_set(
        self,
        assessment_id: str,
        command: CreateTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot:
        self._require_authorized_role(_TRANSCRIPT_EDITOR_ROLES)
        assessment = self.get_assessment(assessment_id)
        if command.assessment_id != assessment.id:
            raise self._policy_error("segment_set_not_reviewable")
        return self._repository_call(
            lambda: self.repository.create_transcript_segment_set(
                self.scope,
                command,
                correlation_id,
            )
        )

    def attest_transcript_segment_set(
        self,
        transcript_segment_set_id: str,
        command: AttestTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot:
        self._require_authorized_role(_TRANSCRIPT_ATTESTATION_ROLES)
        if command.transcript_segment_set_id != transcript_segment_set_id:
            raise self._policy_error("segment_set_not_reviewable")
        return self._repository_call(
            lambda: self.repository.attest_transcript_segment_set(
                self.scope,
                command,
                correlation_id,
            )
        )

    def create_transcript_segment_audio_replay_grant(
        self,
        transcript_segment_id: str,
    ) -> SegmentAudioReplayGrant:
        self._require_clinical_role()
        target = self._repository_call(
            lambda: self.repository.get_transcript_segment_replay_target(
                self.scope,
                transcript_segment_id,
            )
        )
        if target is None:
            raise self._policy_error("segment_not_found")
        segment, recording = target
        if recording is None:
            return SegmentAudioReplayGrant(
                segment_id=segment.id,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                available=False,
                url=None,
                expires_at=None,
                expires_in_seconds=None,
            )
        grant = self._storage_call(
            lambda: self._storage_or_error().create_signed_download_grant(recording.object_key)
        )
        return SegmentAudioReplayGrant(
            segment_id=segment.id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            available=True,
            url=grant.url,
            expires_at=grant.expires_at,
            expires_in_seconds=grant.expires_in_seconds,
        )

    def get_current_evidence(self, assessment_id: str) -> EvidenceRunSnapshot:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        evidence = self._repository_call(
            lambda: self.repository.get_current_evidence(self.scope, assessment_id)
        )
        if evidence is None:
            raise self._policy_error("evidence_not_found")
        return evidence

    def create_evidence_run(
        self,
        assessment_id: str,
        transcript_revision_id: str,
        adapted: AdaptedEvidence,
        correlation_id: str,
    ) -> EvidenceRunSnapshot:
        self._require_authorized_role(_EVIDENCE_RUN_ROLES)
        self.get_assessment(assessment_id)
        return self._repository_call(
            lambda: self.repository.create_evidence_run(
                self.scope,
                assessment_id,
                transcript_revision_id,
                adapted,
                correlation_id,
            )
        )

    def enqueue_current_evidence_processing(
        self, assessment_id: str, correlation_id: str
    ) -> ProcessingRunSnapshot:
        """Create or return the durable job for the current attested transcript."""

        self._require_authorized_role(_EVIDENCE_RUN_ROLES)
        return self._repository_call(
            lambda: self.repository.enqueue_current_evidence_processing(
                self.scope, assessment_id, correlation_id
            )
        )

    def create_current_evidence_run(
        self, assessment_id: str, correlation_id: str
    ) -> ProcessingRunSnapshot:
        """Compatibility alias for callers migrating to the durable action."""

        return self.enqueue_current_evidence_processing(assessment_id, correlation_id)

    def get_current_evidence_processing_run(self, assessment_id: str) -> ProcessingRunSnapshot:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        processing_run = self._repository_call(
            lambda: self.repository.get_current_evidence_processing_run(self.scope, assessment_id)
        )
        if processing_run is None:
            raise self._policy_error("processing_run_not_found")
        return processing_run

    def retry_processing_run(
        self, processing_run_id: str, expected_version: int, correlation_id: str
    ) -> ProcessingRunSnapshot:
        self._require_authorized_role(_EVIDENCE_RUN_ROLES)
        return self._repository_call(
            lambda: self.repository.retry_evidence_processing_run(
                self.scope, processing_run_id, expected_version, correlation_id
            )
        )

    def cancel_processing_run(
        self, processing_run_id: str, expected_version: int, correlation_id: str
    ) -> ProcessingRunSnapshot:
        self._require_authorized_role(_EVIDENCE_RUN_ROLES)
        return self._repository_call(
            lambda: self.repository.request_evidence_processing_cancellation(
                self.scope, processing_run_id, expected_version, correlation_id
            )
        )

    def transition_assessment(
        self, assessment_id: str, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        current = self.get_assessment(assessment_id)
        if command.expected_version != current.version:
            raise self._policy_error("stale_assessment_version")
        if (
            current.state is not AssessmentState.DRAFT
            or command.target_state is not AssessmentState.CANCELLED
        ):
            raise self._policy_error("workflow_stage_unavailable")
        return self._repository_call(
            lambda: self.repository.transition_assessment(self.scope, command, correlation_id)
        )

    def select_protocol(self, assessment_id: str, correlation_id: str) -> CaptureSnapshot:
        """Derive the capture protocol from persisted assessment context only."""

        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        assessment = self.get_assessment(assessment_id)
        primary_language = assessment.language_context.get("primary")
        additional_languages = assessment.language_context.get("additional")
        try:
            protocol = select_protocol(
                primary_language=primary_language if isinstance(primary_language, str) else "",
                additional_languages=(
                    additional_languages
                    if isinstance(additional_languages, (tuple, list))
                    else None
                ),
                age_months=assessment.age_months,
                purpose=assessment.purpose,
            )
        except ProtocolUnavailableError as error:
            raise self._policy_error("protocol_unavailable") from error
        return self._repository_call(
            lambda: self.repository.select_protocol_and_ready(
                self.scope,
                SelectProtocol(
                    assessment_id=assessment.id,
                    protocol_version_key=protocol.protocol_version_key,
                    expected_version=assessment.version,
                ),
                correlation_id,
            )
        )

    def get_capture(self, assessment_id: str) -> CaptureSnapshot:
        self._require_clinical_role()
        capture = self._repository_call(
            lambda: self.repository.get_capture(self.scope, assessment_id)
        )
        if capture is None:
            raise self._policy_error("assessment_not_found")
        return capture

    def start_capture(self, assessment_id: str, correlation_id: str) -> AssessmentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        return self._repository_call(
            lambda: self.repository.start_capture_if_consented(
                self.scope,
                StartCapture(assessment_id=assessment_id),
                correlation_id,
            )
        )

    def create_recording(
        self, command: CreateRecording, correlation_id: str
    ) -> RecordingIntentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        return self._repository_call(
            lambda: self.repository.create_recording_if_capture_active(
                self.scope,
                command,
                correlation_id,
            )
        )

    def create_upload_intent(
        self, recording_id: str, correlation_id: str
    ) -> tuple[RecordingSnapshot, SignedUploadGrant]:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        recording = self._recording_or_error(recording_id)
        if recording.upload_state not in {
            RecordingUploadState.PENDING,
            RecordingUploadState.UPLOADING,
        }:
            raise self._policy_error("upload_verification_failed")
        if self._recording_expired(recording):
            expire_recording = getattr(self.repository, "expire_recording_upload_if_needed", None)
            if expire_recording is not None:
                self._repository_call(
                    lambda: expire_recording(
                        self.scope,
                        recording.id,
                        recording.version,
                        correlation_id,
                    )
                )
            raise self._policy_error("upload_intent_expired")
        storage = self._storage_or_error()
        grant = self._storage_call(
            lambda: storage.create_signed_upload_grant(
                recording.object_key,
                recording.declared_content_type,
                recording.declared_size_bytes,
            )
        )
        updated = self._repository_call(
            lambda: self.repository.mark_recording_uploading_if_capture_active(
                self.scope,
                MarkRecordingUploading(
                    recording_id=recording.id,
                    expected_version=recording.version,
                    expires_at=grant.expires_at,
                ),
                correlation_id,
            )
        )
        return updated, grant

    def complete_upload(self, recording_id: str, correlation_id: str) -> RecordingIntentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        recording = self._recording_or_error(recording_id)
        if recording.upload_state is RecordingUploadState.VERIFIED:
            return self._repository_call(
                lambda: self.repository.complete_recording_upload_if_capture_active(
                    self.scope,
                    CompleteRecordingUpload(
                        recording_id=recording.id,
                        expected_version=recording.version,
                        observed_content_type=(
                            recording.verified_content_type or recording.declared_content_type
                        ),
                        observed_size_bytes=(
                            recording.verified_size_bytes or recording.declared_size_bytes
                        ),
                        completed_at=recording.verified_at or self.now(),
                    ),
                    correlation_id,
                )
            )
        if recording.upload_state is RecordingUploadState.UPLOADED:
            return self._repository_call(
                lambda: self.repository.complete_recording_upload_if_capture_active(
                    self.scope,
                    CompleteRecordingUpload(
                        recording_id=recording.id,
                        expected_version=recording.version,
                        observed_content_type=recording.declared_content_type,
                        observed_size_bytes=recording.declared_size_bytes,
                        completed_at=self.now(),
                    ),
                    correlation_id,
                )
            )
        if recording.upload_state is not RecordingUploadState.UPLOADING:
            raise self._policy_error("upload_verification_failed")
        metadata = self._storage_call(
            lambda: self._storage_or_error().get_object_metadata(
                recording.object_key,
                expected_content_type=recording.declared_content_type,
                expected_size_bytes=recording.declared_size_bytes,
            )
        )
        if (
            metadata.content_type is None
            or metadata.size_bytes is None
            or metadata.content_type != recording.declared_content_type
            or metadata.size_bytes != recording.declared_size_bytes
        ):
            raise self._policy_error("upload_verification_failed")
        return self._repository_call(
            lambda: self.repository.complete_recording_upload_if_capture_active(
                self.scope,
                CompleteRecordingUpload(
                    recording_id=recording.id,
                    expected_version=recording.version,
                    observed_content_type=metadata.content_type,
                    observed_size_bytes=metadata.size_bytes,
                    completed_at=self.now(),
                ),
                correlation_id,
            )
        )

    def get_recording(self, recording_id: str) -> RecordingSnapshot:
        """Return safe recording metadata only after authoritative verification."""

        self._require_clinical_role()
        recording = self._recording_or_error(recording_id)
        if recording.upload_state is not RecordingUploadState.VERIFIED:
            raise self._policy_error("recording_not_verified")
        return recording

    def get_recording_quality(self, recording_id: str) -> RecordingQualitySnapshot:
        self._require_clinical_role()
        self.get_recording(recording_id)
        quality = self._repository_call(
            lambda: self.repository.get_recording_quality_if_consented(self.scope, recording_id)
        )
        if quality is None:
            raise self._policy_error("required_activity_not_usable")
        return quality

    def download_intent(
        self, recording_id: str
    ) -> tuple[RecordingSnapshot, SignedDownloadGrant]:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        recording = self.get_recording(recording_id)
        grant = self._storage_call(
            lambda: self._storage_or_error().create_signed_download_grant(recording.object_key)
        )
        return recording, grant

    def delete_recording(self, recording_id: str, correlation_id: str) -> bool:
        """Tombstone metadata before deleting the private object.

        A missing record is a successful idempotent deletion. A failed storage
        cleanup leaves the durable tombstone for a later retry.
        The repository intentionally does not distinguish inaccessible records here.
        """

        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        recording = self._repository_call(
            lambda: self.repository.get_recording_if_consented(self.scope, recording_id)
        )
        if recording is None:
            return True
        tombstone = self._repository_call(
            lambda: self.repository.mark_recording_deleted_if_consented(
                self.scope,
                recording.id,
                recording.version,
                correlation_id,
            )
        )
        if tombstone is None:
            return True
        # The metadata tombstone and cleanup intent must survive a later
        # Storage failure.  Commit this boundary before crossing into the
        # external provider; the request transaction may still be rolled back
        # without resurrecting the recording.
        commit_transaction = getattr(self.repository, "commit_transaction", None)
        if commit_transaction is not None:
            commit_transaction()
        self._storage_call(lambda: self._storage_or_error().delete_object(tombstone.object_key))
        self._repository_call(
            lambda: self.repository.complete_cleanup_for_recording(self.scope, tombstone.id)
        )
        return True

    def complete_capture(self, assessment_id: str, correlation_id: str) -> AssessmentSnapshot:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        assessment = self.get_assessment(assessment_id)
        return self._repository_call(
            lambda: self.repository.complete_capture_if_required_usable(
                self.scope,
                CompleteCapture(
                    assessment_id=assessment.id,
                    expected_version=assessment.version,
                ),
                correlation_id,
            )
        )

    def get_processing_run(self, processing_run_id: str) -> ProcessingRunSnapshot:
        self._require_clinical_role()
        processing_run = self._repository_call(
            lambda: self.repository.get_processing_run_if_consented(
                self.scope, processing_run_id
            )
        )
        if processing_run is None:
            raise self._policy_error("processing_run_not_found")
        return processing_run

    @property
    def scope(self) -> AccessScope:
        return AccessScope(
            user_id=self.user.user_id,
            organization_id=self.user.organization_id,
            role=self.authorized_role,
        )

    def _require_clinical_role(self) -> None:
        if not self.user.membership_active:
            raise self._policy_error("inactive_membership")
        if self.authorized_role not in _CLINICAL_ROLES:
            raise self._policy_error("role_not_permitted")

    def _require_authorized_role(self, allowed_roles: frozenset[str]) -> None:
        self._require_clinical_role()
        if self.authorized_role not in allowed_roles:
            raise self._policy_error("role_not_permitted")

    def _age_in_months(self, child: ChildSnapshot) -> int:
        current = self.now()
        age_months = (current.year - child.birth_year) * 12 + current.month - child.birth_month
        if not 0 <= age_months <= _MAX_ASSESSMENT_AGE_MONTHS:
            raise self._policy_error("age_out_of_range")
        return age_months

    def _repository_call(self, operation: Callable[[], _Result]) -> _Result:
        try:
            return operation()
        except RepositoryError as error:
            raise self._policy_error(error.code) from error

    def _recording_or_error(self, recording_id: str) -> RecordingSnapshot:
        recording = self._repository_call(
            lambda: self.repository.get_recording_if_consented(self.scope, recording_id)
        )
        if recording is None:
            raise self._policy_error("recording_not_found")
        return recording

    def _recording_expired(self, recording: RecordingSnapshot) -> bool:
        expires_at = recording.expires_at
        now = self.now()
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return expires_at <= now

    def _storage_or_error(self) -> CaptureStorageAdapter:
        if self.storage is None:
            raise self._policy_error("storage_unavailable")
        return self.storage

    def _storage_call(self, operation: Callable[[], _Result]) -> _Result:
        try:
            return operation()
        except (StorageInputError, StorageUnavailableError):
            raise self._policy_error("storage_unavailable") from None
        except Exception:
            raise self._policy_error("storage_unavailable") from None

    def compare_assessments(
        self,
        assessment_id: str,
        baseline_assessment_id: str,
        policy_version: str,
        correlation_id: str,
    ) -> AssessmentComparisonRecord:
        self._require_clinical_role()
        curr_asmt = self.get_assessment(assessment_id)
        base_asmt = self.get_assessment(baseline_assessment_id)

        if curr_asmt.child_id != base_asmt.child_id:
            raise self._policy_error("different_child")

        if (
            curr_asmt.organization_id != base_asmt.organization_id
            or curr_asmt.organization_id != self.scope.organization_id
        ):
            raise self._policy_error("tenant_mismatch")

        has_consent = self._repository_call(
            lambda: self.repository.has_active_consent(
                self.scope, curr_asmt.child_id, ConsentPurpose.CLINICAL_ASSESSMENT
            )
        )
        if not has_consent:
            raise self._policy_error("active_consent_required")

        curr_evidence = self.get_current_evidence(assessment_id)
        base_evidence = self.get_current_evidence(baseline_assessment_id)

        curr_lang = "th"
        if isinstance(curr_asmt.language_context, dict):
            curr_lang = str(curr_asmt.language_context.get("primary", "th"))
        elif curr_asmt.language_context:
            curr_lang = str(curr_asmt.language_context)

        base_lang = "th"
        if isinstance(base_asmt.language_context, dict):
            base_lang = str(base_asmt.language_context.get("primary", "th"))
        elif base_asmt.language_context:
            base_lang = str(base_asmt.language_context)

        curr_protocol = curr_evidence.provenance.protocol_version_key
        base_protocol = base_evidence.provenance.protocol_version_key

        comparison_session = compare_evidence_runs(
            baseline_run=base_evidence,
            current_run=curr_evidence,
            baseline_protocol_key=base_protocol,
            current_protocol_key=curr_protocol,
            baseline_language=base_lang,
            current_language=curr_lang,
            child_id=curr_asmt.child_id,
            baseline_child_id=base_asmt.child_id,
            organization_id=self.scope.organization_id,
            baseline_organization_id=base_asmt.organization_id,
            policy_version=policy_version,
        )

        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("comparison_save_failed")

        long_repo = LongitudinalRepository(session)
        comp_id = long_repo.save_comparison(
            comparison_session=comparison_session,
            compared_by_user_id=self.user.user_id,
        )
        record = long_repo.get_comparison(self.scope.organization_id, comp_id)
        if record is None:
            raise self._policy_error("comparison_save_failed")
        return record

    def list_assessment_comparisons(self, assessment_id: str) -> list[AssessmentComparisonRecord]:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            return []
        long_repo = LongitudinalRepository(session)
        return long_repo.list_comparisons_for_assessment(self.scope.organization_id, assessment_id)

    def get_assessment_comparison(self, assessment_id: str, comparison_id: str) -> AssessmentComparisonRecord:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("comparison_not_found")
        long_repo = LongitudinalRepository(session)
        comp = long_repo.get_comparison(self.scope.organization_id, comparison_id)
        if comp is None:
            raise self._policy_error("comparison_not_found")
        if comp.current_assessment_id != assessment_id and comp.baseline_assessment_id != assessment_id:
            raise self._policy_error("comparison_not_found")
        return comp

    def list_child_assessment_history(self, child_id: str) -> list[dict[str, object]]:
        self._require_clinical_role()
        self.get_child(child_id)
        assessments = self._repository_call(
            lambda: self.repository.list_assessments(self.scope, child_id)
        )
        history: list[dict[str, object]] = []
        for asmt in assessments:
            evidence = self._repository_call(
                lambda: self.repository.get_current_evidence(self.scope, asmt.id)
            )
            lang = "th"
            if isinstance(asmt.language_context, dict):
                lang = str(asmt.language_context.get("primary", "th"))
            elif asmt.language_context:
                lang = str(asmt.language_context)

            is_comp = False
            proto_key = None
            ev_id = None
            if evidence is not None and evidence.state is EvidenceState.COMPLETED:
                is_comp = True
                proto_key = evidence.provenance.protocol_version_key
                ev_id = evidence.id

            created_at = asmt.created_at if getattr(asmt, "created_at", None) is not None else self.now()
            history.append({
                "assessment_id": asmt.id,
                "created_at": created_at,
                "purpose": asmt.purpose.value,
                "state": asmt.state.value,
                "age_months": asmt.age_months,
                "protocol_version_key": proto_key,
                "language": lang,
                "evidence_run_id": ev_id,
                "is_comparable": is_comp,
            })
        return history

    def get_or_create_clinical_review(self, assessment_id: str) -> ClinicalReviewSession:
        self._require_clinical_role()
        asmt = self.get_assessment(assessment_id)
        evidence = self._repository_call(
            lambda: self.repository.get_current_evidence(self.scope, assessment_id)
        )
        if evidence is None or evidence.state is not EvidenceState.COMPLETED:
            raise self._policy_error("evidence_not_found")

        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("clinical_review_not_found")

        rev_repo = ClinicalReviewRepository(session)
        existing = rev_repo.get_review_session(self.scope.organization_id, assessment_id)
        if existing is not None:
            return existing

        feature_dict = {f.name: f.value for f in evidence.features}
        limitations = list(evidence.limitations or [])
        initial_cues = evaluate_attention_cues(
            assessment_id=assessment_id,
            evidence_run_id=evidence.id,
            features=feature_dict,
            limitations=limitations,
        )
        return rev_repo.get_or_create_review_session(
            organization_id=self.scope.organization_id,
            assessment_id=assessment_id,
            child_id=asmt.child_id,
            evidence_run_id=evidence.id,
            initial_cues=initial_cues,
        )

    def review_attention_cue(
        self,
        assessment_id: str,
        cue_id: str,
        status: CueStatus,
        rationale: str | None = None,
    ) -> AttentionCue:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        rev = self.get_or_create_clinical_review(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("clinical_review_not_found")

        rev_repo = ClinicalReviewRepository(session)
        return rev_repo.update_cue_feedback(
            organization_id=self.scope.organization_id,
            review_id=rev.review_id,
            cue_id=cue_id,
            reviewer_id=self.user.user_id,
            status=status,
            rationale=rationale,
        )

    def update_clinical_disposition(
        self,
        assessment_id: str,
        disposition: ClinicalDispositionType,
        disposition_notes: str | None = None,
        follow_up: FollowUpPlan | None = None,
        expected_version: int | None = None,
    ) -> ClinicalReviewSession:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        rev = self.get_or_create_clinical_review(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("clinical_review_not_found")

        rev_repo = ClinicalReviewRepository(session)
        try:
            return rev_repo.update_disposition(
                organization_id=self.scope.organization_id,
                review_id=rev.review_id,
                disposition=disposition,
                disposition_notes=disposition_notes,
                follow_up_plan=follow_up,
                reviewer_id=self.user.user_id,
                expected_version=expected_version,
            )
        except ValueError as exc:
            if "concurrency conflict" in str(exc).lower():
                raise self._policy_error("stale_assessment_version") from exc
            raise self._policy_error("clinical_review_not_found") from exc

    def create_report_draft(
        self,
        assessment_id: str,
        purpose: str | None = None,
        comparison_id: str | None = None,
    ) -> AssessmentReportRecord:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        asmt = self.get_assessment(assessment_id)
        if not self._repository_call(
            lambda: self.repository.has_active_consent(self.scope, asmt.child_id, ConsentPurpose.CLINICAL_ASSESSMENT)
        ):
            raise self._policy_error("active_consent_required")

        evidence = self._repository_call(
            lambda: self.repository.get_current_evidence(self.scope, assessment_id)
        )
        if evidence is None or evidence.state is not EvidenceState.COMPLETED:
            raise self._policy_error("evidence_not_found")

        rev_session = self.get_or_create_clinical_review(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")

        rep_repo = ReportsRepository(session)
        child = self.get_child(asmt.child_id)

        feature_dict = {f.name: f.value for f in evidence.features}
        limitations = list(evidence.limitations or [])
        report_purpose = purpose or f"การประเมินพัฒนาการทางภาษาตามโพรโทคอล {asmt.protocol_version_key or 'มาตรฐาน'}"

        comparisons_dict = None
        if comparison_id:
            long_repo = LongitudinalRepository(session)
            comp = long_repo.get_comparison(self.scope.organization_id, comparison_id)
            if comp:
                comparisons_dict = {
                    feat.feature_key: {
                        "baseline": feat.baseline_value,
                        "target": feat.current_value,
                        "delta": feat.absolute_delta,
                        "unit": feat.unit or "",
                    }
                    for feat in comp.features
                }

        markdown = generate_report_draft_markdown(
            child_code=child.child_code,
            assessment_date=asmt.created_at.strftime("%Y-%m-%d") if getattr(asmt, "created_at", None) else "2026-09-12",
            purpose=report_purpose,
            features=feature_dict,
            limitations=limitations,
            cues=rev_session.cues,
            disposition=rev_session.disposition,
            disposition_notes=rev_session.disposition_notes,
            follow_up=rev_session.follow_up,
            comparisons=comparisons_dict,
        )

        title = f"รายงานการประเมิน {child.child_code} ({report_purpose[:30]})"
        return rep_repo.create_report_draft(
            organization_id=self.scope.organization_id,
            assessment_id=assessment_id,
            child_id=asmt.child_id,
            evidence_run_id=evidence.id,
            review_id=rev_session.review_id,
            title=title,
            purpose=report_purpose,
            content_markdown=markdown,
            limitations=limitations,
            comparison_id=comparison_id,
        )

    def get_current_report(self, assessment_id: str) -> AssessmentReportRecord:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")
        rep_repo = ReportsRepository(session)
        rep = rep_repo.get_current_report(self.scope.organization_id, assessment_id)
        if rep is None:
            raise self._policy_error("report_not_found")
        return rep

    def get_report(self, assessment_id: str, report_id: str) -> AssessmentReportRecord:
        self._require_clinical_role()
        self.get_assessment(assessment_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")
        rep_repo = ReportsRepository(session)
        rep = rep_repo.get_report(self.scope.organization_id, report_id)
        if rep is None or rep.assessment_id != assessment_id:
            raise self._policy_error("report_not_found")
        return rep

    def update_report_draft(
        self,
        assessment_id: str,
        report_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
        limitations: list[str] | None = None,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        self.get_report(assessment_id, report_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")
        rep_repo = ReportsRepository(session)
        try:
            return rep_repo.update_report_draft(
                organization_id=self.scope.organization_id,
                report_id=report_id,
                title=title,
                purpose=purpose,
                content_markdown=content_markdown,
                limitations=limitations,
                expected_version=expected_version,
            )
        except ValueError as exc:
            msg = str(exc).lower()
            if "immutable" in msg:
                raise self._policy_error("report_immutable") from exc
            if "concurrency conflict" in msg:
                raise self._policy_error("stale_report_version") from exc
            raise self._policy_error("report_not_found") from exc

    def sign_off_report(
        self,
        assessment_id: str,
        report_id: str,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        self._require_authorized_role(_TRANSCRIPT_ATTESTATION_ROLES)
        asmt = self.get_assessment(assessment_id)
        has_consent = self._repository_call(
            lambda: self.repository.has_active_consent(self.scope, asmt.child_id, ConsentPurpose.CLINICAL_ASSESSMENT)
        )
        if not has_consent:
            raise self._policy_error("active_consent_required")

        evidence = self._repository_call(
            lambda: self.repository.get_current_evidence(self.scope, assessment_id)
        )
        if evidence is None or evidence.state is not EvidenceState.COMPLETED:
            raise self._policy_error("evidence_not_found")

        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")

        rep_repo = ReportsRepository(session)
        report = rep_repo.get_report(self.scope.organization_id, report_id)
        if report is None or report.assessment_id != assessment_id:
            raise self._policy_error("report_not_found")

        if report.status == ReportStatus.SIGNED_OFF.value:
            return report

        rev_session = self.get_or_create_clinical_review(assessment_id)
        child = self.get_child(asmt.child_id)

        readiness = check_report_signoff_readiness(
            consent_status="consented" if has_consent else "withdrawn",
            evidence_is_current=not report.is_stale,
            cues=rev_session.cues,
            disposition=rev_session.disposition,
            assigned_therapist_id=child.assigned_clinician_id or self.user.user_id,
            signing_user_id=self.user.user_id,
            markdown_text=report.content_markdown,
            expected_version=expected_version,
            current_version=report.version,
        )
        if not readiness.can_sign_off:
            raise ClinicalPolicyError(
                "report_not_ready",
                409,
                f"Report sign-off is blocked: {'; '.join(readiness.blocking_reasons)}",
                details={"blocking_reasons": readiness.blocking_reasons},
            )

        now = self.now()
        signed_at_iso = now.isoformat()
        snapshot, snapshot_hash = build_signed_report_snapshot(
            report_id=report.report_id,
            assessment_id=assessment_id,
            tenant_id=self.scope.organization_id,
            child_code=child.child_code,
            report_version=report.version,
            evidence_run_id=report.evidence_run_id,
            comparison_id=report.comparison_id,
            review_id=report.review_id,
            purpose=report.purpose,
            observations=[],
            descriptive_profile={f.name: f.value for f in evidence.features},
            comparisons=None,
            limitations=list(report.limitations_json or []),
            disposition=rev_session.disposition.value if rev_session.disposition else "continue_monitoring",
            follow_up_plan={
                "target_date": rev_session.follow_up.target_date if rev_session.follow_up else None,
                "recommended_protocol": rev_session.follow_up.recommended_protocol if rev_session.follow_up else None,
            },
            clinician_review=[
                {"cue_id": c.cue_id, "status": c.status.value, "rationale": c.clinician_feedback.rationale if c.clinician_feedback else None}
                for c in rev_session.cues
            ],
            markdown_content=report.content_markdown,
            signed_by=self.user.user_id,
            signed_at_iso=signed_at_iso,
        )

        return rep_repo.sign_off_report(
            organization_id=self.scope.organization_id,
            report_id=report_id,
            signed_by=self.user.user_id,
            signed_at=now,
            signed_snapshot=snapshot,
            signed_snapshot_hash=snapshot_hash,
            expected_version=expected_version,
        )

    def create_report_amendment(
        self,
        assessment_id: str,
        report_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
    ) -> AssessmentReportRecord:
        self._require_authorized_role(_CLINICAL_MUTATION_ROLES)
        self.get_report(assessment_id, report_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            raise self._policy_error("report_not_found")
        rep_repo = ReportsRepository(session)
        try:
            return rep_repo.create_amendment_draft(
                organization_id=self.scope.organization_id,
                signed_report_id=report_id,
                new_title=title,
                new_purpose=purpose,
                new_content_markdown=content_markdown,
            )
        except ValueError as exc:
            raise self._policy_error("invalid_assessment_transition") from exc

    def export_report(
        self,
        assessment_id: str,
        report_id: str,
        export_format: str,
    ) -> dict[str, Any]:
        self._require_clinical_role()
        asmt = self.get_assessment(assessment_id)
        if not self._repository_call(
            lambda: self.repository.has_active_consent(self.scope, asmt.child_id, ConsentPurpose.CLINICAL_ASSESSMENT)
        ):
            raise self._policy_error("active_consent_required")

        report = self.get_report(assessment_id, report_id)
        if report.status != ReportStatus.SIGNED_OFF.value:
            raise self._policy_error("report_export_not_ready")

        requested = export_format.lower()
        now = self.now()
        base_resp = {
            "report_id": report.report_id,
            "report_hash": report.signed_snapshot_hash,
            "signed_by": report.signed_by,
            "export_timestamp": now,
        }

        if requested == "pdf":
            import base64
            snapshot = report.signed_snapshot or {}
            pdf_bytes = render_assessment_v2_pdf(snapshot)
            b64_pdf = base64.b64encode(pdf_bytes).decode("ascii") if pdf_bytes else ""
            return {
                **base_resp,
                "format": "pdf",
                "content_type": "application/pdf",
                "filename": f"{report.report_id}.pdf",
                "base64_content": b64_pdf,
            }
        elif requested == "html":
            from html import escape
            html_lines = [f"<p>{escape(line)}</p>" for line in report.content_markdown.splitlines() if line.strip()]
            return {
                **base_resp,
                "format": "html",
                "content_type": "text/html",
                "filename": f"{report.report_id}.html",
                "content": "\n".join(html_lines),
            }
        else:
            return {
                **base_resp,
                "format": "markdown",
                "content_type": "text/markdown",
                "filename": f"{report.report_id}.md",
                "content": report.content_markdown,
            }

    def get_report_lineage(self, assessment_id: str, report_id: str) -> list[AssessmentReportRecord]:
        self._require_clinical_role()
        self.get_report(assessment_id, report_id)
        session = getattr(self.repository, "session", None)
        if session is None:
            return []
        rep_repo = ReportsRepository(session)
        return rep_repo.get_amendment_lineage(self.scope.organization_id, report_id)

    @staticmethod
    def _policy_error(code: str) -> ClinicalPolicyError:
        status_code, safe_message = _POLICY_MESSAGES.get(
            code, (409, "The clinical operation could not be completed.")
        )
        return ClinicalPolicyError(code, status_code, safe_message)

