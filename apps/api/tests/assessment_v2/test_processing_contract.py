from datetime import datetime, timezone

import pytest

from app.assessment_v2.domain.models import (
    ProcessingRunSnapshot,
    ProcessingRunStage,
    ProcessingRunState,
)


UTC = timezone.utc


def _evidence_snapshot(**overrides: object) -> ProcessingRunSnapshot:
    values: dict[str, object] = {
        "id": "processing_run_opaque_01",
        "organization_id": "org_opaque_01",
        "recording_id": None,
        "assessment_id": "assessment_opaque_01",
        "transcript_revision_id": "transcript_revision_opaque_01",
        "stage": ProcessingRunStage.EVIDENCE_EXTRACTION,
        "state": ProcessingRunState.QUEUED,
        "attempt_count": 0,
        "max_attempts": 3,
        "available_at": datetime(2026, 9, 8, tzinfo=UTC),
        "error_code": None,
        "result_available": False,
        "can_retry": False,
        "can_cancel": True,
        "version": 1,
    }
    values.update(overrides)
    return ProcessingRunSnapshot(**values)


def _capture_snapshot(**overrides: object) -> ProcessingRunSnapshot:
    values: dict[str, object] = {
        "id": "processing_run_opaque_02",
        "organization_id": "org_opaque_01",
        "recording_id": "recording_opaque_01",
        "assessment_id": None,
        "transcript_revision_id": None,
        "stage": ProcessingRunStage.UPLOAD_VERIFICATION,
        "state": ProcessingRunState.QUEUED,
        "attempt_count": 0,
        "max_attempts": 3,
        "available_at": datetime(2026, 9, 8, tzinfo=UTC),
        "error_code": None,
        "result_available": False,
        "can_retry": False,
        "can_cancel": False,
        "version": 1,
    }
    values.update(overrides)
    return ProcessingRunSnapshot(**values)


def test_evidence_processing_snapshot_exposes_recovery_state_without_sensitive_worker_fields() -> None:
    snapshot = _evidence_snapshot()

    assert snapshot.id == "processing_run_opaque_01"
    assert snapshot.organization_id == "org_opaque_01"
    assert snapshot.recording_id is None
    assert snapshot.assessment_id == "assessment_opaque_01"
    assert snapshot.transcript_revision_id == "transcript_revision_opaque_01"
    assert snapshot.stage is ProcessingRunStage.EVIDENCE_EXTRACTION
    assert snapshot.state is ProcessingRunState.QUEUED
    assert snapshot.attempt_count == 0
    assert snapshot.max_attempts == 3
    assert snapshot.available_at == datetime(2026, 9, 8, tzinfo=UTC)
    assert snapshot.error_code is None
    assert snapshot.result_available is False
    assert snapshot.can_retry is False
    assert snapshot.can_cancel is True
    assert snapshot.version == 1
    assert not hasattr(snapshot, "lease_token")
    assert not hasattr(snapshot, "content")
    assert not hasattr(snapshot, "transcript_content")


def test_capture_processing_snapshot_remains_recording_targeted_without_public_actions() -> None:
    snapshot = _capture_snapshot()

    assert snapshot.recording_id == "recording_opaque_01"
    assert snapshot.assessment_id is None
    assert snapshot.transcript_revision_id is None
    assert snapshot.result_available is False
    assert snapshot.can_retry is False
    assert snapshot.can_cancel is False


@pytest.mark.parametrize("field_name", ("result_available", "can_retry", "can_cancel"))
def test_capture_processing_snapshot_rejects_results_or_actions(field_name: str) -> None:
    with pytest.raises(ValueError):
        _capture_snapshot(**{field_name: True})


@pytest.mark.parametrize(
    "overrides",
    (
        {"max_attempts": 0},
        {"version": 0},
        {
            "recording_id": None,
            "assessment_id": None,
            "transcript_revision_id": None,
        },
        {
            "recording_id": "recording_opaque_01",
            "assessment_id": "assessment_opaque_01",
            "transcript_revision_id": "transcript_revision_opaque_01",
        },
        {
            "stage": ProcessingRunStage.UPLOAD_VERIFICATION,
            "recording_id": None,
            "assessment_id": "assessment_opaque_01",
            "transcript_revision_id": "transcript_revision_opaque_01",
        },
        {
            "recording_id": "recording_opaque_01",
            "assessment_id": None,
            "transcript_revision_id": None,
        },
        {"transcript_revision_id": None},
    ),
)
def test_processing_snapshot_rejects_invalid_counts_or_target_families(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _evidence_snapshot(**overrides)
