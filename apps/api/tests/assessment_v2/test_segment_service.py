from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.assessment_v2.db.repositories import RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    AttestTranscriptSegmentSet,
    CreateTranscriptSegmentSet,
    TranscriptSegmentSpeakerRole,
    TranscriptSource,
    TranscriptReviewState,
)
from app.assessment_v2.domain.segments import (
    TranscriptSegment,
    TranscriptSegmentSetSnapshot,
    TranscriptSegmentSnapshot,
)
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.core.security import CurrentUser


def therapist(role: str = "therapist", user_id: str = "therapist_01") -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        role=role,
        display_name="Synthetic Therapist",
        organization_id="org_alpha",
    )


def assessment() -> AssessmentSnapshot:
    return AssessmentSnapshot(
        id="assessment_01",
        organization_id="org_alpha",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=AssessmentState.REVIEW_REQUIRED,
        assigned_clinician_id="therapist_01",
        version=2,
        age_months=36,
        language_context={"primary": "th", "additional": []},
    )


def segment_set() -> TranscriptSegmentSetSnapshot:
    segment = TranscriptSegment(
        ordinal=1,
        start_ms=0,
        end_ms=900,
        speaker_role=TranscriptSegmentSpeakerRole.CHILD,
        text="hello",
    )
    return TranscriptSegmentSetSnapshot(
        id="segment_set_01",
        organization_id="org_alpha",
        assessment_id="assessment_01",
        transcript_revision_id="transcript_01",
        transcript_content_sha256="a" * 64,
        recording_id=None,
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.DRAFT,
        segments_sha256="b" * 64,
        segments=(
            TranscriptSegmentSnapshot(
                id="segment_01",
                organization_id="org_alpha",
                segment_set_id="segment_set_01",
                ordinal=segment.ordinal,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                speaker_role=segment.speaker_role,
                text=segment.text,
                confidence=segment.confidence,
                uncertainty_reason=segment.uncertainty_reason,
                created_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
            ),
        ),
        created_by_user_id="therapist_01",
        created_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        attested_by_user_id=None,
        attested_at=None,
        version=1,
    )


class FakeRepository:
    def __init__(self) -> None:
        self.assessment_value = assessment()
        self.segment_set_value = segment_set()
        self.created = None
        self.attested = None

    def get_assessment(self, scope: AccessScope, assessment_id: str):
        return self.assessment_value if assessment_id == self.assessment_value.id else None

    def get_current_transcript_segment_set(self, scope: AccessScope, assessment_id: str):
        return self.segment_set_value if assessment_id == self.assessment_value.id else None

    def create_transcript_segment_set(self, scope, command, correlation_id):
        self.created = (scope, command, correlation_id)
        return self.segment_set_value

    def attest_transcript_segment_set(self, scope, command, correlation_id):
        self.attested = (scope, command, correlation_id)
        return self.segment_set_value


def service_for(repository: FakeRepository, user: CurrentUser | None = None) -> AssessmentService:
    return AssessmentService(repository, user or therapist())


def create_command(assessment_id: str = "assessment_01") -> CreateTranscriptSegmentSet:
    return CreateTranscriptSegmentSet(
        assessment_id=assessment_id,
        transcript_revision_id="transcript_01",
        segments=(
            TranscriptSegment(
                ordinal=1,
                start_ms=0,
                end_ms=900,
                speaker_role=TranscriptSegmentSpeakerRole.CHILD,
                text="hello",
            ),
        ),
        source=TranscriptSource.MANUAL,
    )


def test_service_reads_current_segment_set_through_clinical_scope() -> None:
    service = service_for(FakeRepository())

    result = service.get_current_transcript_segment_set("assessment_01")

    assert result.id == "segment_set_01"


def test_service_creates_segment_set_only_for_matching_assessment() -> None:
    repository = FakeRepository()
    service = service_for(repository)

    with pytest.raises(ClinicalPolicyError) as error:
        service.create_transcript_segment_set(
            "assessment_01",
            create_command("other_assessment"),
            "request-01",
        )

    assert error.value.code == "segment_set_not_reviewable"
    assert repository.created is None


def test_service_requires_therapist_or_supervisor_for_segment_writes() -> None:
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(FakeRepository(), therapist(role="org_admin")).create_transcript_segment_set(
            "assessment_01",
            create_command(),
            "request-02",
        )

    assert error.value.code == "role_not_permitted"


def test_service_maps_repository_stale_transcript_without_leaking_data() -> None:
    class StaleRepository(FakeRepository):
        def create_transcript_segment_set(self, scope, command, correlation_id):
            raise RepositoryError("segment_transcript_stale")

    with pytest.raises(ClinicalPolicyError) as error:
        service_for(StaleRepository()).create_transcript_segment_set(
            "assessment_01",
            create_command(),
            "request-03",
        )

    assert error.value.code == "segment_transcript_stale"
    assert error.value.status_code == 409


def test_service_attestation_requires_matching_path_identifier() -> None:
    repository = FakeRepository()
    service = service_for(repository)

    with pytest.raises(ClinicalPolicyError) as error:
        service.attest_transcript_segment_set(
            "other_segment_set",
            AttestTranscriptSegmentSet(
                transcript_segment_set_id="segment_set_01",
                expected_version=1,
            ),
            "request-04",
        )

    assert error.value.code == "segment_set_not_reviewable"
    assert repository.attested is None
