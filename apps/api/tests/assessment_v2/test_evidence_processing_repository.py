from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.assessment_v2.db.repositories as repository_module
from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    EvidenceRunRecord,
    OrganizationMembershipRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    TranscriptRevisionRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository, RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentState,
    AttestTranscript,
    ConsentPurpose,
    ConsentStatus,
    CreateAssessment,
    CreateChild,
    CreateTranscriptRevision,
    ProcessingRunState,
    RecordConsent,
    SelectProtocol,
    TranscriptReviewState,
    TranscriptSource,
)
from app.core.security import CurrentUser
from app.assessment_v2.evidence import (
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.evidence_adapter import AdaptedEvidence


CORRELATION_ID = "0123456789abcdef0123456789abcdef"
PROTOCOL_KEY = "thai_guided_language_sample:v0"


@dataclass
class FakeClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: int) -> None:
        self.current += timedelta(**delta)


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
    return AccessScope(
        user_id="therapist_01",
        organization_id="org_alpha",
        role="therapist",
    )


def _seed_evidence_context(
    session: Session,
    *,
    clock: FakeClock | None = None,
) -> tuple[AssessmentRepository, AccessScope, AssessmentRecord, TranscriptRevisionRecord]:
    scope = _scope()
    repository = AssessmentRepository(session, clock=clock)
    repository.synchronize_principal(
        CurrentUser(
            user_id=scope.user_id,
            organization_id=scope.organization_id,
            role=scope.role,
            display_name="Synthetic Therapist",
        ),
        correlation_id=CORRELATION_ID,
    )
    session.add(
        OrganizationMembershipRecord(
            membership_id="membership_evidence_01",
            organization_id=scope.organization_id,
            user_id=scope.user_id,
            role=scope.role,
            active=True,
        )
    )
    session.add(
        ProtocolVersionRecord(
            protocol_version_key=PROTOCOL_KEY,
            primary_language="th",
            minimum_age_months=18,
            maximum_age_months=72,
            supported_purposes=(
                "initial,developmental_follow_up,post_intervention_follow_up,additional_evidence"
            ),
        )
    )
    session.add(
        ProtocolActivityRecord(
            protocol_version_key=PROTOCOL_KEY,
            activity_key="free_play",
            required=True,
            target_duration_seconds=180,
            minimum_duration_seconds=120,
            sort_order=1,
        )
    )
    session.flush()

    child = repository.create_child(
        scope,
        CreateChild(
            display_code="LL-EVIDENCE-01",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": []},
        ),
        correlation_id=CORRELATION_ID,
    )
    repository.add_consent(
        scope,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id=CORRELATION_ID,
    )
    assessment_snapshot = repository.create_assessment(
        scope,
        CreateAssessment(
            child_id=child.id,
            purpose=AssessmentPurpose.INITIAL,
            age_months=36,
            language_context={"primary": "th", "additional": []},
            assigned_clinician_id=scope.user_id,
        ),
        correlation_id=CORRELATION_ID,
    )
    repository.select_protocol_and_ready(
        scope,
        SelectProtocol(
            assessment_id=assessment_snapshot.id,
            protocol_version_key=PROTOCOL_KEY,
            expected_version=assessment_snapshot.version,
        ),
        correlation_id=CORRELATION_ID,
    )
    assessment = session.scalar(
        select(AssessmentRecord).where(
            AssessmentRecord.assessment_id == assessment_snapshot.id
        )
    )
    assert assessment is not None
    # Transcript review is intentionally independent from the capture happy
    # path in this repository fixture.
    assessment.state = AssessmentState.PROCESSING.value
    session.flush()
    transcript_snapshot = repository.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment_snapshot.id,
            content="@UTF8\n@Begin\n*CHI:\thello .\n@End\n",
            source=TranscriptSource.MANUAL,
        ),
        correlation_id=CORRELATION_ID,
    )
    repository.attest_transcript(
        scope,
        AttestTranscript(
            transcript_revision_id=transcript_snapshot.id,
            expected_version=transcript_snapshot.version,
        ),
        correlation_id=CORRELATION_ID,
    )
    transcript = session.scalar(
        select(TranscriptRevisionRecord).where(
            TranscriptRevisionRecord.transcript_revision_id == transcript_snapshot.id
        )
    )
    assert transcript is not None
    return repository, scope, assessment, transcript


