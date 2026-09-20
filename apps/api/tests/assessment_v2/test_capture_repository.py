from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib import import_module

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    AuditEventRecord,
    EvidenceDomainProfileRecord,
    EvidenceFeatureRecord,
    EvidenceRunRecord,
    OrganizationMembershipRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingQualityResultRecord,
    RecordingRecord,
    TranscriptRevisionRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository, RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentState,
    ConsentPurpose,
    ConsentStatus,
    CreateAssessment,
    CreateChild,
    ProcessingRunState,
    RecordConsent,
    AttestTranscript,
    CreateTranscriptRevision,
)
from app.core.security import CurrentUser
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.assessment_v2.storage import StorageDeletionResult, StorageUnavailableError
from app.assessment_v2.quality import MediaQuality, QualityDecision
from app.assessment_v2.worker import CaptureProcessingWorker
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.evidence_adapter import AdaptedEvidence


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AssessmentBase.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as value:
        yield value
    AssessmentBase.metadata.drop_all(engine)


def _scope() -> AccessScope:
    return AccessScope(user_id="therapist_01", organization_id="org_alpha", role="therapist")


def _seed_catalog(session: Session) -> None:
    session.add(
        ProtocolVersionRecord(
            protocol_version_key="thai_guided_language_sample:v0",
            primary_language="th",
            minimum_age_months=18,
            maximum_age_months=72,
            supported_purposes="initial,developmental_follow_up,post_intervention_follow_up,additional_evidence",
        )
    )
    session.add_all(
        [
            ProtocolActivityRecord(
                protocol_version_key="thai_guided_language_sample:v0",
                activity_key="free_play",
                required=True,
                target_duration_seconds=180,
                minimum_duration_seconds=120,
                sort_order=1,
            ),
            ProtocolActivityRecord(
                protocol_version_key="thai_guided_language_sample:v0",
                activity_key="shared_book",
                required=False,
                target_duration_seconds=120,
                minimum_duration_seconds=60,
                sort_order=2,
            ),
        ]
    )
    session.flush()


