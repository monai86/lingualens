from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.assessment_v2.evidence import EvidenceState
from app.assessment_v2.evidence_adapter import adapt_analysis_result


def analysis_result(
    *,
    status: str,
    feature_values: dict[str, object],
    abstention_reason: str | None = None,
    input_sha256: str | None = "a" * 64,
    feature_schema_version: str = "descriptive-transcript-features-v1",
):
    return SimpleNamespace(
        status=status,
        provenance=SimpleNamespace(
            input_ref="recording_opaque_01",
            input_sha256=input_sha256,
            pipeline_version="reviewed-transcript-descriptors-v1",
            feature_schema_version=feature_schema_version,
            analyzed_at=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
        ),
        feature_values=feature_values,
        warnings=("SHORT_SAMPLE",),
        abstention_reason=abstention_reason,
        not_diagnostic=True,
        decision_support_only=True,
    )


def test_adapter_maps_completed_analysis_values_and_preserves_provenance() -> None:
    result = adapt_analysis_result(
        analysis_result(
            status="completed",
            feature_values={
                "child_token_count": 12,
                "child_unique_token_count": 8,
                "mean_child_tokens_per_utterance": 3.0,
                "child_type_token_ratio": 0.6667,
                "analysis_profile_checksum_sha256": "not-a-measurement",
            },
        ),
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.state is EvidenceState.COMPLETED
    assert [feature.key for feature in result.features] == [
        "child_token_count",
        "child_unique_token_count",
        "mean_child_tokens_per_utterance",
        "child_type_token_ratio",
    ]
    assert result.features[0].unit == "tokens"
    assert result.features[0].provenance.input_sha256 == "a" * 64
    assert result.features[0].provenance.protocol_version_key == "thai_guided_language_sample:v0"
    assert result.features[0].limitation
    assert "SHORT_SAMPLE" in result.limitations
    assert any("Unsupported analysis outputs" in item for item in result.limitations)


def test_adapter_preserves_partially_unavailable_channels_without_fabricating_values() -> None:
    result = adapt_analysis_result(
        analysis_result(
            status="completed",
            feature_values={"child_token_count": 12, "question_ratio": None},
        ),
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
    )

    by_key = {feature.key: feature for feature in result.features}
    assert result.state is EvidenceState.COMPLETED
    assert by_key["child_token_count"].value == 12
    assert by_key["question_ratio"].value is None
    assert by_key["question_ratio"].state is EvidenceState.INSUFFICIENT_DATA
    assert by_key["question_ratio"].limitation


def test_adapter_maps_insufficient_analysis_to_explicit_unavailable_evidence() -> None:
    result = adapt_analysis_result(
        analysis_result(
            status="insufficient_data",
            feature_values={},
            abstention_reason="NO_CHILD_CONTENT: no reviewed child content",
            input_sha256="b" * 64,
        ),
        input_sha256="b" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.state is EvidenceState.INSUFFICIENT_DATA
    assert result.features == ()
    assert any("NO_CHILD_CONTENT" in item for item in result.limitations)


def test_adapter_rejects_analysis_result_that_breaks_non_diagnostic_boundary() -> None:
    invalid = analysis_result(status="completed", feature_values={"child_token_count": 1})
    invalid.not_diagnostic = False

    with pytest.raises(ValueError, match="non-diagnostic"):
        adapt_analysis_result(
            invalid,
            input_sha256="c" * 64,
            protocol_version_key="thai_guided_language_sample:v0",
        )


def test_adapter_marks_input_checksum_mismatch_as_stale_without_features() -> None:
    result = adapt_analysis_result(
        analysis_result(
            status="completed",
            feature_values={"child_token_count": 12},
            input_sha256="b" * 64,
        ),
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
    )

    assert result.state is EvidenceState.STALE
    assert result.features == ()
    assert any("checksum" in limitation.lower() for limitation in result.limitations)


def test_adapter_marks_schema_mismatch_as_unavailable_without_features() -> None:
    result = adapt_analysis_result(
        analysis_result(
            status="completed",
            feature_values={"child_token_count": 12},
            feature_schema_version="descriptive-transcript-features-v1",
        ),
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
        expected_feature_schema_version="descriptive-transcript-features-v2",
    )

    assert result.state is EvidenceState.UNAVAILABLE
    assert result.features == ()
    assert any("schema" in limitation.lower() for limitation in result.limitations)
