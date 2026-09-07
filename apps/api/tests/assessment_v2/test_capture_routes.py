from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    CaptureSnapshot,
    ProcessingRunSnapshot,
    ProcessingRunStage,
    ProcessingRunState,
    ProtocolActivity,
    ProtocolSelectionSnapshot,
    RecordingIntentSnapshot,
    RecordingQualitySnapshot,
    RecordingQualityStatus,
    RecordingSnapshot,
    RecordingUploadState,
)
from app.assessment_v2.storage import SignedDownloadGrant, SignedUploadGrant
from app.main import app


UTC = timezone.utc


class _CaptureRouteService:
    def __init__(self) -> None:
        self.assessment = AssessmentSnapshot(
            id="assessment_opaque_01",
            organization_id="org_alpha",
            child_id="child_opaque_01",
            purpose=AssessmentPurpose.INITIAL,
            state=AssessmentState.DRAFT,
            assigned_clinician_id="therapist_01",
            version=1,
            age_months=36,
            language_context={"primary": "th", "additional": []},
        )
        self.selection = ProtocolSelectionSnapshot(
            assessment_id=self.assessment.id,
            protocol_version_key="thai_guided_language_sample:v0",
            selected_at=datetime(2026, 9, 6, tzinfo=UTC),
            version=1,
        )
        self.recording = RecordingSnapshot(
            id="recording_opaque_01",
            organization_id="org_alpha",
            assessment_id=self.assessment.id,
            protocol_version_key=self.selection.protocol_version_key,
            activity_code="free_play",
            declared_content_type="audio/webm",
            declared_size_bytes=456,
            declared_checksum="sha256:0123456789abcdef0123456789abcdef",
            object_key="capture/0123456789abcdef0123456789abcdef",
            upload_state=RecordingUploadState.PENDING,
            expires_at=datetime(2026, 9, 6, 1, tzinfo=UTC),
            verified_content_type=None,
            verified_size_bytes=None,
            verified_checksum=None,
            verified_at=None,
            version=1,
        )
        self.run = ProcessingRunSnapshot(
            id="run_opaque_01",
            organization_id="org_alpha",
            recording_id=self.recording.id,
            stage=ProcessingRunStage.UPLOAD_VERIFICATION,
            state=ProcessingRunState.QUEUED,
            attempt_count=0,
            available_at=datetime(2026, 9, 6, tzinfo=UTC),
            error_code=None,
        )

    def _capture(self) -> CaptureSnapshot:
        return CaptureSnapshot(
            assessment=self.assessment,
            protocol_selection=self.selection,
            activities=(
                ProtocolActivity(
                    activity_key="free_play",
                    required=True,
                    target_duration_seconds=180,
                    minimum_duration_seconds=120,
                ),
            ),
            recordings=(self.recording,),
            quality_results=(),
        )

    def select_protocol(self, assessment_id: str, correlation_id: str) -> CaptureSnapshot:
        assert assessment_id == self.assessment.id
        self.assessment = replace(
            self.assessment,
            state=AssessmentState.READY_FOR_CAPTURE,
            version=2,
        )
        return self._capture()

    def get_capture(self, assessment_id: str) -> CaptureSnapshot:
        assert assessment_id == self.assessment.id
        return self._capture()

    def start_capture(self, assessment_id: str, correlation_id: str) -> AssessmentSnapshot:
        assert assessment_id == self.assessment.id
        self.assessment = replace(self.assessment, state=AssessmentState.CAPTURING, version=3)
        return self.assessment

    def create_recording(self, command, correlation_id: str) -> RecordingIntentSnapshot:
        assert command.assessment_id == self.assessment.id
        assert command.activity_code == "free_play"
        assert command.idempotency_key == "recording-request-01"
        return RecordingIntentSnapshot(recording=self.recording, processing_run=self.run)

    def create_upload_intent(self, recording_id: str, correlation_id: str):
        assert recording_id == self.recording.id
        self.recording = replace(
            self.recording,
            upload_state=RecordingUploadState.UPLOADING,
            version=2,
        )
        return self.recording, SignedUploadGrant(
            tus_endpoint="https://project-ref.supabase.co/storage/v1/upload/resumable",
            headers={"x-signature": "opaque-signature"},
            upload_metadata={"objectName": self.recording.object_key},
            bucket="capture-private",
            object_key=self.recording.object_key,
            expires_at=datetime(2026, 9, 6, 1, tzinfo=UTC),
            expires_in_seconds=1800,
            chunk_size_bytes=1024,
            upload_length_bytes=456,
            content_type="audio/webm",
            upsert=False,
            url="https://project-ref.supabase.co/storage/v1/object/upload/sign/capture-private/token",
        )

    def complete_upload(self, recording_id: str, correlation_id: str) -> RecordingIntentSnapshot:
        assert recording_id == self.recording.id
        self.recording = replace(
            self.recording,
            upload_state=RecordingUploadState.UPLOADED,
            verified_at=None,
            version=3,
        )
        self.run = replace(
            self.run,
            stage=ProcessingRunStage.UPLOAD_VERIFICATION,
            state=ProcessingRunState.QUEUED,
        )
        return RecordingIntentSnapshot(recording=self.recording, processing_run=self.run)

    def get_recording(self, recording_id: str) -> RecordingSnapshot:
        assert recording_id == self.recording.id
        return self.recording

    def get_recording_quality(self, recording_id: str) -> RecordingQualitySnapshot:
        assert recording_id == self.recording.id
        return RecordingQualitySnapshot(
            id="quality_opaque_01",
            organization_id="org_alpha",
            recording_id=recording_id,
            status=RecordingQualityStatus.USABLE,
            measured_duration_seconds=None,
            measured_loudness_db=None,
            measured_silence_ratio=None,
            measured_decodability=None,
            unavailable_checks=(),
            provenance="task-four-worker",
            evaluated_at=datetime(2026, 9, 6, tzinfo=UTC),
            version=1,
        )

    def download_intent(self, recording_id: str):
        assert recording_id == self.recording.id
        return self.recording, SignedDownloadGrant(
            url="https://project-ref.supabase.co/storage/v1/object/sign/capture-private/opaque",
            expires_at=datetime(2026, 9, 6, tzinfo=UTC),
            expires_in_seconds=900,
        )

    def delete_recording(self, recording_id: str, correlation_id: str) -> bool:
        assert recording_id == self.recording.id
        return True

    def complete_capture(self, assessment_id: str, correlation_id: str) -> AssessmentSnapshot:
        assert assessment_id == self.assessment.id
        self.assessment = replace(self.assessment, state=AssessmentState.PROCESSING, version=4)
        return self.assessment

    def get_processing_run(self, processing_run_id: str) -> ProcessingRunSnapshot:
        assert processing_run_id == self.run.id
        return self.run


