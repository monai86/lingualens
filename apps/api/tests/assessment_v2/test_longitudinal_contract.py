"""Tests for longitudinal comparison contract, compatibility policy, and safety boundaries."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from app.assessment_v2.evidence import (
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.longitudinal import (
    CompatibilityStatus,
    FeatureComparisonInput,
    FeatureComparisonResult,
    IncompatibilityReason,
    NumericalTrend,
    evaluate_feature_comparison,
)


def _sample_provenance(
    protocol_version_key: str = "thai_guided_language_sample:v0",
    feature_schema_version: str = "features_v1",
) -> EvidenceProvenance:
    return EvidenceProvenance(
        input_ref="seg-001",
        input_sha256="a" * 64,
        protocol_version_key=protocol_version_key,
        extractor="transcript_extractor_v1",
        pipeline_version="1.0.0",
        feature_schema_version=feature_schema_version,
        analyzed_at=datetime(2026, 9, 12, 1, 0, tzinfo=timezone.utc),
    )


def test_compatible_numeric_features_produce_exact_delta_and_percent_change() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    baseline_feat = MeasuredFeature(
        key="total_utterances",
        value=10.0,
        unit="count",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    current_feat = MeasuredFeature(
        key="total_utterances",
        value=12.0,
        unit="count",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    comp_input = FeatureComparisonInput(
        feature_key="total_utterances",
        baseline_feature=baseline_feat,
        current_feature=current_feat,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    result = evaluate_feature_comparison(comp_input)

    assert result.status == CompatibilityStatus.COMPATIBLE
    assert len(result.incompatibility_reasons) == 0
    assert result.baseline_value == 10.0
    assert result.current_value == 12.0
    assert result.absolute_delta == 2.0
    assert result.percent_change == 20.0
    assert result.percent_change_limitation is None
    assert result.numerical_trend == NumericalTrend.INCREASED
    # Clinical safety boundary: interpretation must stay indeterminate without a validated clinical norm
    assert result.clinical_interpretation == "indeterminate"


def test_zero_baseline_sets_percent_change_to_none_with_limitation() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    baseline_feat = MeasuredFeature(
        key="total_utterances",
        value=0.0,
        unit="count",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    current_feat = MeasuredFeature(
        key="total_utterances",
        value=5.0,
        unit="count",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    comp_input = FeatureComparisonInput(
        feature_key="total_utterances",
        baseline_feature=baseline_feat,
        current_feature=current_feat,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    result = evaluate_feature_comparison(comp_input)

    assert result.status == CompatibilityStatus.COMPATIBLE
    assert result.absolute_delta == 5.0
    # Percent change cannot be computed when dividing by zero
    assert result.percent_change is None
    assert result.percent_change_limitation == "zero_baseline"
    assert result.numerical_trend == NumericalTrend.INCREASED


def test_different_child_or_tenant_is_not_comparable() -> None:
    child_a = uuid4()
    child_b = uuid4()
    org_a = uuid4()
    org_b = uuid4()
    prov = _sample_provenance()

    feat_a = MeasuredFeature(
        key="mlu_words",
        value=2.5,
        unit="words_per_utterance",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat_b = MeasuredFeature(
        key="mlu_words",
        value=3.0,
        unit="words_per_utterance",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    # Different children
    input_diff_child = FeatureComparisonInput(
        feature_key="mlu_words",
        baseline_feature=feat_a,
        current_feature=feat_b,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_b,
        baseline_child_id=child_a,
        organization_id=org_a,
        baseline_organization_id=org_a,
    )
    res_child = evaluate_feature_comparison(input_diff_child)
    assert res_child.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.DIFFERENT_CHILD in res_child.incompatibility_reasons
    assert res_child.absolute_delta is None
    assert res_child.numerical_trend == NumericalTrend.INDETERMINATE

    # Different organizations (tenant isolation)
    input_diff_org = FeatureComparisonInput(
        feature_key="mlu_words",
        baseline_feature=feat_a,
        current_feature=feat_b,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_a,
        baseline_child_id=child_a,
        organization_id=org_b,
        baseline_organization_id=org_a,
    )
    res_org = evaluate_feature_comparison(input_diff_org)
    assert res_org.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.TENANT_MISMATCH in res_org.incompatibility_reasons
    assert res_org.absolute_delta is None


def test_incompatible_protocol_or_language_blocks_comparison() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    feat = MeasuredFeature(
        key="total_utterances",
        value=15.0,
        unit="count",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    # Incompatible language (th vs en)
    input_lang = FeatureComparisonInput(
        feature_key="total_utterances",
        baseline_feature=feat,
        current_feature=feat,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="en",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )
    res_lang = evaluate_feature_comparison(input_lang)
    assert res_lang.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.LANGUAGE_MISMATCH in res_lang.incompatibility_reasons

    # Incompatible protocol
    input_proto = FeatureComparisonInput(
        feature_key="total_utterances",
        baseline_feature=feat,
        current_feature=feat,
        baseline_protocol_key="unstructured_play:v1",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )
    res_proto = evaluate_feature_comparison(input_proto)
    assert res_proto.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.PROTOCOL_INCOMPATIBLE in res_proto.incompatibility_reasons


def test_non_completed_or_missing_feature_is_not_comparable() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    completed_feat = MeasuredFeature(
        key="ttr",
        value=0.45,
        unit="ratio",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    pending_feat = MeasuredFeature(
        key="ttr",
        value=None,
        unit="ratio",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.PENDING,
        limitation="Feature calculation pending",
        provenance=prov,
    )

    # Baseline pending
    input_pending = FeatureComparisonInput(
        feature_key="ttr",
        baseline_feature=pending_feat,
        current_feature=completed_feat,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )
    res_pending = evaluate_feature_comparison(input_pending)
    assert res_pending.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.BASELINE_FEATURE_NOT_COMPLETED in res_pending.incompatibility_reasons
    # Missing values remain None, never 0
    assert res_pending.baseline_value is None
    assert res_pending.current_value == 0.45
    assert res_pending.absolute_delta is None

    # Current feature missing entirely
    input_missing = FeatureComparisonInput(
        feature_key="ttr",
        baseline_feature=completed_feat,
        current_feature=None,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )
    res_missing = evaluate_feature_comparison(input_missing)
    assert res_missing.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.MISSING_FEATURE in res_missing.incompatibility_reasons
    assert res_missing.current_value is None


def test_matching_values_do_not_imply_clinical_stability_without_policy() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    feat1 = MeasuredFeature(
        key="vocabulary_size",
        value=50.0,
        unit="words",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat2 = MeasuredFeature(
        key="vocabulary_size",
        value=50.0,
        unit="words",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    comp_input = FeatureComparisonInput(
        feature_key="vocabulary_size",
        baseline_feature=feat1,
        current_feature=feat2,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    result = evaluate_feature_comparison(comp_input)
    assert result.status == CompatibilityStatus.COMPATIBLE
    assert result.absolute_delta == 0.0
    assert result.percent_change == 0.0
    assert result.numerical_trend == NumericalTrend.UNCHANGED
    # Must NOT claim clinically "stable" or "improved" without calibrated evidence policy
    assert result.clinical_interpretation == "indeterminate"


def test_unit_mismatch_blocks_comparison() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    feat_sec = MeasuredFeature(
        key="latency",
        value=2.0,
        unit="seconds",
        source=EvidenceSource.AUDIO_QUALITY,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat_ms = MeasuredFeature(
        key="latency",
        value=2000.0,
        unit="milliseconds",
        source=EvidenceSource.AUDIO_QUALITY,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    comp_input = FeatureComparisonInput(
        feature_key="latency",
        baseline_feature=feat_sec,
        current_feature=feat_ms,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    result = evaluate_feature_comparison(comp_input)
    assert result.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.UNIT_MISMATCH in result.incompatibility_reasons
    assert result.absolute_delta is None


def test_non_numeric_values_are_not_comparable_for_numeric_delta() -> None:
    child_id = uuid4()
    org_id = uuid4()
    prov = _sample_provenance()

    feat_str1 = MeasuredFeature(
        key="dominant_speaker",
        value="CHI",
        unit="speaker_code",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat_str2 = MeasuredFeature(
        key="dominant_speaker",
        value="MOT",
        unit="speaker_code",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    comp_input = FeatureComparisonInput(
        feature_key="dominant_speaker",
        baseline_feature=feat_str1,
        current_feature=feat_str2,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    result = evaluate_feature_comparison(comp_input)
    assert result.status == CompatibilityStatus.NOT_COMPARABLE
    assert IncompatibilityReason.NON_NUMERIC_VALUE in result.incompatibility_reasons
    assert result.absolute_delta is None


def test_compare_evidence_runs_aggregate_session() -> None:
    from app.assessment_v2.evidence import (
        DevelopmentalDomain,
        DevelopmentalEvidenceProfile,
        DomainProfile,
        DomainProfileStatus,
        EvidenceRunSnapshot,
    )

    child_id = uuid4()
    org_id = uuid4()
    base_asmt_id = uuid4()
    curr_asmt_id = uuid4()
    base_run_id = uuid4()
    curr_run_id = uuid4()
    prov = _sample_provenance()

    feat_comp_base = MeasuredFeature(
        key="ttr",
        value=0.4,
        unit="ratio",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat_comp_curr = MeasuredFeature(
        key="ttr",
        value=0.5,
        unit="ratio",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    feat_mismatch_base = MeasuredFeature(
        key="pitch",
        value=220.0,
        unit="Hz",
        source=EvidenceSource.AUDIO_QUALITY,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )
    feat_mismatch_curr = MeasuredFeature(
        key="pitch",
        value=220.0,
        unit="semitones",  # unit mismatch!
        source=EvidenceSource.AUDIO_QUALITY,
        state=EvidenceState.COMPLETED,
        limitation=None,
        provenance=prov,
    )

    domain_prof = DomainProfile(
        domain=DevelopmentalDomain.EXPRESSIVE_LANGUAGE,
        status=DomainProfileStatus.DESCRIPTIVE_ONLY,
        summary="Expressive language observed.",
        feature_keys=("ttr",),
        supporting_features=(),
        conflicting_features=(),
        limitations=(),
    )

    base_dev_prof = DevelopmentalEvidenceProfile(
        assessment_id=str(base_asmt_id),
        state=EvidenceState.COMPLETED,
        generated_at=datetime(2026, 9, 12, 1, 0, tzinfo=timezone.utc),
        features=(feat_comp_base, feat_mismatch_base),
        domains=(domain_prof,),
        limitations=(),
    )
    curr_dev_prof = DevelopmentalEvidenceProfile(
        assessment_id=str(curr_asmt_id),
        state=EvidenceState.COMPLETED,
        generated_at=datetime(2026, 9, 12, 2, 0, tzinfo=timezone.utc),
        features=(feat_comp_curr, feat_mismatch_curr),
        domains=(domain_prof,),
        limitations=(),
    )

    base_run = EvidenceRunSnapshot(
        id=str(base_run_id),
        organization_id=str(org_id),
        assessment_id=str(base_asmt_id),
        transcript_revision_id=str(uuid4()),
        state=EvidenceState.COMPLETED,
        provenance=prov,
        profile=base_dev_prof,
        version=1,
        segment_set_id="segset-001",
        segment_set_sha256="b" * 64,
    )
    curr_run = EvidenceRunSnapshot(
        id=str(curr_run_id),
        organization_id=str(org_id),
        assessment_id=str(curr_asmt_id),
        transcript_revision_id=str(uuid4()),
        state=EvidenceState.COMPLETED,
        provenance=prov,
        profile=curr_dev_prof,
        version=1,
        segment_set_id="segset-002",
        segment_set_sha256="c" * 64,
    )

    from app.assessment_v2.longitudinal import compare_evidence_runs

    session = compare_evidence_runs(
        baseline_run=base_run,
        current_run=curr_run,
        baseline_protocol_key="thai_guided_language_sample:v0",
        current_protocol_key="thai_guided_language_sample:v0",
        baseline_language="th",
        current_language="th",
        child_id=child_id,
        baseline_child_id=child_id,
        organization_id=org_id,
        baseline_organization_id=org_id,
    )

    assert session.baseline_assessment_id == base_asmt_id
    assert session.current_assessment_id == curr_asmt_id
    assert session.compatible_feature_count == 1
    assert session.incompatible_feature_count == 1
    assert len(session.feature_comparisons) == 2

    # Verify serialization
    data = session.to_dict()
    assert data["baseline_evidence_sha256"] == "b" * 64
    assert data["current_evidence_sha256"] == "c" * 64
    assert data["compatible_feature_count"] == 1
    assert data["incompatible_feature_count"] == 1
    assert len(data["feature_comparisons"]) == 2

