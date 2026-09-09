from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    ProcessingRunSnapshot,
    ProcessingRunStage,
    ProcessingRunState,
)
from app.assessment_v2.services import ClinicalPolicyError
from app.main import app


UTC = timezone.utc


def processing_run(
    *,
    state: ProcessingRunState = ProcessingRunState.QUEUED,
    error_code: str | None = None,
    can_retry: bool = False,
    can_cancel: bool = True,
    version: int = 1,
) -> ProcessingRunSnapshot:
    return ProcessingRunSnapshot(
        id="evidence_processing_run_opaque_01",
        organization_id="org_opaque_01",
        recording_id=None,
        assessment_id="assessment_opaque_01",
        transcript_revision_id="transcript_revision_opaque_01",
        stage=ProcessingRunStage.EVIDENCE_EXTRACTION,
        state=state,
        attempt_count=0,
        max_attempts=3,
        available_at=datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        error_code=error_code,
        result_available=state is ProcessingRunState.SUCCEEDED,
        can_retry=can_retry,
        can_cancel=can_cancel,
        version=version,
    )


class FakeEvidenceProcessingService:
    def __init__(self) -> None:
        self.run = processing_run()
        self.enqueue_calls: list[tuple[str, str]] = []
        self.current_calls: list[str] = []
        self.retry_calls: list[tuple[str, int, str]] = []
        self.cancel_calls: list[tuple[str, int, str]] = []

    def enqueue_current_evidence_processing(self, assessment_id: str, correlation_id: str):
        self.enqueue_calls.append((assessment_id, correlation_id))
        return self.run

    def get_current_evidence_processing_run(self, assessment_id: str):
        self.current_calls.append(assessment_id)
        return self.run

    def get_processing_run(self, processing_run_id: str):
        assert processing_run_id == self.run.id
        return self.run

    def retry_processing_run(self, processing_run_id: str, expected_version: int, correlation_id: str):
        self.retry_calls.append((processing_run_id, expected_version, correlation_id))
        self.run = processing_run(version=expected_version + 1)
        return self.run

    def cancel_processing_run(self, processing_run_id: str, expected_version: int, correlation_id: str):
        self.cancel_calls.append((processing_run_id, expected_version, correlation_id))
        self.run = processing_run(
            state=ProcessingRunState.CANCELLED,
            error_code="cancel_requested",
            can_cancel=False,
            version=expected_version + 1,
        )
        return self.run


@pytest.fixture
def evidence_client() -> Iterator[tuple[TestClient, FakeEvidenceProcessingService]]:
    service = FakeEvidenceProcessingService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        yield TestClient(app), service
    finally:
        app.dependency_overrides.clear()


def test_evidence_action_enqueues_and_is_idempotent_without_worker_fields(
    evidence_client: tuple[TestClient, FakeEvidenceProcessingService],
) -> None:
    client, service = evidence_client

    first = client.post("/api/v2/assessments/assessment_opaque_01/evidence-runs")
    repeat = client.post("/api/v2/assessments/assessment_opaque_01/evidence-runs")

    assert first.status_code == 202
    assert first.json()["processing_run"]["state"] == "queued"
    assert first.json()["processing_run"]["max_attempts"] == 3
    assert first.json()["processing_run"]["can_cancel"] is True
    assert repeat.json()["processing_run"]["id"] == first.json()["processing_run"]["id"]
    assert len(service.enqueue_calls) == 2
    assert "lease_token" not in first.text
    assert "content" not in first.text


def test_evidence_processing_current_run_and_direct_lookup_are_reloadable(
    evidence_client: tuple[TestClient, FakeEvidenceProcessingService],
) -> None:
    client, service = evidence_client

    current = client.get(
        "/api/v2/assessments/assessment_opaque_01/evidence-processing-run"
    )
    direct = client.get(f"/api/v2/processing-runs/{service.run.id}")

    assert current.status_code == direct.status_code == 200
    assert current.json()["processing_run"] == direct.json()
    assert service.current_calls == ["assessment_opaque_01"]


def test_evidence_processing_retry_and_cancel_use_expected_version(
    evidence_client: tuple[TestClient, FakeEvidenceProcessingService],
) -> None:
    client, service = evidence_client

    retried = client.post(
        f"/api/v2/processing-runs/{service.run.id}/retry",
        json={"expected_version": 1},
    )
    cancelled = client.post(
        f"/api/v2/processing-runs/{service.run.id}/cancel",
        json={"expected_version": 2},
    )

    assert retried.status_code == 200
    assert retried.json()["state"] == "queued"
    assert retried.json()["version"] == 2
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    assert cancelled.json()["error_code"] == "cancel_requested"
    assert service.retry_calls[0][1] == 1
    assert service.cancel_calls[0][1] == 2


@pytest.mark.parametrize(
    ("method", "path", "payload", "code"),
    [
        (
            "post",
            "/api/v2/processing-runs/evidence_processing_run_opaque_01/retry",
            {"expected_version": 1},
            "processing_run_not_retryable",
        ),
        (
            "post",
            "/api/v2/processing-runs/evidence_processing_run_opaque_01/cancel",
            {"expected_version": 1},
            "processing_run_not_cancellable",
        ),
    ],
)
def test_evidence_processing_action_errors_remain_safe(
    evidence_client: tuple[TestClient, FakeEvidenceProcessingService],
    monkeypatch,
    method: str,
    path: str,
    payload: dict[str, int],
    code: str,
) -> None:
    client, service = evidence_client
    failure = ClinicalPolicyError(code, 409, "safe processing action message")
    monkeypatch.setattr(service, "retry_processing_run", lambda *_args, **_kwargs: (_ for _ in ()).throw(failure))
    monkeypatch.setattr(service, "cancel_processing_run", lambda *_args, **_kwargs: (_ for _ in ()).throw(failure))

    response = getattr(client, method)(path, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == code
    assert "safe processing action message" in response.json()["error"]["message"]
    assert "lease_token" not in response.text
    assert "content" not in response.text