@pytest.fixture
def capture_client() -> tuple[TestClient, _CaptureRouteService]:
    service = _CaptureRouteService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        yield TestClient(app), service
    finally:
        app.dependency_overrides.clear()


def test_capture_route_selection_start_intent_and_safe_progress_contract(
    capture_client: tuple[TestClient, _CaptureRouteService],
) -> None:
    client, _ = capture_client
    assessment_id = "assessment_opaque_01"

    selected = client.post(f"/api/v2/assessments/{assessment_id}/protocol-selection", json={})
    started = client.post(f"/api/v2/assessments/{assessment_id}/capture/start")
    missing_idempotency = client.post(
        f"/api/v2/assessments/{assessment_id}/activities/free_play/recordings",
        json={
            "content_type": "audio/webm",
            "size_bytes": 456,
                "checksum": "sha256:" + "0" * 64,
        },
    )
    created = client.post(
        f"/api/v2/assessments/{assessment_id}/activities/free_play/recordings",
        headers={"Idempotency-Key": "recording-request-01"},
        json={
            "content_type": "audio/webm",
            "size_bytes": 456,
                "checksum": "sha256:" + "0" * 64,
        },
    )
    capture = client.get(f"/api/v2/assessments/{assessment_id}/capture")

    assert selected.status_code == 200
    assert selected.json()["state"] == "ready_for_capture"
    assert started.status_code == 200
    assert started.json() == {
        "assessment_id": assessment_id,
        "state": "capturing",
        "version": 3,
    }
    assert missing_idempotency.status_code == 422
    assert missing_idempotency.json()["error"]["code"] == "request_validation_failed"
    assert created.status_code == 201
    assert created.json()["recording"]["activity_code"] == "free_play"
    assert created.json()["processing_run"]["stage"] == "upload_verification"
    assert capture.status_code == 200
    assert capture.json()["progress"] == {
        "required_activities_total": 1,
        "required_activities_verified": 0,
        "required_activities_usable": 0,
    }
    assert "object_key" not in capture.text
    assert "0123456789abcdef0123456789abcdef" not in capture.text


def test_capture_upload_quality_download_delete_complete_and_run_routes_are_safe(
    capture_client: tuple[TestClient, _CaptureRouteService],
) -> None:
    client, _ = capture_client
    recording_id = "recording_opaque_01"
    assessment_id = "assessment_opaque_01"
    run_id = "run_opaque_01"

    upload = client.post(f"/api/v2/recordings/{recording_id}/upload-intent")
    completed_upload = client.post(f"/api/v2/recordings/{recording_id}/complete-upload")
    recording = client.get(f"/api/v2/recordings/{recording_id}")
    quality = client.get(f"/api/v2/recordings/{recording_id}/quality")
    download = client.post(f"/api/v2/recordings/{recording_id}/download-intent")
    deleted = client.delete(f"/api/v2/recordings/{recording_id}")
    completed_capture = client.post(f"/api/v2/assessments/{assessment_id}/capture/complete")
    processing_run = client.get(f"/api/v2/processing-runs/{run_id}")

    assert upload.status_code == 200
    assert "bucket" not in upload.json()["upload"]
    assert "object_key" not in upload.json()["upload"]
    assert "upload_metadata" not in upload.json()["upload"]
    assert "Upload-Metadata" not in upload.text
    assert "capture/0123456789abcdef0123456789abcdef" not in upload.text
    assert upload.json()["upload"]["url"].startswith("https://project-ref.supabase.co/")
    assert completed_upload.status_code == 200
    assert completed_upload.json()["recording"]["upload_state"] == "uploaded"
    assert completed_upload.json()["processing_run"]["stage"] == "upload_verification"
    assert recording.status_code == 200
    assert "object_key" not in recording.text
    assert quality.status_code == 200
    assert quality.json() == {
        "status": "usable",
        "evaluated_at": "2026-09-06T00:00:00Z",
        "version": 1,
    }
    assert download.status_code == 200
    assert "/public/" not in download.json()["download"]["url"]
    assert deleted.status_code == 200
    assert deleted.json() == {"id": recording_id, "deleted": True}
    assert completed_capture.status_code == 200
    assert completed_capture.json()["state"] == "processing"
    assert processing_run.status_code == 200
    assert processing_run.json() == {
        "id": run_id,
        "stage": "upload_verification",
        "state": "queued",
        "attempt_count": 0,
        "error_code": None,
    }