def _adapted_evidence(transcript: TranscriptRevisionRecord) -> AdaptedEvidence:
    provenance = EvidenceProvenance(
        input_ref=f"transcript-revision:{transcript.transcript_revision_id}",
        input_sha256=transcript.content_sha256,
        protocol_version_key=PROTOCOL_KEY,
        extractor="analysis-contract-reviewed-transcript",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc),
    )
    return AdaptedEvidence(
        state=EvidenceState.COMPLETED,
        features=(
            MeasuredFeature(
                key="child_token_count",
                value=1,
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


def test_evidence_idempotency_key_is_canonical_and_bounded() -> None:
    identity = ("assessment-01", "transcript-01", "pipeline-v1", "schema-v1")
    first = repository_module._evidence_idempotency_key(*identity)
    repeated = repository_module._evidence_idempotency_key(*identity)
    changed = repository_module._evidence_idempotency_key(
        identity[0], identity[1], "pipeline-v2", identity[3]
    )

    assert first == repeated
    assert first != changed
    assert first.startswith("evidence:v1:")
    assert len(first) <= 128
    assert len(first.removeprefix("evidence:v1:")) == 64


def test_enqueue_is_idempotent_and_requires_current_attested_input(session: Session) -> None:
    repository, scope, assessment, transcript = _seed_evidence_context(session)

    first = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    second = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    assert first.id == second.id
    assert first.state is ProcessingRunState.QUEUED
    assert first.assessment_id == assessment.assessment_id
    assert first.transcript_revision_id == transcript.transcript_revision_id
    assert first.recording_id is None
    assert session.scalar(
        select(func.count(ProcessingRunRecord.processing_run_id)).where(
            ProcessingRunRecord.stage == "evidence_extraction"
        )
    ) == 1

    transcript.review_state = TranscriptReviewState.DRAFT.value
    transcript.version += 1
    session.flush()
    with pytest.raises(RepositoryError, match="transcript_not_reviewable"):
        repository.enqueue_current_evidence_processing(
            scope, assessment.assessment_id, CORRELATION_ID
        )


def test_current_reads_exclude_superseded_analysis_contract(session: Session, monkeypatch) -> None:
    repository, scope, assessment, transcript = _seed_evidence_context(session)
    repository.create_evidence_run(
        scope,
        assessment.assessment_id,
        transcript.transcript_revision_id,
        _adapted_evidence(transcript),
        CORRELATION_ID,
    )
    repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    monkeypatch.setattr(repository_module, "_EVIDENCE_PIPELINE_VERSION", "reviewed-transcript-descriptors-v2")
    monkeypatch.setattr(repository_module, "_EVIDENCE_FEATURE_SCHEMA_VERSION", "descriptive-transcript-features-v2")

    assert repository.get_current_evidence(scope, assessment.assessment_id) is None
    assert repository.get_current_evidence_processing_run(scope, assessment.assessment_id) is None


def test_evidence_claim_is_bound_to_the_worker_tenant(session: Session) -> None:
    repository, scope, assessment, _ = _seed_evidence_context(session)
    repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    other_tenant_repository = AssessmentRepository(
        session,
        worker_organization_id="org_beta",
    )

    assert other_tenant_repository.claim_next_evidence_processing_run() is None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.organization_id == scope.organization_id,
            ProcessingRunRecord.assessment_id == assessment.assessment_id,
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.QUEUED.value


def test_claim_reclaims_expired_lease_and_rejects_stale_completion(session: Session) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc))
    repository, scope, assessment, transcript = _seed_evidence_context(
        session, clock=clock
    )
    repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    first = repository.claim_next_evidence_processing_run()
    assert first is not None
    assert first.attempt_count == 1
    assert first.lease_expires_at == clock.current + timedelta(seconds=120)
    assert first.lease_token

    clock.advance(seconds=121)
    reclaimed = repository.claim_next_evidence_processing_run()
    assert reclaimed is not None
    assert reclaimed.attempt_count == 2
    assert reclaimed.lease_token != first.lease_token

    assert repository.complete_evidence_processing_run(first, _adapted_evidence(transcript)) is None
    assert session.scalar(select(EvidenceRunRecord)) is None

    completed = repository.complete_evidence_processing_run(
        reclaimed, _adapted_evidence(transcript)
    )
    assert completed is not None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == reclaimed.run_id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.SUCCEEDED.value
    assert stored.evidence_run_id == completed.id


def test_expired_current_lease_cannot_persist_evidence(session: Session) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc))
    repository, scope, assessment, transcript = _seed_evidence_context(
        session, clock=clock
    )
    repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None

    clock.advance(seconds=121)

    assert repository.complete_evidence_processing_run(item, _adapted_evidence(transcript)) is None
    assert session.scalar(select(EvidenceRunRecord)) is None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == item.run_id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.RUNNING.value


