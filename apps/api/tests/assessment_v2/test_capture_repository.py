from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from importlib import import_module

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    OrganizationMembershipRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingQualityResultRecord,
    RecordingRecord,
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
    RecordConsent,
)
from app.core.security import CurrentUser
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.assessment_v2.storage import StorageDeletionResult, StorageUnavailableError
from app.assessment_v2.quality import MediaQuality
from app.assessment_v2.worker import CaptureProcessingWorker


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

    assert quality is not None and quality.status.value == "usable"
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
