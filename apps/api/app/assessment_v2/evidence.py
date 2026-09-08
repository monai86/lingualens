"""Versioned, non-diagnostic evidence contracts for assessment v2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import math
import re
from typing import Mapping


class EvidenceState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_DATA = "insufficient_data"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    STALE = "stale"


class EvidenceSource(StrEnum):
    REVIEWED_TRANSCRIPT = "reviewed_transcript"
    AUDIO_QUALITY = "audio_quality"
    OBSERVATION = "observation"
    INSTRUMENT = "instrument"


class DevelopmentalDomain(StrEnum):
    EXPRESSIVE_LANGUAGE = "expressive_language"
    SPEECH_CLARITY_PRODUCTION = "speech_clarity_production"
    CONVERSATIONAL_INTERACTION = "conversational_interaction"
    SOCIAL_COMMUNICATION = "social_communication"
    REPETITIVE_LANGUAGE = "repetitive_language"
    PROSODY_TEMPORAL_ORGANIZATION = "prosody_temporal_organization"
    EVIDENCE_QUALITY_SUFFICIENCY = "evidence_quality_sufficiency"


class DomainProfileStatus(StrEnum):
    DESCRIPTIVE_ONLY = "descriptive_only"
    WITHIN_REFERENCE_BAND = "within_reference_band"
    OUTSIDE_REFERENCE_BAND = "outside_reference_band"
    ATTENTION_SUGGESTED = "attention_suggested"
    INSUFFICIENT_DATA = "insufficient_data"
    REFERENCE_UNAVAILABLE = "reference_unavailable"
    NOT_ASSESSED = "not_assessed"


EvidenceValue = bool | int | float | str
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_INCOMPLETE_STATES = frozenset(EvidenceState) - {EvidenceState.COMPLETED}


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or any(char in value for char in "\r\n"):
        raise ValueError(f"{field_name} must be a non-empty value without newlines")


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a 64-character lowercase SHA-256 digest")


def _require_utc_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    """The reproducibility metadata attached to every measured feature."""

    input_ref: str
    input_sha256: str
    protocol_version_key: str
    extractor: str
    pipeline_version: str
    feature_schema_version: str
    analyzed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.input_ref, str) or _OPAQUE_REF.fullmatch(self.input_ref) is None:
            raise ValueError("input_ref must be an opaque reference token")
        _require_sha256(self.input_sha256, "input_sha256")
        _require_text(self.protocol_version_key, "protocol_version_key")
        _require_text(self.extractor, "extractor")
        _require_text(self.pipeline_version, "pipeline_version")
        _require_text(self.feature_schema_version, "feature_schema_version")
        _require_utc_timestamp(self.analyzed_at, "analyzed_at")

    def to_dict(self) -> dict[str, object]:
        return {
            "input_ref": self.input_ref,
            "input_sha256": self.input_sha256,
            "protocol_version_key": self.protocol_version_key,
            "extractor": self.extractor,
            "pipeline_version": self.pipeline_version,
            "feature_schema_version": self.feature_schema_version,
            "analyzed_at": self.analyzed_at.astimezone(timezone.utc).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MeasuredFeature:
    """A descriptive scalar measurement with an explicit evidence state."""

    key: str
    value: EvidenceValue | None
    unit: str
    source: EvidenceSource
    state: EvidenceState
    limitation: str | None
    provenance: EvidenceProvenance

    def __post_init__(self) -> None:
        _require_text(self.key, "feature key")
        _require_text(self.unit, "feature unit")
        if self.value is not None:
            if not isinstance(self.value, (bool, int, float, str)):
                raise ValueError("feature value must be a scalar")
            if isinstance(self.value, float) and not math.isfinite(self.value):
                raise ValueError("feature value must be finite")
        if self.state is EvidenceState.COMPLETED and self.value is None:
            raise ValueError("completed feature must carry a value")
        if self.state in _INCOMPLETE_STATES and self.value is not None:
            raise ValueError("non-completed feature must not carry a value")
        if self.state in _INCOMPLETE_STATES and not self.limitation:
            raise ValueError("non-completed feature requires a limitation")
        if self.limitation is not None:
            _require_text(self.limitation, "feature limitation")

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "source": self.source.value,
            "state": self.state.value,
            "limitation": self.limitation,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DomainProfile:
    """One developmental domain kept separate from diagnosis semantics."""

    domain: DevelopmentalDomain
    status: DomainProfileStatus
    summary: str
    feature_keys: tuple[str, ...]
    supporting_features: tuple[str, ...]
    conflicting_features: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.summary, "domain summary")
        if set(self.supporting_features) & set(self.conflicting_features):
            raise ValueError("a feature cannot be both supporting and conflicting evidence")
        for key in (*self.feature_keys, *self.supporting_features, *self.conflicting_features):
            _require_text(key, "domain feature key")
        for limitation in self.limitations:
            _require_text(limitation, "domain limitation")

    def to_dict(self) -> dict[str, object]:
        return {
            "domain": self.domain.value,
            "status": self.status.value,
            "summary": self.summary,
            "feature_keys": list(self.feature_keys),
            "supporting_features": list(self.supporting_features),
            "conflicting_features": list(self.conflicting_features),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class DevelopmentalEvidenceProfile:
    """A profile that reports evidence, not a diagnostic conclusion."""

    assessment_id: str
    state: EvidenceState
    generated_at: datetime
    features: tuple[MeasuredFeature, ...]
    domains: tuple[DomainProfile, ...]
    limitations: tuple[str, ...]
    not_diagnostic: bool = True
    decision_support_only: bool = True

    def __post_init__(self) -> None:
        _require_text(self.assessment_id, "assessment_id")
        _require_utc_timestamp(self.generated_at, "generated_at")
        if not self.not_diagnostic or not self.decision_support_only:
            raise ValueError("developmental profiles must remain non-diagnostic decision support")
        for limitation in self.limitations:
            _require_text(limitation, "profile limitation")

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "state": self.state.value,
            "generated_at": self.generated_at.astimezone(timezone.utc).isoformat(),
            "features": [feature.to_dict() for feature in self.features],
            "domains": [domain.to_dict() for domain in self.domains],
            "limitations": list(self.limitations),
            "not_diagnostic": self.not_diagnostic,
            "decision_support_only": self.decision_support_only,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRunSnapshot:
    """A persisted evidence run plus its descriptive profile."""

    id: str
    organization_id: str
    assessment_id: str
    transcript_revision_id: str
    state: EvidenceState
    provenance: EvidenceProvenance
    profile: DevelopmentalEvidenceProfile
    version: int

    def __post_init__(self) -> None:
        _require_text(self.id, "evidence run id")
        _require_text(self.organization_id, "organization id")
        _require_text(self.assessment_id, "assessment id")
        _require_text(self.transcript_revision_id, "transcript revision id")
        if self.version < 1:
            raise ValueError("evidence run version must be positive")
        if self.profile.assessment_id != self.assessment_id:
            raise ValueError("evidence profile assessment must match its run")
        if self.profile.state is not self.state:
            raise ValueError("evidence profile state must match its run")

    def to_dict(self) -> dict[str, object]:
        payload = self.profile.to_dict()
        payload.update(
            {
                "evidence_run_id": self.id,
                "transcript_revision_id": self.transcript_revision_id,
                "provenance": self.provenance.to_dict(),
                "version": self.version,
            }
        )
        return payload


_DOMAIN_FEATURES: Mapping[DevelopmentalDomain, frozenset[str]] = {
    DevelopmentalDomain.EXPRESSIVE_LANGUAGE: frozenset({
        "child_utterance_count",
        "child_token_count",
        "child_unique_token_count",
        "mean_child_tokens_per_utterance",
        "child_type_token_ratio",
        "total_utterances",
        "total_words",
        "mlu",
        "mluw",
        "ttr",
    }),
    DevelopmentalDomain.SPEECH_CLARITY_PRODUCTION: frozenset({
        "unintelligible_count",
        "unintelligible_ratio",
        "zero_vocalization_count",
        "nonverbal_vocalization_count",
    }),
    DevelopmentalDomain.CONVERSATIONAL_INTERACTION: frozenset({
        "child_adult_turn_ratio",
        "turn_taking_count",
        "response_ratio",
        "question_response_ratio",
        "response_latency_avg",
        "turn_taking_latency_sec",
    }),
    DevelopmentalDomain.SOCIAL_COMMUNICATION: frozenset({
        "question_ratio",
        "pronoun_reversal_count",
        "pronoun_reversal_rate",
    }),
    DevelopmentalDomain.REPETITIVE_LANGUAGE: frozenset({
        "echolalia_count",
        "echolalia_ratio",
        "echolalia_similarity_score",
        "repetitive_phrase_count",
    }),
    DevelopmentalDomain.PROSODY_TEMPORAL_ORGANIZATION: frozenset({
        "speech_rate_words_per_minute",
        "pause_count",
        "pause_ratio",
        "pitch_mean",
        "pitch_variability",
        "voiced_ratio",
        "duration_sec",
    }),
}


def build_developmental_profile(
    *,
    assessment_id: str,
    features: list[MeasuredFeature] | tuple[MeasuredFeature, ...],
    generated_at: datetime,
) -> DevelopmentalEvidenceProfile:
    """Build descriptive domain views without applying reference thresholds."""

    feature_values = tuple(features)
    domains = tuple(
        _build_domain_profile(domain, feature_values)
        for domain in DevelopmentalDomain
        if domain is not DevelopmentalDomain.EVIDENCE_QUALITY_SUFFICIENCY
    )
    domains += (_build_quality_domain(feature_values),)

    if not feature_values:
        state = EvidenceState.INSUFFICIENT_DATA
        limitations = ("No measured features are available for this assessment.",)
    elif any(feature.state is EvidenceState.COMPLETED for feature in feature_values):
        state = EvidenceState.COMPLETED
        limitations = tuple(
            dict.fromkeys(
                feature.limitation
                for feature in feature_values
                if feature.state is not EvidenceState.COMPLETED and feature.limitation
            )
        )
    elif all(feature.state is EvidenceState.STALE for feature in feature_values):
        state = EvidenceState.STALE
        limitations = ("All current measurements depend on stale input.",)
    elif all(feature.state in {EvidenceState.UNAVAILABLE, EvidenceState.FAILED} for feature in feature_values):
        state = EvidenceState.UNAVAILABLE
        limitations = ("The available measurement channels could not be evaluated.",)
    else:
        state = EvidenceState.INSUFFICIENT_DATA
        limitations = ("The available measurements are not sufficient for a complete profile.",)

    return DevelopmentalEvidenceProfile(
        assessment_id=assessment_id,
        state=state,
        generated_at=generated_at,
        features=feature_values,
        domains=domains,
        limitations=limitations,
    )


def _build_domain_profile(
    domain: DevelopmentalDomain,
    features: tuple[MeasuredFeature, ...],
) -> DomainProfile:
    keys = _DOMAIN_FEATURES[domain]
    matching = tuple(feature for feature in features if feature.key in keys)
    if not matching:
        return DomainProfile(
            domain=domain,
            status=DomainProfileStatus.NOT_ASSESSED,
            summary="No measurement is available for this domain.",
            feature_keys=(),
            supporting_features=(),
            conflicting_features=(),
            limitations=("This domain was not assessed by the available evidence.",),
        )
    incomplete = tuple(feature for feature in matching if feature.state is not EvidenceState.COMPLETED)
    if incomplete:
        limitations = tuple(dict.fromkeys(
            [
                *(feature.limitation for feature in incomplete if feature.limitation),
                "One or more measurements for this domain are not currently usable.",
            ]
        ))
        return DomainProfile(
            domain=domain,
            status=DomainProfileStatus.INSUFFICIENT_DATA,
            summary="Some descriptive measurements are unavailable or require review.",
            feature_keys=tuple(feature.key for feature in matching),
            supporting_features=tuple(feature.key for feature in matching if feature.state is EvidenceState.COMPLETED),
            conflicting_features=(),
            limitations=limitations,
        )
    return DomainProfile(
        domain=domain,
        status=DomainProfileStatus.DESCRIPTIVE_ONLY,
        summary="Descriptive measurements are available; no compatible reference band was applied.",
        feature_keys=tuple(feature.key for feature in matching),
        supporting_features=tuple(feature.key for feature in matching),
        conflicting_features=(),
        limitations=tuple(feature.limitation for feature in matching if feature.limitation),
    )


def _build_quality_domain(features: tuple[MeasuredFeature, ...]) -> DomainProfile:
    if not features:
        return DomainProfile(
            domain=DevelopmentalDomain.EVIDENCE_QUALITY_SUFFICIENCY,
            status=DomainProfileStatus.INSUFFICIENT_DATA,
            summary="No evidence is available to assess sufficiency.",
            feature_keys=(),
            supporting_features=(),
            conflicting_features=(),
            limitations=("Collect and review evidence before interpreting a domain profile.",),
        )
    completed = tuple(feature for feature in features if feature.state is EvidenceState.COMPLETED)
    if len(completed) != len(features):
        return DomainProfile(
            domain=DevelopmentalDomain.EVIDENCE_QUALITY_SUFFICIENCY,
            status=DomainProfileStatus.INSUFFICIENT_DATA,
            summary="The profile contains a mix of usable and unavailable evidence channels.",
            feature_keys=tuple(feature.key for feature in features),
            supporting_features=tuple(feature.key for feature in completed),
            conflicting_features=(),
            limitations=("Unavailable channels are not treated as negative evidence.",),
        )
    return DomainProfile(
        domain=DevelopmentalDomain.EVIDENCE_QUALITY_SUFFICIENCY,
        status=DomainProfileStatus.DESCRIPTIVE_ONLY,
        summary="All supplied measurements have completed provenance checks.",
        feature_keys=tuple(feature.key for feature in features),
        supporting_features=tuple(feature.key for feature in features),
        conflicting_features=(),
        limitations=("Sufficiency is descriptive until an approved reference and clinical review are available.",),
    )