def test_expired_lease_failure_does_not_mutate_the_run(session: Session) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc))
    repository, scope, assessment, _ = _seed_evidence_context(session, clock=clock)
    repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None

    clock.advance(seconds=121)

    settled = repository.fail_evidence_processing_run(
        item, "evidence_processing_failed", retryable=True
    )

    assert settled.state is ProcessingRunState.RUNNING
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == item.run_id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.RUNNING.value
    assert stored.lease_token == item.lease_token
    assert stored.error_code is None


def test_expired_lease_at_max_attempts_is_terminal(session: Session) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc))
    repository, scope, assessment, _ = _seed_evidence_context(session, clock=clock)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == queued.id
        )
    )
    assert stored is not None
    stored.attempt_count = stored.max_attempts
    stored.lease_expires_at = clock.current - timedelta(seconds=1)
    session.flush()

    assert repository.claim_next_evidence_processing_run() is None
    assert stored.state == ProcessingRunState.FAILED.value
    assert stored.error_code == "retry_limit_exceeded"


def test_persisted_cancellation_precedes_retry_exhaustion_during_reclaim(
    session: Session,
) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc))
    repository, scope, assessment, _ = _seed_evidence_context(session, clock=clock)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == queued.id
        )
    )
    assert stored is not None
    stored.attempt_count = stored.max_attempts
    stored.lease_expires_at = clock.current - timedelta(seconds=1)
    stored.cancel_requested_at = clock.current
    session.flush()

    assert repository.claim_next_evidence_processing_run() is None
    assert stored.state == ProcessingRunState.CANCELLED.value
    assert stored.error_code == "cancel_requested"


def test_retry_policy_uses_backoff_and_explicit_retry_resets_the_run(session: Session) -> None:
    clock = FakeClock(datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc))
    repository, scope, assessment, _ = _seed_evidence_context(session, clock=clock)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    first = repository.claim_next_evidence_processing_run()
    assert first is not None
    after_first = repository.fail_evidence_processing_run(
        first, "worker_interrupted", retryable=True
    )
    assert after_first.state is ProcessingRunState.QUEUED
    assert after_first.available_at == clock.current + timedelta(seconds=5)

    clock.advance(seconds=5)
    second = repository.claim_next_evidence_processing_run()
    assert second is not None
    after_second = repository.fail_evidence_processing_run(
        second, "worker_interrupted", retryable=True
    )
    assert after_second.state is ProcessingRunState.QUEUED
    assert after_second.available_at == clock.current + timedelta(seconds=30)

    clock.advance(seconds=30)
    third = repository.claim_next_evidence_processing_run()
    assert third is not None
    terminal = repository.fail_evidence_processing_run(
        third, "worker_interrupted", retryable=True
    )
    assert terminal.state is ProcessingRunState.FAILED
    assert terminal.can_retry is True

    restarted = repository.retry_evidence_processing_run(
        scope, queued.id, terminal.version, CORRELATION_ID
    )
    assert restarted.state is ProcessingRunState.QUEUED
    assert restarted.attempt_count == 0
    assert restarted.error_code is None
    assert restarted.can_cancel is True


