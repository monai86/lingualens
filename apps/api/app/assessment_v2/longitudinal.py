"""Longitudinal assessment comparison contracts, compatibility policies, and safety boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import math
from typing import Mapping, Sequence
from uuid import UUID

from app.assessment_v2.evidence import (
    EvidenceRunSnapshot,
    EvidenceState,
    MeasuredFeature,
)


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    NOT_COMPARABLE = "not_comparable"


class NumericalTrend(StrEnum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"
    INDETERMINATE = "indeterminate"


class IncompatibilityReason(StrEnum):
    DIFFERENT_CHILD = "different_child"
    TENANT_MISMATCH = "tenant_mismatch"
    PROTOCOL_INCOMPATIBLE = "protocol_incompatible"
    LANGUAGE_MISMATCH = "language_mismatch"
    UNIT_MISMATCH = "unit_mismatch"
    EXTRACTOR_MISMATCH = "extractor_mismatch"
    BASELINE_FEATURE_NOT_COMPLETED = "baseline_feature_not_completed"
    CURRENT_FEATURE_NOT_COMPLETED = "current_feature_not_completed"
    MISSING_FEATURE = "missing_feature"
    NON_NUMERIC_VALUE = "non_numeric_value"
    QUALITY_INSUFFICIENT = "quality_insufficient"


@dataclass(frozen=True, slots=True)
class FeatureComparisonInput:
    """Pair of measurements with their operational and clinical context."""

    feature_key: str
    baseline_feature: MeasuredFeature | None
    current_feature: MeasuredFeature | None
    baseline_protocol_key: str
    current_protocol_key: str
    baseline_language: str
    current_language: str
    child_id: UUID | str
    baseline_child_id: UUID | str
    organization_id: UUID | str
    baseline_organization_id: UUID | str


@dataclass(frozen=True, slots=True)
class FeatureComparisonResult:
    """Result of comparing a single feature across two assessments."""

    feature_key: str
    unit: str | None
    status: CompatibilityStatus
    incompatibility_reasons: tuple[IncompatibilityReason, ...]
    baseline_value: float | int | None
    current_value: float | int | None
    absolute_delta: float | None
    percent_change: float | None
    percent_change_limitation: str | None
    numerical_trend: NumericalTrend
    clinical_interpretation: str
    policy_version: str

    def to_dict(self) -> dict[str, object]:
        return {
            "feature_key": self.feature_key,
            "unit": self.unit,
            "status": self.status.value,
            "incompatibility_reasons": [r.value for r in self.incompatibility_reasons],
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "absolute_delta": self.absolute_delta,
            "percent_change": self.percent_change,
            "percent_change_limitation": self.percent_change_limitation,
            "numerical_trend": self.numerical_trend.value,
            "clinical_interpretation": self.clinical_interpretation,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True, slots=True)
class AssessmentComparisonSession:
    """Aggregate comparison between a baseline and a current evidence run."""

    baseline_assessment_id: UUID | str
    baseline_evidence_run_id: UUID | str
    baseline_evidence_sha256: str
    current_assessment_id: UUID | str
    current_evidence_run_id: UUID | str
    current_evidence_sha256: str
    child_id: UUID | str
    organization_id: UUID | str
    policy_version: str
    created_at: datetime
    feature_comparisons: tuple[FeatureComparisonResult, ...]
    compatible_feature_count: int
    incompatible_feature_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_assessment_id": str(self.baseline_assessment_id),
            "baseline_evidence_run_id": str(self.baseline_evidence_run_id),
            "baseline_evidence_sha256": self.baseline_evidence_sha256,
            "current_assessment_id": str(self.current_assessment_id),
            "current_evidence_run_id": str(self.current_evidence_run_id),
            "current_evidence_sha256": self.current_evidence_sha256,
            "child_id": str(self.child_id),
            "organization_id": str(self.organization_id),
            "policy_version": self.policy_version,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "feature_comparisons": [f.to_dict() for f in self.feature_comparisons],
            "compatible_feature_count": self.compatible_feature_count,
            "incompatible_feature_count": self.incompatible_feature_count,
        }


def _is_numeric(val: object) -> bool:
    """Return True if value is a real number (int or float, but NOT bool)."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return math.isfinite(val)
    return False


