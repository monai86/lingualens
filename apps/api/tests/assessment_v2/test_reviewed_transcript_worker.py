from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest

from app.assessment_v2.domain.models import (
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptRevisionSnapshot,
    TranscriptReviewState,
    TranscriptSource,
)
from app.assessment_v2.domain.segments import TranscriptSegmentSnapshot, TranscriptSegmentSetSnapshot
from app.assessment_v2.reviewed_transcript_worker import (
    extract_reviewed_segment_set,
    extract_reviewed_transcript,
)


UTC = timezone.utc


def transcript_snapshot(content: str, *, review_state: TranscriptReviewState = TranscriptReviewState.ATTESTED) -> TranscriptRevisionSnapshot:
    return TranscriptRevisionSnapshot(
        id="transcript_revision_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        revision=1,
        source=TranscriptSource.ASR_DRAFT,
        review_state=review_state,
        content=content,
        content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        created_by_user_id="therapist_opaque_01",
        created_at=datetime(2026, 9, 7, 8, 0, tzinfo=UTC),
        attested_by_user_id="therapist_opaque_01" if review_state is TranscriptReviewState.ATTESTED else None,
        attested_at=datetime(2026, 9, 7, 8, 1, tzinfo=UTC) if review_state is TranscriptReviewState.ATTESTED else None,
        version=2 if review_state is TranscriptReviewState.ATTESTED else 1,
    )


def test_extracts_descriptive_features_from_reviewed_chat_without_diagnosis() -> None:
    result = extract_reviewed_transcript(
        transcript_snapshot(
            "@UTF8\n@Begin\n*INV: do you see the red car ?\n*CHI: red car .\n*INV: what color ?\n*CHI: red .\n@End\n"
        ),
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.status == "completed"
    assert result.feature_values["child_utterance_count"] == 2
    assert result.feature_values["child_token_count"] == 3
    assert result.feature_values["child_unique_token_count"] == 2
    assert result.feature_values["mean_child_tokens_per_utterance"] == 1.5
    assert result.provenance.input_ref == "transcript-revision:transcript_revision_opaque_01"
    assert result.not_diagnostic is True
    assert result.decision_support_only is True
    assert "diagnos" not in " ".join(result.warnings).lower()


def test_returns_insufficient_data_when_child_speaker_is_not_explicit() -> None:
    result = extract_reviewed_transcript(
        transcript_snapshot("@UTF8\n@Begin\n*INV: hello there .\n@End\n"),
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.status == "insufficient_data"
    assert result.feature_values == {}
    assert result.abstention_reason


def test_worker_requires_attested_transcript() -> None:
    with pytest.raises(ValueError, match="attested"):
        extract_reviewed_transcript(
            transcript_snapshot(
                "@UTF8\n@Begin\n*CHI: hello .\n@End\n",
                review_state=TranscriptReviewState.DRAFT,
            ),
            protocol_version_key="thai_guided_language_sample:v0",
        )


def test_worker_uses_the_maintained_thai_tokenizer_profile() -> None:
    result = extract_reviewed_transcript(
        transcript_snapshot(
            "@UTF8\n@Begin\n*CHI: เด็กกินข้าว .\n@End\n"
        ),
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.status == "completed"
    assert result.feature_values["child_token_count"] == 2
    assert result.provenance.pipeline_version == "reviewed-transcript-descriptors-v1"
    assert result.provenance.feature_schema_version == "descriptive-transcript-features-v1"


def test_worker_does_not_turn_an_unavailable_adult_channel_into_zero_evidence() -> None:
    result = extract_reviewed_transcript(
        transcript_snapshot(
            "@UTF8\n@Begin\n*CHI: hello .\n*CHI: world .\n@End\n"
        ),
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert "response_ratio" not in result.feature_values
    assert all(value != 0.0 for key, value in result.feature_values.items() if key == "response_ratio")


def test_extract_reviewed_segment_set_uses_attested_segment_text() -> None:
    transcript = transcript_snapshot(
        "@UTF8\n@Begin\n*CHI: original transcript has more words .\n@End\n"
    )
    segment = TranscriptSegmentSnapshot(
        id="segment_opaque_01",
        organization_id=transcript.organization_id,
        segment_set_id="segment_set_opaque_01",
        ordinal=1,
        start_ms=0,
        end_ms=900,
        speaker_role=TranscriptSegmentSpeakerRole.CHILD,
        text="corrected",
        confidence=0.99,
        uncertainty_reason=TranscriptSegmentUncertaintyReason.NONE,
        created_at=datetime(2026, 9, 7, 8, 0, tzinfo=UTC),
    )
    segment_set = TranscriptSegmentSetSnapshot(
        id="segment_set_opaque_01",
        organization_id=transcript.organization_id,
        assessment_id=transcript.assessment_id,
        transcript_revision_id=transcript.id,
        transcript_content_sha256=transcript.content_sha256,
        recording_id=None,
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.ATTESTED,
        segments_sha256="a" * 64,
        segments=(segment,),
        created_by_user_id="therapist_opaque_01",
        created_at=datetime(2026, 9, 7, 8, 0, tzinfo=UTC),
        attested_by_user_id="therapist_opaque_01",
        attested_at=datetime(2026, 9, 7, 8, 1, tzinfo=UTC),
        version=2,
    )

    result = extract_reviewed_segment_set(
        transcript,
        segment_set,
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.status == "completed"
    assert result.feature_values["child_utterance_count"] == 1
    assert result.feature_values["child_token_count"] == 1
    assert result.provenance.input_ref == "transcript-segment-set:segment_set_opaque_01"
