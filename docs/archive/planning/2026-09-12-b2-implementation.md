# Implementation Plan - Slice B2: Longitudinal API & Persistence

## 1. Goal & Context
Build durable persistence, repositories, service methods, and typed HTTP API routes for longitudinal assessment comparisons in LinguaLens under `/api/v2`.

## 2. Relational Schema & Migration (`0011_longitudinal_comparisons.py`)
- Tables:
  1. `assessment_comparisons`:
     - `comparison_id` (VARCHAR(64), PK)
     - `organization_id` (VARCHAR(64), FK to organizations, indexed)
     - `child_id` (VARCHAR(64), FK to children, indexed)
     - `baseline_assessment_id` (VARCHAR(64), FK to assessments)
     - `current_assessment_id` (VARCHAR(64), FK to assessments)
     - `baseline_evidence_run_id` (VARCHAR(64), FK to evidence_runs)
     - `current_evidence_run_id` (VARCHAR(64), FK to evidence_runs)
     - `baseline_evidence_sha256` (VARCHAR(64))
     - `current_evidence_sha256` (VARCHAR(64))
     - `policy_version` (VARCHAR(64), default 'longitudinal_v1')
     - `status` (VARCHAR(32), 'compatible' | 'not_comparable')
     - `is_stale` (BOOLEAN, default False)
     - `created_at` (TIMESTAMP WITH TIME ZONE)
     - Unique constraint: `(organization_id, baseline_evidence_run_id, current_evidence_run_id, policy_version)`
     - Tenant RLS: `ENABLE/FORCE ROW LEVEL SECURITY`, tenant isolation policy checking `app.current_organization_id`.
  2. `assessment_comparison_features`:
     - `comparison_feature_id` (VARCHAR(64), PK)
     - `organization_id` (VARCHAR(64), FK to organizations, indexed)
     - `comparison_id` (VARCHAR(64), FK to assessment_comparisons, indexed)
     - `feature_key` (VARCHAR(64))
     - `unit` (VARCHAR(32), nullable)
     - `status` (VARCHAR(32), 'compatible' | 'not_comparable')
     - `incompatibility_reasons_json` (JSON, list of reason strings)
     - `baseline_value` (FLOAT, nullable)
     - `current_value` (FLOAT, nullable)
     - `absolute_delta` (FLOAT, nullable)
     - `percent_change` (FLOAT, nullable)
     - `percent_change_limitation` (VARCHAR(64), nullable)
     - `numerical_trend` (VARCHAR(32))
     - `clinical_interpretation` (VARCHAR(64), default 'indeterminate')
     - `created_at` (TIMESTAMP WITH TIME ZONE)
     - Unique constraint: `(organization_id, comparison_id, feature_key)`
     - Tenant RLS: enabled with tenant isolation policy.

## 3. Longitudinal Repository (`apps/api/app/assessment_v2/db/longitudinal_repository.py`)
- `save_comparison(session: AssessmentComparisonSession) -> AssessmentComparisonRecord`
- `get_comparison(organization_id: str, comparison_id: str) -> AssessmentComparisonRecord | None`
- `get_comparison_by_runs(organization_id: str, baseline_run_id: str, current_run_id: str, policy_version: str) -> AssessmentComparisonRecord | None`
- `list_comparisons_for_assessment(organization_id: str, assessment_id: str) -> list[AssessmentComparisonRecord]`
- `list_assessments_history_for_child(organization_id: str, child_id: str) -> list[ChildAssessmentHistoryItem]`
- `mark_stale_comparisons_for_evidence_run(organization_id: str, superseded_evidence_run_id: str) -> int`

## 4. API Endpoints & Schemas (`schemas.py`, `routes.py`)
- `POST /api/v2/assessments/{assessment_id}/comparisons`:
  - Request: `{"baseline_assessment_id": "uuid", "policy_version": "longitudinal_v1"}`
  - Responses: `201 Created` / `200 OK` (idempotent), `400 Bad Request` (different child, invalid scope), `404 Not Found`, `403 Forbidden`
- `GET /api/v2/assessments/{assessment_id}/comparisons`:
  - Returns list of comparisons for this assessment.
- `GET /api/v2/children/{child_id}/assessments/history`:
  - Returns ordered list of child assessments with dates, protocol key, language, evidence status, and comparison eligibility.

## 5. TDD RED Phase Tests
- `apps/api/tests/assessment_v2/test_longitudinal_db_models.py`:
  - Verify table existence, columns, foreign keys, and Alembic upgrade/downgrade to `0011_longitudinal_comparisons`.
- `apps/api/tests/assessment_v2/test_longitudinal_repository.py`:
  - Verify save, retrieval, idempotent lookup, stale marking, and child history listing.
- `apps/api/tests/assessment_v2/test_longitudinal_routes.py`:
  - Verify route authorization, same-child validation, tenant isolation, zero baseline response, and stale flag.
- `apps/api/tests/assessment_v2/test_longitudinal_migration_rls.py`:
  - Verify RLS ddl and policies in migration 0011.

## 6. Acceptance Criteria
- Full test suite passes without regressions.
- Migration smoke script runs through 0011 cleanly.
