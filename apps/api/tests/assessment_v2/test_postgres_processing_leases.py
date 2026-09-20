from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.assessment_v2.db.models import (
    AssessmentRecord,
    AssessmentProtocolSelectionRecord,
    AuditEventRecord,
    CareTeamAssignmentRecord,
    ChildRecord,
    ConsentRecord,
    EvidenceRunRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    TranscriptSegmentRecord,
    TranscriptSegmentSetRecord,
    TranscriptRevisionRecord,
    UserProfileRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.domain.models import (
    ProcessingRunStage,
    ProcessingRunState,
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptReviewState,
    TranscriptSource,
)
from app.assessment_v2.domain.segments import TranscriptSegment, compute_transcript_segments_sha256


pytestmark = pytest.mark.assessment_postgres


def _database_url() -> URL:
    value = os.getenv("LINGUALENS_ASSESSMENT_TEST_DATABASE_URL")
    if not value:
        pytest.skip("assessment PostgreSQL lease tests require a PostgreSQL URL")
    parsed = make_url(value)
    if parsed.get_backend_name() != "postgresql":
        pytest.skip("assessment PostgreSQL lease tests require a PostgreSQL URL")
    return parsed


@pytest.fixture
def lease_fixture() -> Iterator[tuple[object, str, str]]:
    url = _database_url()
    engine = create_engine(url, pool_size=4, max_overflow=0)
    suffix = uuid4().hex[:12]
    organization_id = f"lease_org_{suffix}"
    user_id = f"lease_user_{suffix}"
    child_id = f"lease_child_{suffix}"
    assessment_id = f"lease_assessment_{suffix}"
    transcript_id = f"lease_transcript_{suffix}"
    protocol_key = "thai_guided_language_sample:v0"
    selection_id = f"lease_selection_{suffix}"
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        session.add_all(
            [
                OrganizationRecord(
                    organization_id=organization_id,
                    display_label="Synthetic lease organization",
                    active=True,
                    created_at=now,
                    updated_at=now,
                ),
                UserProfileRecord(
                    user_id=user_id,
                    display_label="Synthetic lease therapist",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.flush()
        if session.get(ProtocolVersionRecord, protocol_key) is None:
            session.add(
                ProtocolVersionRecord(
                    protocol_version_key=protocol_key,
                    primary_language="th",
                    minimum_age_months=18,
                    maximum_age_months=72,
                    supported_purposes="initial",
                    created_at=now,
                )
            )
            session.flush()
        if session.get(ProtocolActivityRecord, (protocol_key, "free_play")) is None:
            session.add(
                ProtocolActivityRecord(
                    protocol_version_key=protocol_key,
                    activity_key="free_play",
                    required=True,
                    target_duration_seconds=180,
                    minimum_duration_seconds=120,
                    sort_order=1,
                    created_at=now,
                )
            )
            session.flush()
        session.add_all(
            [
                OrganizationMembershipRecord(
                    membership_id=f"lease_membership_{suffix}",
                    organization_id=organization_id,
                    user_id=user_id,
                    role="therapist",
                    active=True,
                    created_at=now,
                    updated_at=now,
                ),
                ChildRecord(
                    child_id=child_id,
                    organization_id=organization_id,
                    display_code=f"LL-LEASE-{suffix}",
                    birth_month=6,
                    birth_year=2021,
                    language_context='{"additional":[],"primary":"th"}',
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                CareTeamAssignmentRecord(
                    assignment_id=f"lease_assignment_{suffix}",
                    organization_id=organization_id,
                    child_id=child_id,
                    user_id=user_id,
                    role="assigned_clinician",
                    active=True,
                    created_at=now,
                    updated_at=now,
                ),
                ConsentRecord(
                    consent_record_id=f"lease_consent_{suffix}",
                    organization_id=organization_id,
                    child_id=child_id,
                    purpose="clinical_assessment",
                    scope_version="clinical-v1",
                    status="active",
                    granted_at=now,
                    recorded_by_user_id=user_id,
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
                AssessmentRecord(
                    assessment_id=assessment_id,
                    organization_id=organization_id,
                    child_id=child_id,
                    purpose="initial",
                    state="review_required",
                    age_months=36,
                    language_context='{"additional":[],"primary":"th"}',
                    assigned_clinician_id=user_id,
                    version=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        session.flush()
        session.add(
            AssessmentProtocolSelectionRecord(
                    assessment_protocol_selection_id=selection_id,
                    organization_id=organization_id,
                    assessment_id=assessment_id,
                    protocol_version_key=protocol_key,
                    selected_by_user_id=user_id,
                    selected_at=now,
                    version=1,
                    created_at=now,
                    updated_at=now,
            )
        )
        session.flush()
        session.add(
            TranscriptRevisionRecord(
                    transcript_revision_id=transcript_id,
                    organization_id=organization_id,
                    assessment_id=assessment_id,
                    revision=1,
                    source="manual",
                    review_state="attested",
                content="@UTF8\n@Begin\n*CHI:\thello .\n@End\n",
                content_sha256=sha256(
                    "@UTF8\n@Begin\n*CHI:\thello .\n@End\n".encode()
                ).hexdigest(),
                    created_by_user_id=user_id,
                    attested_by_user_id=user_id,
                    attested_at=now,
                    version=2,
                    created_at=now,
                    updated_at=now,
            )
        )
        session.flush()
        segment_set_id = f"lease_segment_set_{suffix}"
        lease_segments = (
            TranscriptSegment(
                ordinal=1,
                start_ms=0,
                end_ms=900,
                speaker_role=TranscriptSegmentSpeakerRole.CHILD,
                text="hello",
                confidence=0.9,
            ),
            TranscriptSegment(
                ordinal=2,
                start_ms=900,
                end_ms=1_700,
                speaker_role=TranscriptSegmentSpeakerRole.THERAPIST,
                text="tell me more",
                confidence=0.8,
            ),
        )
        segment_set_sha256 = compute_transcript_segments_sha256(lease_segments)
        session.add(
            TranscriptSegmentSetRecord(
                transcript_segment_set_id=segment_set_id,
                organization_id=organization_id,
                assessment_id=assessment_id,
                transcript_revision_id=transcript_id,
                transcript_content_sha256=sha256(
                    "@UTF8\n@Begin\n*CHI:\thello .\n@End\n".encode()
                ).hexdigest(),
                recording_id=None,
                revision=1,
                source=TranscriptSource.MANUAL.value,
                review_state=TranscriptReviewState.ATTESTED.value,
                segments_sha256=segment_set_sha256,
                created_by_user_id=user_id,
                attested_by_user_id=user_id,
                attested_at=now,
                version=2,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add_all(
            TranscriptSegmentRecord(
                transcript_segment_id=f"lease_segment_{suffix}_{segment.ordinal}",
                organization_id=organization_id,
                transcript_segment_set_id=segment_set_id,
                ordinal=segment.ordinal,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                speaker_role=segment.speaker_role.value,
                text=segment.text,
                confidence=segment.confidence,
                uncertainty_reason=segment.uncertainty_reason.value,
                created_at=now,
            )
            for segment in lease_segments
        )
        session.flush()
        session.add(
            ProcessingRunRecord(
                    processing_run_id=f"lease_run_{suffix}",
                    organization_id=organization_id,
                    recording_id=None,
                    assessment_id=assessment_id,
                    transcript_revision_id=transcript_id,
                    evidence_run_id=None,
                    stage=ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                    state=ProcessingRunState.QUEUED.value,
                    segment_set_id=segment_set_id,
                    segment_set_sha256=segment_set_sha256,
                    idempotency_key=f"evidence:v3:{'b' * 64}",
                    attempt_count=0,
                    max_attempts=3,
                    available_at=now,
                    pipeline_version="reviewed-transcript-descriptors-v1",
                    feature_schema_version="descriptive-transcript-features-v1",
                    version=1,
                    created_at=now,
                    updated_at=now,
            )
        )
        session.flush()
        session.commit()

    try:
        yield engine, organization_id, f"lease_run_{suffix}"
    finally:
        with Session(engine) as session:
            session.execute(
                delete(AuditEventRecord).where(
                    AuditEventRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(EvidenceRunRecord).where(
                    EvidenceRunRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(ProcessingRunRecord).where(
                    ProcessingRunRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(TranscriptSegmentRecord).where(
                    TranscriptSegmentRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(TranscriptSegmentSetRecord).where(
                    TranscriptSegmentSetRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(TranscriptRevisionRecord).where(
                    TranscriptRevisionRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(AssessmentProtocolSelectionRecord).where(
                    AssessmentProtocolSelectionRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(AssessmentRecord).where(
                    AssessmentRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(ConsentRecord).where(ConsentRecord.organization_id == organization_id)
            )
            session.execute(
                delete(CareTeamAssignmentRecord).where(
                    CareTeamAssignmentRecord.organization_id == organization_id
                )
            )
            session.execute(
                delete(ChildRecord).where(ChildRecord.organization_id == organization_id)
            )
            session.execute(
                delete(OrganizationMembershipRecord).where(
                    OrganizationMembershipRecord.organization_id == organization_id
                )
            )
            session.execute(delete(UserProfileRecord).where(UserProfileRecord.user_id == user_id))
            session.execute(
                delete(OrganizationRecord).where(
                    OrganizationRecord.organization_id == organization_id
                )
            )
            session.commit()
        engine.dispose()


def test_postgres_committed_claim_has_one_lease_owner_and_reclaims_expired_token(
    lease_fixture: tuple[object, str, str],
) -> None:
    engine, organization_id, run_id = lease_fixture
    first_session = Session(engine, expire_on_commit=False)
    second_session = Session(engine, expire_on_commit=False)
    try:
        first = AssessmentRepository(first_session).claim_next_evidence_processing_run()
        assert first is not None
        assert first.organization_id == organization_id
        # The worker commits the lease before extraction. The second session
        # must observe the durable RUNNING state rather than waiting on the
        # first worker's parent-row locks.
        first_session.commit()

        second = AssessmentRepository(second_session).claim_next_evidence_processing_run()
        assert second is None

        with Session(engine) as reset_session:
            stored = reset_session.scalar(
                select(ProcessingRunRecord).where(
                    ProcessingRunRecord.processing_run_id == run_id
                )
            )
            assert stored is not None
            stored.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            reset_session.commit()

        reclaimed = AssessmentRepository(second_session).claim_next_evidence_processing_run()
        assert reclaimed is not None
        assert reclaimed.run_id == run_id
        assert reclaimed.lease_token != first.lease_token
        second_session.commit()

        # The first worker's token is stale after reclaim and cannot complete
        # or create an evidence result.
        assert AssessmentRepository(first_session).complete_evidence_processing_run(
            first, object()
        ) is None
        assert first_session.scalar(
            select(EvidenceRunRecord).where(
                EvidenceRunRecord.organization_id == organization_id
            )
        ) is None
    finally:
        first_session.close()
        second_session.close()


def test_postgres_parent_lock_contention_waits_instead_of_failing_the_job(
    lease_fixture: tuple[object, str, str],
) -> None:
    engine, organization_id, run_id = lease_fixture
    blocker = Session(engine, expire_on_commit=False)
    started = threading.Event()
    result: dict[str, object] = {}

    blocker.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.assessment_id.like("lease_assessment_%"))
        .with_for_update()
    ).first()

    def claim_in_worker_thread() -> None:
        worker_session = Session(engine, expire_on_commit=False)
        try:
            started.set()
            result["item"] = AssessmentRepository(
                worker_session
            ).claim_next_evidence_processing_run()
            worker_session.commit()
        except BaseException as error:  # pragma: no cover - surfaced below
            result["error"] = error
        finally:
            worker_session.close()

    worker = threading.Thread(target=claim_in_worker_thread)
    worker.start()
    assert started.wait(timeout=2)
    time.sleep(0.2)
    assert worker.is_alive(), "parent-row contention must not be treated as absence"

    blocker.commit()
    worker.join(timeout=5)
    try:
        assert not worker.is_alive()
        assert "error" not in result
        item = result.get("item")
        assert item is not None
        assert item.run_id == run_id
        assert item.organization_id == organization_id
    finally:
        blocker.close()
