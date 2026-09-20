"""Run the maintained, versioned analysis contract on an attested transcript.

The assessment workflow owns authorization, consent, provenance persistence,
and evidence presentation. The analysis-only package owns CHAT validation,
Thai tokenization, semantic checksums, and descriptive feature definitions.
Keeping this worker as a thin adapter prevents two implementations from
sharing one provenance identity while producing different measurements.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from packages.analysis_contract.models import (
    AnalysisInput,
    AnalysisInputKind,
    AnalysisRequest,
    AnalysisResult,
)
from packages.analysis_contract.transcript import (
    FEATURE_DEFINITION_VERSION,
    TRANSCRIPT_PIPELINE_VERSION,
    analyze_reviewed_chat,
)

from app.assessment_v2.domain.models import TranscriptRevisionSnapshot, TranscriptReviewState
from app.assessment_v2.domain.segments import TranscriptSegmentSetSnapshot


def extract_reviewed_transcript(
    transcript: TranscriptRevisionSnapshot,
    *,
    protocol_version_key: str,
    analyzed_at: datetime | None = None,
) -> AnalysisResult:
    """Extract descriptive features through the shared analysis contract.

    ``protocol_version_key`` remains at this workflow seam for the caller's
    policy context. It is persisted by the evidence adapter; the analysis-only
    contract stays independent from protocol policy.
    """

    if transcript.review_state is not TranscriptReviewState.ATTESTED:
        raise ValueError("reviewed transcript must be attested before extraction")

    return _analyze_chat(
        transcript,
        transcript.content,
        input_ref=f"transcript-revision:{transcript.id}",
        transcript_version=transcript.revision,
        content_sha256=transcript.content_sha256,
        protocol_version_key=protocol_version_key,
        analyzed_at=analyzed_at,
    )


def extract_reviewed_segment_set(
    transcript: TranscriptRevisionSnapshot,
    segment_set: TranscriptSegmentSetSnapshot,
    *,
    protocol_version_key: str,
    analyzed_at: datetime | None = None,
) -> AnalysisResult:
    """Extract descriptive features from the exact attested segment snapshot."""

    if transcript.review_state is not TranscriptReviewState.ATTESTED:
        raise ValueError("reviewed transcript must be attested before extraction")
    if segment_set.review_state is not TranscriptReviewState.ATTESTED:
        raise ValueError("reviewed segment set must be attested before extraction")
    if (
        segment_set.transcript_revision_id != transcript.id
        or segment_set.transcript_content_sha256 != transcript.content_sha256
    ):
        raise ValueError("reviewed segment set must match the attested transcript")

    chat_text = _render_segment_set_as_chat(segment_set)
    return _analyze_chat(
        transcript,
        chat_text,
        input_ref=f"transcript-segment-set:{segment_set.id}",
        transcript_version=segment_set.revision,
        content_sha256=sha256(chat_text.encode("utf-8")).hexdigest(),
        protocol_version_key=protocol_version_key,
        analyzed_at=analyzed_at,
    )


def _analyze_chat(
    transcript: TranscriptRevisionSnapshot,
    chat_text: str,
    *,
    input_ref: str,
    transcript_version: int,
    content_sha256: str,
    protocol_version_key: str,
    analyzed_at: datetime | None,
) -> AnalysisResult:
    del protocol_version_key
    request = AnalysisRequest(
        input=AnalysisInput(
            input_ref=input_ref,
            input_kind=AnalysisInputKind.REVIEWED_TRANSCRIPT,
            session_ref=f"assessment:{transcript.assessment_id}",
            transcript_version=transcript_version,
            content_sha256=content_sha256,
        ),
        pipeline_version=TRANSCRIPT_PIPELINE_VERSION,
        feature_schema_version=FEATURE_DEFINITION_VERSION,
    )
    return analyze_reviewed_chat(request, chat_text, analyzed_at=analyzed_at)


def _render_segment_set_as_chat(segment_set: TranscriptSegmentSetSnapshot) -> str:
    speaker_codes = {
        "child": "CHI",
        "therapist": "INV",
        "caregiver": "PAR",
        "unknown": "UNK",
    }
    lines = ["@UTF8", "@Begin"]
    for segment in segment_set.segments:
        code = speaker_codes[segment.speaker_role.value]
        lines.append(
            f"*{code}:\t{segment.text} \x15{segment.start_ms}_{segment.end_ms}\x15"
        )
    lines.append("@End")
    return "\n".join(lines) + "\n"
