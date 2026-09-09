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
from app.assessment_v2.evidence import EvidenceRunSnapshot
from app.assessment_v2.evidence_adapter import AdaptedEvidence
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
    "evidence_not_found": (404, "Evidence is not available for this assessment."),
    "evidence_provenance_required": (409, "Evidence provenance is required."),
    "evidence_protocol_mismatch": (409, "Evidence does not match the assessment protocol."),
    "evidence_provenance_mismatch": (409, "Evidence provenance is inconsistent."),
    "evidence_no_measurements": (409, "The completed evidence run contains no measurements."),
    "stale_evidence_input": (409, "The evidence input is stale."),
    "storage_unavailable": (503, "Private storage is temporarily unavailable."),
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

    @staticmethod
    def _policy_error(code: str) -> ClinicalPolicyError:
        status_code, safe_message = _POLICY_MESSAGES.get(
            code, (409, "The clinical operation could not be completed.")
        )
        return ClinicalPolicyError(code, status_code, safe_message)