def test_cancel_running_job_is_observed_before_evidence_persist(session: Session) -> None:
    repository, scope, assessment, transcript = _seed_evidence_context(session)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    cancelled = repository.request_evidence_processing_cancellation(
        scope, queued.id, queued.version, CORRELATION_ID
    )
    assert cancelled.state is ProcessingRunState.CANCELLED
    assert cancelled.error_code == "cancel_requested"
    assert cancelled.can_retry is True

    restarted = repository.retry_evidence_processing_run(
        scope, queued.id, cancelled.version, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None
    requested = repository.request_evidence_processing_cancellation(
        scope, item.run_id, restarted.version + 1, CORRELATION_ID
    )
    assert requested.state is ProcessingRunState.RUNNING
    assert requested.can_cancel is False

    assert repository.complete_evidence_processing_run(item, _adapted_evidence(transcript)) is None
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == item.run_id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.CANCELLED.value
    assert stored.error_code == "cancel_requested"
    assert session.scalar(select(EvidenceRunRecord)) is None


def test_cancel_request_wins_over_a_late_retryable_worker_failure(session: Session) -> None:
    repository, scope, assessment, _ = _seed_evidence_context(session)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    item = repository.claim_next_evidence_processing_run()
    assert item is not None
    claimed = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == queued.id
        )
    )
    assert claimed is not None

    requested = repository.request_evidence_processing_cancellation(
        scope, item.run_id, claimed.version, CORRELATION_ID
    )
    assert requested.state is ProcessingRunState.RUNNING

    settled = repository.fail_evidence_processing_run(
        item, "evidence_processing_failed", retryable=True
    )

    assert settled.state is ProcessingRunState.CANCELLED
    assert settled.error_code == "cancel_requested"
    assert settled.can_retry is True
    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == queued.id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.CANCELLED.value


def test_system_cancellation_and_contract_supersession_are_not_user_retryable(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, scope, assessment, transcript = _seed_evidence_context(session)
    old_run = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )

    transcript_content = "@UTF8\n@Begin\n*CHI:\thello world .\n@End\n"
    superseding = repository.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.assessment_id,
            content=transcript_content,
            source=TranscriptSource.MANUAL,
            expected_revision=transcript.revision,
            expected_version=transcript.version,
        ),
        correlation_id=CORRELATION_ID,
    )
    stored_old = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == old_run.id
        )
    )
    assert stored_old is not None
    assert stored_old.state == ProcessingRunState.CANCELLED.value
    assert stored_old.error_code == "transcript_superseded"
    with pytest.raises(RepositoryError, match="processing_run_not_retryable"):
        repository.retry_evidence_processing_run(
            scope, old_run.id, old_run.version + 1, CORRELATION_ID
        )

    repository.attest_transcript(
        scope,
        AttestTranscript(
            transcript_revision_id=superseding.id,
            expected_version=superseding.version,
        ),
        correlation_id=CORRELATION_ID,
    )
    current = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    monkeypatch.setattr(
        repository_module,
        "_EVIDENCE_PIPELINE_VERSION",
        "reviewed-transcript-descriptors-v2",
    )
    newer_contract = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    assert newer_contract.id != current.id
    current_record = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == current.id
        )
    )
    assert current_record is not None
    assert current_record.state == ProcessingRunState.CANCELLED.value
    assert current_record.error_code == "analysis_contract_superseded"


def test_consent_withdrawal_cancels_queued_evidence_job(session: Session) -> None:
    repository, scope, assessment, _ = _seed_evidence_context(session)
    queued = repository.enqueue_current_evidence_processing(
        scope, assessment.assessment_id, CORRELATION_ID
    )
    child_id = assessment.child_id
    repository.add_consent(
        scope,
        child_id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v2",
            status=ConsentStatus.WITHDRAWN,
        ),
        correlation_id=CORRELATION_ID,
    )

    stored = session.scalar(
        select(ProcessingRunRecord).where(
            ProcessingRunRecord.processing_run_id == queued.id
        )
    )
    assert stored is not None
    assert stored.state == ProcessingRunState.CANCELLED.value
    assert stored.error_code == "consent_revoked"