def evaluate_feature_comparison(
    input: FeatureComparisonInput,
    policy_version: str = "longitudinal_v1",
) -> FeatureComparisonResult:
    """Evaluate compatibility and calculate numerical change for a single feature."""
    reasons: list[IncompatibilityReason] = []

    # 1. Identity & Tenant isolation check
    if input.child_id != input.baseline_child_id:
        reasons.append(IncompatibilityReason.DIFFERENT_CHILD)
    if input.organization_id != input.baseline_organization_id:
        reasons.append(IncompatibilityReason.TENANT_MISMATCH)

    # 2. Context & Protocol compatibility check
    if input.baseline_protocol_key != input.current_protocol_key:
        reasons.append(IncompatibilityReason.PROTOCOL_INCOMPATIBLE)
    if input.baseline_language != input.current_language:
        reasons.append(IncompatibilityReason.LANGUAGE_MISMATCH)

    # 3. Presence of features
    if input.baseline_feature is None or input.current_feature is None:
        reasons.append(IncompatibilityReason.MISSING_FEATURE)
        base_val = (
            input.baseline_feature.value
            if input.baseline_feature and _is_numeric(input.baseline_feature.value)
            else None
        )
        curr_val = (
            input.current_feature.value
            if input.current_feature and _is_numeric(input.current_feature.value)
            else None
        )
        unit = (
            input.baseline_feature.unit
            if input.baseline_feature
            else (input.current_feature.unit if input.current_feature else None)
        )
        return FeatureComparisonResult(
            feature_key=input.feature_key,
            unit=unit,
            status=CompatibilityStatus.NOT_COMPARABLE,
            incompatibility_reasons=tuple(reasons),
            baseline_value=base_val,
            current_value=curr_val,
            absolute_delta=None,
            percent_change=None,
            percent_change_limitation=None,
            numerical_trend=NumericalTrend.INDETERMINATE,
            clinical_interpretation="indeterminate",
            policy_version=policy_version,
        )

    base_feat = input.baseline_feature
    curr_feat = input.current_feature
    unit = base_feat.unit

    # 4. Feature completion states
    if base_feat.state != EvidenceState.COMPLETED:
        reasons.append(IncompatibilityReason.BASELINE_FEATURE_NOT_COMPLETED)
    if curr_feat.state != EvidenceState.COMPLETED:
        reasons.append(IncompatibilityReason.CURRENT_FEATURE_NOT_COMPLETED)

    # 5. Unit matching
    if base_feat.unit != curr_feat.unit:
        reasons.append(IncompatibilityReason.UNIT_MISMATCH)

    # 6. Schema & extractor compatibility
    if (
        base_feat.provenance.extractor != curr_feat.provenance.extractor
        or base_feat.provenance.feature_schema_version != curr_feat.provenance.feature_schema_version
    ):
        reasons.append(IncompatibilityReason.EXTRACTOR_MISMATCH)

    # 7. Numeric value validation
    base_is_num = _is_numeric(base_feat.value)
    curr_is_num = _is_numeric(curr_feat.value)
    if not (base_is_num and curr_is_num):
        reasons.append(IncompatibilityReason.NON_NUMERIC_VALUE)

    base_val = float(base_feat.value) if base_is_num else None
    curr_val = float(curr_feat.value) if curr_is_num else None

    if reasons:
        return FeatureComparisonResult(
            feature_key=input.feature_key,
            unit=unit,
            status=CompatibilityStatus.NOT_COMPARABLE,
            incompatibility_reasons=tuple(reasons),
            baseline_value=base_val,
            current_value=curr_val,
            absolute_delta=None,
            percent_change=None,
            percent_change_limitation=None,
            numerical_trend=NumericalTrend.INDETERMINATE,
            clinical_interpretation="indeterminate",
            policy_version=policy_version,
        )

    # Valid compatible comparison
    assert base_val is not None and curr_val is not None
    absolute_delta = round(curr_val - base_val, 6)

    percent_change: float | None = None
    percent_limitation: str | None = None
    if base_val == 0.0:
        percent_change = None
        percent_limitation = "zero_baseline"
    else:
        percent_change = round(((curr_val - base_val) / abs(base_val)) * 100.0, 4)

    if absolute_delta > 0.0:
        trend = NumericalTrend.INCREASED
    elif absolute_delta < 0.0:
        trend = NumericalTrend.DECREASED
    else:
        trend = NumericalTrend.UNCHANGED

    return FeatureComparisonResult(
        feature_key=input.feature_key,
        unit=unit,
        status=CompatibilityStatus.COMPATIBLE,
        incompatibility_reasons=(),
        baseline_value=base_val,
        current_value=curr_val,
        absolute_delta=absolute_delta,
        percent_change=percent_change,
        percent_change_limitation=percent_limitation,
        numerical_trend=trend,
        clinical_interpretation="indeterminate",
        policy_version=policy_version,
    )


