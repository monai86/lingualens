from datetime import datetime, timezone

import pytest

from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DomainProfileStatus,
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
    build_developmental_profile,
)


def provenance() -> EvidenceProvenance:
    return EvidenceProvenance(
        input_ref="recording_opaque_01",
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
        extractor="reviewed-transcript-adapter",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
    )


def test_completed_feature_keeps_measurement_quality_and_provenance() -> None:
    feature = MeasuredFeature(
        key="child_token_count",
        value=12,
        unit="tokens",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation="Descriptive value; compare only with compatible samples.",
        provenance=provenance(),
    )

    assert feature.to_dict() == {
        "key": "child_token_count",
        "value": 12,
        "unit": "tokens",
        "source": "reviewed_transcript",
        "state": "completed",
        "limitation": "Descriptive value; compare only with compatible samples.",
        "provenance": {
            "input_ref": "recording_opaque_01",
            "input_sha256": "a" * 64,
            "protocol_version_key": "thai_guided_language_sample:v0",
            "extractor": "reviewed-transcript-adapter",
            "pipeline_version": "reviewed-transcript-descriptors-v1",
            "feature_schema_version": "descriptive-transcript-features-v1",
            "analyzed_at": "2026-09-07T08:00:00+00:00",
        },
    }


def test_unavailable_feature_cannot_carry_a_fabricated_value() -> None:
    with pytest.raises(ValueError, match="must not carry a value"):
        MeasuredFeature(
            key="pitch_variability",
            value=0.0,
            unit="hertz",
            source=EvidenceSource.AUDIO_QUALITY,
            state=EvidenceState.UNAVAILABLE,
            limitation="Pitch could not be measured from this sample.",
            provenance=provenance(),
        )


def test_profile_keeps_domains_independent_when_one_channel_is_insufficient() -> None:
    features = [
        MeasuredFeature(
            key="child_token_count",
            value=12,
            unit="tokens",
            source=EvidenceSource.REVIEWED_TRANSCRIPT,
            state=EvidenceState.COMPLETED,
            limitation="Descriptive value only.",
            provenance=provenance(),
        ),
        MeasuredFeature(
            key="question_ratio",
            value=None,
            unit="ratio",
            source=EvidenceSource.REVIEWED_TRANSCRIPT,
            state=EvidenceState.INSUFFICIENT_DATA,
            limitation="The reviewed sample is too short for a stable estimate.",
            provenance=provenance(),
        ),
    ]

    profile = build_developmental_profile(
        assessment_id="assessment_opaque_01",
        features=features,
        generated_at=datetime(2026, 9, 7, 8, 1, tzinfo=timezone.utc),
    )
    domains = {item.domain: item for item in profile.domains}

    assert domains[DevelopmentalDomain.EXPRESSIVE_LANGUAGE].status is DomainProfileStatus.DESCRIPTIVE_ONLY
    assert domains[DevelopmentalDomain.SOCIAL_COMMUNICATION].status is DomainProfileStatus.INSUFFICIENT_DATA
    assert domains[DevelopmentalDomain.SOCIAL_COMMUNICATION].limitations
    assert profile.state is EvidenceState.COMPLETED


def test_profile_is_explicitly_non_diagnostic_and_exposes_no_probability_field() -> None:
    profile = build_developmental_profile(
        assessment_id="assessment_opaque_01",
        features=[],
        generated_at=datetime(2026, 9, 7, 8, 1, tzinfo=timezone.utc),
    )

    payload = profile.to_dict()

    assert payload["not_diagnostic"] is True
    assert payload["decision_support_only"] is True
    assert payload["state"] == "insufficient_data"
    assert "diagnosis" not in payload
    assert "asd_probability" not in payload
    assert "probability" not in payload
