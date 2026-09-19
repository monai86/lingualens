from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

from app.assessment_v2 import evidence_worker
from app.assessment_v2.db.repositories import EvidenceWorkItem
from app.assessment_v2.domain.models import (
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptRevisionSnapshot,
    TranscriptReviewState,
    TranscriptSource,
)
from app.assessment_v2.domain.segments import TranscriptSegmentSnapshot, TranscriptSegmentSetSnapshot
from app.assessment_v2.evidence import EvidenceProvenance, EvidenceState
from app.assessment_v2.evidence_adapter import AdaptedEvidence


PROTOCOL_KEY = "thai_guided_language_sample:v0"
CONTENT = "@UTF8\n@Begin\n*CHI:\thello .\n@End\n"
CONTENT_SHA256 = sha256(CONTENT.encode()).hexdigest()


def _item() -> EvidenceWorkItem:
    transcript = TranscriptRevisionSnapshot(
        id="transcript_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.ATTESTED,
        content=CONTENT,
        content_sha256=CONTENT_SHA256,
        created_by_user_id="therapist_opaque_01",
        created_at=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
        attested_by_user_id="therapist_opaque_01",
        attested_at=datetime(2026, 9, 8, 12, 1, tzinfo=timezone.utc),
        version=2,
    )
    return EvidenceWorkItem(
        run_id="processing_run_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        transcript_revision_id="transcript_opaque_01",
        protocol_version_key=PROTOCOL_KEY,
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        content_sha256=CONTENT_SHA256,
        lease_token="lease_token_opaque_01",
        lease_expires_at=datetime(2026, 9, 8, 12, 3, tzinfo=timezone.utc),
        attempt_count=1,
        max_attempts=3,
        transcript=transcript,
        segment_set=TranscriptSegmentSetSnapshot(
            id="segment_set_opaque_01",
            organization_id=transcript.organization_id,
            assessment_id=transcript.assessment_id,
            transcript_revision_id=transcript.id,
            transcript_content_sha256=transcript.content_sha256,
            recording_id=None,
            revision=1,
            source=TranscriptSource.MANUAL,
            review_state=TranscriptReviewState.ATTESTED,
            segments_sha256="b" * 64,
            segments=(
                TranscriptSegmentSnapshot(
                    id="segment_opaque_01",
                    organization_id=transcript.organization_id,
                    segment_set_id="segment_set_opaque_01",
                    ordinal=1,
                    start_ms=0,
                    end_ms=900,
                    speaker_role=TranscriptSegmentSpeakerRole.CHILD,
                    text="hello .",
                    confidence=0.99,
                    uncertainty_reason=TranscriptSegmentUncertaintyReason.NONE,
                    created_at=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
                ),
            ),
            created_by_user_id="therapist_opaque_01",
            created_at=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
            attested_by_user_id="therapist_opaque_01",
            attested_at=datetime(2026, 9, 8, 12, 1, tzinfo=timezone.utc),
            version=2,
        ),
    )


def _adapted(state: EvidenceState) -> AdaptedEvidence:
    provenance = EvidenceProvenance(
        input_ref="transcript-revision:transcript_opaque_01",
        input_sha256=CONTENT_SHA256,
        protocol_version_key=PROTOCOL_KEY,
        extractor="analysis-contract-reviewed-transcript",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 8, 12, 2, tzinfo=timezone.utc),
    )
    return AdaptedEvidence(
        state=state,
        features=(),
        limitations=("The reviewed sample did not contain sufficient measurements.",),
        provenance=provenance,
    )


