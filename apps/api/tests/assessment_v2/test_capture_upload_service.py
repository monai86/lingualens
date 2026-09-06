from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import import_module

import pytest

from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    ProcessingRunStage,
    ProcessingRunState,
    RecordingUploadState,
)
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.assessment_v2.storage import (
    SignedDownloadGrant,
    SignedUploadGrant,
    StorageObjectMetadata,
    StorageUnavailableError,
)
from app.core.security import CurrentUser


UTC = timezone.utc


class _CaptureRepository:
    def __init__(self) -> None:
        domain = import_module("app.assessment_v2.domain.models")
        self.assessment = AssessmentSnapshot(
            id="assessment_opaque_01",
            organization_id="org_alpha",
            child_id="child_opaque_01",
            purpose=AssessmentPurpose.INITIAL,
            state=AssessmentState.CAPTURING,
            assigned_clinician_id="therapist_01",
            version=3,
            age_months=36,
            language_context={"primary": "th", "additional": []},
        )
        self.recording = domain.RecordingSnapshot(
            id="recording_opaque_01",
            organization_id="org_alpha",
            assessment_id=self.assessment.id,
            protocol_version_key="thai_guided_language_sample:v0",
            activity_code="free_play",
            declared_content_type="audio/webm",
            declared_size_bytes=456,
            declared_checksum="sha256:0123456789abcdef0123456789abcdef",
            object_key="capture/0123456789abcdef0123456789abcdef",
            upload_state=RecordingUploadState.PENDING,
            expires_at=datetime(2026, 9, 6, tzinfo=UTC) + timedelta(hours=2),
            verified_content_type=None,
            verified_size_bytes=None,
            verified_checksum=None,
            verified_at=None,
            version=1,
        )
        self.completed = False

    def get_recording_if_consented(self, scope, recording_id: str):
        return self.recording if recording_id == self.recording.id else None

    def mark_recording_uploading_if_capture_active(self, scope, command, correlation_id: str):
        assert command.recording_id == self.recording.id
        assert command.expected_version == self.recording.version
        self.recording = replace(
            self.recording,
            upload_state=RecordingUploadState.UPLOADING,
            expires_at=command.expires_at,
            version=self.recording.version + 1,
        )
        return self.recording

    def complete_recording_upload_if_capture_active(self, scope, command, correlation_id: str):
        assert command.recording_id == self.recording.id
        assert command.expected_version == self.recording.version
        self.completed = True
        self.recording = replace(
            self.recording,
            upload_state=RecordingUploadState.VERIFIED,
            verified_content_type=command.verified_content_type,
            verified_size_bytes=command.verified_size_bytes,
            verified_checksum=command.verified_checksum,
            verified_at=command.verified_at,
            version=self.recording.version + 1,
        )
        domain = import_module("app.assessment_v2.domain.models")
        return domain.RecordingIntentSnapshot(
            recording=self.recording,
            processing_run=domain.ProcessingRunSnapshot(
                id="run_opaque_01",
                organization_id="org_alpha",
                recording_id=self.recording.id,
                stage=ProcessingRunStage.QUALITY_ANALYSIS,
                state=ProcessingRunState.QUEUED,
                attempt_count=0,
                available_at=datetime(2026, 9, 6, tzinfo=UTC),
                error_code=None,
            ),
        )


class _Storage:
    def __init__(self, metadata: StorageObjectMetadata | None = None) -> None:
        self.metadata = metadata or StorageObjectMetadata(
            content_type="audio/webm",
            size_bytes=456,
            etag="opaque-etag",
            checksum=None,
        )
        self.metadata_requests: list[tuple[str, str | None, int | None]] = []

    def create_signed_upload_grant(self, object_key: str, content_type: str, declared_size_bytes: int):
        return SignedUploadGrant(
            tus_endpoint="https://project-ref.supabase.co/storage/v1/upload/resumable",
            headers={"x-signature": "opaque-signature"},
            upload_metadata={"objectName": object_key},
            bucket="capture-private",
            object_key=object_key,
            expires_at=datetime(2026, 9, 6, tzinfo=UTC) + timedelta(minutes=30),
            expires_in_seconds=1800,
            chunk_size_bytes=1024,
            upload_length_bytes=declared_size_bytes,
            content_type=content_type,
            upsert=False,
        )

    def get_object_metadata(
        self,
        object_key: str,
        *,
        expected_content_type: str | None = None,
        expected_size_bytes: int | None = None,
    ) -> StorageObjectMetadata:
        self.metadata_requests.append((object_key, expected_content_type, expected_size_bytes))
        return self.metadata

    def create_signed_download_grant(self, object_key: str) -> SignedDownloadGrant:
        return SignedDownloadGrant(
            url="https://project-ref.supabase.co/storage/v1/object/sign/capture-private/opaque",
            expires_at=datetime(2026, 9, 6, tzinfo=UTC) + timedelta(minutes=15),
            expires_in_seconds=900,
        )