def _ready_capture_repository(session: Session):
    domain = import_module("app.assessment_v2.domain.models")
    repo = AssessmentRepository(session)
    scope = _scope()
    repo.synchronize_principal(
        CurrentUser(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            role=scope.role,
            display_name="Synthetic Therapist",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    session.add(
        OrganizationMembershipRecord(
            membership_id="membership_capture_01",
            organization_id=scope.organization_id,
            user_id=scope.user_id,
            role=scope.role,
            active=True,
        )
    )
    session.flush()
    _seed_catalog(session)
    child = repo.create_child(
        scope,
        CreateChild(
            display_code="LL-CAPTURE-01",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": []},
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.add_consent(
        scope,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    assessment = repo.create_assessment(
        scope,
        CreateAssessment(
            child_id=child.id,
            purpose=AssessmentPurpose.INITIAL,
            age_months=36,
            language_context={"primary": "th", "additional": []},
            assigned_clinician_id=scope.user_id,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    selected = repo.select_protocol_and_ready(
        scope,
        domain.SelectProtocol(
            assessment_id=assessment.id,
            protocol_version_key="thai_guided_language_sample:v0",
            expected_version=assessment.version,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    started = repo.start_capture_if_consented(
        scope,
        domain.StartCapture(assessment_id=assessment.id),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    assert selected.assessment.state is AssessmentState.READY_FOR_CAPTURE
    assert started.state is AssessmentState.CAPTURING
    return repo, scope, child, started, domain


def test_recording_intent_is_atomic_idempotent_and_uses_only_opaque_object_paths(session: Session) -> None:
    assert hasattr(AssessmentRepository, "select_protocol_and_ready")
    assert hasattr(AssessmentRepository, "start_capture_if_consented")
    assert hasattr(AssessmentRepository, "create_recording_if_capture_active")
    repo, scope, child, assessment, domain = _ready_capture_repository(session)
    command = domain.CreateRecording(
        assessment_id=assessment.id,
        activity_code="free_play",
        content_type="audio/webm",
        size_bytes=456,
        checksum="sha256:0123456789abcdef0123456789abcdef",
        idempotency_key="recording-request-01",
    )

    first = repo.create_recording_if_capture_active(
        scope,
        command,
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repeated = repo.create_recording_if_capture_active(
        scope,
        command,
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert first.recording.id == repeated.recording.id
    assert first.processing_run.id == repeated.processing_run.id
    assert first.recording.upload_state.value == "pending"
    assert first.processing_run.stage.value == "upload_verification"
    assert first.processing_run.state.value == "queued"
    assert first.recording.object_key.startswith("capture/")
    assert assessment.id not in first.recording.object_key
    assert child.id not in first.recording.object_key
    assert command.idempotency_key not in first.recording.object_key

    with pytest.raises(RepositoryError) as raised:
        repo.create_recording_if_capture_active(
            scope,
            domain.CreateRecording(
                assessment_id=assessment.id,
                activity_code="free_play",
                content_type="audio/webm",
                size_bytes=457,
                checksum="sha256:0123456789abcdef0123456789abcdef",
                idempotency_key="recording-request-01",
            ),
            correlation_id="0123456789abcdef0123456789abcdef",
        )

    assert raised.value.code == "idempotency_conflict"
    stored = session.scalar(select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id))
    assert stored is not None
    assert stored.state == AssessmentState.CAPTURING.value


def test_worker_does_not_claim_upload_verification_before_upload_completion(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-worker-gate-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert repo.claim_next_processing_run() is None
    stored_run = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == created.processing_run.id
        )
    )
    assert stored_run is not None
    assert stored_run.state == ProcessingRunState.QUEUED.value
    assert stored_run.attempt_count == 0


def test_worker_reclaims_an_expired_capture_lease_after_a_crash(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-worker-reclaim-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    uploading = repo.mark_recording_uploading_if_capture_active(
        scope,
        domain.MarkRecordingUploading(
            recording_id=created.recording.id,
            expected_version=created.recording.version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    completed_upload = repo.complete_recording_upload_if_capture_active(
        scope,
        domain.CompleteRecordingUpload(
            recording_id=uploading.id,
            expected_version=uploading.version,
            observed_content_type="audio/webm",
            observed_size_bytes=456,
            completed_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    first = repo.claim_next_processing_run()
    assert first is not None
    assert first.lease_token
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == completed_upload.processing_run.id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.RUNNING.value
    first_attempt_count = stored.attempt_count
    stored.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.flush()

    reclaimed = repo.claim_next_processing_run()

    assert reclaimed is not None
    assert reclaimed.run_id == first.run_id
    assert reclaimed.lease_token != first.lease_token
    assert stored.attempt_count == first_attempt_count + 1
    assert stored.state == ProcessingRunState.RUNNING.value
    assert stored.lease_expires_at is not None
    assert stored.lease_expires_at > datetime.now(timezone.utc)


def test_worker_expires_abandoned_uploads_and_queues_cleanup(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:" + "0" * 64,
            idempotency_key="recording-expired-upload-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    recording = session.scalar(
        select(RecordingRecord).where(RecordingRecord.recording_id == created.recording.id)
    )
    assert recording is not None
    recording.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.flush()

    cleanup_item = repo.claim_next_processing_run()

    assert recording.upload_state == "expired"
    cleanup = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.recording_id == recording.recording_id,
            ProcessingRunRecord.stage == "cleanup",
        )
    )
    assert cleanup is not None
    # The worker claims the newly queued cleanup run in the same polling
    # cycle, so the durable record is already running when this call returns.
    assert cleanup.state == ProcessingRunState.RUNNING.value
    assert cleanup_item is not None
    assert cleanup_item.stage.value == "cleanup"


def test_upload_intent_expiry_is_persisted_when_the_therapist_retries(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-expiry-api-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    recording = session.scalar(
        select(RecordingRecord).where(RecordingRecord.recording_id == created.recording.id)
    )
    assert recording is not None
    recording.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.flush()
    service = AssessmentService(
        repo,
        CurrentUser(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            role=scope.role,
            display_name="Synthetic Therapist",
        ),
    )

    with pytest.raises(ClinicalPolicyError) as raised:
        service.create_upload_intent(created.recording.id, "0123456789abcdef0123456789abcdef")

    assert raised.value.code == "upload_intent_expired"
    assert recording.upload_state == "expired"
    cleanup = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.recording_id == recording.recording_id,
            ProcessingRunRecord.stage == "cleanup",
        )
    )
    assert cleanup is not None


def test_worker_transitions_emit_auditable_events(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-worker-audit-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    uploading = repo.mark_recording_uploading_if_capture_active(
        scope,
        domain.MarkRecordingUploading(
            recording_id=created.recording.id,
            expected_version=created.recording.version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    uploaded = repo.complete_recording_upload_if_capture_active(
        scope,
        domain.CompleteRecordingUpload(
            recording_id=uploading.id,
            expected_version=uploading.version,
            observed_content_type="audio/webm",
            observed_size_bytes=456,
            completed_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    upload_item = repo.claim_next_processing_run()
    assert upload_item is not None
    assert repo.verify_recording_upload_worker(
        upload_item,
        "sha256:0123456789abcdef0123456789abcdef",
    ) is True
    quality_item = repo.claim_next_processing_run()
    assert quality_item is not None
    assert repo.persist_quality_result(
        quality_item,
        MediaQuality(135.0, -24.0, 0.1, 1.0, ()),
        QualityDecision(status="usable", unavailable_checks=()),
    ) is True

    events = session.scalars(
        select(AuditEventRecord)
        .where(
            AuditEventRecord.organization_id == scope.organization_id,
            AuditEventRecord.actor_user_id == "capture-worker",
        )
        .order_by(AuditEventRecord.occurred_at, AuditEventRecord.audit_event_id)
    ).all()
    actions = {event.action for event in events}
    assert {
        "processing_run.claimed",
        "processing_run.succeeded",
        "processing_run.queued",
        "recording.upload_verified",
        "recording.quality_recorded",
    }.issubset(actions)
    assert all(len(event.correlation_id) == 32 for event in events)
    assert all(int(event.correlation_id, 16) >= 0 for event in events)


def test_verified_required_recording_needs_a_persisted_usable_quality_result_before_capture_completion(
    session: Session,
) -> None:
    assert all(
        hasattr(AssessmentRepository, method)
        for method in (
            "mark_recording_uploading_if_capture_active",
            "complete_recording_upload_if_capture_active",
            "verify_recording_upload",
            "complete_capture_if_required_usable",
        )
    )
    repo, scope, child, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-request-02",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    uploading = repo.mark_recording_uploading_if_capture_active(
        scope,
        domain.MarkRecordingUploading(
            recording_id=created.recording.id,
            expected_version=created.recording.version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    completed_upload = repo.complete_recording_upload_if_capture_active(
        scope,
        domain.CompleteRecordingUpload(
            recording_id=uploading.id,
            expected_version=uploading.version,
            observed_content_type="audio/webm",
            observed_size_bytes=456,
            completed_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    with pytest.raises(RepositoryError) as no_quality:
        repo.complete_capture_if_required_usable(
            scope,
            domain.CompleteCapture(
                assessment_id=assessment.id,
                expected_version=assessment.version,
            ),
            correlation_id="0123456789abcdef0123456789abcdef",
        )

    assert completed_upload.recording.upload_state.value == "uploaded"
    assert completed_upload.recording.verified_checksum is None
    assert completed_upload.processing_run.stage.value == "upload_verification"
    assert completed_upload.processing_run.state.value == "queued"
    with pytest.raises(RepositoryError) as checksum_mismatch:
        repo.verify_recording_upload(
            scope,
            domain.VerifyRecordingUpload(
                recording_id=uploading.id,
                expected_version=completed_upload.recording.version,
                verified_content_type="audio/webm",
                verified_size_bytes=456,
                server_computed_checksum="sha256:fedcba9876543210fedcba9876543210",
                verified_at=datetime.now(timezone.utc),
            ),
            correlation_id="0123456789abcdef0123456789abcdef",
        )
    assert checksum_mismatch.value.code == "upload_verification_failed"
    still_unverified = session.scalar(
        select(RecordingRecord).where(RecordingRecord.recording_id == uploading.id)
    )
    assert still_unverified is not None
    assert still_unverified.upload_state == "uploaded"
    assert still_unverified.verified_checksum is None
    assert still_unverified.version == completed_upload.recording.version
    verified = repo.verify_recording_upload(
        scope,
        domain.VerifyRecordingUpload(
            recording_id=uploading.id,
            expected_version=completed_upload.recording.version,
            verified_content_type="audio/webm",
            verified_size_bytes=456,
            server_computed_checksum="sha256:0123456789abcdef0123456789abcdef",
            verified_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    assert no_quality.value.code == "capture_incomplete"

    with pytest.raises(RepositoryError) as no_quality_after_verification:
        repo.complete_capture_if_required_usable(
            scope,
            domain.CompleteCapture(
                assessment_id=assessment.id,
                expected_version=assessment.version,
            ),
            correlation_id="0123456789abcdef0123456789abcdef",
        )

    assert no_quality_after_verification.value.code == "required_activity_not_usable"
    session.add(
        RecordingQualityResultRecord(
            recording_quality_result_id="quality_opaque_01",
            organization_id=scope.organization_id,
            recording_id=created.recording.id,
            status="usable",
            unavailable_checks_json=[],
            provenance="task-four-worker",
            evaluated_at=datetime.now(timezone.utc),
            version=1,
        )
    )
    session.flush()

    completed_capture = repo.complete_capture_if_required_usable(
        scope,
        domain.CompleteCapture(
            assessment_id=assessment.id,
            expected_version=assessment.version,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert verified.recording.upload_state.value == "verified"
    assert verified.recording.verified_checksum == "sha256:0123456789abcdef0123456789abcdef"
    assert completed_capture.state is AssessmentState.PROCESSING
    assert completed_capture.version == assessment.version + 1


def test_recording_quality_processing_and_delete_remain_tenant_scoped_and_idempotent(
    session: Session,
) -> None:
    assert all(
        hasattr(AssessmentRepository, method)
        for method in (
            "get_recording_quality_if_consented",
            "get_processing_run_if_consented",
            "mark_recording_deleted_if_consented",
        )
    )
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-request-03",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    session.add(
        RecordingQualityResultRecord(
            recording_quality_result_id="quality_opaque_02",
            organization_id=scope.organization_id,
            recording_id=created.recording.id,
            status="usable",
            unavailable_checks_json=[],
            provenance="task-four-worker",
            evaluated_at=datetime.now(timezone.utc),
            version=1,
        )
    )
    stored_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )
    assert stored_assessment is not None
    stored_assessment.state = AssessmentState.PROCESSING.value
    stored_assessment.version += 1
    session.flush()

    quality = repo.get_recording_quality_if_consented(scope, created.recording.id)
    run = repo.get_processing_run_if_consented(scope, created.processing_run.id)
    deleted = repo.mark_recording_deleted_if_consented(
        scope,
        created.recording.id,
        created.recording.version,
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    deleted_again = repo.mark_recording_deleted_if_consented(
        scope,
        created.recording.id,
        deleted.version,
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    invalidated_quality = repo.get_recording_quality_if_consented(scope, created.recording.id)
    invalidated_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )

    assert quality is not None and quality.status.value == "usable"
    assert invalidated_quality is not None
    assert invalidated_quality.status.value == "unavailable"
    assert invalidated_quality.unavailable_checks == ("recording_deleted",)
    assert invalidated_assessment is not None
    assert invalidated_assessment.state == AssessmentState.CAPTURING.value
    assert run is not None and run.id == created.processing_run.id
    assert deleted.upload_state.value == "failed"
    assert deleted_again.upload_state.value == "failed"
    stored_run = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == created.processing_run.id
        )
    )
    assert stored_run is not None and stored_run.state == "cancelled"


def test_delete_persists_tombstone_before_storage_and_retries_cleanup_safely(
    session: Session,
) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=456,
            checksum="sha256:0123456789abcdef0123456789abcdef",
            idempotency_key="recording-delete-race-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    observed_states: list[str] = []

    class _Storage:
        def __init__(self) -> None:
            self.calls = 0

        def delete_object(self, object_key: str) -> StorageDeletionResult:
            self.calls += 1
            stored = session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == created.recording.id,
                )
            )
            assert stored is not None
            observed_states.append(stored.upload_state)
            if self.calls == 1:
                raise StorageUnavailableError()
            return StorageDeletionResult(deleted=True, status="deleted")

    storage = _Storage()
    service = AssessmentService(
        repo,
        CurrentUser(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            role=scope.role,
            display_name="Synthetic Therapist",
        ),
        storage=storage,
    )

    with pytest.raises(ClinicalPolicyError) as failed_cleanup:
        service.delete_recording(created.recording.id, "0123456789abcdef0123456789abcdef")

    # Simulate the request transaction being rolled back after Storage fails.
    # The tombstone must already be durable before that rollback can happen.
    session.rollback()
    tombstone = session.scalar(
        select(RecordingRecord).where(
            RecordingRecord.organization_id == scope.organization_id,
            RecordingRecord.recording_id == created.recording.id,
        )
    )
    assert failed_cleanup.value.code == "storage_unavailable"
    assert observed_states == ["failed"]
    assert tombstone is not None
    assert tombstone.upload_state == "failed"
    assert session.scalar(
        select(ProcessingRunRecord.state).where(
            ProcessingRunRecord.organization_id == scope.organization_id,
            ProcessingRunRecord.recording_id == created.recording.id,
        )
    ) == "cancelled"

    assert service.delete_recording(created.recording.id, "0123456789abcdef0123456789abcdef") is True
    assert observed_states == ["failed", "failed"]
    cleanup_run = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.organization_id == scope.organization_id,
            ProcessingRunRecord.recording_id == created.recording.id,
            ProcessingRunRecord.stage == "cleanup",
        )
    )
    assert cleanup_run is not None
    assert cleanup_run.state == "succeeded"


def test_sqlite_worker_claims_upload_then_quality_runs_from_durable_state(
    session: Session,
) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    payload = b"capture"
    checksum = "sha256:" + __import__("hashlib").sha256(payload).hexdigest()
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=len(payload),
            checksum=checksum,
            idempotency_key="recording-worker-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    uploading = repo.mark_recording_uploading_if_capture_active(
        scope,
        domain.MarkRecordingUploading(
            recording_id=created.recording.id,
            expected_version=created.recording.version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.complete_recording_upload_if_capture_active(
        scope,
        domain.CompleteRecordingUpload(
            recording_id=uploading.id,
            expected_version=uploading.version,
            observed_content_type="audio/webm",
            observed_size_bytes=len(payload),
            completed_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    class _Storage:
        def download_object(self, object_key: str) -> bytes:
            assert object_key.startswith("capture/")
            return payload

        def delete_object(self, object_key: str) -> None:
            del object_key

    upload_result = CaptureProcessingWorker(repo, _Storage()).run_once()
    assert upload_result.status == "verified"
    quality_result = CaptureProcessingWorker(
        repo,
        _Storage(),
        probe=type(
            "Probe",
            (),
            {"probe": lambda _self, _path: MediaQuality(135.0, -24.0, 0.1, 1.0, ())},
        )(),
    ).run_once()
    assert quality_result.status == "quality_recorded"


def test_client_idempotency_key_cannot_collide_with_worker_quality_key(
    session: Session,
) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    payload = b"capture"
    checksum = "sha256:" + __import__("hashlib").sha256(payload).hexdigest()
    first = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=len(payload),
            checksum=checksum,
            idempotency_key="recording-worker-collision-source",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.mark_recording_uploading_if_capture_active(
        scope,
        domain.MarkRecordingUploading(
            recording_id=first.recording.id,
            expected_version=first.recording.version,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.complete_recording_upload_if_capture_active(
        scope,
        domain.CompleteRecordingUpload(
            recording_id=first.recording.id,
            expected_version=2,
            observed_content_type="audio/webm",
            observed_size_bytes=len(payload),
            completed_at=datetime.now(timezone.utc),
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="shared_book",
            content_type="audio/webm",
            size_bytes=len(payload),
            checksum=checksum,
            idempotency_key=f"quality-{first.recording.id}",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    class _Storage:
        def download_object(self, object_key: str) -> bytes:
            del object_key
            return payload

    result = CaptureProcessingWorker(repo, _Storage()).run_once()

    assert result.status == "verified"


def test_worker_cancels_queued_capture_processing_after_consent_withdrawal(
    session: Session,
) -> None:
    repo, scope, child, assessment, domain = _ready_capture_repository(session)
    created = repo.create_recording_if_capture_active(
        scope,
        domain.CreateRecording(
            assessment_id=assessment.id,
            activity_code="free_play",
            content_type="audio/webm",
            size_bytes=7,
            checksum="sha256:" + "a" * 64,
            idempotency_key="recording-worker-consent-01",
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.add_consent(
        scope,
        child.id,
        domain.RecordConsent(
            purpose=domain.ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="capture-v2",
            status=domain.ConsentStatus.WITHDRAWN,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert repo.claim_next_processing_run() is None
    run = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.organization_id == scope.organization_id,
            ProcessingRunRecord.processing_run_id == created.processing_run.id,
        )
    )
    assert run is not None
    assert run.state == "cancelled"


def test_transcript_revisions_are_append_only_and_attestation_is_versioned(
    session: Session,
) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    stored_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )
    assert stored_assessment is not None
    stored_assessment.state = domain.AssessmentState.PROCESSING.value
    session.flush()
    first_content = "@UTF8\n@Begin\n*CHI: hello .\n@End\n"
    second_content = "@UTF8\n@Begin\n*CHI: hello world .\n@End\n"

    first = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content=first_content,
            source=domain.TranscriptSource.MANUAL,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    second = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content=second_content,
            source=domain.TranscriptSource.MANUAL,
            expected_revision=first.revision,
            expected_version=first.version,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert first.revision == 1
    assert first.review_state is domain.TranscriptReviewState.DRAFT
    assert first.content_sha256 == sha256(first_content.encode("utf-8")).hexdigest()
    stored_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )
    assert stored_assessment is not None
    assert stored_assessment.state == domain.AssessmentState.REVIEW_REQUIRED.value
    assert second.revision == 2
    assert second.review_state is domain.TranscriptReviewState.DRAFT
    stored_first = session.scalar(
        select(TranscriptRevisionRecord).where(
            TranscriptRevisionRecord.transcript_revision_id == first.id
        )
    )
    assert stored_first is not None
    assert stored_first.review_state == domain.TranscriptReviewState.SUPERSEDED.value
    assert stored_first.version == 2
    assert session.scalar(
        select(AuditEventRecord).where(
            AuditEventRecord.target_id == first.id,
            AuditEventRecord.action == "transcript.revision_superseded",
        )
    ) is not None

    with pytest.raises(RepositoryError, match="stale_transcript_version"):
        repo.create_transcript_revision(
            scope,
            CreateTranscriptRevision(
                assessment_id=assessment.id,
                content="@UTF8\n@Begin\n*CHI: stale .\n@End\n",
                source=domain.TranscriptSource.MANUAL,
                expected_revision=first.revision,
                expected_version=first.version,
            ),
            correlation_id="0123456789abcdef0123456789abcdef",
        )

    attested = repo.attest_transcript(
        scope,
        AttestTranscript(transcript_revision_id=second.id, expected_version=second.version),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert attested.review_state is domain.TranscriptReviewState.ATTESTED
    assert attested.attested_by_user_id == scope.user_id
    assert attested.attested_at is not None


def _adapted_evidence(input_sha256: str) -> AdaptedEvidence:
    provenance = EvidenceProvenance(
        input_ref="transcript_input_opaque_01",
        input_sha256=input_sha256,
        protocol_version_key="thai_guided_language_sample:v0",
        extractor="reviewed-transcript-adapter",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 7, 8, 2, tzinfo=timezone.utc),
    )
    return AdaptedEvidence(
        state=EvidenceState.COMPLETED,
        features=(
            MeasuredFeature(
                key="child_token_count",
                value=12,
                unit="tokens",
                source=EvidenceSource.REVIEWED_TRANSCRIPT,
                state=EvidenceState.COMPLETED,
                limitation="Descriptive measurement only.",
                provenance=provenance,
            ),
        ),
        limitations=("No compatible reference band was applied.",),
        provenance=provenance,
    )


def test_evidence_run_requires_attested_transcript_and_persists_profile(
    session: Session,
) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    stored_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )
    assert stored_assessment is not None
    stored_assessment.state = domain.AssessmentState.PROCESSING.value
    session.flush()
    content = "@UTF8\n@Begin\n*CHI: hello .\n@End\n"
    transcript = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content=content,
            source=domain.TranscriptSource.MANUAL,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    adapted = _adapted_evidence(transcript.content_sha256)

    with pytest.raises(RepositoryError) as raised:
        repo.create_evidence_run(
            scope,
            assessment.id,
            transcript.id,
            adapted,
            correlation_id="0123456789abcdef0123456789abcdef",
        )
    assert raised.value.code == "transcript_not_reviewable"

    repo.attest_transcript(
        scope,
        AttestTranscript(transcript_revision_id=transcript.id, expected_version=1),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    run = repo.create_evidence_run(
        scope,
        assessment.id,
        transcript.id,
        adapted,
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repeated = repo.create_evidence_run(
        scope,
        assessment.id,
        transcript.id,
        adapted,
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    assert run.id == repeated.id
    assert run.state is EvidenceState.COMPLETED
    assert run.profile.not_diagnostic is True
    assert len(run.profile.features) == 1
    assert len(run.profile.domains) == len(tuple(DevelopmentalDomain))
    stored_run = session.scalar(
        select(EvidenceRunRecord).where(EvidenceRunRecord.evidence_run_id == run.id)
    )
    stored_feature = session.scalar(
        select(EvidenceFeatureRecord).where(EvidenceFeatureRecord.evidence_run_id == run.id)
    )
    stored_domain = session.scalar(
        select(EvidenceDomainProfileRecord).where(EvidenceDomainProfileRecord.evidence_run_id == run.id)
    )
    assert stored_run is not None
    assert stored_run.input_sha256 == transcript.content_sha256
    assert stored_feature is not None
    assert stored_feature.value_json == 12
    assert stored_domain is not None
    assert stored_domain.status == "descriptive_only"


def test_new_transcript_revision_stales_dependent_evidence_run(session: Session) -> None:
    repo, scope, _, assessment, domain = _ready_capture_repository(session)
    stored_assessment = session.scalar(
        select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
    )
    assert stored_assessment is not None
    stored_assessment.state = domain.AssessmentState.PROCESSING.value
    session.flush()
    first_content = "@UTF8\n@Begin\n*CHI: hello .\n@End\n"
    first_transcript = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content=first_content,
            source=domain.TranscriptSource.MANUAL,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.attest_transcript(
        scope,
        AttestTranscript(transcript_revision_id=first_transcript.id, expected_version=1),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    run = repo.create_evidence_run(
        scope,
        assessment.id,
        first_transcript.id,
        _adapted_evidence(first_transcript.content_sha256),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    second = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content="@UTF8\n@Begin\n*CHI: hello world .\n@End\n",
            source=domain.TranscriptSource.MANUAL,
            expected_revision=first_transcript.revision,
            expected_version=2,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    stored_run = session.scalar(
        select(EvidenceRunRecord).where(EvidenceRunRecord.evidence_run_id == run.id)
    )
    current = repo.get_current_evidence(scope, assessment.id)
    assert second.review_state is domain.TranscriptReviewState.DRAFT
    assert stored_run is not None
    assert stored_run.state == EvidenceState.STALE.value
    assert stored_run.version == 2
    assert current is None
