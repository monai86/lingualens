from datetime import datetime, timezone
import inspect

import pytest

from app.assessment_v2.domain.models import (
    AttestTranscript,
    CreateTranscriptRevision,
    TranscriptReviewState,
    TranscriptSource,
    TranscriptRevisionSnapshot,
)
from app.assessment_v2.db.repositories import AssessmentRepository


def test_transcript_revision_preserves_review_state_and_content_checksum() -> None:
    revision = TranscriptRevisionSnapshot(
        id="transcript_revision_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.DRAFT,
        content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
        content_sha256="a" * 64,
        created_by_user_id="therapist_opaque_01",
        created_at=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
        attested_by_user_id=None,
        attested_at=None,
        version=1,
    )

    assert revision.to_dict()["review_state"] == "draft"
    assert revision.to_dict()["content_sha256"] == "a" * 64
    assert revision.to_dict()["content"] == "@UTF8\n@Begin\n*CHI: hello .\n@End\n"


def test_transcript_revision_rejects_non_sha256_content_checksum() -> None:
    with pytest.raises(ValueError, match="content_sha256"):
        TranscriptRevisionSnapshot(
            id="transcript_revision_opaque_01",
            organization_id="org_opaque_01",
            assessment_id="assessment_opaque_01",
            revision=1,
            source=TranscriptSource.MANUAL,
            review_state=TranscriptReviewState.DRAFT,
            content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
            content_sha256="not-a-digest",
            created_by_user_id="therapist_opaque_01",
            created_at=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
            attested_by_user_id=None,
            attested_at=None,
            version=1,
        )


def test_transcript_attestation_requires_a_positive_expected_version() -> None:
    with pytest.raises(ValueError, match="expected_version"):
        AttestTranscript(transcript_revision_id="transcript_revision_opaque_01", expected_version=0)


def test_transcript_revision_write_requires_a_matching_current_revision_pair() -> None:
    with pytest.raises(ValueError, match="expected_revision and expected_version"):
        CreateTranscriptRevision(
            assessment_id="assessment_opaque_01",
            content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
            source=TranscriptSource.MANUAL,
            expected_revision=1,
        )

    with pytest.raises(ValueError, match="expected_revision"):
        CreateTranscriptRevision(
            assessment_id="assessment_opaque_01",
            content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
            source=TranscriptSource.MANUAL,
            expected_version=1,
        )


def test_attestation_uses_the_same_assessment_child_transcript_lock_order_as_revision_writes() -> None:
    source = inspect.getsource(AssessmentRepository.attest_transcript)

    assessment_lock = source.index("self._locked_assessment")
    child_lock = source.index("self._locked_child")
    transcript_lock = source.index(".with_for_update()")

    assert assessment_lock < child_lock < transcript_lock