@dataclass
class FakeRepository:
    item: EvidenceWorkItem | None
    completed: list[tuple[EvidenceWorkItem, AdaptedEvidence]]
    failed: list[tuple[EvidenceWorkItem, str, bool]]
    complete_result: object = object()
    events: list[str] = field(default_factory=list)

    def claim_next_evidence_processing_run(self) -> EvidenceWorkItem | None:
        self.events.append("claim")
        item, self.item = self.item, None
        return item

    def commit_transaction(self) -> None:
        self.events.append("commit")

    def complete_evidence_processing_run(
        self, item: EvidenceWorkItem, adapted: AdaptedEvidence
    ) -> object:
        self.events.append("complete")
        self.completed.append((item, adapted))
        return self.complete_result

    def fail_evidence_processing_run(
        self, item: EvidenceWorkItem, error_code: str, *, retryable: bool
    ) -> None:
        self.events.append("fail")
        self.failed.append((item, error_code, retryable))


def _worker(repository: FakeRepository) -> evidence_worker.EvidenceProcessingWorker:
    return evidence_worker.EvidenceProcessingWorker(repository)


def test_worker_persists_one_result_for_an_attested_revision(monkeypatch) -> None:
    repository = FakeRepository(_item(), [], [])
    monkeypatch.setattr(
        evidence_worker,
        "extract_reviewed_segment_set",
        lambda transcript, segment_set, *, protocol_version_key: object(),
    )
    monkeypatch.setattr(
        evidence_worker,
        "adapt_analysis_result",
        lambda result, **kwargs: _adapted(EvidenceState.COMPLETED),
    )

    result = _worker(repository).run_once()

    assert result.status == "evidence_recorded"
    assert result.run_id == "processing_run_opaque_01"
    assert len(repository.completed) == 1
    assert repository.failed == []
    assert repository.completed[0][0].transcript.content == CONTENT
    assert "hello" not in repr(repository.completed[0][0])


def test_worker_commits_the_lease_before_extraction(monkeypatch) -> None:
    repository = FakeRepository(_item(), [], [])

    def extract(*_args, **_kwargs):
        repository.events.append("extract")
        return object()

    monkeypatch.setattr(evidence_worker, "extract_reviewed_segment_set", extract)
    monkeypatch.setattr(
        evidence_worker,
        "adapt_analysis_result",
        lambda result, **kwargs: _adapted(EvidenceState.COMPLETED),
    )

    result = _worker(repository).run_once()

    assert result.status == "evidence_recorded"
    assert repository.events == ["claim", "commit", "extract", "complete"]


def test_worker_preserves_insufficient_data_as_a_completed_job(monkeypatch) -> None:
    repository = FakeRepository(_item(), [], [])
    monkeypatch.setattr(
        evidence_worker,
        "extract_reviewed_segment_set",
        lambda transcript, segment_set, *, protocol_version_key: object(),
    )
    monkeypatch.setattr(
        evidence_worker,
        "adapt_analysis_result",
        lambda result, **kwargs: _adapted(EvidenceState.INSUFFICIENT_DATA),
    )

    result = _worker(repository).run_once()

    assert result.status == "evidence_recorded"
    assert repository.completed[0][1].state is EvidenceState.INSUFFICIENT_DATA
    assert repository.failed == []


def test_worker_marks_retryable_extraction_failure_without_logging_input(monkeypatch) -> None:
    repository = FakeRepository(_item(), [], [])

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("provider detail must stay out of worker output")

    monkeypatch.setattr(evidence_worker, "extract_reviewed_segment_set", interrupted)

    result = _worker(repository).run_once()

    assert result.status == "failed"
    assert repository.completed == []
    assert len(repository.failed) == 1
    assert repository.failed[0][1:] == ("evidence_processing_failed", True)


def test_worker_reports_cancelled_when_lease_is_no_longer_owned(monkeypatch) -> None:
    repository = FakeRepository(_item(), [], [], complete_result=None)
    monkeypatch.setattr(
        evidence_worker,
        "extract_reviewed_segment_set",
        lambda transcript, segment_set, *, protocol_version_key: object(),
    )
    monkeypatch.setattr(
        evidence_worker,
        "adapt_analysis_result",
        lambda result, **kwargs: _adapted(EvidenceState.COMPLETED),
    )

    result = _worker(repository).run_once()

    assert result.status == "cancelled"
    assert repository.failed == []
