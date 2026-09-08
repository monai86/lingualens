"""Run the maintained, versioned analysis contract on an attested transcript.

The assessment workflow owns authorization, consent, provenance persistence,
and evidence presentation. The analysis-only package owns CHAT validation,
Thai tokenization, semantic checksums, and descriptive feature definitions.
Keeping this worker as a thin adapter prevents two implementations from
sharing one provenance identity while producing different measurements.
"""

from __future__ import annotations

from datetime import datetime

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

    del protocol_version_key
    request = AnalysisRequest(
        input=AnalysisInput(
            input_ref=f"transcript-revision:{transcript.id}",
            input_kind=AnalysisInputKind.REVIEWED_TRANSCRIPT,
            session_ref=f"assessment:{transcript.assessment_id}",
            transcript_version=transcript.revision,
            content_sha256=transcript.content_sha256,
        ),
        pipeline_version=TRANSCRIPT_PIPELINE_VERSION,
        feature_schema_version=FEATURE_DEFINITION_VERSION,
    )
    return analyze_reviewed_chat(request, transcript.content, analyzed_at=analyzed_at)
