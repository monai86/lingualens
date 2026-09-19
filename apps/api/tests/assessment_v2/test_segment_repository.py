from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    CareTeamAssignmentRecord,
    OrganizationMembershipRecord,
    RecordingRecord,
    TranscriptSegmentSetRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository, RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AttestTranscript,
    AttestTranscriptSegmentSet,
    ConsentPurpose,
    ConsentStatus,
    CreateAssessment,
    CreateChild,
    CreateTranscriptRevision,
    CreateTranscriptSegmentSet,
    RecordConsent,
    TranscriptSegmentSpeakerRole,
    TranscriptSource,
    TranscriptReviewState,
)
from app.assessment_v2.domain.segments import (
    TranscriptSegment,
    compute_transcript_segments_sha256,
)
from app.core.security import CurrentUser


CORRELATION_ID = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def context() -> Iterator[tuple[Session, AssessmentRepository, AccessScope, object, object]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AssessmentBase.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        repository = AssessmentRepository(session, clock=lambda: datetime(2026, 9, 9, tzinfo=timezone.utc))
        scope = AccessScope("therapist_01", "org_alpha", "therapist")
        repository.synchronize_principal(
            CurrentUser(
                user_id=scope.user_id,
                organization_id=scope.organization_id,
                role=scope.role,
                display_name="Synthetic Therapist",
            ),
            CORRELATION_ID,
        )
        session.add(
            OrganizationMembershipRecord(
                membership_id=uuid4().hex,
                organization_id=scope.organization_id,
                user_id=scope.user_id,
                role=scope.role,
                active=True,
            )
        )
        session.flush()
        child = repository.create_child(
            scope,
            CreateChild(
                display_code="LL-SEGMENT-01",
                birth_year=2021,
                birth_month=6,
                language_context={"primary": "th", "additional": []},
            ),
            CORRELATION_ID,
        )
        repository.add_consent(
            scope,
            child.id,
            RecordConsent(
                purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
                scope_version="clinical-v1",
                status=ConsentStatus.ACTIVE,
            ),
            CORRELATION_ID,
        )
        assessment = repository.create_assessment(
            scope,
            CreateAssessment(
                child_id=child.id,
                purpose=AssessmentPurpose.INITIAL,
                age_months=36,
                language_context={"primary": "th", "additional": []},
                assigned_clinician_id=scope.user_id,
            ),
            CORRELATION_ID,
        )
        stored_assessment = session.scalar(
            select(AssessmentRecord).where(AssessmentRecord.assessment_id == assessment.id)
        )
        assert stored_assessment is not None
        stored_assessment.state = "processing"
        session.flush()
        transcript = repository.create_transcript_revision(
            scope,
            CreateTranscriptRevision(
                assessment_id=assessment.id,
                content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
                source=TranscriptSource.MANUAL,
            ),
            CORRELATION_ID,
        )
        transcript = repository.attest_transcript(
            scope,
            AttestTranscript(transcript_revision_id=transcript.id, expected_version=1),
            CORRELATION_ID,
        )
        yield session, repository, scope, assessment, transcript
    AssessmentBase.metadata.drop_all(engine)


def _segments(text: str = "hello") -> tuple[TranscriptSegment, ...]:
    return (
        TranscriptSegment(
            ordinal=1,
            start_ms=0,
            end_ms=900,
            speaker_role=TranscriptSegmentSpeakerRole.CHILD,
            text=text,
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


def _create_command(assessment_id: str, transcript_id: str, segments: tuple[TranscriptSegment, ...]):
    return CreateTranscriptSegmentSet(
        assessment_id=assessment_id,
        transcript_revision_id=transcript_id,
        segments=segments,
        source=TranscriptSource.MANUAL,
    )


def test_create_segment_set_binds_current_transcript_and_server_checksum(context) -> None:
    session, repository, scope, assessment, transcript = context
    segments = _segments()

    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, segments),
        CORRELATION_ID,
    )

    assert created.revision == 1
    assert created.review_state is TranscriptReviewState.DRAFT
    assert created.transcript_revision_id == transcript.id
    assert created.transcript_content_sha256 == transcript.content_sha256
    assert created.segments_sha256 == compute_transcript_segments_sha256(segments)
    assert tuple(segment.to_segment() for segment in created.segments) == segments
    stored = session.get(TranscriptSegmentSetRecord, created.id)
    assert stored is not None
    assert stored.transcript_content_sha256 == transcript.content_sha256


def test_editing_segment_set_creates_new_revision_and_rejects_stale_version(context) -> None:
    _, repository, scope, assessment, transcript = context
    first = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )

    second = repository.create_transcript_segment_set(
        scope,
        CreateTranscriptSegmentSet(
            assessment_id=assessment.id,
            transcript_revision_id=transcript.id,
            segments=_segments("hello edited"),
            source=TranscriptSource.MANUAL,
            expected_revision=first.revision,
            expected_version=first.version,
        ),
        CORRELATION_ID,
    )

    assert second.revision == 2
    assert second.review_state is TranscriptReviewState.DRAFT
    superseded = repository.session.get(TranscriptSegmentSetRecord, first.id)
    assert superseded is not None
    assert superseded.review_state == TranscriptReviewState.SUPERSEDED.value
    assert superseded.version == 2

    with pytest.raises(RepositoryError, match="stale_segment_set_version"):
        repository.create_transcript_segment_set(
            scope,
            CreateTranscriptSegmentSet(
                assessment_id=assessment.id,
                transcript_revision_id=transcript.id,
                segments=_segments("stale"),
                source=TranscriptSource.MANUAL,
                expected_revision=first.revision,
                expected_version=first.version,
            ),
            CORRELATION_ID,
        )