def compare_evidence_runs(
    baseline_run: EvidenceRunSnapshot,
    current_run: EvidenceRunSnapshot,
    baseline_protocol_key: str,
    current_protocol_key: str,
    baseline_language: str,
    current_language: str,
    child_id: UUID | str,
    baseline_child_id: UUID | str,
    organization_id: UUID | str,
    baseline_organization_id: UUID | str,
    policy_version: str = "longitudinal_v1",
) -> AssessmentComparisonSession:
    """Compare all features between two evidence runs under the longitudinal policy."""
    now = datetime.now(timezone.utc)
    base_features_by_key = {f.key: f for f in baseline_run.profile.features}
    curr_features_by_key = {f.key: f for f in current_run.profile.features}
    all_keys = sorted(set(base_features_by_key.keys()) | set(curr_features_by_key.keys()))

    results: list[FeatureComparisonResult] = []
    for key in all_keys:
        input_item = FeatureComparisonInput(
            feature_key=key,
            baseline_feature=base_features_by_key.get(key),
            current_feature=curr_features_by_key.get(key),
            baseline_protocol_key=baseline_protocol_key,
            current_protocol_key=current_protocol_key,
            baseline_language=baseline_language,
            current_language=current_language,
            child_id=child_id,
            baseline_child_id=baseline_child_id,
            organization_id=organization_id,
            baseline_organization_id=baseline_organization_id,
        )
        results.append(evaluate_feature_comparison(input_item, policy_version=policy_version))

    compatible_count = sum(1 for r in results if r.status == CompatibilityStatus.COMPATIBLE)
    incompatible_count = len(results) - compatible_count

    baseline_sha256 = baseline_run.segment_set_sha256 or baseline_run.provenance.input_sha256
    current_sha256 = current_run.segment_set_sha256 or current_run.provenance.input_sha256

    return AssessmentComparisonSession(
        baseline_assessment_id=UUID(baseline_run.assessment_id) if isinstance(baseline_run.assessment_id, str) else baseline_run.assessment_id,
        baseline_evidence_run_id=UUID(baseline_run.id) if isinstance(baseline_run.id, str) else baseline_run.id,
        baseline_evidence_sha256=baseline_sha256,
        current_assessment_id=UUID(current_run.assessment_id) if isinstance(current_run.assessment_id, str) else current_run.assessment_id,
        current_evidence_run_id=UUID(current_run.id) if isinstance(current_run.id, str) else current_run.id,
        current_evidence_sha256=current_sha256,
        child_id=child_id,
        organization_id=organization_id,
        policy_version=policy_version,
        created_at=now,
        feature_comparisons=tuple(results),
        compatible_feature_count=compatible_count,
        incompatible_feature_count=incompatible_count,
    )
