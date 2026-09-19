from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.assessment_v2.domain.models import (
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptSource,
)
from app.assessment_v2.domain.segments import (
    TranscriptSegment,
    TranscriptSegmentSnapshot,
    canonicalize_transcript_segments,
    compute_transcript_segments_sha256,
)
from app.assessment_v2.schemas import TranscriptSegmentSetCreateRequest


def _segment(
    ordinal: int = 1,
    *,
    start_ms: int = 0,
    end_ms: int = 900,
    text: str = "hello",
    confidence: float | None = 0.92,
    uncertainty_reason: TranscriptSegmentUncertaintyReason = (
        TranscriptSegmentUncertaintyReason.NONE
    ),
) -> TranscriptSegment:
    return TranscriptSegment(
        ordinal=ordinal,
        start_ms=start_ms,
        end_ms=end_ms,
        speaker_role=TranscriptSegmentSpeakerRole.CHILD,
        text=text,
        confidence=confidence,
        uncertainty_reason=uncertainty_reason,
    )


def test_segment_contract_accepts_ordered_segments_and_computes_stable_sha256() -> None:
    segments = (
        _segment(1, start_ms=0, end_ms=900),
        _segment(
            2,
            start_ms=900,
            end_ms=1_800,
            text="world",
            confidence=None,
            uncertainty_reason=TranscriptSegmentUncertaintyReason.LOW_ASR_CONFIDENCE,
        ),
    )

    canonical = canonicalize_transcript_segments(segments)

    assert canonical == segments
    assert compute_transcript_segments_sha256(segments) == compute_transcript_segments_sha256(
        tuple(segments)
    )
    assert len(compute_transcript_segments_sha256(segments)) == 64


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("ordinal", 0, "ordinal"),
        ("start_ms", -1, "start_ms"),
        ("end_ms", 0, "end_ms must be greater"),
        ("confidence", -0.1, "confidence"),
        ("confidence", 1.1, "confidence"),
        ("text", "   ", "text"),
    ),
)
def test_segment_contract_rejects_invalid_segment_values(field: str, value: object, message: str) -> None:
    kwargs = {field: value}
    with pytest.raises(ValueError, match=message):
        _segment(**kwargs)


def test_segment_contract_rejects_unsupported_enums() -> None:
    with pytest.raises(ValueError, match="speaker_role"):
        TranscriptSegment(
            ordinal=1,
            start_ms=0,
            end_ms=100,
            speaker_role="unknown-speaker",  # type: ignore[arg-type]
            text="hello",
        )

    with pytest.raises(ValueError, match="uncertainty_reason"):
        TranscriptSegment(
            ordinal=1,
            start_ms=0,
            end_ms=100,
            speaker_role=TranscriptSegmentSpeakerRole.CHILD,
            text="hello",
            uncertainty_reason="not-supported",  # type: ignore[arg-type]
        )


def test_segment_contract_rejects_duplicate_or_non_contiguous_ordinals() -> None:
    with pytest.raises(ValueError, match="ordinal"):
        canonicalize_transcript_segments((_segment(1), _segment(1, start_ms=900, end_ms=1_800)))

    with pytest.raises(ValueError, match="contiguous"):
        canonicalize_transcript_segments((_segment(1), _segment(3, start_ms=900, end_ms=1_800)))


def test_segment_contract_rejects_time_that_moves_backwards() -> None:
    with pytest.raises(ValueError, match="start_ms"):
        canonicalize_transcript_segments(
            (_segment(1, start_ms=500), _segment(2, start_ms=400, end_ms=900))
        )


def test_segment_contract_rejects_client_checksum_mismatch() -> None:
    with pytest.raises(ValueError, match="client checksum"):
        canonicalize_transcript_segments((_segment(),), client_checksum="b" * 64)


def test_segment_contract_uses_enum_values_in_canonical_digest() -> None:
    child = compute_transcript_segments_sha256((_segment(),))
    therapist = compute_transcript_segments_sha256(
        (
            TranscriptSegment(
                ordinal=1,
                start_ms=0,
                end_ms=900,
                speaker_role=TranscriptSegmentSpeakerRole.THERAPIST,
                text="hello",
            ),
        )
    )

    assert child != therapist


def test_segment_snapshot_keeps_opaque_id_without_changing_canonical_segment() -> None:
    segment = _segment()
    snapshot = TranscriptSegmentSnapshot(
        id="segment_opaque_01",
        organization_id="org_opaque_01",
        segment_set_id="segment_set_opaque_01",
        ordinal=segment.ordinal,
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        speaker_role=segment.speaker_role,
        text=segment.text,
        confidence=segment.confidence,
        uncertainty_reason=segment.uncertainty_reason,
        created_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )

    assert snapshot.to_segment() == segment
    assert snapshot.id == "segment_opaque_01"


def test_segment_set_request_rejects_duplicate_ordinals_and_newline_text() -> None:
    base = {
        "transcript_revision_id": "transcript_opaque_01",
        "source": TranscriptSource.MANUAL,
    }
    duplicate = {
        **base,
        "segments": [
            {"ordinal": 1, "start_ms": 0, "end_ms": 100, "speaker_role": "child", "text": "one"},
            {"ordinal": 1, "start_ms": 100, "end_ms": 200, "speaker_role": "child", "text": "two"},
        ],
    }
    with pytest.raises(ValueError, match="contiguous"):
        TranscriptSegmentSetCreateRequest.model_validate(duplicate)

    with pytest.raises(ValueError, match="newline"):
        TranscriptSegmentSetCreateRequest.model_validate(
            {
                **base,
                "segments": [
                    {
                        "ordinal": 1,
                        "start_ms": 0,
                        "end_ms": 100,
                        "speaker_role": "child",
                        "text": "one\ntwo",
                    }
                ],
            }
        )