def test_attesting_segment_set_requires_current_transcript_and_expected_version(context) -> None:
    _, repository, scope, assessment, transcript = context
    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )

    with pytest.raises(RepositoryError, match="stale_segment_set_version"):
        repository.attest_transcript_segment_set(
            scope,
            AttestTranscriptSegmentSet(
                transcript_segment_set_id=created.id,
                expected_version=created.version + 1,
            ),
            CORRELATION_ID,
        )

    attested = repository.attest_transcript_segment_set(
        scope,
        AttestTranscriptSegmentSet(
            transcript_segment_set_id=created.id,
            expected_version=created.version,
        ),
        CORRELATION_ID,
    )

    assert attested.review_state is TranscriptReviewState.ATTESTED
    assert attested.attested_by_user_id == scope.user_id
    assert attested.attested_at is not None
    assert attested.version == 2


def test_attestation_collision_reports_stale_version_before_state_conflict(context) -> None:
    _, repository, scope, assessment, transcript = context
    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )
    repository.attest_transcript_segment_set(
        scope,
        AttestTranscriptSegmentSet(
            transcript_segment_set_id=created.id,
            expected_version=created.version,
        ),
        CORRELATION_ID,
    )

    with pytest.raises(RepositoryError, match="stale_segment_set_version"):
        repository.attest_transcript_segment_set(
            scope,
            AttestTranscriptSegmentSet(
                transcript_segment_set_id=created.id,
                expected_version=created.version,
            ),
            CORRELATION_ID,
        )


def test_current_draft_segment_set_can_request_bounded_replay(context) -> None:
    _, repository, scope, assessment, transcript = context
    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )

    target = repository.get_transcript_segment_replay_target(
        scope,
        created.segments[0].id,
    )

    assert target is not None
    segment, recording = target
    assert segment.text == "hello"
    assert recording is None


def test_new_transcript_can_create_first_segment_set_without_historical_expected_version(
    context,
) -> None:
    _, repository, scope, assessment, transcript = context
    first = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )
    repository.attest_transcript_segment_set(
        scope,
        AttestTranscriptSegmentSet(
            transcript_segment_set_id=first.id,
            expected_version=first.version,
        ),
        CORRELATION_ID,
    )
    newer_transcript = repository.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content="@UTF8\n@Begin\n*CHI: changed .\n@End\n",
            source=TranscriptSource.MANUAL,
            expected_revision=transcript.revision,
            expected_version=transcript.version,
        ),
        CORRELATION_ID,
    )
    newer_transcript = repository.attest_transcript(
        scope,
        AttestTranscript(
            transcript_revision_id=newer_transcript.id,
            expected_version=newer_transcript.version,
        ),
        CORRELATION_ID,
    )

    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, newer_transcript.id, _segments("changed")),
        CORRELATION_ID,
    )

    assert created.revision == 2
    assert created.review_state is TranscriptReviewState.DRAFT


def test_observer_care_team_assignment_cannot_edit_segment_sets(context) -> None:
    session, repository, scope, assessment, transcript = context
    assignment = session.scalar(
        select(CareTeamAssignmentRecord).where(
            CareTeamAssignmentRecord.organization_id == scope.organization_id,
            CareTeamAssignmentRecord.child_id == assessment.child_id,
            CareTeamAssignmentRecord.user_id == scope.user_id,
        )
    )
    assert assignment is not None
    assignment.role = "observer"
    session.flush()

    with pytest.raises(RepositoryError, match="segment_role_not_permitted"):
        repository.create_transcript_segment_set(
            scope,
            _create_command(assessment.id, transcript.id, _segments()),
            CORRELATION_ID,
        )