def _service(repository: _CaptureRepository, storage: _Storage) -> AssessmentService:
    service = AssessmentService(
        repository,
        CurrentUser(
            user_id="therapist_01",
            organization_id="org_alpha",
            role="therapist",
            display_name="Synthetic Therapist",
        ),
        storage=storage,
    )
    service.now = lambda: datetime(2026, 9, 6, tzinfo=UTC)
    return service


def test_upload_intent_and_completion_use_declared_metadata_then_queue_quality_work() -> None:
    assert all(
        hasattr(AssessmentService, method)
        for method in ("create_upload_intent", "complete_upload")
    )
    repository = _CaptureRepository()
    storage = _Storage()
    service = _service(repository, storage)

    uploading, grant = service.create_upload_intent(
        "recording_opaque_01", "0123456789abcdef0123456789abcdef"
    )
    completed = service.complete_upload("recording_opaque_01", "0123456789abcdef0123456789abcdef")

    assert uploading.upload_state is RecordingUploadState.UPLOADING
    assert grant.object_key == "capture/0123456789abcdef0123456789abcdef"
    assert completed.recording.upload_state is RecordingUploadState.VERIFIED
    assert completed.processing_run.stage is ProcessingRunStage.QUALITY_ANALYSIS
    assert completed.processing_run.state is ProcessingRunState.QUEUED
    assert storage.metadata_requests == [
        ("capture/0123456789abcdef0123456789abcdef", "audio/webm", 456)
    ]
    assert repository.completed is True


def test_complete_upload_rejects_metadata_mismatch_without_marking_recording_verified() -> None:
    assert hasattr(AssessmentService, "complete_upload")
    repository = _CaptureRepository()
    repository.recording = replace(repository.recording, upload_state=RecordingUploadState.UPLOADING)
    storage = _Storage(
        StorageObjectMetadata(
            content_type="audio/wav",
            size_bytes=456,
            etag="opaque-etag",
            checksum=None,
        )
    )

    with pytest.raises(ClinicalPolicyError) as raised:
        _service(repository, storage).complete_upload(
            "recording_opaque_01", "0123456789abcdef0123456789abcdef"
        )

    assert raised.value.code == "upload_verification_failed"
    assert repository.recording.upload_state is RecordingUploadState.UPLOADING
    assert repository.completed is False


def test_upload_intent_maps_private_storage_failure_to_a_safe_503() -> None:
    assert hasattr(AssessmentService, "create_upload_intent")

    class _UnavailableStorage(_Storage):
        def create_signed_upload_grant(self, object_key: str, content_type: str, declared_size_bytes: int):
            raise StorageUnavailableError()

    with pytest.raises(ClinicalPolicyError) as raised:
        _service(_CaptureRepository(), _UnavailableStorage()).create_upload_intent(
            "recording_opaque_01", "0123456789abcdef0123456789abcdef"
        )

    assert raised.value.code == "storage_unavailable"
    assert raised.value.status_code == 503


def test_download_intent_requires_verified_recording_and_returns_only_private_grant() -> None:
    assert hasattr(AssessmentService, "download_intent")
    repository = _CaptureRepository()
    storage = _Storage()

    with pytest.raises(ClinicalPolicyError) as pending:
        _service(repository, storage).download_intent("recording_opaque_01")

    repository.recording = replace(
        repository.recording,
        upload_state=RecordingUploadState.VERIFIED,
        verified_at=datetime(2026, 9, 6, tzinfo=UTC),
    )
    recording, grant = _service(repository, storage).download_intent("recording_opaque_01")

    assert pending.value.code == "recording_not_verified"
    assert recording.id == "recording_opaque_01"
    assert grant.url.startswith("https://project-ref.supabase.co/storage/v1/object/sign/")
    assert "/public/" not in grant.url
