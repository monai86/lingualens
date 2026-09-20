"""Adapter from the analysis-only contract into assessment v2 evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from app.assessment_v2.evidence import (
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)


@dataclass(frozen=True, slots=True)
class AdaptedEvidence:
    """A safe handoff envelope before evidence is persisted or rendered."""

    state: EvidenceState
    features: tuple[MeasuredFeature, ...]
    limitations: tuple[str, ...]
    provenance: EvidenceProvenance | None = None


_FEATURE_UNITS: Mapping[str, str] = {
    "child_utterance_count": "utterances",
    "child_token_count": "tokens",
    "child_unique_token_count": "tokens",
    "mean_child_tokens_per_utterance": "tokens_per_utterance",
    "child_type_token_ratio": "ratio",
    "total_utterances": "utterances",
    "total_words": "words",
    "mlu": "morphemes_per_utterance",
    "mluw": "words_per_utterance",
    "ttr": "ratio",
    "unintelligible_count": "utterances",
    "unintelligible_ratio": "ratio",
    "zero_vocalization_count": "utterances",
    "nonverbal_vocalization_count": "vocalizations",
    "question_ratio": "ratio",
    "echolalia_count": "utterances",
    "echolalia_ratio": "ratio",
    "pronoun_reversal_count": "utterances",
    "pronoun_reversal_rate": "ratio",
    "pause_count": "pauses",
    "pause_ratio": "ratio",
    "therapist_utterances": "utterances",
    "caregiver_utterances": "utterances",
    "turn_taking_count": "turns",
    "response_latency_avg": "seconds",
    "turn_taking_latency_sec": "seconds",
    "child_adult_turn_ratio": "ratio",
    "response_ratio": "ratio",
    "question_response_ratio": "ratio",
    "repetitive_phrase_count": "phrases",
    "echolalia_similarity_score": "score",
    "speech_rate_words_per_minute": "words_per_minute",
    "pitch_mean": "hertz",
    "pitch_variability": "hertz",
    "voiced_ratio": "ratio",
    "duration_sec": "seconds",
}


def adapt_analysis_result(
    result: Any,
    *,
    input_sha256: str,
    protocol_version_key: str,
    expected_feature_schema_version: str | None = None,
) -> AdaptedEvidence:
    """Translate an analysis result without importing the analysis package.

    The loose input seam keeps the API boundary independent from the
    analysis-only package. Its dataclass result can be adapted by reading only
    the small set of required fields.
    """

    if getattr(result, "not_diagnostic", True) is not True or getattr(
        result, "decision_support_only", True
    ) is not True:
        raise ValueError("analysis result must remain non-diagnostic decision support")

    provenance_source = getattr(result, "provenance", None)
    if provenance_source is None:
        raise ValueError("analysis result provenance is required")
    analyzed_at = getattr(provenance_source, "analyzed_at", None)
    if not isinstance(analyzed_at, datetime):
        raise ValueError("analysis result timestamp is required")

    provenance = EvidenceProvenance(
        input_ref=str(getattr(provenance_source, "input_ref", "")),
        input_sha256=input_sha256,
        protocol_version_key=protocol_version_key,
        extractor="analysis-contract-reviewed-transcript",
        pipeline_version=str(getattr(provenance_source, "pipeline_version", "")),
        feature_schema_version=str(getattr(provenance_source, "feature_schema_version", "")),
        analyzed_at=analyzed_at,
    )
    warnings = _safe_limitations(getattr(result, "warnings", ()))
    status = _enum_value(getattr(result, "status", ""))
    abstention_reason = getattr(result, "abstention_reason", None)
    if abstention_reason:
        warnings = (*warnings, str(abstention_reason))

    result_input_sha256 = getattr(provenance_source, "input_sha256", None)
    if result_input_sha256 is not None and result_input_sha256 != input_sha256:
        return AdaptedEvidence(
            state=EvidenceState.STALE,
            features=(),
            limitations=(*warnings, "Analysis input checksum does not match the reviewed input."),
            provenance=provenance,
        )
    if (
        expected_feature_schema_version is not None
        and provenance.feature_schema_version != expected_feature_schema_version
    ):
        return AdaptedEvidence(
            state=EvidenceState.UNAVAILABLE,
            features=(),
            limitations=(*warnings, "Analysis feature schema is not compatible with this evidence contract."),
            provenance=provenance,
        )

    if status == "insufficient_data":
        return AdaptedEvidence(
            state=EvidenceState.INSUFFICIENT_DATA,
            features=(),
            limitations=warnings or ("The analysis did not contain sufficient reviewed evidence.",),
            provenance=provenance,
        )
    if status == "failed":
        return AdaptedEvidence(
            state=EvidenceState.UNAVAILABLE,
            features=(),
            limitations=warnings or ("The analysis failed and produced no usable measurements.",),
            provenance=provenance,
        )
    if status != "completed":
        raise ValueError("unsupported analysis result status")

    raw_features = getattr(result, "feature_values", {})
    if not isinstance(raw_features, Mapping):
        raise ValueError("analysis feature_values must be a mapping")

    unknown_output = False
    feature_limitations = _feature_limitations(warnings)
    features: list[MeasuredFeature] = []
    for key, value in raw_features.items():
        if key not in _FEATURE_UNITS:
            unknown_output = True
            continue
        feature_state = EvidenceState.COMPLETED if value is not None else EvidenceState.INSUFFICIENT_DATA
        limitation = (
            feature_limitations
            if value is not None
            else "This measurement channel was unavailable for the reviewed input."
        )
        features.append(
            MeasuredFeature(
                key=key,
                value=value,
                unit=_FEATURE_UNITS[key],
                source=EvidenceSource.REVIEWED_TRANSCRIPT,
                state=feature_state,
                limitation=limitation,
                provenance=provenance,
            )
        )

    limitations = list(warnings)
    if unknown_output:
        limitations.append("Unsupported analysis outputs were excluded from the v2 evidence contract.")
    if not features:
        limitations.append("The completed analysis contained no recognized descriptive measurements.")
        return AdaptedEvidence(
            state=EvidenceState.INSUFFICIENT_DATA,
            features=(),
            limitations=tuple(dict.fromkeys(limitations)),
            provenance=provenance,
        )
    return AdaptedEvidence(
        state=EvidenceState.COMPLETED,
        features=tuple(features),
        limitations=tuple(dict.fromkeys(limitations)),
        provenance=provenance,
    )


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _safe_limitations(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    try:
        normalized = [str(value).strip() for value in values if str(value).strip()]
    except TypeError as error:
        raise ValueError("analysis warnings must be iterable") from error
    return tuple(dict.fromkeys(normalized))


def _feature_limitations(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return "Descriptive measurement only; no compatible reference band was applied."
    return "Descriptive measurement only; analysis limitation codes: " + ", ".join(warnings)