def test_new_transcript_supersedes_segment_set_and_old_transcript_cannot_be_reused(context) -> None:
    _, repository, scope, assessment, transcript = context
    created = repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )

    newer_transcript = repository.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content="@UTF8\n@Begin\n*CHI: changed .\n@End\n",
            source=TranscriptSource.MANUAL,
            expected_revision=transcript.revision,
            expected_version=transcript.version,
        ),
        CORRELATION_ID,
    )

    stored = repository.session.get(TranscriptSegmentSetRecord, created.id)
    assert stored is not None
    assert stored.review_state == TranscriptReviewState.SUPERSEDED.value
    assert repository.get_current_transcript_segment_set(scope, assessment.id) is None
    with pytest.raises(RepositoryError, match="segment_transcript_stale"):
        repository.create_transcript_segment_set(
            scope,
            _create_command(assessment.id, transcript.id, _segments("old transcript")),
            CORRELATION_ID,
        )
    assert newer_transcript.id != transcript.id


def test_segment_set_rejects_client_checksum_mismatch_without_persisting(context) -> None:
    _, repository, scope, assessment, transcript = context

    with pytest.raises(ValueError, match="client checksum"):
        command = CreateTranscriptSegmentSet(
            assessment_id=assessment.id,
            transcript_revision_id=transcript.id,
            segments=_segments(),
            source=TranscriptSource.MANUAL,
            client_checksum="b" * 64,
        )
        repository.create_transcript_segment_set(scope, command, CORRELATION_ID)


def test_segment_set_requires_active_consent_and_editor_membership(context) -> None:
    session, repository, scope, assessment, transcript = context
    membership = session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == scope.organization_id,
            OrganizationMembershipRecord.user_id == scope.user_id,
        )
    )
    assert membership is not None
    membership.role = "org_admin"
    session.flush()
    with pytest.raises(RepositoryError, match="segment_role_not_permitted"):
        repository.create_transcript_segment_set(
            scope,
            _create_command(assessment.id, transcript.id, _segments()),
            CORRELATION_ID,
        )


def test_segment_set_binds_only_verified_recording(context) -> None:
    session, repository, scope, assessment, transcript = context
    recording = RecordingRecord(
        recording_id="recording_segment_01",
        organization_id=scope.organization_id,
        assessment_id=assessment.id,
        protocol_version_key="protocol-opaque",
        activity_key="free_play",
        declared_content_type="audio/webm",
        declared_size_bytes=100,
        declared_checksum="sha256:" + "a" * 64,
        object_key="capture/opaque-recording-segment-01",
        upload_state="verified",
        expires_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
        verified_content_type="audio/webm",
        verified_size_bytes=100,
        verified_checksum="sha256:" + "a" * 64,
        verified_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        version=2,
    )
    session.add(recording)
    session.flush()

    created = repository.create_transcript_segment_set(
        scope,
        CreateTranscriptSegmentSet(
            assessment_id=assessment.id,
            transcript_revision_id=transcript.id,
            segments=_segments(),
            source=TranscriptSource.MANUAL,
            recording_id=recording.recording_id,
        ),
        CORRELATION_ID,
    )

    assert created.recording_id == recording.recording_id


def test_segment_set_read_requires_current_consent_and_care_team_scope(context) -> None:
    _, repository, scope, assessment, transcript = context
    repository.create_transcript_segment_set(
        scope,
        _create_command(assessment.id, transcript.id, _segments()),
        CORRELATION_ID,
    )
    outsider = AccessScope("outsider_01", "org_beta", "therapist")
    assert repository.get_current_transcript_segment_set(outsider, assessment.id) is None

    repository.add_consent(
        scope,
        assessment.child_id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.WITHDRAWN,
        ),
        CORRELATION_ID,
    )
    with pytest.raises(RepositoryError, match="consent_revoked"):
        repository.get_current_transcript_segment_set(scope, assessment.id)


def test_segment_set_creation_rejects_unattested_current_transcript(context) -> None:
    session, repository, scope, assessment, transcript = context
    draft = repository.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id=assessment.id,
            content="@UTF8\n@Begin\n*CHI: draft .\n@End\n",
            source=TranscriptSource.MANUAL,
            expected_revision=transcript.revision,
            expected_version=transcript.version,
        ),
        CORRELATION_ID,
    )
    with pytest.raises(RepositoryError, match="transcript_not_reviewable"):
        repository.create_transcript_segment_set(
            scope,
            _create_command(assessment.id, draft.id, _segments()),
            CORRELATION_ID,
        )
    assert session.scalar(
        select(TranscriptSegmentSetRecord).where(
            TranscriptSegmentSetRecord.assessment_id == assessment.id
        )
    ) is None
