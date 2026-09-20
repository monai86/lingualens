# Implementation Plan - Slice B1: Longitudinal Comparison Contract & Policy

## 1. Goal & Context
Define immutable longitudinal comparison contracts, compatibility evaluation policies, numerical delta calculations, and clinical safety boundaries for follow-up assessments in LinguaLens.

## 2. Core Principles & Clinical Safety
- **Separation of Concerns:** Numerical change (e.g., delta = 2.0, percent change = 20%) is strictly separated from clinical interpretation.
- **Indeterminate Default:** Without an empirically validated Thai clinical norm or intervention directionality policy, the interpretation is `TrendDirection.INDETERMINATE` / `TrendDirection.UNCHANGED` (numerical only), NEVER automatically labeled `improved` or `worsened`.
- **Zero Baseline Handling:** If baseline value is 0.0, percent change is unavailable (`None`), with reason `zero_baseline`.
- **Strict Compatibility Rules:** Comparing two features requires:
  - Same child (`child_id`) and same organization (`organization_id`).
  - Compatible protocol keys (must match or belong to an explicitly registered equivalent protocol).
  - Compatible language (e.g. `th`).
  - Matching units (`unit`).
  - Compatible extractor / schema version.
  - Feature state must be `COMPLETED` on both runs. Missing or incomplete states return `NOT_COMPARABLE` with reasons, and `None` for values (missing values remain missing, never 0).
- **Prohibited:** No ASD probability percentages, no synthetic thresholds, no uncalibrated diagnostic severity metrics.

## 3. Proposed Files & Exact Paths
- Domain Module: `apps/api/app/assessment_v2/longitudinal.py`
- Test Suite: `apps/api/tests/assessment_v2/test_longitudinal_contract.py`

## 4. Domain Models & Types (`longitudinal.py`)

### Enumerations:
- `CompatibilityStatus`:
  - `COMPATIBLE = "compatible"`
  - `NOT_COMPARABLE = "not_comparable"`
- `NumericalTrend`:
  - `INCREASED = "increased"`
  - `DECREASED = "decreased"`
  - `UNCHANGED = "unchanged"`
  - `INDETERMINATE = "indeterminate"`
- `IncompatibilityReason`:
  - `DIFFERENT_CHILD = "different_child"`
  - `TENANT_MISMATCH = "tenant_mismatch"`
  - `PROTOCOL_INCOMPATIBLE = "protocol_incompatible"`
  - `LANGUAGE_MISMATCH = "language_mismatch"`
  - `UNIT_MISMATCH = "unit_mismatch"`
  - `EXTRACTOR_MISMATCH = "extractor_mismatch"`
  - `BASELINE_FEATURE_NOT_COMPLETED = "baseline_feature_not_completed"`
  - `CURRENT_FEATURE_NOT_COMPLETED = "current_feature_not_completed"`
  - `MISSING_FEATURE = "missing_feature"`
  - `NON_NUMERIC_VALUE = "non_numeric_value"`
  - `QUALITY_INSUFFICIENT = "quality_insufficient"`

### Dataclasses:
- `FeatureComparisonInput`:
  - `feature_key`: str
  - `baseline_feature`: MeasuredFeature | None
  - `current_feature`: MeasuredFeature | None
  - `baseline_protocol_key`: str
  - `current_protocol_key`: str
  - `baseline_language`: str
  - `current_language`: str
  - `child_id`: UUID
  - `baseline_child_id`: UUID
  - `organization_id`: UUID
  - `baseline_organization_id`: UUID
- `FeatureComparisonResult`:
  - `feature_key`: str
  - `unit`: str | None
  - `status`: CompatibilityStatus
  - `incompatibility_reasons`: tuple[IncompatibilityReason, ...]
  - `baseline_value`: float | int | None
  - `current_value`: float | int | None
  - `absolute_delta`: float | None
  - `percent_change`: float | None
  - `percent_change_limitation`: str | None (e.g. `"zero_baseline"`)
  - `numerical_trend`: NumericalTrend
  - `clinical_interpretation`: str ("indeterminate")
  - `policy_version`: str
- `AssessmentComparisonSession`:
  - `baseline_assessment_id`: UUID
  - `baseline_evidence_run_id`: UUID
  - `baseline_evidence_sha256`: str
  - `current_assessment_id`: UUID
  - `current_evidence_run_id`: UUID
  - `current_evidence_sha256`: str
  - `child_id`: UUID
  - `organization_id`: UUID
  - `policy_version`: str
  - `created_at`: datetime
  - `feature_comparisons`: tuple[FeatureComparisonResult, ...]
  - `compatible_feature_count`: int
  - `incompatible_feature_count`: int

### Core Functions:
- `evaluate_feature_comparison(input: FeatureComparisonInput, policy_version: str = "longitudinal_v1") -> FeatureComparisonResult`
- `compare_evidence_runs(baseline_run, current_run, ...) -> AssessmentComparisonSession`

## 5. Failing Tests (TDD RED Phase)
In `apps/api/tests/assessment_v2/test_longitudinal_contract.py`:
1. `test_compatible_numeric_features_produce_exact_delta_and_percent_change`:
   - baseline = 10.0, current = 12.0 -> absolute_delta = 2.0, percent_change = 20.0, trend = INCREASED, clinical_interpretation = "indeterminate".
2. `test_zero_baseline_sets_percent_change_to_none_with_limitation`:
   - baseline = 0.0, current = 5.0 -> absolute_delta = 5.0, percent_change = None, limitation = "zero_baseline".
3. `test_different_child_or_tenant_is_not_comparable`:
   - mismatch child_id or organization_id -> status = NOT_COMPARABLE, reason = DIFFERENT_CHILD / TENANT_MISMATCH, absolute_delta = None.
4. `test_incompatible_protocol_or_language_blocks_comparison`:
   - thai_v0 vs english_v0 or different protocol -> status = NOT_COMPARABLE, reason = PROTOCOL_INCOMPATIBLE / LANGUAGE_MISMATCH, no trend arrow.
5. `test_non_completed_or_missing_feature_is_not_comparable`:
   - baseline state = PENDING or UNAVAILABLE -> status = NOT_COMPARABLE, reason = BASELINE_FEATURE_NOT_COMPLETED, values stay None (never 0).
6. `test_matching_values_do_not_imply_clinical_stability_without_policy`:
   - baseline = 15.0, current = 15.0 -> delta = 0.0, numerical_trend = UNCHANGED, clinical_interpretation = "indeterminate".
7. `test_unit_mismatch_blocks_comparison`:
   - seconds vs words -> status = NOT_COMPARABLE, reason = UNIT_MISMATCH.
8. `test_non_numeric_values_are_not_comparable_for_numeric_delta`:
   - boolean or string feature values -> status = NOT_COMPARABLE, reason = NON_NUMERIC_VALUE.

## 6. Verification Commands
```bash
PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_longitudinal_contract.py -v
PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q
```
