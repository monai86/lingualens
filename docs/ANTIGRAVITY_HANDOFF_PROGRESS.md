# LinguaLens Antigravity Handoff Progress

This document tracks the execution progress of the LinguaLens therapist research prototype roadmap according to `docs/superpowers/plans/2026-09-12-antigravity-remaining-work-roadmap.md`.

---

## Slice: P0 — Make the Starting Point Reproducible
- **Status:** accepted
- **Workspace / branch / base / candidate:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - Base Commit: `5fb37457167b079d63d5ffe10d63a1cd2cd88706` (`feat(assessment): add durable evidence processing`)
  - Upstream Base / Root Workstream: `/Users/porschecaa/lingualens`, branch `codex/ml-workflow-hardening`, commit `a60aa2df` (contains root ML research changes, preserved untouched)
  - Frozen A2 Source: `/Users/porschecaa/lingualens/.worktrees/assessment-v2-segment-review`, branch `codex/assessment-v2-segment-review`, HEAD `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
  - Frozen A2 Candidate ID: `sha256:19f144e944e768982412cec31397b3e7bb62ac9241dc66a9a9f43fb646304ef3`
  - Common Git Directory: `/Users/porschecaa/lingualens/.git`
  - Assurance Ledger: `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md`
- **Acceptance criteria and actual result:**
  - *Criteria:* Verified A2 inventory and hashes match manifest with 0 divergence; reproducible source snapshot created in separate continuation workspace without copying credentials/caches/dependency dirs; root ML workstream preserved untouched; snapshot provenance and integration base recorded; A2 terminal assurance limitations carried forward.
  - *Actual Result:* All 51 manifest files verified with SHA-256 matching `candidate-manifest.json` exactly (0 divergence). Continuation workspace created from commit `5fb37457` on branch `antigravity/assessment-v2-continuation` with the 51 files overlaid and re-verified. Root `codex/ml-workflow-hardening` and frozen A2 workspace remain pristine and untouched.
- **Changed files (including untracked):**
  - Tracked/modified from A2 (38 files):
    - `CHANGELOG.md`
    - `DEVELOPER_SETUP.md`
    - `README.md`
    - `apps/api/app/assessment_v2/db/models.py`
    - `apps/api/app/assessment_v2/db/repositories.py`
    - `apps/api/app/assessment_v2/domain/models.py`
    - `apps/api/app/assessment_v2/evidence.py`
    - `apps/api/app/assessment_v2/evidence_worker.py`
    - `apps/api/app/assessment_v2/reviewed_transcript_worker.py`
    - `apps/api/app/assessment_v2/routes.py`
    - `apps/api/app/assessment_v2/schemas.py`
    - `apps/api/app/assessment_v2/services.py`
    - `apps/api/tests/assessment_v2/test_capture_db_models.py`
    - `apps/api/tests/assessment_v2/test_capture_route_integration.py`
    - `apps/api/tests/assessment_v2/test_db_models.py`
    - `apps/api/tests/assessment_v2/test_evidence_db_models.py`
    - `apps/api/tests/assessment_v2/test_evidence_processing_repository.py`
    - `apps/api/tests/assessment_v2/test_evidence_processing_worker.py`
    - `apps/api/tests/assessment_v2/test_native_runtime_contract.py`
    - `apps/api/tests/assessment_v2/test_postgres_processing_leases.py`
    - `apps/api/tests/assessment_v2/test_postgres_rls.py`
    - `apps/api/tests/assessment_v2/test_processing_db_models.py`
    - `apps/api/tests/assessment_v2/test_reviewed_transcript_worker.py`
    - `apps/lingualens-app/e2e/assessment-v2-transcript.smoke.spec.ts`
    - `apps/lingualens-app/src/__tests__/assessment-evidence-workspace.test.tsx`
    - `apps/lingualens-app/src/__tests__/assessment-transcript-review-workspace.test.tsx`
    - `apps/lingualens-app/src/__tests__/assessment-v2-client.test.ts`
    - `apps/lingualens-app/src/app/assessments/[assessmentId]/transcript/page.tsx`
    - `apps/lingualens-app/src/services/assessment-v2-client.ts`
    - `docs/CURRENT_HANDOFF.md`
    - `docs/DEVELOPMENT.md`
    - `docs/PROJECT_SOURCE_OF_TRUTH.md`
    - `docs/ux/therapist-workflow/api-screen-contract-map.md`
    - `docs/ux/therapist-workflow/figma-delivery-manifest.md`
    - `docs/ux/therapist-workflow/frame-inventory.csv`
    - `docs/ux/therapist-workflow/prototype-scenarios.md`
    - `scripts/check_assessment_v2_migrations.py`
    - `scripts/check_assessment_v2_native.py`
  - Untracked from A2 (13 files):
    - `apps/api/app/assessment_v2/db/migrations/versions/0008_transcript_segments.py`
    - `apps/api/app/assessment_v2/db/migrations/versions/0009_segment_evidence_provenance.py`
    - `apps/api/app/assessment_v2/domain/segments.py`
    - `apps/api/tests/assessment_v2/test_segment_contract.py`
    - `apps/api/tests/assessment_v2/test_segment_db_models.py`
    - `apps/api/tests/assessment_v2/test_segment_migration_rls.py`
    - `apps/api/tests/assessment_v2/test_segment_repository.py`
    - `apps/api/tests/assessment_v2/test_segment_routes.py`
    - `apps/api/tests/assessment_v2/test_segment_service.py`
    - `apps/lingualens-app/src/__tests__/assessment-segment-review-workspace.test.tsx`
    - `apps/lingualens-app/src/features/assessment-v2/components/assessment-segment-review-ui.tsx`
    - `apps/lingualens-app/src/features/assessment-v2/components/assessment-segment-review-workspace.tsx`
    - `docs/plans/2026-09-09-assessment-v2-segment-review.md`
  - Continuation tracking (1 file):
    - `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` (this file)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - P0 is an operations, baseline setup, and documentation slice. No code behavior changes were made; no retroactive TDD claims.
- **Commands, exit status, environment and receipt paths:**
  - `git worktree add -b antigravity/assessment-v2-continuation /Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation 5fb37457167b079d63d5ffe10d63a1cd2cd88706`: exit 0
  - Python candidate manifest hash recomputation: exit 0 (51 files, 0 divergence, computed candidate ID `sha256:19f144e944e768982412cec31397b3e7bb62ac9241dc66a9a9f43fb646304ef3` matches expected)
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_segment_contract.py -q`: exit 0 (14 passed in 0.45s)
  - `PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_migrations.py`: exit 0 (upgrades and downgrades through 0009 pass)
  - `npm test -- src/__tests__/assessment-segment-review-workspace.test.tsx`: exit 0 (4 tests passed)
  - `git diff --check`: exit 0
- **Research / Figma / external evidence:**
  - Inherited Figma status: Manifest records working skeleton (`docs/ux/therapist-workflow/figma-delivery-manifest.md`). Remote export/acceptance remains pending.
  - ML Research status: Root folder `docs/DATA_INVENTORY_AND_ML_ROADMAP.md` and `reports/ml/` detail feature v2/v3 explorations and data inventory. Preserved without collision.
- **Assurance status and inherited limitations:**
  - A2 unit status carried forward: `parent-completed`, `review-exhausted`, `final-strict-not-achieved`.
  - Review budget: 3/3 calls used; budget is exhausted and must not be reset.
  - Historical TDD gap: Contemporaneous RED receipts are missing for call-1 fixes (unbound-job cancellation, replay race/currentness, attestation-collision handling).
  - External release blocker: Frontend dependency audit has 8 known advisories (2 moderate, 5 high, 1 critical).
  - Merge/release restriction: Release or merge of the candidate requires exact owner acceptance per AGENTS. Local development and testing are permitted; automated commit/push/merge/deploy is strictly prohibited.
- **Unresolved issues / exact external action needed:**
  - Remote Figma authenticated inspection/exports for U1.
  - Managed Supabase staging credentials for S1.
- **Next smallest task:**
  - Complete U1/E1 (done) and proceed to Slice B1 (Comparison Contract & Policy).

---

## Slice: U1 — UX & Design Review Handoff
- **Status:** accepted (local specs and frame inventory extended; remote Figma sync blocked)
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Check for live Figma access or local token; inspect Figma manifest and frame inventory; create comprehensive screen-level specification document covering all 5 therapist steps and missing comparative/history/error frames; document exact 7-step checklist for future authenticated Figma session; do not fake visual assets or claim remote acceptance.
  - *Actual Result:* Verified no Figma tokens/credentials exist in local environment. Created complete wireframe & screen specification document `docs/ux/therapist-workflow/wireframes-and-screen-specs.md` detailing layouts, states, clinical safety banners, and interaction contracts for all steps: Step 1 (Child/Consent/Protocol), Step 2 (Recording/Capture/Quality Gate), Step 3 (Segment Review/Boundary/Split/Merge/Attestation), Step 4 (Profile, Comparable History `H14-Compatible`/`H14-Incompatible`/`H14-NoHistory`, Observations & Instruments), Step 5 (Notes/Goals/Follow-up & Signed Report). Extended `docs/ux/therapist-workflow/frame-inventory.csv` with explicit rows for `H14-NoHistory`, `H14-Incompatible`, `H14-Compatible`, and `E18`. Maintained remote delivery status in `docs/ux/therapist-workflow/figma-delivery-manifest.md` as `blocked` with 7-step authorized session checklist.
- **Changed files:**
  - `docs/ux/therapist-workflow/wireframes-and-screen-specs.md` (new)
  - `docs/ux/therapist-workflow/frame-inventory.csv` (modified: added H14-NoHistory, H14-Incompatible, H14-Compatible, E18)
  - `docs/ux/therapist-workflow/figma-delivery-manifest.md` (updated)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - Non-code UX documentation slice.
- **Assurance status and limitations:**
  - Remote Figma delivery blocked due to missing API token and unauthenticated local environment. Screen specs establish unambiguous layout and contract requirements for all subsequent UI slices.
- **Next smallest task:**
  - Slices B1, B2, B3 for Longitudinal comparison contract and therapist history UI.

---

## Slice: E1 — Feature Evidence Completeness & Multimodal Research Alignment
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Audit local scientific papers at `/Users/porschecaa/Desktop/Paper-ASD/` against feature inventory; document feature evidence matrix with 15 canonical features, missing states, acoustic boundary caveats, and Thai tonal transfer constraints; implement domain models for structured clinician observations and standardized instruments (M-CHAT-R/F, Vineland-3, ADOS-2, Thai TDLR-II); implement database models, Alembic migration with PostgreSQL tenant RLS, and repository with strict TDD.
  - *Actual Result:* Audited 10 research papers directly from disk (`RBSTR768`, `27IITKNS`, `2M5MN383`, `2BW3LG5M`, `7IKT7JCG`, `XSIL8EJU`, `H7DB7I5I`, `KMH2LMXK`, `QJR8K5QS`, `G8VSSXXB`). Created comprehensive `docs/research/feature-evidence-matrix.md` (v2.0) with exact page citations, cohort demographics, language/task contexts, Thai tonal transfer boundaries, and explicit separation of measured features, qualitative observations, and generic instruments. Implemented `AssessmentObservation`, `InstrumentAdministration`, `AssessmentInstrumentItem` domain models; added SQLAlchemy ORM records with tenant foreign keys and RLS policies; created migration `0010_observations_instruments.py` (verified <=32 char revision ID); implemented `AssessmentObservationRepository`. All TDD cycles documented (RED -> GREEN).
- **Changed files:**
  - `docs/research/feature-evidence-matrix.md` (new / updated v2.0)
  - `apps/api/app/assessment_v2/domain/observations.py` (new)
  - `apps/api/app/assessment_v2/domain/instruments.py` (new)
  - `apps/api/app/assessment_v2/db/models.py` (modified: added observation and instrument ORM models)
  - `apps/api/app/assessment_v2/db/migrations/versions/0010_observations_instruments.py` (new)
  - `apps/api/app/assessment_v2/db/observations_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_observations.py` (new)
  - `apps/api/tests/assessment_v2/test_instruments.py` (new)
  - `apps/api/tests/assessment_v2/test_observation_db_models.py` (new)
  - `apps/api/tests/assessment_v2/test_observation_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_observation_migration_rls.py` (new)
  - `scripts/check_assessment_v2_migrations.py` (modified: added 0010 tables and head revision)
  - `apps/api/tests/assessment_v2/test_capture_db_models.py` (modified: excluded new tables, updated head revision)
  - `apps/api/tests/assessment_v2/test_evidence_db_models.py` (modified: updated head revision)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `test_observations.py`: RED (ImportError: domain.observations not found) -> GREEN (4 passed)
  - `test_instruments.py`: RED (ImportError: domain.instruments not found) -> GREEN (3 passed)
  - `test_observation_db_models.py`: RED (ImportError: ORM models not defined) -> GREEN (5 passed)
  - `test_observation_repository.py`: RED (ImportError: repository not defined) -> GREEN (4 passed)
  - `test_observation_migration_rls.py`: RED (migration missing) -> GREEN (1 passed)
- **Commands, exit status, environment and receipt paths:**
  - `PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_migrations.py`: exit 0 (migrations 0001 through 0010 upgrade and downgrade cleanly)
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q`: exit 0 (405 passed, 10 deselected, 2 warnings in 13.46s)
  - `npm test -- src/__tests__/assessment-`: exit 0 (7 test files, 32 passed in 1.84s)
- **Assurance status and limitations:**
  - Research domain entities and DB tables are ready for multimodal fusion. Thai tonal acoustic features remain bounded by Praat/openSMILE script requirements per research matrix.
- **Next smallest task:**
  - Slice B1 completed; proceed to Slice B2 (Longitudinal API & Persistence).

---

## Slice: B1 — Longitudinal Comparison Contract & Policy
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Define per-feature compatibility policy across identity (child/tenant), language, protocol key, units, extractor/schema version, and completion state; separate numerical change from clinical interpretation; default trend/interpretation to `indeterminate` without calibrated clinical norm; handle zero baseline percent change safely (`None` with `zero_baseline` limitation); maintain missing values as `None` without substituting zero; provide immutable comparison inputs linking evidence runs, assessments, checksums, and policy version.
  - *Actual Result:* Implemented `apps/api/app/assessment_v2/longitudinal.py` with `CompatibilityStatus`, `NumericalTrend`, `IncompatibilityReason`, `FeatureComparisonInput`, `FeatureComparisonResult`, and `AssessmentComparisonSession`. Implemented strict `evaluate_feature_comparison()` and `compare_evidence_runs()` functions. All criteria verified with 9 comprehensive unit tests in `apps/api/tests/assessment_v2/test_longitudinal_contract.py`.
- **Changed files:**
  - `docs/superpowers/plans/2026-09-12-b1-implementation.md` (new)
  - `apps/api/app/assessment_v2/longitudinal.py` (new)
  - `apps/api/tests/assessment_v2/test_longitudinal_contract.py` (new)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `test_longitudinal_contract.py`: RED (ModuleNotFoundError: No module named 'app.assessment_v2.longitudinal', exit 2) -> GREEN (9 passed in 0.07s).
- **Commands, exit status, environment and receipt paths:**
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_longitudinal_contract.py -v`: exit 0 (9 passed in 0.07s)
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q`: exit 0 (405 passed, 10 deselected, 2 warnings in 12.30s)
- **Assurance status and limitations:**
  - Numerical delta evaluation is completely decoupled from diagnostic claims. Thai longitudinal norm bands remain unavailable until validated reference cohorts are established.
- **Next smallest task:**
  - Slice B1 completed; proceeded to Slice B2 and B3.

---

## Slice: B2 — Longitudinal API & Persistence
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Implement ORM models (`AssessmentComparisonRecord`, `AssessmentComparisonFeatureRecord`) with tenant foreign keys and PostgreSQL RLS; create additive Alembic migration `0011_longitudinal_comparisons.py` (revision ID <= 32 characters) with downgrade and upgrade verified; build `LongitudinalRepository` with idempotent session persistence, run-based lookup, and stale-source marking; implement service methods and API endpoints under `/api/v2` (`POST /api/v2/assessments/{assessment_id}/comparisons`, `GET /api/v2/assessments/{assessment_id}/comparisons`, `GET /api/v2/assessments/{assessment_id}/comparisons/{comparison_id}`, `GET /api/v2/children/{child_id}/assessments/history`); enforce security gates: tenant isolation, same-child boundary, protocol/language/schema mismatch handling, consent withdrawal blocking, stale source detection, and concurrency safety.
  - *Actual Result:* Added ORM models in `apps/api/app/assessment_v2/db/models.py`; created Alembic migration `0011_longitudinal_comparisons.py` with PostgreSQL tenant RLS policies; created `LongitudinalRepository` with transactional idempotency in `apps/api/app/assessment_v2/db/longitudinal_repository.py`; added Pydantic schemas in `schemas.py`; implemented service methods in `services.py`; added REST endpoints in `routes.py`. All 19 unit, model, repository, and route tests pass cleanly. Native PostgreSQL DB/RLS check passed against local PostgreSQL database.
- **Changed files:**
  - `docs/superpowers/plans/2026-09-12-b2-implementation.md` (new)
  - `apps/api/app/assessment_v2/db/models.py` (modified: added `AssessmentComparisonRecord` and `AssessmentComparisonFeatureRecord`)
  - `apps/api/app/assessment_v2/db/migrations/versions/0011_longitudinal_comparisons.py` (new)
  - `apps/api/app/assessment_v2/db/longitudinal_repository.py` (new)
  - `apps/api/app/assessment_v2/schemas.py` (modified: added comparison request/response schemas)
  - `apps/api/app/assessment_v2/services.py` (modified: added longitudinal comparison and history services)
  - `apps/api/app/assessment_v2/routes.py` (modified: added comparison and history endpoints)
  - `apps/api/tests/assessment_v2/test_longitudinal_db_models.py` (new)
  - `apps/api/tests/assessment_v2/test_longitudinal_migration_rls.py` (new)
  - `apps/api/tests/assessment_v2/test_longitudinal_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_longitudinal_routes.py` (new)
  - `scripts/check_assessment_v2_migrations.py` (modified: registered 0011 migration and comparison tables)
  - `scripts/check_assessment_v2_native.py` (modified: registered 0011 migration and comparison tables)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `test_longitudinal_db_models.py`: RED (ImportError: models not defined, exit 2) -> GREEN (1 passed)
  - `test_longitudinal_migration_rls.py`: RED (migration missing, exit 2) -> GREEN (1 passed)
  - `test_longitudinal_repository.py`: RED (ImportError: repository not defined, exit 2) -> GREEN (2 passed)
  - `test_longitudinal_routes.py`: RED (AttributeError / 404 routes not defined, exit 2) -> GREEN (6 passed)
- **Commands, exit status, environment and receipt paths:**
  - `PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_migrations.py`: exit 0 (migrations 0001 through 0011 upgrade and downgrade cleanly)
  - `PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_native.py`: exit 0 (10 passed, migrations=0009..0011, RLS verified, worker leases passed)
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_longitudinal_*.py -v`: exit 0 (19 passed in 1.76s)
  - `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q`: exit 0 (415 passed, 10 deselected, 2 warnings in 12.56s)
- **Assurance status and limitations:**
  - All comparisons are tenant-scoped and child-scoped. Stale source checks mark historical comparisons when new evidence runs are completed for an assessment.
- **Next smallest task:**
  - Proceed to Slice B3: Therapist History UI Workspace.

---

## Slice: B3 — Therapist History UI Workspace & 3-Visit Scenario
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Extend TypeScript API client (`assessment-v2-client.ts`) with longitudinal comparison and history endpoints; build React workspace component `assessment-longitudinal-workspace.tsx` implementing frames `H14-NoHistory`, `H14-Incompatible`, and `H14-Compatible`; display baseline selector dropdown, stale warning banner, zero baseline limitation badges, and non-diagnostic clinical safety disclaimers; integrate route `/assessments/[assessmentId]/history`; write component unit tests and an end-to-end Playwright browser scenario for a synthetic 3-visit child history where Visit 2 is incompatible (different protocol) and Visit 1 is compatible.
  - *Actual Result:* Implemented client methods and types (`createComparison`, `getComparisons`, `getComparison`, `getChildAssessmentHistory`); built `assessment-longitudinal-workspace.tsx` and history page route; connected link in evidence workspace; wrote 3 Vitest component tests in `src/__tests__/assessment-longitudinal-workspace.test.tsx` (covering empty history, 3-visit scenario, stale warning, zero baseline, and clinical safety); wrote Playwright E2E spec in `e2e/assessment-v2-longitudinal.smoke.spec.ts`. All 35 assessment Vitest tests pass; full Vitest suite (548 tests in 65 files) passes; TypeScript typecheck passes with 0 errors; Playwright E2E test passed in 13.0s.
- **Changed files:**
  - `apps/lingualens-app/src/services/assessment-v2-client.ts` (modified: added longitudinal comparison types and methods)
  - `apps/lingualens-app/src/features/assessment-v2/components/assessment-longitudinal-workspace.tsx` (new)
  - `apps/lingualens-app/src/app/assessments/[assessmentId]/history/page.tsx` (new)
  - `apps/lingualens-app/src/features/assessment-v2/components/assessment-evidence-workspace.tsx` (modified: added history navigation link)
  - `apps/lingualens-app/src/__tests__/assessment-longitudinal-workspace.test.tsx` (new)
  - `apps/lingualens-app/e2e/assessment-v2-longitudinal.smoke.spec.ts` (new)
  - `apps/lingualens-app/playwright.config.ts` (modified: webpack flag for symlink resolution)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `assessment-longitudinal-workspace.test.tsx`: RED (Cannot find module '../components/assessment-longitudinal-workspace') -> GREEN (3 passed in 360ms)
  - `e2e/assessment-v2-longitudinal.smoke.spec.ts`: RED (label selector mismatch) -> GREEN (1 passed in 13.0s)
- **Commands, exit status, environment and receipt paths:**
  - `npm test -- src/__tests__/assessment-longitudinal-workspace.test.tsx`: exit 0 (3 passed in 360ms)
  - `npm test -- src/__tests__/assessment-`: exit 0 (8 test files, 35 passed in 2.15s)
  - `npm run typecheck`: exit 0 (0 errors)
  - `PLAYWRIGHT_FRONTEND_PORT=3188 PLAYWRIGHT_BACKEND_PORT=8088 npx playwright test e2e/assessment-v2-longitudinal.smoke.spec.ts`: exit 0 (1 passed in 13.0s)
  - `PLAYWRIGHT_FRONTEND_PORT=3188 PLAYWRIGHT_BACKEND_PORT=8088 npx playwright test e2e/assessment-v2-transcript.smoke.spec.ts`: exit 0 (1 passed in 19.0s)
  - `bash scripts/check_project.sh`: exit 0 (All 7 project verification steps passed: repo consistency, security scan, Python imports, 1,228 core Python tests, Alembic migrations 0001->0013 API & 0001->0011 assessment-v2, 415 assessment-v2 tests, 548 frontend vitest tests, Next.js production build compiled).
- **Assurance status and limitations:**
  - Clinical safety is strictly enforced in the UI: numerical deltas are displayed with units and signs, but clinical interpretations remain `indeterminate`. No automated "improved" or "stable" labels are generated. Zero baseline changes are clearly marked with `N/A (zero_baseline)` limitations.
- **Next smallest task:**
  - Slices B1–B3 complete. Proceeded to Slices C1–C2.

---

## Slice: C1 — Reviewable Attention Cues & Clinician Disposition
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Implement non-exclusive attention cues referenced to evidence and policy version (`cues-v2.0`); support clinician actions (`acknowledged`, `disagreed`, `more_evidence_requested`) with required rationale for disagreement / requests; implement clinician disposition and follow-up plan with optimistic concurrency versioning; ensure computed cues NEVER auto-populate report conclusions without clinician review; multiple concerns represented independently without diagnostic probabilities (ASD / delay percentages).
  - *Actual Result:* Implemented domain model in `clinical_review.py` (`AttentionCue`, `AttentionCueType`, `CueStatus`, `ClinicalDispositionType`, `FollowUpPlan`, `ClinicalReviewSession`, `evaluate_attention_cues`); created ORM models `AssessmentClinicalReviewRecord` and `AssessmentAttentionCueRecord` in `models.py`; created `ClinicalReviewRepository` with optimistic versioning; implemented REST endpoints (`GET /clinical-review`, `POST /cues/{cue_id}`, `POST /disposition`); built `assessment-clinical-review-workspace.tsx` and Next.js page `/assessments/[assessmentId]/review`. All contract, repository, and route tests pass.
- **Changed files:**
  - `apps/api/app/assessment_v2/clinical_review.py` (new)
  - `apps/api/app/assessment_v2/db/clinical_review_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_clinical_review_contract.py` (new)
  - `apps/api/tests/assessment_v2/test_clinical_review_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_clinical_review_routes.py` (new)
  - `apps/lingualens-app/src/features/assessment-v2/components/assessment-clinical-review-workspace.tsx` (new)
  - `apps/lingualens-app/src/app/assessments/[assessmentId]/review/page.tsx` (new)
  - `apps/lingualens-app/src/__tests__/assessment-clinical-review-workspace.test.tsx` (new)
- **TDD & Verification evidence:**
  - `test_clinical_review_contract.py`: 5 passed
  - `test_clinical_review_repository.py`: 1 passed
  - `test_clinical_review_routes.py`: 3 passed
  - `assessment-clinical-review-workspace.test.tsx`: 5 passed
- **Assurance status and limitations:**
  - Attention cues are decision-support only. No ASD or language delay percentages are computed.

---

## Slice: C2 — Report Draft, Immutable Sign-Off, PDF Export & Amendment Lineage
- **Status:** accepted
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Server-side readiness validation (active consent, current evidence, zero unreviewed cues, disposition present, authorized assigned signer match, safety text checks, optimistic concurrency); immutable signed snapshot with deterministic SHA-256 hash; repeated sign idempotency; authorized PDF export with Thai font rendering; post-sign edits create linked amendment drafts with audit lineage.
  - *Actual Result:* Implemented domain model in `reports.py` (`ReportStatus`, `ReportReadiness`, `check_report_signoff_readiness`, `generate_report_draft_markdown`, `build_signed_report_snapshot`, `render_assessment_v2_pdf`); created ORM model `AssessmentReportRecord` in `models.py`; created Alembic migration `0012_clinical_review_reports.py` with PostgreSQL tenant RLS policies; created `ReportsRepository` with optimistic concurrency, hash idempotency, and amendment branching; implemented REST endpoints (`POST /reports/draft`, `GET /reports/current`, `GET /reports/{id}`, `PUT /reports/{id}`, `POST /reports/{id}/sign`, `POST /reports/{id}/amend`, `GET /reports/{id}/export`, `GET /reports/{id}/lineage`); built `assessment-report-workspace.tsx` and Next.js page `/assessments/[assessmentId]/report`.
- **Changed files:**
  - `apps/api/app/assessment_v2/reports.py` (new)
  - `apps/api/app/assessment_v2/db/reports_repository.py` (new)
  - `apps/api/app/assessment_v2/db/migrations/versions/0012_clinical_review_reports.py` (new)
  - `apps/api/tests/assessment_v2/test_reports_contract.py` (new)
  - `apps/api/tests/assessment_v2/test_reports_repository.py` (new)
  - `apps/api/tests/assessment_v2/test_reports_routes.py` (new)
  - `apps/api/tests/assessment_v2/test_reports_pdf_export.py` (new)
  - `apps/lingualens-app/src/features/assessment-v2/components/assessment-report-workspace.tsx` (new)
  - `apps/lingualens-app/src/app/assessments/[assessmentId]/report/page.tsx` (new)
  - `apps/lingualens-app/src/__tests__/assessment-report-workspace.test.tsx` (new)
  - `scripts/check_assessment_v2_migrations.py` (modified: registered 0012 migration)
  - `scripts/check_assessment_v2_native.py` (modified: registered 0012 migration and tables)
- **TDD & Verification evidence:**
  - `test_reports_contract.py`: 3 passed
  - `test_reports_pdf_export.py`: 1 passed (Thai TTF rendering verified)
  - `test_reports_repository.py`: 1 passed
  - `test_reports_routes.py`: 3 passed
  - `assessment-report-workspace.test.tsx`: 5 passed
  - `test_postgres_rls.py`: 11 passed in native PostgreSQL check
  - `check_assessment_v2_migrations.py`: exit 0 (migrations 0001 -> 0012 upgrade and downgrade verified)
  - `check_assessment_v2_native.py`: exit 0
  - `npm run typecheck`: exit 0
  - `npm run build`: exit 0 (compiled successfully with /review and /report pages)
- **Assurance status and limitations:**
  - Signed snapshots are strictly immutable (HTTP 409 `report_immutable` on edit attempts). Changes require `POST /amend` creating a traceable amendment lineage.
- **Next smallest task:**
  - C1 and C2 completed. Proceeded to S1/V1 preparation.

---

## Slice: S1/V1 — Staging Preparation & Therapist Pilot / Research Deliverables
- **Status:** accepted (preparation & local checks verified; external staging execution & live user test pending)
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Acceptance criteria and actual result:**
  - *Criteria:* Prepare reproducible staging checks and runbook; run external staging ONLY when exact environment authority and live credentials are present; verify real JWT/JWKS, two-tenant RLS, care-team, consent, private storage/expiry, worker recovery, backup/restore, and redacted telemetry; local mocks must never count as evidence of managed Supabase staging; collect usability results from real participants without fabricating synthetic user data (state execution pending if not yet run); compile paper traceability and reproducibility package; separate prototype-ready, pilot-ready, and clinical-validation with exact blockers; do not erase real data or exceed authority.
  - *Actual Result:*
    - Staging Runbook created at `docs/staging/STAGING_READINESS_RUNBOOK.md` detailing exact procedures for real Supabase staging gates. Local disposable PostgreSQL RLS verified (11/11 tests pass in `scripts/check_assessment_v2_native.py` with forced RLS on all 24 tables); external staging marked **EXECUTION PENDING** on live operator credentials/authority (zero fake claims).
    - Therapist Walkthrough Guide created at `docs/ux/therapist-workflow/THERAPIST_WALKTHROUGH_GUIDE.md` covering 7 synthetic clinical scenarios: normal progression, sparse evidence, conflicting attention cues, incompatible follow-up, consent withdrawal, offline upload, and amended report lineage.
    - Usability Evaluation Plan created at `docs/ux/therapist-workflow/USABILITY_EVALUATION_PLAN.md` with recruitment criteria ($N=5$ SLPs), session schedule, task cards (T1–T5), evaluation rubrics (SUS, completion, time on task), and the mandatory safety probe ("Does this screen diagnose ASD?"). Current execution status explicitly marked: **EXECUTION PENDING (Zero fabricated participant responses)**.
    - Reproducibility Package compiled at `docs/research/REPRODUCIBILITY_PACKAGE.md` with 10-paper traceability table (DOI, pages, cohorts, features, Thai transfer boundaries), canonical schema versions (`features_v2`, `cues-v2.0`, `longitudinal_v1`, `report_v1`), toolchain versions, and deterministic test receipts.
    - Readiness Assessment Summary compiled at `docs/readiness/READINESS_ASSESSMENT_SUMMARY.md` explicitly categorizing:
      1. **Prototype-Ready:** 100% COMPLETE & VERIFIED locally.
      2. **Pilot-Ready:** BLOCKED on 6 external prerequisites (live Supabase credentials, managed RLS run, private storage bucket, IRB ethics approval, live therapist testing, clinic PDPA agreement).
      3. **Clinical-Validation:** NOT VALIDATED (Research prototype; explicitly not a diagnostic device; automated ASD diagnosis is strictly prohibited; separate representative Thai clinical validation required).
- **Changed files:**
  - `docs/staging/STAGING_READINESS_RUNBOOK.md` (new)
  - `docs/ux/therapist-workflow/THERAPIST_WALKTHROUGH_GUIDE.md` (new)
  - `docs/ux/therapist-workflow/USABILITY_EVALUATION_PLAN.md` (new)
  - `docs/research/REPRODUCIBILITY_PACKAGE.md` (new)
  - `docs/readiness/READINESS_ASSESSMENT_SUMMARY.md` (new)
  - `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` (modified: this file)
- **TDD & Verification evidence:**
  - `check_assessment_v2_native.py`: 11/11 passed (Native PostgreSQL RLS isolation verified on all 24 tables)
  - `check_assessment_v2_migrations.py`: exit 0 (migrations 0001 -> 0012 upgrade and downgrade verified)
  - `pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q`: 432 passed
  - `npm run typecheck`: exit 0
  - `npm run build`: exit 0
- **Assurance status and limitations:**
  - External staging and live therapist usability evaluation require real operator authority, live staging credentials, and institutional IRB approval. All limitations and pending execution statuses are documented transparently without mock substitution.
- **Next smallest task:**
  - S1/V1 preparation complete. Deliver handoff summary to user.

---

## Continuation Audit — Current Candidate Reconciliation
- **Date:** 2026-09-12 (Asia/Bangkok)
- **Workspace / branch / base:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - HEAD/base: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
- **Reconciliation result:** The continuation workspace is not the frozen A2 candidate anymore. Against the A2 51-path manifest, 36 paths still match byte-for-byte, 15 paths have changed, 57 additional paths are present, and 0 manifest paths are missing. Current `git status --porcelain=v1 --untracked-files=all` reports 108 paths. The 15 changed paths include later E1/B/C migration, API, test, and client-contract edits; the 57 additions include the later observation, longitudinal, clinical-review, report, UX, research, readiness, and handoff artifacts plus the current D1 test. Therefore historical full-suite/native/browser receipts above are not treated as current-candidate attestations.
- **A2 assurance boundary:** Common Git directory is `/Users/porschecaa/lingualens/.git`; `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md` remains `UNIT_STATUS: parent-completed`, `REVIEW_STATUS: review-exhausted`, `REVIEW_CALLS_USED: 3`, with no active reservation. No A2 budget was reopened or changed.
- **Root workstream check:** Root `/Users/porschecaa/lingualens` remains on `codex/ml-workflow-hardening` at `a60aa2df`; its pre-existing ML workstream was not edited by this round.

## Slice: D1 — Thin-client no-silent-fallback hardening (first checkpoint)
- **Status:** implemented (D1 slice remains in progress)
- **Workspace / branch / base:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - Base: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
- **Acceptance criteria and actual result:**
  - *Criteria for this smallest checkpoint:* when `mock_mode=False`, live REST failures must remain errors; the GUI/TUI must not report local mock success after an API outage, authorization failure, or server error. Explicit mock behavior remains available only when `mock_mode=True`.
  - *Actual Result:* Removed silent `except Exception: pass` fallback from the live branches of case, session, transcript, findings, attestation, and report operations in `packages/tui/client.py`. The shared client is consumed by both `packages/tui/workflow.py` and `packages/gui/app.py`, so this closes the same fallback path for both clients. Local mock data is unchanged and is used only in explicit mock mode.
- **Changed files:**
  - `packages/tui/client.py` (modified: propagate live REST failures instead of returning local mock state)
  - `tests/test_tui.py` (new regression test covering case/session/transcript/findings/report operations and no mock-state mutation)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `TDD_REQUIRED: yes`.
  - Observable seam: `LinguaLensClient` live-operation boundary with `mock_mode=False`.
  - RED: `PYTHONPATH=.:src python3 -m pytest tests/test_tui.py -q` -> 1 failed, 4 passed; the new test failed with `Failed: DID NOT RAISE RuntimeError`, demonstrating live calls were swallowed and local fallback was returned.
  - GREEN: same command after the minimal client change -> 5 passed (4 existing audio warnings only).
  - REFACTOR: removed duplicated exception-swallowing branches without changing explicit `mock_mode=True` paths; consumer GUI/TUI suite remains green.
- **Commands, exit status, environment and receipt paths:**
  - Current source verification used Python `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` (not the historical 3.12 receipt environment).
  - `PYTHONPATH=.:src python3 -m pytest tests/test_tui.py tests/test_gui.py -q` -> exit 0, `21 passed`, 4 pre-existing audio dependency warnings.
  - `python3 -m py_compile packages/tui/client.py packages/tui/workflow.py packages/gui/app.py` -> exit 0.
  - `git diff --check -- packages/tui/client.py tests/test_tui.py` -> exit 0.
  - Current diff scope: 43 tracked changed paths plus 65 untracked paths before this handoff update; the full candidate remains intentionally uncommitted and mixed with prior continuation work.
- **Research / Figma / external evidence:** unchanged. No remote Figma action, staging credential use, deployment, merge, release, or external mutation occurred.
- **Assurance status and limitations:** This is a focused D1 checkpoint, not a final-strict review and not acceptance of all D1. Auth headers/session expiry, retry/cancellation policy, V2 contract parity, GUI/TUI workflow mapping, and full current-candidate verification remain open. Historical A2 review budget remains exhausted and untouched.
- **Unresolved issues / exact external action needed:** No external action is needed for this checkpoint. Live auth/session behavior still needs a separate bounded D1 test-first task; managed Supabase staging still needs authorized credentials as already recorded under S1/V1.
- **Next smallest task:** Add explicit auth/session-expiry and generic error classification at the shared client boundary, with test-first coverage; then inventory/map GUI/TUI actions to the accepted V2 contracts before attempting R1 runtime/dependency work.

---

## Task 0 — Reconcile Receipts, Source Inventory & Establish Supported Python 3.12 Runtime
- **Status:** accepted
- **Workspace / branch / base / candidate:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
  - Git Common Directory: `/Users/porschecaa/lingualens/.git`
  - Staged Changes: 0 files (`git diff --cached --stat` empty)
  - Tracked Modified: 43 files
  - Untracked Files: 66 files
  - Total Candidate Records: 109 paths (`git status --porcelain=v1 --untracked-files=all`)
  - Full Candidate Inventory: `.local/verification/antigravity-d1/source_inventory.json` (SHA-256: `c4f0ef2d4f8f65ae267b99b7d666df0647c45395da0e9a58b7fc764e79176f39`)
- **A2 Frozen Hash Comparison:**
  - Frozen A2 Worktree (`/Users/porschecaa/lingualens/.worktrees/assessment-v2-segment-review`): 51/51 manifest files match `candidate-manifest.json` exactly (0 divergence, candidate ID `sha256:19f144e944e768982412cec31397b3e7bb62ac9241dc66a9a9f43fb646304ef3`).
  - Continuation Workspace: 36/51 manifest files match frozen A2 byte-for-byte; 15 paths modified by subsequent accepted additive slices (E1, B1, B2, B3, C1, C2, and initial D1 no-fallback patch). 0 manifest paths missing.
  - A2 Ledger Preservation: `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md` remains `UNIT_STATUS: parent-completed`, `REVIEW_STATUS: review-exhausted`, `REVIEW_CALLS_USED: 3`. No reviews reopened or renamed.
- **Supported Runtime Environment Selection:**
  - Selected Interpreter: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/.venv/bin/python`
  - Version: `Python 3.12.14 | packaged by Anaconda, Inc. | (main, Aug 27 2026, 14:38:15) [Clang 20.1.8 ]`
  - Compliance: Satisfies `pyproject.toml` (`requires-python = ">=3.11,<3.14"`).
  - Historical Receipt Reclassification: The prior `21 passed` receipt obtained under Python 3.14.2 is classified as historical, out-of-spec evidence. Supported runtime status is now anchored exclusively to Python 3.12.14.
- **Rerun of Focused Client Suite on Python 3.12:**
  - Command: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui.py tests/test_gui.py -v`
  - Exit Code: 0
  - Result: 21 passed in 1.30s (5 TUI tests, 16 GUI tests)
  - Verification Log: `.local/verification/antigravity-d1/focused_client_suite_py312.log` (SHA-256: `b51dd2ab864a2443aaa6a0fa3a19e7805415432f228ea4f37c43b0bf9c4c7259`)
- **Audit Findings & Corrections to Broad Prior Claims:**
  - Local Mock Mutation Gaps: While the previous patch removed silent `except Exception: pass` HTTP fallback for case/session/transcript reads/writes, multiple client methods never made HTTP requests and mutated `self._mock_data` directly regardless of `mock_mode=False`:
    1. `ingest_audio_file`: Ran local audio pipeline (or mock utterance fallback) and wrote directly to `self._mock_data["transcripts"]`, `self._mock_data["sessions"]`, and `self._mock_data["features"]`.
    2. `ingest_transcript_text`: Locally parsed text and directly wrote to `self._mock_data["transcripts"]` without contacting the backend.
    3. `update_utterance`: Modified `self._mock_data["transcripts"]` in-place with no live HTTP branch.
    4. `auto_refine_speakers`: Applied local diarization rule directly to `self._mock_data["transcripts"]`.
    5. `swap_speakers`: Swapped speakers directly in `self._mock_data["transcripts"]`.
  - GUI Direct `_mock_data` Access: `packages/gui/app.py` line 2883 accessed `self.client._mock_data.get("cases", [])` directly instead of calling client methods or local UI state.
  - TUI Direct `_mock_data` Access: `packages/tui/workflow.py` lines 309 and 338 iterated over `self.client._mock_data["reports"]` directly instead of using a client query method.
  - Delivery Conclusion Correction: The inherited claim of "100% prototype-ready" is inaccurate. Live workflows remain vulnerable to local mock mutation; D1, R1, and external U1/S1/V1 are incomplete.
- **Next smallest task:** Task 1 — Finish the D1 failure boundary (TDD implementation plan, loopback transport tests, parameterization of failure regression, local state immutability assertion, unsupported operation errors for live local-only methods, GUI/TUI error presentation).

---

## Task 1 — D1 Failure Boundary & Thin-Client State Immutability
- **Status:** accepted (Task 1 boundary closed and verified; live auth/session and V2 parity continue under Task 2/3)
- **Workspace / branch / base:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
- **Acceptance criteria and actual result:**
  - *Criteria:* Live mode (`mock_mode=False`) must NEVER fall back to mock data or mutate local mock state upon REST/HTTP failure; all 12 live operations plus 4 local-only operations must enforce failure boundaries; local-only methods (`ingest_audio_file`, `update_utterance`, `auto_refine_speakers`, `swap_speakers`) must explicitly raise `LinguaLensUnsupportedOperationError` in live mode rather than mutating `self._mock_data`; eliminate all direct GUI/TUI `_mock_data` accesses; error messages must be sanitized (never leak clinical payloads, child IDs, or auth tokens); GUI must present API errors cleanly; explicit mock mode (`mock_mode=True`) preserved for local demo/research.
  - *Actual Result:*
    1. Implemented structured error hierarchy in `packages/tui/client.py`: `LinguaLensApiError`, `LinguaLensAuthError`, `LinguaLensPermissionError`, `LinguaLensConflictError`, `LinguaLensRateLimitError`, `LinguaLensServerError`, `LinguaLensUnsupportedOperationError`.
    2. Hardened `_http_request` with classification of HTTP status codes (401 -> Auth, 403 -> Permission, 409 -> Conflict, 429 -> RateLimit, 5xx -> Server, other -> ApiError) and payload sanitization omitting query tokens, patient IDs, and payload bodies from exception messages.
    3. Added live-mode guards to `ingest_audio_file`, `update_utterance`, `auto_refine_speakers`, and `swap_speakers` to raise `LinguaLensUnsupportedOperationError` before any state mutation.
    4. Added `get_report(report_id)` and `get_session_report(session_id)` to `LinguaLensClient`.
    5. Eliminated direct `_mock_data` accesses: Updated `packages/tui/workflow.py` to use `client.get_session_report()`; updated `packages/gui/app.py` to check treeview item count instead of querying `client._mock_data["cases"]`.
    6. Added GUI failure presentation test `test_gui_failure_presentation_on_api_error` in `tests/test_gui.py`.
- **Changed files:**
  - `packages/tui/client.py` (modified: structured exceptions, status mapping, sanitization, live-mode guards, get_report/get_session_report)
  - `packages/tui/workflow.py` (modified: eliminated direct `_mock_data["reports"]` access)
  - `packages/gui/app.py` (modified: eliminated direct `_mock_data.get("cases")` access)
  - `tests/test_tui_transport.py` (new: 9 loopback transport tests covering 200, 401, 403, 409, 429, 500, invalid JSON, connection errors, sanitization)
  - `tests/test_tui.py` (modified: parameterized live failure suite covering 12 operations + 4 unsupported operations with deep-copy state immutability assertion)
  - `tests/test_gui.py` (modified: added GUI error presentation test)
  - `README.md` (modified: documented client failure boundary and error taxonomy)
  - `CHANGELOG.md` (modified: added client failure boundary hardening notes)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `TDD_REQUIRED: yes`.
  - RED Phase: Observed and saved failure logs to `.local/verification/antigravity-d1/red_d1_failure_boundary.log` (SHA-256: `b60848ab89b604e1c39539ec2fdb876ab160f97f46240331b22c55e81508ee8c`). Tests failed due to missing error classes, unhandled status codes, direct `_mock_data` mutations, and missing client report methods.
  - GREEN Phase: Minimal implementations added in `packages/tui/client.py`, `packages/tui/workflow.py`, and `packages/gui/app.py`.
  - REFACTOR Phase: Cleaned up error sanitization, unified docstrings, verified py_compile and git diff whitespace.
- **Commands, exit status, environment and receipt paths:**
  - Python Environment: `.venv/bin/python` (Python 3.12.14).
  - Loopback Transport & TUI Suite:
    - Command: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui.py tests/test_tui_transport.py -v`
    - Exit Code: 0 (29 passed in 4.26s)
  - GUI Suite:
    - Command: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_gui.py -v`
    - Exit Code: 0 (17 passed in 2.49s)
  - Combined Client Verification Log:
    - Path: `.local/verification/antigravity-d1/task1_client_suite_green.log`
    - SHA-256: `2259a50d7d92a564891d3be0ec05d7388ec5a13ec16a65deeccd97f72728fab8`
  - Backend Assessment V2 Regression Gate:
    - Command: `PYTHONPATH=.:apps/api .venv/bin/pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q`
    - Exit Code: 0 (432 passed, 11 deselected, 4 warnings in 13.51s)
    - Verification Log: `.local/verification/antigravity-d1/assessment_v2_py312_green.log`
    - SHA-256: `248b170263c71cc037e7154cef6c5c68e8ee10a08248ce7d4fb710fbfa32fb62`
  - Syntax Compilation:
    - Command: `.venv/bin/python -m py_compile packages/tui/client.py packages/tui/workflow.py packages/gui/app.py`
    - Exit Code: 0
  - Git Diff Check:
    - Command: `git diff --check -- packages/tui/client.py packages/tui/workflow.py packages/gui/app.py tests/test_tui.py tests/test_tui_transport.py tests/test_gui.py README.md CHANGELOG.md`
    - Exit Code: 0
- **Assurance status and limitations:**
  - Client live failure boundary and local state immutability are verified for all current operations.
  - Operations requiring future backend V2 endpoints (`ingest_audio_file`, `update_utterance`, `auto_refine_speakers`, `swap_speakers`) fail safely with `LinguaLensUnsupportedOperationError` rather than silently corrupting local state.
  - A2 ledger remains preserved (`parent-completed`, budget 3/3 exhausted).
- **Next smallest task:**
  - Complete Task 1 gap closure (WorkflowRunner crash recovery, list_sessions contract validation, traceback sanitization, GUI error modal handling) and proceed to Task 2 Auth & Session Lifecycle.

---

## Task 1 Gap Closure — Crash Recovery, Contract Validation, Traceback Sanitization & GUI Modals
- **Status:** accepted
- **Workspace / branch / base:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
  - Python Environment: `.venv/bin/python` (Python 3.12.14)
- **Acceptance criteria and actual result:**
  - *Criteria:*
    1. `WorkflowRunner.start()`: API errors (`LinguaLensApiError`) encountered during main loop execution must not crash the TUI out of the interactive loop without user notification and recovery prompt.
    2. `list_sessions()`: Contract validation required; an API response missing the required `"sessions"` list field must raise `LinguaLensApiError` rather than silently returning an empty list.
    3. Traceback & exception chaining sanitization: Sever exception causes using `raise ... from None` to ensure underlying `urllib.error.HTTPError` or `urllib.error.URLError` (which contain the full target URL, query strings, and auth parameters) do not leak via `__cause__` or `__context__` in unhandled tracebacks.
    4. GUI synchronous callbacks & async error paths: Ensure dialog modal actions (`_do_create` in case and session creation dialogs) handle API errors with `messagebox.showerror` without crashing or false success; batch audio ingestion tracks failure counts and alerts users rather than assuming 100% success.
  - *Actual Result:*
    1. Hardened `WorkflowRunner.start()` in `packages/tui/workflow.py` with try/except around menu item execution catching `LinguaLensApiError`, printing a sanitized error banner and prompting the user to continue.
    2. Added contract validation in `LinguaLensClient.list_sessions()` raising `LinguaLensApiError` when the `"sessions"` key is absent or not a list.
    3. Applied `raise ... from None` across all status mapping branches and URL error handlers in `packages/tui/client.py`. Verified in test `test_traceback_chaining_does_not_leak_target_url` that `__cause__` and `__context__` are None.
    4. Wrapped `_do_create` in `_show_new_case_modal` and `_show_new_session_modal` in `packages/gui/app.py` with try/except to show error dialog; updated `_batch_ingest_audio_files` to count failures and show warning if failures occurred.
- **Changed files:**
  - `packages/tui/client.py`
  - `packages/tui/workflow.py`
  - `packages/gui/app.py`
  - `tests/test_tui.py`
  - `tests/test_tui_transport.py`
  - `tests/test_gui.py`
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `TDD_REQUIRED: yes`.
  - RED Phase: 4 tests added demonstrating reachable failures:
    - `test_workflow_runner_handles_api_error_without_crashing_loop`
    - `test_list_sessions_missing_sessions_field_raises_api_error`
    - `test_traceback_chaining_does_not_leak_target_url`
    - `test_gui_modal_creation_error_handling`
    - Failure Receipt: `.local/verification/antigravity-d1/red_task1_gap_closure.log` (SHA-256: `f3acb6bb3387d40a891d347ee90abb958f7cd136c7cf4ce35af14ff438618e43`)
  - GREEN Phase: Minimal code additions in client, workflow, and GUI app.
  - Verification Receipt: `.local/verification/antigravity-d1/task1_gap_closure_green.log` (SHA-256: `6a2c61824fb934cadca73bb0ac5ac0d137f3d8f9369eb0ae5811d525ad48c559`, 51 passed in 4.09s).
- **Assurance status and limitations:**
  - All Task 1 gaps verified closed under Python 3.12.14.

---

## Task 2 — Auth and Session Lifecycle for Shared Transport
- **Status:** implemented (checkpoint-ready)
- **Workspace / branch / base / candidate:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
  - Python Environment: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/.venv/bin/python` (Python 3.12.14)
  - Implementation Plan: `docs/superpowers/plans/2026-09-12-d1-auth-session-implementation.md`
- **Acceptance criteria and actual result:**
  - *Criteria:*
    1. Explicit Session Representation: `ClientSession` dataclass holding `access_token`, `organization_id`, `token_id`, and `created_at`. Shared transport methods `set_session()`, `get_session()`, `clear_session()`.
    2. Origin Scoping & Redirect Credential Stripping: `Authorization: Bearer <token>` sent ONLY to configured `base_url` origin (scheme, hostname, port). Custom `_SafeRedirectHandler` strips `Authorization` headers on any redirect to a different origin/port (tested via dual loopback servers).
    3. HTTP 401 Session Invalidation: 401 response invalidates current session immediately, prevents token replay, and raises `LinguaLensAuthError`. Late 401 from an earlier request using a replaced/expired token does NOT invalidate a newly active session.
    4. HTTP 403 Permission Denial: Raises `LinguaLensPermissionError` without invalidating session or clearing credentials.
    5. HTTP 409 Conflict: Raises `LinguaLensConflictError` allowing client reconciliation without clearing session.
    6. HTTP 429 Rate Limit Handling: Parses `Retry-After` header safely (integer seconds or HTTP date string; handles missing/malformed values gracefully). Mutations (POST/PUT/PATCH/DELETE) are NEVER automatically retried.
    7. TUI / GUI Auth Error Presentation: Surfaces authentication failure with clear re-authentication guidance. GUI status bar updates to `"⚠️ Authentication Required: Session expired. Please sign in."` with informative dialog.
    8. Security Boundaries: Synthetic tokens used exclusively (`test-token-...`); zero tokens in logs, fixtures, or source; zero synthetic login endpoints or fake grant emulation created.
  - *Actual Result:*
    - Implemented `ClientSession` dataclass, `_SafeRedirectHandler`, `set_session`, `get_session`, `clear_session`, and origin-scoped bearer header injection in `packages/tui/client.py`.
    - Integrated token-version tracking (`token_used`) during request execution to prevent late-401 races from clearing newer sessions.
    - Updated `WorkflowRunner` in `packages/tui/workflow.py` to handle `LinguaLensAuthError` with specific re-auth guidance.
    - Updated `LinguaLensGUIApp` in `packages/gui/app.py` to handle `LinguaLensAuthError` in `_on_task_done` with dedicated status warning and dialog.
    - Added 7 loopback transport tests, 1 TUI test, and 1 GUI test in `tests/test_tui_transport.py`, `tests/test_tui.py`, and `tests/test_gui.py`.
- **Changed files:**
  - `packages/tui/client.py` (modified: added ClientSession, _SafeRedirectHandler, set_session, get_session, clear_session, 401/429 hardening)
  - `packages/tui/workflow.py` (modified: added LinguaLensAuthError catch with re-auth guidance in start())
  - `packages/gui/app.py` (modified: added LinguaLensAuthError detection and UI guidance in _on_task_done)
  - `tests/test_tui_transport.py` (modified: added 7 loopback auth/session lifecycle tests)
  - `tests/test_tui.py` (modified: added TUI auth failure workflow test)
  - `tests/test_gui.py` (modified: added GUI auth failure status and dialog test)
  - `docs/superpowers/plans/2026-09-12-d1-auth-session-implementation.md` (new)
  - `.local/verification/antigravity-d1/source_inventory.json` (updated)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `TDD_REQUIRED: yes`.
  - RED Phase: Observed 9 failures across transport, TUI, and GUI test suites.
    - Failure Receipt: `.local/verification/antigravity-d1/red_task2_auth_session.log`
    - SHA-256: `217f0151c036ff1161c2c996e80faa596e36dad19036558c98f17360fa82ba91`
  - GREEN Phase: Added session management, redirect handler, origin matching, late-401 protection, and UI handlers.
  - REFACTOR & Gap Closure Phase:
    - Resolved Tkinter modal grab and event loop lockup in batch worker (`after_idle` dispatch and idle event processing), allowing full GUI test suite to complete cleanly.
    - Implemented RFC HTTP-date parsing and delta-seconds in `_parse_retry_after()`, normalizing past dates/negative values to 0.0 and ignoring NaN/Inf.
    - Added monotonic `generation` to `ClientSession`, `_session_lock` in `LinguaLensClient`, and compare-and-clear logic in `_handle_auth_failure` to prevent late-401 races from clearing newer sessions (including same-token reconnects).
    - Hardened `_SafeRedirectHandler` to reject mutation (POST/PUT/PATCH/DELETE) redirects and case-insensitively strip both `Authorization` and `X-Organization-ID` on cross-origin redirects.
    - Masked sensitive tokens in `ClientSession.__repr__` and `__str__`.
    - Hardened GUI on auth error to clear active clinical state (`active_case_id`, `active_session_id`, `active_transcript`) and clear treeviews.
- **Commands, exit status, environment and receipt paths:**
  - Loopback Transport & TUI & GUI Client Suites (Completed Receipt):
    - Command: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_tui.py tests/test_tui_transport.py tests/test_gui.py -v`
    - Exit Code: 0 (67 passed in 13.41s)
    - Receipt Path: `.local/verification/antigravity-d1/task2_client_suite_green_completed.log`
    - SHA-256: `f86699267ee42251cdbcdbc2817d892df30fc9cdc0f5c20d696b9f3b6b6083e5`
  - Gap Closure RED Phase Receipt:
    - Receipt Path: `.local/verification/antigravity-d1/red_task2_closing_gaps.log`
    - SHA-256: `6d66ca1f890e7bdd8e7f9bc69f8c32ec4b7a86ebfcbb42d2b6593cf336758e1f`
  - Backend Assessment V2 Regression Gate:
    - Command: `PYTHONPATH=.:apps/api .venv/bin/pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q`
    - Exit Code: 0 (432 passed, 11 deselected, 4 warnings in 13.38s)
    - Receipt Path: `.local/verification/antigravity-d1/backend_v2_regression.log`
    - SHA-256: `5736275773bcc1b6290ccb43356a0262753cbc4ae90715c37b0c6b7a255b2f59`
  - Working Tree Inventory (Completed Task 2):
    - Path: `.local/verification/antigravity-d1/source_inventory_task2_complete.json`
    - SHA-256: `279e92b463486358a95593df68a2db204d1caa8ba15c05d8e724ec90aae73b0d`
    - File Count: 115 records (43 modified, 72 untracked) parsed via `git status --porcelain=v1 -z --untracked-files=all` with zero directory placeholders.
- **Assurance status and limitations:**
  - Status is designated `implemented (checkpoint-ready)`.
  - Token injection and session lifecycle verified on loopback transport with zero mock mutation.
  - Traceback chaining semantics verified: `raise ... from None` sets `__suppress_context__ = True` and `__cause__ = None`, preventing transport URL and token leaks.
  - Zero mock fallback and zero credential leakage verified on cross-origin redirects.
  - A2 review ledger remains intact (`parent-completed`, review budget 3/3 exhausted).
  - External Supabase staging credentials for full multi-tenant integration remain pending.
- **Next smallest task:**
  - Reconcile Stage 1 V2 parity contracts and integrate canonical FastAPI route tests.

---

## Slice: V2-1 — Assessment V2 Parity: Stage 1 (Child, Consent & Assessment Context)
- **Status:** implemented (checkpoint-ready)
- **Workspace / branch / base / candidate:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
  - Base / HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
  - Python Environment: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/.venv/bin/python` (Python 3.12.14)
  - Parity Specification: `docs/readiness/GUI_TUI_V2_PARITY.md`
- **Acceptance criteria and actual result:**
  - *Criteria:*
    1. Child Management: Implement `create_child()`, `get_child()`, and `list_children()` in `LinguaLensClient` communicating via canonical `POST /api/v2/children`, `GET /api/v2/children/{id}`, and `GET /api/v2/children`.
    2. Consent Tracking & Semantics: Implement `record_consent()`, `list_consents()`, and `get_active_consent()`. Reconcile active consent as derived client behavior: order consent history by latest version; if latest is withdrawn or absent, active consent is None.
    3. Consent Versioning per Purpose & Child Isolation: Backend `add_consent` increments version per `(organization_id, child_id, purpose)` via `max(version)+1`. Python mock and synthetic integration fixtures must NOT use total count of child consents. Enforce sequence: clinical active (v1) -> research active (v1) -> clinical withdrawn (v2) -> clinical active (v3), active consent derivation, and child isolation (child 2 starts at v1).
    4. Assessment Context: Implement `create_assessment()`, `get_assessment()`, and `list_assessments()`. Realign `get_assessment(assessment_id)` to invoke canonical detail route `GET /api/v2/assessments/{assessment_id}` with 404 `assessment_not_found` error semantics in both live and mock modes.
    5. Active Consent Gate: Enforce active clinical consent before assessment creation in both mock mode and live backend (HTTP 409 `active_consent_required` -> `LinguaLensConflictError`).
    6. Canonical Route Integration: Test `LinguaLensClient` directly against real FastAPI routes, schemas, and exception handlers (`app.main`) via `TestClient` bridge (in addition to loopback mock tests).
    7. State Immutability: Ensure live API failures (401, 403, 404, 409, 422) never fall back to or mutate local mock collections.
    8. Specification Audit: Re-audit `docs/readiness/GUI_TUI_V2_PARITY.md` across all 7 stages against live backend routes (48 endpoints), web client, and desktop surfaces.
  - *Actual Result:*
    - Realigned `get_assessment(assessment_id)` in `packages/tui/client.py` to use canonical detail route `GET /api/v2/assessments/{assessment_id}` and raise `LinguaLensApiError` on 404.
    - Updated `get_active_consent` to respect repository ordering semantics (latest version checked; if withdrawn, returns None).
    - Fixed consent versioning in `packages/tui/client.py` mock mode and `tests/test_tui_canonical_integration.py`: `version_num` is calculated strictly per purpose (`max(v)+1 where purpose == ...`), and `list_consents` returns records ordered by version descending.
    - Created canonical FastAPI integration suite `tests/test_tui_canonical_integration.py` (8 tests covering child lifecycle, consent withdrawal semantics, assessment detail route, 422 Pydantic validation rejection, 409 active consent gating, 401/403 status propagation, v1/v2 URL resolution, and per-purpose consent versioning + child isolation).
    - Added canonical SQLite repository + `AssessmentService` test `test_consent_versioning_per_purpose_sequence_and_child_isolation` in `apps/api/tests/assessment_v2/test_repository.py`.
    - Added mock regression test `test_mock_consent_versioning_per_purpose_and_child_isolation` in `tests/test_tui.py`.
    - Added transport detail test `test_transport_v2_get_assessment_detail` in `tests/test_tui_transport.py`.
    - Added `get_assessment` to `LIVE_OPERATIONS` and expanded mock flow in `tests/test_tui.py`.
    - Completely rewrote `docs/readiness/GUI_TUI_V2_PARITY.md` with source-verified routes, schemas, and classifications.
- **Changed files:**
  - `packages/tui/client.py` (modified: realigned `get_assessment(assessment_id)`, fixed `get_active_consent` version ordering and mock per-purpose version increment)
  - `tests/test_tui_canonical_integration.py` (new: 8 canonical FastAPI integration tests)
  - `tests/test_tui_transport.py` (modified: added detail route transport test)
  - `tests/test_tui.py` (modified: added `get_assessment` to `LIVE_OPERATIONS`, tested mock detail + consent withdrawal, added consent versioning regression test)
  - `apps/api/tests/assessment_v2/test_repository.py` (modified: added canonical SQLite fixture test for per-purpose consent versioning and child isolation)
  - `docs/readiness/GUI_TUI_V2_PARITY.md` (rewritten: source-audited parity matrix across all 7 stages)
  - `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` (modified: this file)
- **TDD_REQUIRED and RED/GREEN/REFACTOR evidence:**
  - `TDD_REQUIRED: yes`.
  - RED Phase 1 (Stage 1 Initial Contracts):
    - Receipt Path: `.local/verification/antigravity-d1/red_stage1_contract_closure.log`
    - SHA-256: `5e453d634c0caf3907d7604d3fa8eafa7893486edd0176d15e808219bfc42313`
    - Actual Exit Code: 1 (Observed failures on `get_assessment` signature mismatch and consent withdrawal semantics)
  - RED Phase 2 (Consent Versioning Mismatch):
    - Receipt Path: `.local/verification/antigravity-d1/red_stage1_consent_version_mismatch.log`
    - SHA-256: `b1b1930d226deb1b2b5bc7aec70e90d7d6b4fa306fa682de6a5583d079a0863b`
    - Actual Exit Code: 1 (Observed `assert 2 == 1` failure when adding research_reuse consent after clinical_assessment)
  - GREEN Phase: Updated `packages/tui/client.py` and `tests/test_tui_canonical_integration.py`; all 90 client tests pass cleanly.
    - Receipt Path: `.local/verification/antigravity-d1/task3_stage1_consent_closure_green.log`
    - SHA-256: `3d32b4b87bd68539cea0efb6d55a03d6ea8922332f196f3dbd92989e80e62ec7`
    - Actual Exit Code: 0 (90 passed, 4 warnings in 17.77s)
  - Backend Assessment V2 Regression Gate:
    - Command: `PYTHONPATH=.:apps/api .venv/bin/pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q`
    - Receipt Path: `.local/verification/antigravity-d1/backend_v2_regression_consent_closure.log`
    - SHA-256: `344dbe6976477801ab3b8267b2368f9c5cb79acf627dcdb690cc083c3fe67e14`
    - Actual Exit Code: 0 (433 passed, 11 deselected, 4 warnings in 13.92s)
  - REFACTOR Phase: Verified zero whitespace errors in modified files via `git diff --check`.
- **Working Tree Inventory & Drift Classification:**
  - Candidate Inventory Path: `.local/verification/antigravity-d1/source_inventory_stage1_contract_closure.json`
  - SHA-256: `a10cb5bdd8f2dd3514497f15353d793618f24e7d2ee7e43df30ecf5bee2b2d3a`
  - File Count: 117 records (44 modified, 73 untracked) parsed via `git status --porcelain=v1 -z --untracked-files=all`.
  - Frozen Behavior Identity SHA-256: `b06b5b20445aa75dcc39432fdf8f73cfc85bfd24a3839ab816421c4394e083d5` across all behavior code/test files.
  - Drift Classification:
    - `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` experienced **metadata drift** because the document records the paths and hashes of verification receipts generated during the task.
    - Behavior Identity remains strictly frozen across code and test surfaces, isolating behavioral integrity from mutable progress recording.
- **Assurance Status & Blockers Breakdown (Reconciled):**
  - **Overall Status:** `implemented (checkpoint-ready)`.
  - **Correction & Scope Reconciliation Note (A2 Ledger vs D1 Scope):**
    - *Prior Inaccurate Claim:* Item 3 previously recorded D1's Independent Review Gate as a "terminal limitation" due to the review budget exhaustion of unit A2 (`lingualens/assessment-v2/segment-review`).
    - *Ledger Evidence & Finding:* Inspection of `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md` reveals that A2's objective was strictly limited to Assessment V2 Segment Review (Tasks 0–8), Alembic migrations `0008` & `0009`, and the web transcript review workspace (`assessment-segment-review-workspace.tsx`). Crucially, the A2 ledger line 16 explicitly defined its acceptance boundary: *"no Docker requirement and no GUI/TUI business-rule change"*.
    - *Resolution & Rules Adherence:*
      1. Unit A2 remains permanently terminal (`parent-completed`, `review-exhausted` 3/3 calls used, `final-strict-not-achieved`). A2 is NOT reopened, reset, renamed, or split.
      2. Conflating A2's exhausted budget with D1 was an unsubstantiated leap. D1 is a distinct, qualifying subsequent workstream covering thin-client failure boundaries, transport session lifecycle, and desktop client parity.
      3. Completing D1 cannot and does not claim to confer "final-strict" status upon A2 or the cumulative product.
      4. Durable Solweaver Unit Search: Verified that NO durable D1 assurance unit currently exists in `.git/solweaver/`. D1 operates as an implementation workstream that must establish its own assurance boundary.
  - **Scope Comparison Matrix:**
    | Dimension | A2 Frozen Scope | D1 Workstream Scope | Shared Dependencies |
    | :--- | :--- | :--- | :--- |
    | **Primary Code Surfaces** | `apps/api/app/assessment_v2/reviewed_transcript_worker.py`, migrations `0008`–`0009`, `apps/lingualens-app/.../assessment-segment-review-workspace.tsx` | `packages/tui/client.py`, `packages/tui/workflow.py`, `packages/gui/app.py`, `tests/test_tui*.py`, `tests/test_gui.py` | `apps/api/app/assessment_v2/routes.py`, `schemas.py`, domain models, `repositories.py` |
    | **Explicit Boundary** | *"no GUI/TUI business-rule change"* | Desktop thin-client parity, zero mock fallback, session lifecycle | Assessment V2 REST contracts and data schemas |
    | **Assurance Ledger** | `.git/solweaver/lingualens-assessment-v2-segment-review/ledger.md` (terminal, 3/3 calls) | None currently registered in `.git/solweaver/` | Core verification gates in `scripts/check_project.sh` |
    | **Current Status** | `parent-completed` (`final-strict-not-achieved`) | In-progress (Stage 1 consumer integration pending) | Passed (433 backend regression tests green) |
  - **Assurance Boundary & Verification Classification:**
    1. *Local Implementation Evidence:*
       - **Local Transport Security Suite:** **PASSED & VERIFIED** (`task2_client_suite_green_completed.log`, SHA-256: `f8669926...`). Loopback tests prove Origin-scoped Bearer injection, cross-origin redirect credential stripping, 401 session invalidation, late-401 race protection, 403 preservation, 429 Retry-After parsing, and mutation non-replay.
       - **Client Live Failure Boundary:** **PASSED & VERIFIED** (`task1_client_suite_green.log`). Proves zero mock fallback and local state immutability across all live operations.
       - **Canonical Route & Schema Integration:** **PASSED & VERIFIED** (`task3_stage1_consent_closure_green.log`, SHA-256: `3d32b4b8...`). Proves child, consent, and assessment schemas via FastAPI `TestClient`.
         - *Scope Caveat:* FastAPI `TestClient` tests with service overrides prove route/schema contract compliance and error mapping; they do NOT prove live Supabase JWT JWKS validation or PostgreSQL multi-tenant RLS.
       - **Domain Business Rules & Persistence:** **PASSED & VERIFIED** (`apps/api/tests/assessment_v2/test_repository.py`). Proves `max(version)+1` consent versioning per purpose and child isolation.
         - *Scope Caveat:* SQLite repository tests prove domain models, SQL queries, and schema constraints; they do NOT prove PostgreSQL multi-tenant concurrent lease locks or RLS row isolation.
    2. *Independent-Review Readiness:*
       - D1 implementation is in-progress (Desktop Stage 1 consumer integration pending).
       - When D1 implementation completes, D1 will be eligible for its own independent review under repository review rules as a distinct unit.
       - Independent review of D1 evaluates D1's own acceptance criteria (thin-client state immutability, transport lifecycle, desktop V2 parity); it does NOT reopen A2 or alter A2's terminal record.
    3. *External Managed Staging Gate (Task 5 / S1):*
       - **BLOCKED PENDING AUTHORIZATION & CREDENTIALS**. Per `docs/staging/STAGING_RUNBOOK.md`, verifying live Supabase JWKS token validation, multi-tenant RLS enforcement, and presigned private URLs requires an authorized staging environment and live credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`).
       - Per continuation plan line 102, missing external staging credentials blocks dependent external staging execution ONLY. It does NOT block local consumer implementation planning or local desktop integration.
    4. *Consumer Integration Status:*
       - **Subtask A (Child Selection & Typed Context — Lifecycle, Dispatch & Error Containment Closure):** **COMPLETED & VERIFIED (CHECKPOINT-READY)**.
           - GUI Lifecycle:
             - Converted `_set_active_child`, `_refresh_children`, and `_submit_create_child` to background worker threads posting thread-safe callbacks to `_async_queue` on the Tkinter main thread.
             - Bound completions to session generations (`_current_session_generation`) and request IDs (`_current_child_request_id`), ensuring stale late responses and racing child selections never overwrite newer selections.
             - Fixed `_handle_permission_error` to accept `request_id` and `session_generation`; stale 403 callbacks are discarded and active child context is strictly preserved without wiping.
             - Implemented monotonic `refresh_id` generation on `_refresh_children` to discard out-of-order refresh completions. Pre-clears `tree_children` before repopulating to prevent duplicate iid and TclError.
             - Added modal submission debouncing guard (`win._is_submitting`) to prevent duplicate POST requests while in flight.
             - Modal creation completion checks dialog token (`dlg_token`), verifies window existence (`win.winfo_exists()`), and verifies `child_selection_generation == self._child_selection_generation` before auto-activating over newer selections. Closed/cancelled dialogs discard both success and error presentation.
             - No auto-retry on POST mutation failure; cancel does not purport to roll back server mutations.
           - TUI Direct V2 Routing & Error Containment:
             - Top-level `_entry_menu()` offers direct entry to V2 Child Directory (`[C]`), Legacy Cases (`[1]`), or Quit (`[Q]`) before invoking legacy `list_cases`.
             - Direct selection of V2 never invokes legacy API (`list_cases.assert_not_called()`).
             - Unified main error boundary: HTTP 401 invalidates session and wipes both V2 and legacy clinical contexts; HTTP 403 presents permission denial preserving credentials without logout; transport/API failure loop allows retry, back, or quit without unhandled crashes.
           - Test-Order Flakiness Root Cause Investigation & Resolution:
             - Disproved claim that execution sequence alone was a fix; isolated two concrete root causes:
               1. Lazy `parse_cha_text` import inside worker thread during background AnyIO/GC cycles triggered Python 3.12/macOS `Fatal Python error: Aborted - Garbage-collecting`. Resolved by importing at module top-level in `packages/tui/client.py`.
               2. FastAPI `TestClient(app)` leaked `anyio` background portal threads across tests. Resolved by wrapping in `with TestClient(app) as test_client:`.
               3. Added main-thread `gc.collect()` in GUI teardown fixture to reclaim dead Tkinter C pointers before secondary-thread multi-process/thread runs.
             - Verified bidirectional stability: tests pass 100% cleanly in both orders (`GUI -> canonical integration` AND `canonical integration -> GUI`).
           - Verification Evidence:
             - Combined Client Suite: **124/124 PASSED** in 22.46s (exit code: 0, recorded in `.local/verification/antigravity-d1/task3_subtask_a_final_closure_green.log`, SHA-256: `27273174f8d9ebe69609cd5306fb4c86414cb0baba60023de58c8775c30c057d`).
       - **Subtask B (Consent Status Display & Explicit Recording Interaction):** **COMPLETED & VERIFIED (CHECKPOINT-READY)**.
         - Canonical Schema Adherence:
           - Uses canonical endpoint `POST /api/v2/children/{child_id}/consents` with body fields `purpose`, `scope_version`, and `status` only (`child_id` in path; no extraneous or mock-only fields).
           - Does NOT create assessment endpoints or invoke assessment creation paths (strictly deferred to Subtask C).
         - Consent Status Resolution:
           - Distinguishes 6 distinct observable states: `not-loaded`, `loading`, `active`, `withdrawn`, `no-record`, `error`.
           - Uses `list_consents(child_id)` and canonical latest-version-per-purpose semantics (`purpose == "clinical_assessment"`, `max(version)`). Proves that `withdrawn` is distinctly separated from `no-record` (unlike `get_active_consent` alone, which returns `None` for both).
           - API failure never displays as "no consent" or "no record"; renders explicit error state.
           - Reflects status from latest authoritative fetch with timestamp and explicit refresh button/action (`btn_refresh_consent` / `[R]`); never misleadingly claims live-streamed real-time status.
         - Explicit Recording Interaction:
           - GUI: `_show_record_consent_dialog` modal dialog offering Grant Active Consent vs Withdraw Consent.
           - TUI: `_record_consent_wizard` offering options `[1] Active`, `[2] Withdrawn`, `[C] Cancel`.
           - Mandatory explicit confirmation prompt displays active child code, purpose, scope version, and action before mutation dispatch. Never auto-grants consent on child selection.
           - Clear clinical wording: explicitly clarifies that clinician is recording consent received from or withdrawn by the parent/guardian; does not constitute direct parental consent.
           - Debouncing flag (`win._is_submitting`) prevents duplicate in-flight POST dispatches.
           - On success, authoritative history is re-fetched. No optimistic UI mutation before server confirmation.
          - Lifecycle, Error Containment & Concurrency (Mutation Lifecycle Closure):
            - Dialog Opening Target Binding:
              - Bound immutable `target_child_id`, `target_child_code`, `session_generation`, `child_selection_generation`, and `dialog_token` at dialog open (`_show_record_consent_dialog`).
              - Target context re-checked before confirmation dialog AND before worker thread dispatch. If active child, session generation, or selection generation drifted, submission is immediately aborted with zero POST calls.
              - Purpose strictly fixed to non-editable `clinical_assessment` (no arbitrary purpose tampering).
              - Scope Version validated client-side against schema (`1 <= len(scope) <= 64`); empty/whitespace rejected with validation error without sending POST (no fallback to default when user empties field).
            - Asynchronous Post-Mutation Refresh:
              - Moved post-mutation `list_consents` network calls completely off the UI thread into background worker thread (`_refresh_consent_after_mutation`).
              - Tri-state lifecycle separation:
                1. Mutation succeeded / refresh pending: badge updates immediately to transitional loading state so stale state is never mistaken for authoritative state.
                2. Mutation succeeded / refreshed: badge updates to authoritative versioned status and success dialog is displayed.
                3. Mutation succeeded / refresh failed: badge displays error state, and user is warned that consent was recorded on server but history refresh failed, avoiding false claims of mutation failure.
            - Stale Completion, Session Invalidation & Request Busy Scoping:
              - Closed/cancelled/token-mismatched dialogs discard completion presentation and do not alter clinical context.
              - `_set_busy_state` scoped with `request_id`: older completed/cancelled consent mutations never clear the busy state of a newer in-flight request.
              - 401 Session Invalidation handled as a session-level concern: current-session 401 is always handled (wiping clinical context and clearing credentials) even if dialog was closed, while stale-session 401 from old session generations is discarded without affecting the new session.
              - Both GUI and TUI: post-mutation refresh and 409 conflict refresh never swallow 401 (bubbles to main error boundary); 403 displays permission denial without clearing session credentials.
          - Verification Evidence:
            - Combined Client Suite: **148/148 PASSED** in 23.79s (exit code: 0, recorded in `.local/verification/antigravity-d1/subtask_b_mutation_lifecycle_green.log`, SHA-256: `889d6fc3945090990db97c22e6dfaf55498247dd91e8819fcb415fd1f25163fc`).
            - GUI suite (61/61 passed), TUI suite (50/50 passed), Canonical Integration suite (8/8 passed), Transport suite (29/29 passed).
        - **Subtask C (Assessment Creation & Safe Desktop Context Transition):** **CANCELLATION & ASSESSMENT-SELECTION CLOSURE COMPLETE (CHECKPOINT-READY)**.
          - Canonical Assessment Contract & Purpose Parity:
            - Replaced unsupported UI choices (`progress`, `discharge`) with backend-authoritative enum values (`AssessmentPurpose`):
              1. `initial`
              2. `developmental_follow_up`
              3. `post_intervention_follow_up`
              4. `additional_evidence`
            - Client-side validation: invalid choices or unsupported purpose strings are rejected with validation errors and zero POST (no silent defaulting to `initial`).
            - Direct schema validation test (`test_assessment_purposes_canonical_schema_parity`): proves all 4 UI purposes validate against canonical `AssessmentCreateRequest`, while `progress` and `discharge` are strictly rejected by `pydantic.ValidationError`.
          - Typed Consent Preflight & Fresh Async Read:
            - Eliminated UI badge text parsing as source of truth. `_is_consent_active()` evaluates typed `_current_consent_status == "active"` and `active_consent["status"] == "active"`.
            - Asynchronous preflight fetch (`list_consents`) runs in worker thread prior to mutation POST.
            - If fresh read reveals consent is withdrawn, absent (`no-record`), or error: creation aborts with informative error dialog and zero POST.
            - Context drift and dialog lifetime re-checked after preflight before dispatching `create_assessment` mutation.
            - Backend remains authoritative: on server 409 conflict, active assessment context is never activated, consent history is re-fetched asynchronously, and zero auto-retry POST occurs.
          - Pre-Dispatch Cancellation & Dialog Lifetime Management:
            - Bound thread-safe cancellation event (`win._cancel_event`) and dialog token (`win._dlg_token`) to request lifetime.
            - Background worker thread checks cancellation state and token validity without calling Tkinter UI methods off-thread.
            - Cancellation before mutation dispatch (window close, cancel button, dialog replacement) immediately aborts worker with **zero POST**.
            - Cancellation after mutation dispatch discards stale completion and prevents UI context activation; does NOT falsely claim server rollback or un-creation.
            - Every exit path (cancellation, context drift, error) reliably releases the busy state belonging to that specific `request_id` without clearing newer in-flight requests.
          - Same-Child Assessment Selection Race & Latest Identity:
            - Implemented monotonic `_assessment_selection_generation` and unique request identity across both cache-hit and cache-miss paths.
            - Selecting a new assessment invalidates prior in-flight detail fetches; out-of-order slow responses never overwrite newer selections.
            - Cached records require full canonical fields (`id`, `child_id`, `purpose`, `state`); partial records trigger canonical `get_assessment`.
            - Detail responses must match requested `id` and active `child_id` before context activation; mismatched IDs/children reject activation.
            - Detail load errors or child switches flush active assessment context, preventing old assessments from appearing as successes of new selections.
          - Reachable GUI & TUI Workflows:
            - GUI: Context bar `➕ New Assessment` button (`self.btn_create_assessment`) and Tab 1 `➕ Create Assessment (V2)` button open `_show_create_assessment_dialog()` modal.
            - GUI Assessments Directory Treeview (`self.tree_assessments`) displays active child's assessment records with columns `Assessment ID`, `Child ID`, `Purpose`, `State`, `Clinician`, `Ver`.
            - TUI: `_children_menu()` displays `Active Assessment ID` and offers option `[A] Create Assessment (V2)`. `_create_assessment_wizard()` prompts for canonical purpose [1-4] and optional clinician ID with full confirmation summary.
          - TDD Verification Evidence & Environment Reconciliation:
            - *Environment Reconciliation Note:* The earlier RED receipt `.local/verification/antigravity-d1/red_subtask_c_preflight_and_canonical_contract.log` was executed with system Python (`Python 3.13.12 / pytest 9.0.3`) whereas the subsequent GREEN Py312 receipt was executed with virtualenv Python (`.venv/bin/python`, `Python 3.12.14 / pytest 9.1.1`). Historical records are preserved authentically; earlier receipts establish behavioral failure and parity across these respective environments.
            - *Current Subtask C Gap Closure (Cancellation & Selection):* All commands executed strictly via `.venv/bin/python -m pytest` (`Python 3.12.14 / pytest 9.1.1`):
              - RED Receipt: `.local/verification/antigravity-d1/red_subtask_c_cancellation_and_selection.log` (exit code: 1, 6 failed, 3 passed, 85 deselected in 1.37s, SHA-256: `d0121e0886458d2dd98bac3fdbedbca4997abea9b0aedb482d3b4cecc6004582`).
              - GREEN Combined Client Suite: **189/189 PASSED** in 28.31s (exit code: 0, recorded in `.local/verification/antigravity-d1/subtask_c_cancellation_and_selection_green.log`, SHA-256: `3af059fd082c5423daaa0f7409ad8f99769a29a2c28f1d5ebfc7c5f5360a7bfc`).
              - GUI suite (94/94 passed), TUI suite (58/58 passed), Canonical Integration suite (8/8 passed), Transport suite (29/29 passed).
              - Backend Assessment V2 Regression Suite: **433/433 PASSED**, 11 deselected in 13.23s (exit code: 0, recorded in `.local/verification/antigravity-d1/backend_v2_regression_subtask_c_closure.log`, SHA-256: `c0d3dea776e8b22a92ea81f354fd9a90ba8e645cd1957479c140dd5cc8f6efba`).
              - Scoped Source Inventory (8 files): `.local/verification/antigravity-d1/source_inventory_subtask_c_cancellation_and_selection.json` (SHA-256: `f4e9aa08596f938e0c5804a7e1530f7310f981eacf6b0e88814d95d1dc8c92d8`).
              - *Scope Limitation:* The 8-file inventory is a scoped snapshot of Subtask C code & tests only; it is NOT the cumulative D1 manifest and does NOT constitute final-strict readiness.
- **Next Smallest Task:**
  - Prepare cumulative D1 Stage 1 verification / assurance readiness according to the durable boundary (stopping before Stage 2 audio/upload).

## D1 Call 1 Finding B4 — TUI Legacy Case Contract Closure (Focused Only)

- **Scope/status:** `parent-fixed / focused-verified`; this is not `reviewer-accepted` and does not close any other Call 1 finding.
- **Violated contract:** the legacy TUI must consume the active `/api/v1/cases` contract without changing backend schemas: `POST /cases` accepts `ChildCaseCreate` fields `child_code`, `age_months`, `language`, and `notes`; case responses identify the record with `case_id`. V2 child/assessment IDs remain separate from legacy case/session IDs.
- **Observed RED/reproducer:** the pre-fix TUI read `cases[idx]["id"]` and `new_case["id"]`, while the canonical response uses `case_id`; the wizard passed an integer age through the `birth_year_month` client shape; the client emitted `child_id`, `birth_year_month`, `primary_language`, and `clinical_notes`; invalid `2022-13` mutated local mock state; and a create API error escaped before an explicit no-success state. Receipt: `.local/verification/antigravity-d1/b4_tdd_red_20260913.log` (SHA-256 `0c8a339eeb77166f35a86eb526ddb6ff46d703f62fb684db2d100f24fc70c062`).
- **Files changed for B4:** `packages/tui/workflow.py`, `packages/tui/client.py`, `packages/tui/ui.py`, `tests/test_tui_legacy_b4_contract.py` (new), and canonical-call updates in `tests/test_tui_transport.py`.
- **Focused GREEN:** 93/93 passed using the continuation `.venv/bin/python`: 6 B4 nodes, 58 TUI nodes, and 29 transport nodes. The B4 suite includes a real loopback `POST /cases`, validation through `apps/api/app/schemas/clinical.py::ChildCaseCreate`, canonical selection/creation transition, fail-closed invalid birth month, no fabricated API failure context, and canonical table rendering. Receipt: `.local/verification/antigravity-d1/b4_tdd_green_20260913.log` (SHA-256 `1c81d8170040786ce1edb4079237101bf69a2ee08c886ddc22593674c0b8cbff`).
- **Implementation boundary:** canonical `create_case` sends only the backend fields above. The retired birth-month form is an explicit offline compatibility path that validates `YYYY-MM` and never guesses an age or sends that shape to live `/cases`; live callers receive a fail-closed unsupported-operation error. No `id`/`case_id` fallback was added. The TUI sets `active_case_id` only from `response["case_id"]` and enters the legacy sessions route only after a confirmed create.
- **Remaining limitations:** live `list_sessions` response reconciliation remains the separate B3 finding; GUI/demo callers that still provide birth-month input are not migrated in this B4 slice and are compatibility-only offline. Call 1 runtime binding (`agent_path`/cwd mismatch) remains unresolved. B1–B3 and B5–B6, plus A1–A4, remain open.
- **Candidate/history note:** B4 changed the worktree candidate. The frozen Call 1 candidate identity and all prior Call 1 proof/green receipts remain preserved historical evidence and are not current-candidate acceptance. No full re-review readiness, refreeze, reservation, or Call 2 dispatch was performed.
- **Next smallest task:** reconcile original finding B3's legacy session detail/list contract against the actual API route/schema, without reserving or spawning Call 2.

## D1 Call 1 Finding B3a — Legacy Session List/Detail/Create Contract Reconciliation (Focused Only)

- **Scope/status:** `parent-fixed / focused-verified`; this is not `reviewer-accepted` and does not close Finding B3 as a whole (GUI live startup/refresh error boundary B3b remains OPEN).
- **Violated contract:** The legacy client attempted to read sessions by calling `GET /cases/{case_id}` and asserting an embedded `"sessions"` key in the response dictionary. The canonical backend `ChildCase` schema has no `sessions` attribute. Real backend architecture enumerates sessions for a case via `GET /cases/{case_id}/timeline` (returning `list[TimelineEvent]` where `target_id` is the `session_id`), resolves session details via `GET /sessions/{session_id}` (returning `TherapySession`), and creates sessions via `POST /cases/{case_id}/sessions` (accepting `TherapySessionCreate` with `session_date`, `session_type="therapy_session"`, and `notes`). Furthermore, `get_session()` (auth session token) was distinct from clinical session detail.
- **Observed RED/reproducer:** 4/8 tests failed on pre-fix client against synthetic loopback server enforcing canonical FastAPI schemas (`TimelineEvent`, `TherapySession`, `TherapySessionCreate`). The client attempted `GET /cases/{case_id}` instead of `/cases/{case_id}/timeline`, received 404, failed to parse timeline list vs dict, and raised unexpected 404 on valid empty cases.
  - Receipt: `.local/verification/antigravity-d1/b3a_tdd_red_20260913.log` (SHA-256 `8221bb85c968c81f1f230592c37656e9e3ea3556dfb5bccf37577d115a48fdd6`, exit code: 1, 4 failed, 4 passed in 3.04s, `.venv/bin/python` / Python 3.12.14 / pytest 9.1.1).
- **Files changed for B3a:**
  - `packages/tui/client.py`: Added canonical `get_session_detail(session_id)` querying `GET /sessions/{session_id}`; refactored `list_sessions(case_id)` to query `GET /cases/{case_id}/timeline`, validate list response, resolve each `target_id` via `get_session_detail()`, and assign `session_number`; updated `create_session()` payload to supply `session_type="therapy_session"`; updated `get_session_transcript()` and `get_session_report()` to query session detail first and handle missing IDs / 404 cleanly.
  - `tests/test_tui_transport.py`: Updated `test_list_sessions_raises_api_error_on_malformed_timeline_response` to test timeline list validation.
  - `tests/test_tui_legacy_b3a_contract.py` (new): 8 contract tests covering timeline resolution, valid empty list, malformed responses, fail-closed HTTP errors (401/403/404/500), schema-compliant session creation, TUI session selection, create session wizard, and direct V2 entry isolation.
- **Focused GREEN:**
  - B3a suite: 8/8 passed in 2.91s. Receipt: `.local/verification/antigravity-d1/b3a_tdd_green_20260913.log` (SHA-256 `a364379b3817c291925cfdcd88632f75eef0b08adccf0ddb69cf6f4d723799bf`).
  - Combined focused regression: `tests/test_tui_legacy_b3a_contract.py`, `tests/test_tui_legacy_b4_contract.py`, `tests/test_tui.py`, `tests/test_tui_transport.py` -> **101 passed in 18.40s** (exit code: 0).
- **Implementation boundary:**
  - No new endpoints were added to the backend; client mapped strictly to existing canonical endpoints.
  - Valid empty timeline (`[]`) returns empty list without error, distinct from 404/401/403.
  - No fallback guessing or ID fabrications (`id`/`session_id` fallback avoided).
  - Auth session (`get_session()`) and clinical session (`get_session_detail()`) explicitly separated.
- **Remaining limitations:**
  - B3b is CLOSED below in this round.
  - Finding B3 as a whole is now CLOSED on the parent side (`parent-fixed / focused-verified`).
  - Call 1 runtime binding failure remains OPEN.
  - B1, B2, B5, B6, and A1–A4 remain OPEN.
- **Next smallest task:**
  - Finding B3b (executed below).

## D1 Call 1 Finding B3b — GUI Live-Mode Startup/Search/Manual Refresh Error Containment (Focused Only)

- **Scope/status:** `parent-fixed / focused-verified` (Finding B3 fully closed on parent side via B3a legacy contract alignment + B3b GUI live-mode error boundary corrective closure; NOT reviewer-accepted).
- **Violated contract:** In live API mode (`mock_mode=False`), API failures during GUI startup (`_load_initial_data` / `_refresh_cases` / `_refresh_sessions_for_active_case`), search typing (`_on_case_search_typing`), or manual refresh (`_refresh_all_data`) threw unhandled exceptions out of constructor/callbacks, wiped existing table rows before fetching, falsely claimed "no matching cases" on search outages, switched active cases arbitrarily, displayed fake success info dialogs on partial/failed refreshes while async children were still pending, failed to propagate transcript fetch errors, masked programming errors with blanket `Exception`, and retained stale session/transcript data from previous cases/sessions when fetches failed.
- **Observed RED/reproducer (Initial + Corrective):**
  - Initial RED receipt: `.local/verification/antigravity-d1/b3b_tdd_red_20260913.log` (SHA-256 `688e7272e9cb6670f863d2af2a3d9c57e8e3f9479b79c2b7dfdb4ee0d42b5168`, exit code: 1, 8 failed in 2.48s).
  - Corrective RED receipt: `.local/verification/antigravity-d1/b3b_corrective_red_20260913.log` (SHA-256 `77660ce4de6e378ed10fc0ba7fcc062ad79e71fbb54fdc0d11338b6a2b1c984f`, exit code: 1, 6 failed, 8 passed in 1.72s, `.venv/bin/python` / Python 3.12.14 / pytest 9.1.1).
- **Files changed for B3b:**
  - `packages/gui/app.py`:
    - Imported client error classes (`LinguaLensApiError`, `LinguaLensAuthError`, `LinguaLensPermissionError`, `LinguaLensServerError`) and `urllib.error`.
    - Replaced blanket `Exception` in boundaries with typed network/transport errors (`LinguaLensApiError`, `urllib.error.URLError`, `TimeoutError`, `ConnectionError`, `OSError`), allowing programming bugs (`TypeError`, `AttributeError`, `ValueError`) to raise cleanly.
    - Wrapped `_refresh_cases()`: fetch before mutating UI, preserve existing rows on network/server error, handle 401 via `_handle_auth_error`, handle 403 via `_handle_permission_error`, return `bool`.
    - Added `_invalidate_session_context(error_msg)`: safely wipes session treeview, clears `active_session_id` and `active_transcript`, updates combo and status labels, and wipes transcript/findings views.
    - Wrapped `_refresh_sessions_for_active_case()`: call `_invalidate_session_context` on error, propagate transcript fetch outcome (`return self._refresh_transcript_and_findings()`).
    - Wrapped `_refresh_transcript_and_findings()`: immediately reset `self.active_transcript = None` at top, catch typed errors, return `bool` (`False` on fetch error, `True` on success/empty). Safely handles missing utterance IDs.
    - Wrapped `_on_case_search_typing()`: catch typed errors cleanly, do not claim "no matching cases" on network failure, do not switch active case.
    - Extended `_refresh_children(on_success, on_error)`: support async completion callbacks dispatched via `_async_queue` to main thread, discarding stale completions across session generation or superseded refresh IDs.
    - Updated `_refresh_all_data()`: coordinates async children refresh with callbacks; `_refresh_all_data()` returns `True` immediately when synchronous case/session refreshes succeed and async children refresh has been dispatched. Async children completion success/failure is reported via main-thread queue callbacks (`_on_all_success` / `_on_all_error`), not by retroactively altering the return value of `_refresh_all_data()`. Callers must not treat this return value as an overall completed-success receipt while background workers are pending. If synchronous cases/sessions fail, it reports `messagebox.showerror` and returns `False`.
    - Updated `_load_initial_data()`: only select first case if `_refresh_cases()` succeeds.
  - `tests/test_gui_b3b_error_boundary.py` (new): 14 contract and error containment tests using deterministic `FakeApiClient` (zero network calls).
- **Focused GREEN:**
  - Corrective B3b suite: 14/14 passed in 1.60s. Receipt: `.local/verification/antigravity-d1/b3b_corrective_green_20260913.log` (SHA-256 `b323d8050d0a175cbeebecef8a4f236945e6195fbac564365954a1b5b21eecd3`, exit code: 0).
  - Full GUI suite: `tests/test_gui.py` -> 94/94 passed in 8.74s (exit code: 0).
  - Combined focused regression: `tests/test_gui_b3b_error_boundary.py` (14), `tests/test_tui_legacy_b3a_contract.py` (8), `tests/test_tui_legacy_b4_contract.py` (6) -> **28/28 passed in 5.08s** (exit code: 0).
- **REFACTOR note:**
  - Refactored `_invalidate_session_context` helper to eliminate duplicated session cleanup code across error paths and case transitions. Refactored `_refresh_transcript_and_findings` to return `bool` for uniform caller outcome propagation.
- **Finding B3 Overall Status:** `parent-fixed / focused-verified` (B3a and B3b closed on parent side).
- **Remaining limitations:**
  - B1 (GUI/TUI V2 and legacy context isolation across playback/export/late workers), B2 (sensitive clinical state cleanup on 401), B5 (assessment-list silent empty list; resolved below), B6 (canonical V2 value constraints), A1–A4, and Call 1 runtime binding failure remain OPEN.

## D1 Call 1 Finding B5 — Assessment List Failure Must Not Appear as Empty Success (Focused Only)

- **Scope/status:** `parent-fixed / focused-verified` (Finding B5 closed on parent side after initial criteria 1–8 and fix-induced regression closure for presentation-only error row selection in `_on_assessment_selected`; NOT `reviewer-accepted`).
- **TUI scope:** `not-applicable` (TUI workflow has no assessment directory/list presentation flow; verified via codebase search across `packages/tui/workflow.py` and `packages/tui/ui.py`; no new features created).
- **Violated contract:** When `list_assessments(child_id)` failed (403, 5xx, network error, or malformed non-list response), `_on_assessments_refresh_error` silently ignored the error, leaving the table looking like an empty list (0 assessments). Furthermore, `client.list_assessments` did not validate that response was a list, allowing malformed non-list payloads to pass without raising a contract error.
- **Initial RED/reproducer:** 4/8 tests failed in `tests/test_gui_b5_assessment_list.py` (403/500/network error treated as empty success without status/row indicator, malformed dict response didn't raise `LinguaLensApiError`, failure on child switch didn't track error, retry after transient failure didn't clear error).
  - Receipt: `.local/verification/antigravity-d1/b5_tdd_red_20260913.log` (SHA-256 `1347622238aa25e7a2c58308f7583ba3bcf075cf327f06553afbd902a8d44433`, exit code: 1, 4 failed, 4 passed in 1.05s).
- **Fix-Induced Regression Gap:**
  - `_on_assessments_refresh_error` inserted a presentation error placeholder row `iid="_error"` into `self.tree_assessments`. However, `_on_assessment_selected` treated any selected `iid` as an assessment ID, attempting `client.get_assessment("_error")`, mutating active assessment context, and spawning a selection worker thread.
- **Fix-Induced Regression RED:**
  - Added test 9 (`test_selecting_presentation_error_row_does_not_invoke_detail_api_or_start_selection_worker`) and test 10 (`test_cache_miss_detail_fetch_preserved_for_genuine_assessment_after_recovery`) to `tests/test_gui_b5_assessment_list.py`.
  - Executed: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_b5_assessment_list.py -v` (CWD: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`).
  - Observed failure: `AssertionError: assert '_error' not in ['_error']` on test 9.
  - Receipt: `.local/verification/antigravity-d1/b5_regression_red_20260913.log` (SHA-256 `82aa581a1cf0ddb0c00e8feb7bdd721e1e9530abe2326c64d16e9b4495e92c75`, exit code: 1, 1 failed, 9 passed in 1.12s).
- **Files changed for B5 & Regression Closure:**
  - `packages/tui/client.py` (SHA-256: `cc93e5059a431a36d43521a0edba45e65f4112280d1b1982def358e317792c0c`):
    - In `list_assessments(child_id)`: verified response is a list; raises `LinguaLensApiError` on malformed non-list response.
  - `packages/gui/app.py` (SHA-256: `03fd3a4cc08ea9e75c915bccffefbba3a93b971c209f4b156f2952f34652fd47`):
    - Initial B5: in `_on_assessments_refreshed`, resets `self._assessment_list_error = None` and resets status bar if previously showing assessment failure. In `_on_assessments_refresh_error`, handles 401 via `_handle_auth_error`, sets `self._assessment_list_error`, inserts explicit `_error` indicator row into `self.tree_assessments`, and updates `self.lbl_status`. In `_set_active_child`, resets `self._assessment_list_error = None`.
    - Regression closure: added explicit non-textual presentation row tracking via `self._presentation_row_iids: set[str]` and widget tag `("presentation_error",)`.
    - In `_on_assessment_selected`: non-textual check (`asmt_id in self._presentation_row_iids or "presentation_error" in tags`) deselects presentation row and returns immediately. Does NOT invoke `client.get_assessment("_error")`, does NOT mutate active assessment context, and does NOT launch worker thread. Genuine assessment selections (including cache misses) proceed as normal.
    - In `LinguaLensGUIApp.__init__`, `_set_active_child`, and `_on_assessments_refreshed`: resets `self._presentation_row_iids = set()`.
    - In `_on_assessments_refresh_error`: sets `self._presentation_row_iids = {"_error"}` and applies `tags=("presentation_error",)` to row.
  - `tests/test_gui_b5_assessment_list.py` (SHA-256: `c1fb4efef40931cebc5c134f98585afd8a68f3e2318fba7c69f999743beb24fe`):
    - 10 contract tests covering all 8 original criteria plus test 9 (presentation error row selection rejection) and test 10 (genuine assessment selection and cache-miss recovery).
- **Focused GREEN Verification:**
  - B5 suite: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_b5_assessment_list.py -v` -> **10/10 passed in 1.31s** (exit code: 0).
  - Receipt: `.local/verification/antigravity-d1/b5_regression_green_20260913.log` (SHA-256 `c8d46f06d5278dc5f464e5d1a807be0be458f0f619ccf8bd8f60ee2d399a471e`).
- **Evidence Reconciliation & Multi-Suite Focused Regression:**
  - *Evidence Reconciliation Note:* Earlier task documentation reported a 151-pass regression run as combining B5; raw command review showed that the earlier 151-pass command ran 5 test files (`tests/test_gui_b3b_error_boundary.py`, `tests/test_gui.py`, `tests/test_tui_legacy_b3a_contract.py`, `tests/test_tui_legacy_b4_contract.py`, `tests/test_tui_transport.py`) while B5 was executed in an independent 8-test run. They are recorded accurately as separate runs and not described as a combined run.
  - *New Combined Client Regression Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_b5_assessment_list.py tests/test_gui_b3b_error_boundary.py tests/test_gui.py tests/test_tui_legacy_b3a_contract.py tests/test_tui_legacy_b4_contract.py tests/test_tui_transport.py -v`
    - CWD: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
    - Interpreter: `.venv/bin/python` (Python 3.12.14, pytest 9.1.1)
    - Result: **161/161 passed in 26.89s** (exit code: 0).
    - Breakdown: `test_gui_b5_assessment_list.py` (10), `test_gui_b3b_error_boundary.py` (14), `test_gui.py` (94), `test_tui_legacy_b3a_contract.py` (8), `test_tui_legacy_b4_contract.py` (6), `test_tui_transport.py` (29).
    - Receipt: `.local/verification/antigravity-d1/b5_regression_focused_suite_20260913.log` (SHA-256 `378edf5f3f3c4617f603f351f315e3df5aa33228517c586611fb5cea69d74e59`).
- **REFACTOR note:**
  - Non-textual, tag-based and ID-set-based separation of presentation-only placeholder rows (`_error`) from domain data rows prevents any coupling to displayed UI text strings while keeping domain selection and cache-miss detail fetching clean and isolated.
- **Assurance Boundary & Remaining limitations:**
  - B5 is `parent-fixed / focused-verified` (NOT `reviewer-accepted`).
  - Durable review budget remains: 1 call used / 2 remaining (MAX 3); `ACTIVE_REVIEW_RESERVATION: none`; `REVIEW_READY: no`.
  - Findings B1 (GUI/TUI V2 and legacy context isolation), B2 (sensitive clinical state cleanup on 401), B6 (canonical V2 value constraints), A1–A4, and Call 1 runtime binding failure remain OPEN.
- **Next smallest task:**
  - Finding B6: completed. Next smallest task: Finding B1 (V2/legacy context isolation in GUI/TUI).

---

## Slice: D1 Finding B6 — Canonical V2 Constraints and Mock/Live Parity
- **Status:** parent-fixed / focused-verified (NOT reviewer-accepted)
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Reconciled Contract Matrix (Canonical Routes & Schemas vs Desktop Client):**
  | Operation | Canonical Endpoint & Path Parameters | Request Body Schema (`schemas.py`) | Service & Domain Rules | Mock State Behavior | Desktop Callers (GUI/TUI) | Key Gaps Resolved |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
  | `create_child` | `POST /api/v2/children`<br>(No path parameters) | `ChildCreateRequest`: `display_code` (str 1..64, whitespace stripped), `birth_year` (strict int 1900..2100), `birth_month` (strict int 1..12), `language_context` (`dict[str, object]` validated via `_normalize_language_context`) | Unique `(tenant_id, display_code)`; strict types (rejects bool, float); language normalization (2-letter ISO, lowercase, rejects explicit `additional=None`) | Validates input client-side before dispatch; zero POST in live mode; zero mutation on invalid input; persists child profile in mock dictionary | GUI `_submit_create_child`, TUI `_create_child_wizard`, direct `client.create_child` | Client lacked 1..64 display_code length check; strict integer checks missing; desktop validator previously accepted `additional=None` (now aligned with canonical rejection); invalid input mutated mock state |
  | `record_consent` | `POST /api/v2/children/{child_id}/consents`<br>Path: `child_id` (str 1..64) | `ConsentCreateRequest`: `purpose` (`ConsentPurpose` enum: `clinical_assessment` \| `research_reuse`), `scope_version` (str 1..64, whitespace stripped), `status` (`ConsentStatus` enum: `active` \| `withdrawn`)<br>*(Note: `child_id` is in path, NOT in body)* | Target child must exist; status must be active or withdrawn; purpose must match supported enum values exactly without whitespace padding | Validates input client-side; verifies child exists in mock DB (fails closed if non-existent); updates/appends versioned consent record for child; returns canonical `ConsentResponse` representation | GUI `_submit_consent`, TUI `_consent_wizard`, direct `client.record_consent` | Direct client calls permitted arbitrary purpose/status strings; non-existent child check was absent in mock mode; missing shared validation seam |
  | `create_assessment` | `POST /api/v2/children/{child_id}/assessments`<br>Path: `child_id` (str 1..64) | `AssessmentCreateRequest`: `purpose` (`AssessmentPurpose` enum: 4 canonical values), `assigned_clinician_id` (optional str 1..128, whitespace stripped)<br>*(Note: `child_id` is in path, NOT in body)* | Target child must exist; active `clinical_assessment` consent required (409 Conflict if missing/withdrawn); canonical age computed from child birth date and request clock (`0 <= age <= 216` months); language inherited from child | Verifies child exists in mock DB; enforces active consent gate (raises `LinguaLensConflictError`); computes canonical age dynamically (`(now.year - child.birth_year)*12 + now.month - child.birth_month`); inherits child language; NEVER hardcodes `48` or fabricated language | GUI `_submit_create_assessment`, TUI `_create_assessment_wizard`, direct `client.create_assessment` | Mock hardcoded `age_months: 48` and fabricated default language; child existence check was missing in mock; GUI/TUI input wizards lacked clinician ID length validation (max 128 chars); consent gate existed in mock previously but child existence and constraint validation were absent |
- **Acceptance Criteria & Actual Result:**
  - *Criteria:*
    1. Shared validation seam without backend runtime dependencies to desktop (`packages/tui/validation.py`).
    2. Input validation fails closed with zero POST in live mode and zero local mutation in mock mode.
    3. Exact language context parity: `_normalize_language_context` rejects explicit `additional=None`, allows omitted `additional` (defaulting to `[]`), requires 2-letter ISO codes, strips whitespace, and rejects unknown fields. Documented client convenience default (`language_context=None` -> `{"primary": "th", "additional": []}`) separated from malformed nested payload rejection.
    4. Mock `create_assessment` calculates age dynamically from child's birth date (`(now.year - child.birth_year)*12 + now.month - child.birth_month`) and controllable clock, bounded `0 <= age <= 216`; inherits child's language context; never hardcodes `48` or fabricated language.
    5. Mock verifies child existence on `record_consent` and `create_assessment` before state mutation; enforces consent gate (409 Conflict if consent absent or withdrawn).
    6. GUI and TUI enforce client-side constraints (display_code 1..64, clinician ID 1..128, strict types) without setting fabricated active context.
    7. Legacy B4 `/api/v1/cases` behavior preserved.
  - *Actual Result:* All criteria fully verified with 81 unit, boundary, differential, and parity tests in `tests/test_canonical_v2_b6_constraints.py` and 242 focused multi-suite regression tests.
- **Changed Files:**
  - `packages/tui/validation.py` (new; SHA-256: `48b2b7ca30369bca7fa4fe8053d1ef849558c403f980329b2e399b2afe9da5d2`):
    - Pure-Python shared validators: `normalize_language_context`, `validate_child_input`, `validate_consent_input`, `validate_assessment_input`, `calculate_age_in_months`.
    - Defined `LinguaLensValidationError(ValueError)`.
    - Aligned `normalize_language_context` with canonical backend: rejects explicit `additional=None` (no silent coercion).
  - `packages/tui/client.py` (SHA-256: `df7b24be28cc76442249e3e8a1b0476d83288124ddcb5f6e85d1b376a2a32ed3`):
    - `LinguaLensValidationError(LinguaLensApiError, _BaseValidationError)` imported and subclasses validation base.
    - Added controllable clock injection (`self._clock`, `_get_current_utc_time`, `_get_now()`).
    - Wired `validate_child_input` into `create_child` (validates before HTTP or mock mutation).
    - Wired `validate_consent_input` and child existence check into `record_consent`.
    - Wired `validate_assessment_input`, child existence, consent gate, canonical age calculation, and child language inheritance into `create_assessment`.
  - `packages/gui/app.py` (SHA-256: `04a859e02521ad3b4ca157d06d2e5056e7d22ec51ac16050ff73e739611426a7`):
    - In `_validate_child_intake`: enforced display_code length (1..64), strict types, and shared validation seam.
    - In `_submit_create_assessment`: enforced assigned_clinician_id length (max 128 chars); on violation shows error dialog and returns `None` without mutating context.
  - `packages/tui/workflow.py` (SHA-256: `502fe89988467221be43500096f49ea46efc40c161e3c81e1905327595d273f9`):
    - In `_create_assessment_wizard`: enforced clinician_id length (max 128 chars).
    - In `_create_child_wizard`: enforced display_code length (1..64 chars).
  - `tests/test_canonical_v2_b6_constraints.py` (new; SHA-256: `211f20ca801b39f7789e2dd9a7fdf6ae30691904b1c88f7441e8181e5be32048`):
    - 81 focused tests: 64 initial contract/mock parity tests + 17 differential contract tests comparing desktop validators against canonical Pydantic request models (`ChildCreateRequest`, `ConsentCreateRequest`, `AssessmentCreateRequest`, `_normalize_language_context`).
- **TDD RED/GREEN Evidence:**
  - *Initial B6 RED Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_canonical_v2_b6_constraints.py -v`
    - Result: **59 failed, 5 passed** (exit code: 1).
    - Receipt: `.local/verification/antigravity-d1/b6_tdd_red_20260913.log` (SHA-256: `f5ba799997a82176b0abe55398612e7b0b03dd07c49f6755cfd25862518fe092`).
  - *Initial B6 GREEN Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_canonical_v2_b6_constraints.py -v`
    - Result: **64/64 passed in 1.77s** (exit code: 0).
    - Receipt: `.local/verification/antigravity-d1/b6_tdd_green_20260913.log` (SHA-256: `b7158350e843270b385ecb41d86542e4c61fcd982fb064d02f912fc3acbf8361`).
  - *Differential Reconciliation RED Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_canonical_v2_b6_constraints.py -v`
    - Result: **3 failed, 77 passed** (exit code: 1, captured observable mismatch: explicit `additional=None` silent coercion, enum whitespace rejection parity, and malformed nested payload rejection).
    - Receipt: `.local/verification/antigravity-d1/b6_reconciliation_red_20260913.log` (SHA-256: `44cafa5195c3abeae7f95381f92e0e2ed8beef484895561e6cbceded955e216e`).
  - *Differential Reconciliation GREEN Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_canonical_v2_b6_constraints.py -v`
    - Result: **81/81 passed in 2.32s** (exit code: 0).
    - Receipt: `.local/verification/antigravity-d1/b6_reconciliation_green_20260913.log` (SHA-256: `b739a0b5d60f1e02796a49c51f70b3b00d87e7a552e85150fc68443db04685d4`).
- **Focused Multi-Suite Regression Evidence:**
  - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_canonical_v2_b6_constraints.py tests/test_gui_b5_assessment_list.py tests/test_gui_b3b_error_boundary.py tests/test_gui.py tests/test_tui_legacy_b3a_contract.py tests/test_tui_legacy_b4_contract.py tests/test_tui_transport.py -v`
  - CWD: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Interpreter: `.venv/bin/python` (Python 3.12.14, pytest 9.1.1)
  - Result: **242/242 passed in 28.22s** (exit code: 0).
  - Breakdown: `test_canonical_v2_b6_constraints.py` (81), `test_gui_b5_assessment_list.py` (10), `test_gui_b3b_error_boundary.py` (14), `test_gui.py` (94), `test_tui_legacy_b3a_contract.py` (8), `test_tui_legacy_b4_contract.py` (6), `test_tui_transport.py` (29).
  - Receipt: `.local/verification/antigravity-d1/b6_reconciliation_regression_suite_20260913.log` (SHA-256: `60cef6e5aee21b578c8d96688087d3dfd72ebcd9a1c5f9bbf94b6419e2849c3f`).
- **REFACTOR Evidence:**
  - Shared validation logic remains isolated in `packages/tui/validation.py` using Python Standard Library only (`re`, `datetime`, `typing`). No backend framework dependencies (`pydantic`, `fastapi`, `sqlalchemy`) leak into desktop runtime.
  - Canonical request schemas (`ChildCreateRequest`, `ConsentCreateRequest`, `AssessmentCreateRequest`) are used as oracles strictly inside test boundaries (`tests/test_canonical_v2_b6_constraints.py`).
- **Assurance Boundary & Remaining Limitations:**
  - Finding B6 is `parent-fixed / focused-verified` (NOT `reviewer-accepted`).
  - Durable review budget remains: 1 call used / 2 remaining (MAX 3); `ACTIVE_REVIEW_RESERVATION: none`; `REVIEW_READY: no`.
  - Findings B1 (GUI/TUI V2 and legacy context isolation), B2 (sensitive clinical state cleanup on 401), A1–A4, and Call 1 runtime binding failure remain OPEN.
- **Next Smallest Task:**
  - Finding B1 (completed; see below).

---

## Slice: D1 Finding B1 — GUI/TUI V2–Legacy Context Isolation
- **Status:** parent-fixed / focused-verified (NOT reviewer-accepted)
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Bounded Isolation Matrix (Actual Methods & Test Node IDs):**
  | Subsystem / Entry Point | Actual Triggering Methods / Callbacks | Context Used | Intended Side Effect / Isolation Rule | Existing Guard | Hardened Guard & Enforcement | Test Node ID |
  | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
  | **GUI Case / Session Selectors** | `_on_case_selected`, `_on_global_case_changed`, `_refresh_sessions_for_active_case`, `_show_create_session_dialog` | `active_case_id`, `active_session_id` | Clears all V2 state (`active_child_id`, `active_assessment_id`, `_cached_assessments`, treeview rows, combo), sets `current_mode = "legacy"`, increments legacy generation, stops playback | None (previously coexisted or left dangling selections) | Explicit `current_mode = "legacy"`, total flush of active V2 state and downstream tab switch; direct refresh/dialog callbacks block if `_is_v2_mode()` | `tests/test_gui_tui_b1_context_isolation.py::test_gui_explicit_return_to_legacy_restores_legacy_capabilities`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_child_only_context_blocks_direct_legacy_callbacks` |
  | **GUI V2 Selectors & Async Loaders** | `_set_active_child`, `_on_async_child_selected`, `_on_assessment_selected` | `active_child_id`, `active_assessment_id` | Clears all legacy state (`active_case_id`, `active_session_id`, `active_transcript`, `active_report`, audio path), sets `current_mode = "v2"`, increments legacy generation, stops playback | Relying only on `active_assessment_id` | Explicit `current_mode = "v2"`, flushes legacy context, invalidates prior async request IDs, clears legacy UI tree selections; late child/assessment responses discard if request ID/mode does not match | `tests/test_gui_tui_b1_context_isolation.py::test_gui_entering_v2_clears_legacy_context_and_sets_mode`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_child_only_context_blocks_direct_legacy_callbacks` |
  | **GUI Legacy Ingest / Review Actions** | `_browse_audio_file`, `_batch_ingest_audio_files`, `_process_audio_file`, `_load_demo_dialogue`, `_browse_text_file`, `_ingest_typed_text`, `_save_utterance_edit`, `_auto_refine_speakers`, `_swap_speakers`, `_attest_transcript` | `active_case_id`, `active_session_id`, `active_transcript` | Prohibited in V2 mode; fail closed even if called directly via keyboard/event or code | Partial UI button disabling | Hardened `_guard_v2_mode()` checks `_is_v2_mode()` (mode `"v2"` OR `active_child_id is not None` OR `active_assessment_id is not None`); displays warning and immediately returns `None` | `tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_child_only_context_blocks_direct_legacy_callbacks` |
  | **GUI Playback & Shortcuts** | `_seek_and_play`, `_seek_to_position`, `_play_selected_utterance`, `_play_word_segment`, `_play_audio_range`, `_toggle_continuous_playback`, `_handle_space_shortcut` | `active_audio_path`, `active_session_id`, audio worker | Audio playback disallowed in V2 mode; spacebar shortcut disabled; zero subprocess launch | Unprotected spacebar shortcut, only checked `audio_path` | `_is_v2_mode()` guards in all playback/seek/word callbacks and `_handle_space_shortcut`; stops playback on mode transition | `tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_child_only_context_blocks_direct_legacy_callbacks`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_mode_blocks_actual_export_callbacks_with_residual_data` |
  | **GUI Clipboard & Export Actions** | `_export_cha_file`, `_export_csv_biomarkers`, `_export_html_report`, `_export_report`, `_copy_chat_text` | `active_transcript`, `active_report`, `active_case_id` | Must never export or copy legacy transcript/report while V2 context is active; zero file dialogs, zero file writes, zero API calls | Checked `active_transcript` only | Guarded with `_guard_v2_mode()` at entry: blocks execution and clears/prevents legacy data leakage even if residual legacy data exists | `tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_mode_blocks_actual_export_callbacks_with_residual_data`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_explicit_return_to_legacy_restores_legacy_capabilities` |
  | **GUI Background Worker Completion & Busy Ownership** | `_run_async_task`, `_on_task_done`, `_set_busy_state`, `current_mode.setter` | Thread worker callback, `request_id`, `task_mode`, `generation` | Worker started in legacy mode finishing after user switches to V2 must NOT mutate GUI, NOT alter status text of a newer task, NOT change cursor/progress, and NOT clear busy state owned by V2 task; context transition clears abandoned task busy state without stranding UI | None (`_set_busy_state(False, "Ready")` ran unconditionally before staleness check) | Bound `request_id`, `task_mode`, and `generation` at spawn; `_on_task_done` checks mode/generation staleness BEFORE touching busy state or UI; `current_mode.setter` clears abandoned task busy state on transition | `tests/test_gui_tui_b1_context_isolation.py::test_gui_legacy_worker_started_before_v2_switch_is_discarded`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_stale_legacy_worker_does_not_mutate_ui_or_busy_owner` |
  | **GUI V2 In-Progress / Error / Empty States** | `_on_assessments_refresh_error`, `_on_assessment_selected`, child-only context without assessment | `active_child_id`, `_assessment_list_error` | While assessment is loading, has error, or child has zero assessments, legacy actions must REMAIN BLOCKED | `_guard_v2_mode` previously checked only `active_assessment_id`, opening vulnerability | `_is_v2_mode()` checks `current_mode == "v2" or active_child_id is not None or active_assessment_id is not None`. Direct callbacks and UI remain strictly guarded | `tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_child_only_context_blocks_direct_legacy_callbacks`<br>`tests/test_gui_tui_b1_context_isolation.py::test_gui_v2_assessment_error_keeps_legacy_actions_guarded` |
  | **GUI Explicit Return to Legacy** | `_on_case_selected`, `tree_cases` selection | `case_id` | Re-enables legacy operations, resets `current_mode = "legacy"`, downstream tabs updated, legacy session actions and exports succeed | None | User selection explicitly sets `current_mode = "legacy"`, tears down V2 context, and restores legacy capabilities cleanly | `tests/test_gui_tui_b1_context_isolation.py::test_gui_explicit_return_to_legacy_restores_legacy_capabilities` |
  | **TUI Workflow Dispatch** | `_cases_menu`, `_set_active_case`, `_children_menu`, `_set_active_child`, `_ingest_transcript_flow`, `_review_transcript_flow`, `_view_findings_flow`, `_report_flow`, `_export_flow` | `current_mode`, `active_case_id`, `active_child_id` | TUI legacy flows must fail closed if V2 is active or no legacy case is selected; selecting child sets `current_mode = "v2"`; selecting case sets `current_mode = "legacy"` | Lacked explicit mode separation | Added `self.current_mode = "legacy"`, `_set_active_child` sets `"v2"` and wipes legacy context; `_set_active_case` sets `"legacy"` and wipes V2 context; all legacy action subflows guard against V2 mode | `tests/test_gui_tui_b1_context_isolation.py::test_tui_entering_v2_clears_legacy_context`<br>`tests/test_gui_tui_b1_context_isolation.py::test_tui_entering_legacy_clears_v2_context`<br>`tests/test_gui_tui_b1_context_isolation.py::test_tui_legacy_subflows_fail_closed_if_v2_active` |

- **Changed Files:**
  - `packages/gui/app.py` (SHA-256: `e9553a8e3dd037119c0fee16243cb5149b559ff373aa58a5a98fd2664004d5af`):
    - Added explicit `current_mode` property and setter: setting `"v2"` clears legacy context (`active_case_id`, `active_session_id`, `active_transcript`, `active_report`, `active_audio_path`), stops playback, and cleans up abandoned legacy busy state; setting `"legacy"` clears V2 context and cleans up abandoned V2 busy state.
    - Implemented `_is_v2_mode()` to check `self._current_mode == "v2" or self.active_child_id is not None or self.active_assessment_id is not None`.
    - Hardened `_guard_v2_mode()` to evaluate `_is_v2_mode()`, preventing any legacy fallback when assessment is loading, in error, or cleared.
    - Hardened `_handle_space_shortcut()`, `_play_audio_range()`, `_play_word_segment()`, and playback callbacks (`_seek_and_play`, `_seek_to_position`, `_play_selected_utterance`, `_toggle_continuous_playback`) against V2 mode.
    - Bound `request_id`, `mode`, and monotonic generation in `_run_async_task`, `_set_busy_state`, and `_on_task_done`: stale or cross-mode worker completions check staleness BEFORE touching busy state, status text, or callbacks.
    - Added guards to actual export entry points (`_export_cha_file`, `_export_csv_biomarkers`, `_export_html_report`, `_export_report`, `_copy_chat_text`), preventing dialogs, file writes, and API fetches even when residual legacy data is present.
    - Restored strict non-optional binding on `_on_assessments_refresh_error(child_id, error, request_id, session_gen, child_sel_gen)`.
    - Removed test-only compatibility aliases (`_on_browse_audio`, `_batch_ingest_audio`, `_generate_report`, `_signoff_report`, `_on_child_data_loaded`).
  - `packages/tui/client.py` (SHA-256: `1497c84219e8a71d01022e6ebbb06e3dbc02bca35fdc8cb46dbc56fd8287aa5a`):
    - Maintained authentic `LinguaLensApiError(message: str, status_code: int | None = None)` constructor without unnecessary relaxed `*args/**kwargs`.
  - `packages/tui/workflow.py` (SHA-256: `954a6fb4642c302e11eaa198d0814f6b383b7b632b86b11fa2a46ba9b9fc09fd`):
    - Initialized `self.current_mode = "legacy"`.
    - `_set_active_child`: sets `current_mode = "v2"`, clears legacy case/session/transcript/report context.
    - Added `_set_active_case(case_id)`: sets `current_mode = "legacy"`, clears V2 child/consent/assessment context.
    - Wired `_set_active_case` into case selection and case creation flows in `_cases_menu`.
    - Added fail-closed context guards in `_ingest_transcript_flow`, `_review_transcript_flow`, `_view_findings_flow`, `_report_flow`, and `_export_flow`.
  - `tests/test_gui_tui_b1_context_isolation.py` (SHA-256: `bb0b9ca73676aa01febd20e5b735cca930cd2922a3aea85982de9187ea7f0f99`):
    - 10 focused tests with 100% actual method mapping and zero test-only alias reliance:
      1. `test_gui_entering_v2_clears_legacy_context_and_sets_mode`
      2. `test_gui_v2_child_only_context_blocks_direct_legacy_callbacks`
      3. `test_gui_v2_assessment_error_keeps_legacy_actions_guarded`
      4. `test_gui_legacy_worker_started_before_v2_switch_is_discarded`
      5. `test_gui_stale_legacy_worker_does_not_mutate_ui_or_busy_owner`
      6. `test_gui_v2_mode_blocks_actual_export_callbacks_with_residual_data`
      7. `test_gui_explicit_return_to_legacy_restores_legacy_capabilities`
      8. `test_tui_entering_v2_clears_legacy_context`
      9. `test_tui_entering_legacy_clears_v2_context`
      10. `test_tui_legacy_subflows_fail_closed_if_v2_active`

- **TDD RED / GREEN / REFACTOR Evidence:**
  - *Initial B1 RED Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b1_context_isolation.py -v`
    - Result: **8 failed in 1.27s** (exit code: 1).
    - Receipt: `.local/verification/antigravity-d1/b1_tdd_red_20260913.log` (SHA-256: `8cb99962045c527edcdced2fc73d85e8edbe4f2d301d93e8434c0eec7b45d4d4`).
  - *Corrective Closure RED Run (Stale Busy UI Side Effects & Actual Export Callbacks):*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b1_context_isolation.py -v`
    - Result: **2 failed, 8 passed** (exit code: 1, captured observable failures: `_run_async_task` lacked `request_id` tracking; `_export_cha_file`, `_export_csv_biomarkers`, `_export_html_report` lacked `_guard_v2_mode()` and triggered file dialogs).
    - Receipt: `.local/verification/antigravity-d1/b1_corrective_red_20260913.log` (SHA-256: `f1249d15f8d93f9cd0e6b8d43d6adff350d5224a0b5eb929365f62ff5d686961`).
  - *Corrective Closure GREEN Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b1_context_isolation.py -v`
    - Result: **10/10 passed in 1.11s** (exit code: 0).
    - Receipt: `.local/verification/antigravity-d1/b1_corrective_green_20260913.log` (SHA-256: `f0bfd16e6cde3d2d7178b0726d1e56292ddba4c951173a2ba04c16f40b56971c`).
  - *REFACTOR & Seam Alignment:*
    - Removed all 5 test-only aliases from `packages/gui/app.py`.
    - Tests interact exclusively with actual production entry points and pass authentic request, session, and selection generations.
    - Bound `request_id` and `mode` to busy state management; transition cleanup prevents stranding UI in busy state or clearing busy state of newly dispatched tasks.

- **Focused Multi-Suite Regression Evidence:**
  - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b1_context_isolation.py tests/test_canonical_v2_b6_constraints.py tests/test_gui_b5_assessment_list.py tests/test_gui_b3b_error_boundary.py tests/test_gui.py tests/test_tui_legacy_b3a_contract.py tests/test_tui_legacy_b4_contract.py tests/test_tui_transport.py -v`
  - CWD: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Interpreter: `.venv/bin/python` (Python 3.12.14, pytest 9.1.1)
  - Result: **252 passed in 29.52s** (exit code: 0).
  - Breakdown:
    - `test_gui_tui_b1_context_isolation.py`: 10 passed
    - `test_canonical_v2_b6_constraints.py`: 81 passed
    - `test_gui_b5_assessment_list.py`: 10 passed
    - `test_gui_b3b_error_boundary.py`: 14 passed
    - `test_gui.py`: 94 passed
    - `test_tui_legacy_b3a_contract.py`: 8 passed
    - `test_tui_legacy_b4_contract.py`: 6 passed
    - `test_tui_transport.py`: 29 passed
  - Receipt: `.local/verification/antigravity-d1/b1_corrective_regression_suite_20260913.log` (SHA-256: `f73d12d1893f35bc1907a2cfbe3ddd57eaae7270271fa00ec5ee83809bcd7329`).

- **Assurance Boundary & Limitations:**
  - Finding B1 is `parent-fixed / focused-verified` across all 9 matrix paths (NOT `reviewer-accepted`).
  - Durable review budget remains: 1 call used / 2 remaining (MAX 3); `ACTIVE_REVIEW_RESERVATION: none`; `REVIEW_READY: no`.
  - Finding B2 (session/auth 401 clinical state cleanup), Findings A1–A4, and Call 1 runtime binding failure remain OPEN.
- **Next Smallest Task:**
  - Finding B2 (completed; see below).

---

## Slice: D1 Finding B2 — Current-Session 401 Clinical-State Cleanup
- **Status:** parent-fixed / focused-verified (NOT reviewer-accepted)
- **Workspace / branch:**
  - Continuation Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Branch: `antigravity/assessment-v2-continuation`
- **Auth-Cleanup Matrix (Actual Callers, Boundary Guards & Test Node IDs):**
  | Caller / Subsystem | Entry Point / Method | Identity Evaluated | Auth-Cleanup Rule & Behavior | Guard & Enforcement Mechanism | Test Node ID |
  | :--- | :--- | :--- | :--- | :--- | :--- |
  | **GUI Async Task Dispatcher** | `_run_async_task`, `_on_task_done` | `task_session_gen` vs `current_session_gen` | If typed 401 occurs in the current auth session, trigger `_handle_auth_error` immediately, even if request cancelled or mode/selection changed. Discard 401 only if auth session itself has changed (e.g., after logout/re-login). | `session_gen` captured at dispatch. `_on_task_done` evaluates typed 401 (`isinstance(e, LinguaLensAuthError) or getattr(e, 'status_code', None) == 401`) before context/mode staleness checks; passes to `_handle_auth_error`. | `tests/test_gui_tui_b2_auth_cleanup.py::test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state`<br>`tests/test_gui_tui_b2_auth_cleanup.py::test_mode_switch_and_selection_change_still_triggers_current_session_401_cleanup`<br>`tests/test_gui_tui_b2_auth_cleanup.py::test_stale_401_from_prior_session_does_not_clear_new_session_or_context` |
  | **GUI Cancelled Operations** | In-flight async worker marked cancelled | `cancel_event.is_set()`, `task_session_gen` | Cancellation suppresses UI success/error display, but NEVER suppresses current session 401 cleanup; expired auth must wipe sensitive clinical data regardless of cancellation. | In `_on_task_done` and `_on_create_assessment_error`, typed 401 check executes before cancellation suppression. | `tests/test_gui_tui_b2_auth_cleanup.py::test_cancel_operation_still_triggers_current_session_401_cleanup` |
  | **GUI V2 Consent Refresh Callback** | `_on_consent_refresh_error` | `task_session_gen`, `child_sel_gen`, `child_id` | If consent refresh fails with 401 in current session, clean up auth and sensitive state even if child selection has changed. | Typed 401 evaluated prior to checking `child_sel_gen != self._child_selection_generation`. | `tests/test_gui_tui_b2_auth_cleanup.py::test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state` |
  | **GUI V2 Assessment Detail Callback** | `_on_assessment_detail_error` | `task_session_gen`, `request_id`, selection gen | 401 triggers immediate session invalidation; stale assessment selection checks cannot bypass session cleanup. | Typed 401 evaluated prior to request ID or selection generation match check. | `tests/test_gui_tui_b2_auth_cleanup.py::test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state` |
  | **GUI V2 Assessment List Refresh** | `_on_assessments_refresh_error` | `task_session_gen`, `child_sel_gen`, `request_id` | 401 invalidates current auth session and wipes clinical state; cannot be masked as empty list or ignored due to child deselect. | Typed 401 evaluated before child selection generation or request ID match. | `tests/test_gui_tui_b2_auth_cleanup.py::test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state` |
  | **GUI V2 Assessment Creation Callback** | `_on_create_assessment_error` | `task_session_gen`, `cancel_event`, dialog token | 401 closes dialog, cancels worker, and invalidates session even if dialog was cancelled or dismissed. | Typed 401 evaluated before `cancel_event.is_set()` check. | `tests/test_gui_tui_b2_auth_cleanup.py::test_cancel_operation_still_triggers_current_session_401_cleanup` |
  | **GUI Post-Auth Late Worker Success** | Stale async worker finishing after 401 cleanup | `task_session_gen` vs `current_session_gen` | Success callback of worker launched under invalidated session MUST NOT restore clinical data or alter UI. | In `_on_task_done`, if `task_session_gen != current_session_gen`, result is silently discarded. | `tests/test_gui_tui_b2_auth_cleanup.py::test_late_success_after_auth_invalidation_does_not_restore_clinical_data_or_show_success` |
  | **GUI Concurrent 401 Dialog Storm** | Multiple concurrent workers returning 401 | Reentrancy lock `_auth_dialog_active` | Rapid concurrent 401s must be idempotent: state cleaned once, exactly one session-expired dialog shown to clinician. | `_auth_dialog_active` flag guards against recursive `messagebox.showerror` calls while auth error dialog is active. | `tests/test_gui_tui_b2_auth_cleanup.py::test_repeated_401_is_idempotent_and_prevents_dialog_storm` |
  | **Non-401 Error Discrimination** | 403 Forbidden, 409 Conflict, network failures, validation errors with "auth" or "401" in text | Error type and HTTP status code | Non-401 errors must NOT trigger auth cleanup or logout; errors are displayed via standard error boundaries. | Removed all substring matching (`"auth"` or `"401"` in `str(error)`). Strict check: `isinstance(e, LinguaLensAuthError) or getattr(e, 'status_code', None) == 401`. | `tests/test_gui_tui_b2_auth_cleanup.py::test_403_and_409_and_network_failures_are_not_treated_as_401`<br>`tests/test_gui_tui_b2_auth_cleanup.py::test_error_messages_containing_auth_or_401_substrings_do_not_trigger_logout` |
  | **GUI Residual Clinical Display & Dialog Cleanup** | `_handle_auth_error`, `_poll_async_queue` | Current auth session failure | All visible clinical text (`txt_chat_view`, `txt_narrative`, `txt_recommendations`, `txt_manual`, `txt_radar_summary`), treeviews (`tree_metrics`, `tree_guidelines`, `tree_longitudinal`), canvases (`canvas_waveform`, `canvas_radar`), combobox options (`combo_global_case`, `combo_global_session`, `combo_global_child`), entries (`entry_audio_path`, `entry_u_text`, `entry_case_search`), context labels, and open child dialogs (`Toplevel`) must be wiped clean. | Centralized widget iteration in `_handle_auth_error`; text widgets preserve disabled state; combobox options reset to empty; open child dialogs destroyed. | `tests/test_gui_tui_b2_auth_cleanup.py::test_gui_current_session_401_wipes_all_residual_clinical_displays_and_dialogs` |
  | **TUI Workflow Auth Boundary** | `WorkflowRunner.start`, `_set_active_child`, `_handle_auth_error` | Error type and status code | TUI intercepts 401, clears client credentials and wipes all active legacy and V2 clinical state, prompts user. | Centralized `_handle_auth_error(error)` in `WorkflowRunner` wipes credentials, legacy state, and V2 state. | `tests/test_gui_tui_b2_auth_cleanup.py::test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state` |

- **Sensitive State Cleanup Inventory:**
  - **Credentials & Session:** `self.client.clear_session()` (authentically defined on `LinguaLensClient`), `self._current_session_generation = current_gen + 1`.
  - **Legacy Clinical Context:** `active_case_id = None`, `active_session_id = None`, `active_transcript = None`, `active_report = None`.
  - **V2 Clinical Context:** `active_child_id = None`, `active_child = None`, `active_consent = None`, `_current_consent_status = "not-loaded"`, `active_assessment_id = None`, `active_assessment = None`, `_cached_assessments = []`.
  - **Visible UI Tables & Treeviews (8 total):** `tree_cases`, `tree_sessions`, `tree_children`, `tree_assessments`, `tree_utterances`, `tree_metrics`, `tree_guidelines`, and `tree_longitudinal` cleared via `tree.delete(it)`.
  - **Visible Clinical Text Widgets (5 total):** `txt_chat_view` (state preserved, including `tk.DISABLED`), `txt_narrative`, `txt_recommendations`, `txt_manual`, and `txt_radar_summary` cleared via `w.delete("1.0", tk.END)`.
  - **Canvases / Visual Plots (2 total):** `canvas_waveform` and `canvas_radar` cleared via `c.delete("all")`.
  - **Comboboxes & Selectors (3 total):** `combo_global_case`, `combo_global_session`, and `combo_global_child` have both `values` emptied and selection string cleared (`combo["values"] = []`, `combo.set("")`) preventing clinicians from re-selecting old clinical records.
  - **Entry Fields (3 total):** `entry_audio_path`, `entry_u_text`, and `entry_case_search` cleared via `e.delete(0, tk.END)`.
  - **Context Labels (7 total):** `lbl_ingest_ctx`, `lbl_longitudinal_summary`, `lbl_review_status`, `lbl_report_status`, `lbl_playback_status`, `lbl_time_current`, and `lbl_time_total` reset to default/signed-out text.
  - **Audio State & Playback:** `active_audio_path = None`, audio playback actively stopped via `_stop_playback()`.
  - **Open Clinical Dialogs:** Any open child `tk.Toplevel` windows on `self.root` are safely destroyed to eliminate exposed clinical intake or assessment dialogs.
  - **Pending Callbacks & Busy Ownership:** In-flight assessment dialog cancellation events triggered; busy state reset via `_set_busy_state(False, "Ready")`.
  - **Thread Safety:** Executed deterministically on Tk main thread via `self._async_queue` polled by `_poll_async_queue()` via `self.root.after(30, ...)`.
  - **External Artifact Limitations:** Application does not delete user-exported files previously saved to disk outside application heap, nor does it sweep the operating system clipboard.

- **Changed Files:**
  - `packages/gui/app.py` (SHA-256: `ca0727ae3f425b33485dd797b6c2bd450c164d6093f5000ac9ba3cd73d76936d`):
    - Bound `session_gen` in `_run_async_task` and evaluated typed 401 in `_on_task_done` prior to mode or context staleness checks.
    - Eliminated loose string matching on `"auth"` and `"401"`; enforced typed `LinguaLensAuthError` or `status_code == 401`.
    - Added comprehensive sensitive clinical state and display cleanup in `_handle_auth_error` (including `active_report`, `_cached_assessments`, all 8 treeviews, 5 text widgets with disabled state preservation, 2 canvases, 3 comboboxes' values & selections, 3 entry fields, 7 context labels, and open child dialogs).
    - Added `_auth_dialog_active` reentrancy lock to prevent dialog storms during concurrent 401 responses.
    - Updated `_on_consent_refresh_error`, `_on_assessment_detail_error`, `_on_assessments_refresh_error`, and `_on_create_assessment_error` to evaluate 401 before cancellation and selection staleness.
  - `packages/tui/workflow.py` (SHA-256: `1f9d17c0a5117b63ce1b41636461de2147b584f67257e611c4591949eb98b152`):
    - Added centralized `_handle_auth_error(error)` to invalidate client credentials and wipe both legacy and V2 clinical states.
    - Wired `_handle_auth_error` into `start()` and child selection error handlers.
  - `tests/test_tui.py` (SHA-256: `cf00a3ac2fb951073f4089ccf975fc8f64a6c3e9c6e4e6830a043d91f8d730c4`):
    - Aligned `test_mock_consent_versioning_per_purpose_and_child_isolation` to create mock children before recording consent (satisfying B6 constraint) and use canonical purpose `research_reuse`.
  - `tests/test_gui_tui_b2_auth_cleanup.py` (SHA-256: `c8858cc1e2e90aa0bf61aba1caa4e521eafef8608f7de882f4f17c3cff6508a4`):
    - 9 comprehensive tests covering current session 401, cancelled operations, mode switches, stale session isolation, late worker success discard, idempotent dialog storm prevention, non-401 error discrimination, residual clinical display & dialog cleanup, and TUI auth boundary.

- **TDD RED / GREEN / REFACTOR Evidence:**
  - *Initial RED Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b2_auth_cleanup.py -v`
    - Result: **6 failed, 2 passed** (exit code: 1).
    - Receipt: `.local/verification/antigravity-d1/b2_tdd_red_20260913.log` (SHA-256: `b31d943f915f4a22c1efaee4ccbeca127391fb2e205aa42775e7cc87a856adae`).
  - *Residual Clinical Display RED Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b2_auth_cleanup.py -k "test_gui_current_session_401_wipes_all_residual_clinical_displays_and_dialogs" -v`
    - Result: **1 failed, 8 deselected in 0.91s** (exit code: 1, captured observable failure: `txt_chat_view` retained `SENTINEL_CHILD_TRANSCRIPT_SECRET`).
    - Receipt: `.local/verification/antigravity-d1/b2_residual_display_red_20260913.log` (SHA-256: `35b39ed4ebaad81d9f01ba6a7379c5c0199e0ca07a5e291a2c056b7c7b912dd5`).
  - *Residual Clinical Display GREEN Run:*
    - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b2_auth_cleanup.py -v`
    - Result: **9/9 passed in 1.04s** (exit code: 0).
    - Receipt: `.local/verification/antigravity-d1/b2_residual_display_green_20260913.log` (SHA-256: `e5e3e17c46519434af66b1e3d4ee67a4e3152da9d746bf2a76aa9444fb3e7411`).
  - *REFACTOR:*
    - Cleaned widgets dynamically using `getattr` loops over known UI element categories, handling `tk.DISABLED` state preservation on text widgets without crashing, resetting combobox dropdown lists to prevent re-selection, and destroying child dialogs on root without extra dependencies.

- **Focused Multi-Suite Regression Evidence:**
  - Command: `PYTHONPATH=apps/api:src:. .venv/bin/python -m pytest tests/test_gui_tui_b2_auth_cleanup.py tests/test_gui_tui_b1_context_isolation.py tests/test_tui.py tests/test_gui.py tests/test_gui_b3b_error_boundary.py tests/test_gui_b5_assessment_list.py tests/test_canonical_v2_b6_constraints.py tests/test_tui_transport.py tests/test_tui_legacy_b3a_contract.py tests/test_tui_legacy_b4_contract.py -v`
  - CWD: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`
  - Interpreter: `.venv/bin/python` (Python 3.12.14, pytest 9.1.1)
  - Result: **319 passed in 30.72s** (exit code: 0).
  - Breakdown:
    - `test_gui_tui_b2_auth_cleanup.py`: 9 passed
    - `test_gui_tui_b1_context_isolation.py`: 10 passed
    - `test_tui.py`: 61 passed
    - `test_gui.py`: 94 passed
    - `test_gui_b3b_error_boundary.py`: 14 passed
    - `test_gui_b5_assessment_list.py`: 10 passed
    - `test_canonical_v2_b6_constraints.py`: 81 passed
    - `test_tui_transport.py`: 29 passed
    - `test_tui_legacy_b3a_contract.py`: 8 passed
    - `test_tui_legacy_b4_contract.py`: 6 passed
  - Receipt: `.local/verification/antigravity-d1/b2_residual_regression_suite_20260913.log` (SHA-256: `e249f6337fc80e94973433ae95734a60b12bee6f7dcbf3ddf2de98f28f6389ae`).

- **Assurance Boundary & Limitations:**
  - Finding B2 is now fully closed on the parent side: `parent-fixed / focused-verified` (NOT `reviewer-accepted`).
  - All 6 behavior blockers identified in Call 1 (B1, B2, B3a, B3b, B4, B5, B6) are now `parent-fixed / focused-verified`.
  - Durable review budget remains: 1 call used / 2 remaining (MAX 3); `ACTIVE_REVIEW_RESERVATION: none`; `REVIEW_READY: no`.
  - Findings A1–A4 (assurance packet, scope reconciliation, parity documentation) and the Call 1 runtime binding failure remain OPEN.
- **Next Smallest Task:**
  - Complete D1 Assurance Closure A1–A4 and Readiness Gap Report (done below).

---

## Slice: D1 Draft Evidence Consistency Closure & Readiness Gap Report
- **Status:** draft-consistent / readiness-gap-analyzed (review reserved: no; runtime gate: open)
- **Assurance Unit ID:** `lingualens/assessment-v2/desktop-stage1`
- **Unit Status:** `open`
- **Reopen Generation:** `0`
- **Review Budget:** `calls used: 1/3`, `remaining: 2`, `MAX: 3`, `ACTIVE_REVIEW_RESERVATION: none`, `REVIEW_READY: no`
- **Workspace:** `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation` (branch: `antigravity/assessment-v2-continuation`)
- **Base Commit:** `5fb37457167b079d63d5ffe10d63a1cd2cd88706`

### 1. A1–A4 Finding Status & Reconciliation
- **A1 — Candidate Scope Completeness:** **`draft-reconciled / candidate-freeze-open`**
  - Reconciled draft candidate inventory covering exactly 23 files (5 production, 11 tests, 5 specs/plans, 2 repo docs with D1 hunks).
  - Machine-verified actual git porcelain statuses: 8 tracked modified files strictly `" M"` (unstaged in working tree), 15 untracked files strictly `"??"`.
  - Added 22 read-only dependencies (8 `" M"`, 14 `"clean"`) and 3 assurance metadata files.
  - Explicitly excluded roadmap slices `2026-09-12-b1-implementation.md`, `2026-09-12-b2-implementation.md`, and `2026-09-12-u1-e1-implementation.md` as non-D1 scope.
  - Full file bytes bound for `README.md` (`f8d8ebaf...`) and `CHANGELOG.md` (`c1d04007...`) with explicit hunk ownership documented.
  - Excluded `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md`, `D1_DRAFT_INVENTORY_CANDIDATE2.json`, and `D1_DRAFT_PACKET_CANDIDATE2.md` as **Assurance Metadata** to prevent circular hash invalidation.
  - Formal candidate freezing deferred to immediately prior to Call 2 reservation.
- **A2 — Packet Identity & Coordination Completeness:** **`draft-prepared / reservation-open`**
  - Reconciled draft packet: [docs/readiness/D1_DRAFT_PACKET_CANDIDATE2.md](file:///Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/docs/readiness/D1_DRAFT_PACKET_CANDIDATE2.md) (`sha256:52e0500ea2207d26ea1663e8d49bfe55fd6d979796819d0a6d05013faaf19042`).
  - Draft packet identifier: `packet:lingualens-assessment-v2-desktop-stage1:gen0:candidate-2-draft`.
  - Atomic coordination primitive documented: `mkdir reviewer.lock` / `rmdir`.
  - Honest pending status: All post-reservation fields (`activeReservation`, `attemptId`, `reviewerAgentId`, `rolloutPath`, `rolloutSha256`, `reportSha256`) explicitly marked `pending-reservation` (zero fabricated data).
- **A3 — TDD Evidence Reconciliation:** **`reconciled / gaps-preserved`**
  - Recomputed and bound full SHA-256 hashes directly from on-disk log files across all 18 receipts with exact absolute paths.
  - Recorded exact command provenance and exit codes (explicitly marking `unavailable in log wrapper` where not recorded, eliminating false inferences).
  - Separated signature/setup errors (`TypeError` missing `request_id` in `b1_corrective_red`) from behavioral export dialog failure (`b1_corrective_red` opening save-as dialogs in V2 mode).
  - Separated error-row selection detail API invocation (`assert '_error' not in ['_error']` in `b5_regression_red`) from silent empty list failure (`b5_tdd_red`).
  - Classified post-edit GREEN receipts as **Historical Process Evidence / Unproven Binding** (not current green gates).
  - Defined exact scope and limitations of the 319-pass suite (`b2_residual_regression_suite_20260913.log`), noting it does NOT constitute full D1 readiness.
  - *Crucial Boundary:* Accurately classifying and inventorying historical TDD gaps does NOT mean the gaps are filled; that limitation remains for the parent readiness decision.
- **A4 — Parity Specification Alignment:** **`reconciled / callers-verified`**
  - Audited and updated [docs/readiness/GUI_TUI_V2_PARITY.md](file:///Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/docs/readiness/GUI_TUI_V2_PARITY.md) (`sha256:acf316b336a4bb3930df754ab3543eff9c0d9c89938a3541eadaa4d594178a24`).
  - Removed non-existent function names (`_load_assessments_for_child`, `_load_consent_status_for_child`) and aligned with actual callers (`_refresh_assessments`, `_refresh_consent`).
  - Verified TUI assessment listing and detail inspection remain clearly separated as **Unsupported / No Caller in TUI Stage 1**.
  - Documented reproducible draft consistency check results in [docs/readiness/D1_DRAFT_CONSISTENCY_CHECK.md](file:///Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/docs/readiness/D1_DRAFT_CONSISTENCY_CHECK.md) (`sha256:4b396d1b9a70609ea21fbaf291bb777939c5b886cca83ec87e3886b758ad30f2`).

### 2. Verified Candidate Inventory (23 files)
Detailed manifest: [docs/readiness/D1_DRAFT_INVENTORY_CANDIDATE2.json](file:///Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/docs/readiness/D1_DRAFT_INVENTORY_CANDIDATE2.json) (`sha256:d8ce58460f7d3916b23d8177b5093e5e4ee0bc2217d11958f60a6f88956f9d28`)

- **Production Source (5 files):**
  - `packages/gui/app.py` (259,872 bytes | `sha256:ca0727ae3f425b33485dd797b6c2bd450c164d6093f5000ac9ba3cd73d76936d` | git: `" M"`)
  - `packages/tui/client.py` (64,115 bytes | `sha256:1497c84219e8a71d01022e6ebbb06e3dbc02bca35fdc8cb46dbc56fd8287aa5a` | git: `" M"`)
  - `packages/tui/ui.py` (10,458 bytes | `sha256:396fba0cf8907cda83216fa4fe6a6ead996431736125ba4e6c932277613d0bb8` | git: `" M"`)
  - `packages/tui/workflow.py` (42,482 bytes | `sha256:1f9d17c0a5117b63ce1b41636461de2147b584f67257e611c4591949eb98b152` | git: `" M"`)
  - `packages/tui/validation.py` (6,315 bytes | `sha256:48b2b7ca30369bca7fa4fe8053d1ef849558c403f980329b2e399b2afe9da5d2` | git: `"??"`)
- **Test Suites (11 files):**
  - `tests/test_gui.py` (135,324 bytes | `sha256:4f24c4c628390b49708678b521607088e8b056d865b2e9e08aefcb181a7b0435` | git: `" M"`)
  - `tests/test_tui.py` (45,979 bytes | `sha256:cf00a3ac2fb951073f4089ccf975fc8f64a6c3e9c6e4e6830a043d91f8d730c4` | git: `" M"`)
  - `tests/test_tui_canonical_integration.py` (15,874 bytes | `sha256:77477e4a1bc7e8401f3557cb157be06eb83b58949a36958c2a243d84393b8add` | git: `"??"`)
  - `tests/test_tui_transport.py` (29,534 bytes | `sha256:40b0463b9d684df750105e1f04cc9dda3b7c3c5ce83f9718db4d19c2f13af5c3` | git: `"??"`)
  - `tests/test_tui_legacy_b4_contract.py` (6,519 bytes | `sha256:ba8b42b6a5a80652f2440074ffd6ff9c33cac2e27f7d9e8e8494e6027a22d8ab` | git: `"??"`)
  - `tests/test_tui_legacy_b3a_contract.py` (11,617 bytes | `sha256:a16a89f4a1adefaf4364b5186c81e88910077babb3e8842bc47a777dd0b83f8e` | git: `"??"`)
  - `tests/test_gui_b3b_error_boundary.py` (18,592 bytes | `sha256:75942d5eaed46a20a61c9a5c2a801a44e4842e5c18167c4798b8751ff21dc322` | git: `"??"`)
  - `tests/test_gui_b5_assessment_list.py` (18,662 bytes | `sha256:c1fb4efef40931cebc5c134f98585afd8a68f3e2318fba7c69f999743beb24fe` | git: `"??"`)
  - `tests/test_canonical_v2_b6_constraints.py` (30,007 bytes | `sha256:211f20ca801b39f7789e2dd9a7fdf6ae30691904b1c88f7441e8181e5be32048` | git: `"??"`)
  - `tests/test_gui_tui_b1_context_isolation.py` (22,946 bytes | `sha256:bb0b9ca73676aa01febd20e5b735cca930cd2922a3aea85982de9187ea7f0f99` | git: `"??"`)
  - `tests/test_gui_tui_b2_auth_cleanup.py` (27,537 bytes | `sha256:c8858cc1e2e90aa0bf61aba1caa4e521eafef8608f7de882f4f17c3cff6508a4` | git: `"??"`)
- **Documentation & Parity Specs (5 files):**
  - `docs/readiness/GUI_TUI_V2_PARITY.md` (35,474 bytes | `sha256:acf316b336a4bb3930df754ab3543eff9c0d9c89938a3541eadaa4d594178a24` | git: `"??"`)
  - `docs/superpowers/plans/2026-09-12-antigravity-d1-r1-continuation.md` (14,422 bytes | `sha256:35a705abcf23502f62aa57be3e683bb7a199852fc9330c6665c870c2d9ffb40d` | git: `"??"`)
  - `docs/superpowers/plans/2026-09-12-d1-auth-session-implementation.md` (6,777 bytes | `sha256:37f571c764ec5b7df951c95e5e3c7ea6de81b41fa4c043533a223cd2ca971922` | git: `"??"`)
  - `docs/superpowers/plans/2026-09-12-d1-failure-boundary-implementation.md` (6,643 bytes | `sha256:adddc892210df3d62364729e71c0161e044a2aa46f68e412ca9d1ca958ed3378` | git: `"??"`)
  - `docs/superpowers/plans/2026-09-12-stage1-desktop-consumer-implementation.md` (18,592 bytes | `sha256:9270f70efda2a5f97135fd2bce039204ade51fe072acf8d86f8092b1d1aaad30` | git: `"??"`)
- **Repository Docs with D1 Hunk Ownership (2 files):**
  - `README.md` (30,984 bytes | `sha256:f8d8ebaf661fe9e05b203d22e6ab2a21ff324a65853142e42a111b91e5d57fd6`, D1 hunk: lines 382-390 | git: `" M"`)
  - `CHANGELOG.md` (17,837 bytes | `sha256:c1d04007f84e78fe2b001a46a171a12ffd55e5f651398029ec0d04909ca11d5e`, D1 hunk: lines 6-14 | git: `" M"`)
- **Bound Read-Only Dependencies (22 files):**
  - Reference: `.local/verification/antigravity-d1/dependency_snapshot.json` (Snapshot digest: `sha256:b8eae347...`, all 22 verified matching on disk).
- **Assurance Metadata (3 files):**
  - `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` (role: mutable working journal)
  - `docs/readiness/D1_DRAFT_INVENTORY_CANDIDATE2.json` (role: draft candidate inventory)
  - `docs/readiness/D1_DRAFT_PACKET_CANDIDATE2.md` (role: draft reviewer packet)

### 3. Readiness Gap & Runtime Platform Proof Analysis
- **Call 1 Runtime Mismatch Root Cause:**
  - `extract_child_runtime.py` failed with `agent path mismatch: expected '/Users/porschecaa/.codex/agents/solweaver-reviewer.toml', got None` and observed cwd was root `/Users/porschecaa/lingualens` instead of continuation worktree.
- **Unresolved Platform Gate:**
  - Platform capability to run an authentic child session with valid `observedAgentPath` and worktree cwd remains unproven.
  - Editing local TOML does not solve this telemetry reporting gap.
  - No call budget or reviewer probe may be consumed to test this capability.
  - **Verdict:** Platform runtime gate remains **UNRESOLVED / OPEN**.

- **Next Smallest Task:**
  - Await authentic Codex execution environment capability to establish valid subagent telemetry (`agent_path` and `cwd`) before conducting Candidate 2 pre-reservation freeze.

---

## [HISTORICAL & SUPERSEDED BY CALL 1] Cumulative D1 Stage 1 Verification & Assurance Readiness (Pre-Reservation Snapshot)
> [!NOTE]
> This section records the pre-reservation state snapshot prior to Call 1. On 2026-09-13, Call 1 was reserved and executed, returning verdict `fix-first` with runtime binding mismatch (`calls used: 1/3`, `remaining: 2`, `REVIEW_READY: no`). The records below are preserved authentically as historical process evidence and are superseded by the Call 1 completion record and subsequent focused closures (B4, B3a, B3b).

- **Historical Status:** ready-for-review (candidate-ready; dependency snapshot & receipt reconciliation closed; machine readiness verified; reviewer reservation deferred to next round)
- **Assurance Unit ID:** `lingualens/assessment-v2/desktop-stage1`
- **Unit Status:** `open` (Solweaver pre-reservation state machine)
- **Reopen Generation:** `0`
- **Review Budget State:**
  - `MAX_REVIEW_CALLS:` 3
  - `REVIEW_CALLS_USED:` 0
  - `ACTIVE_REVIEW_RESERVATION:` none
- **Frozen Candidate ID:** `sha256:478c6b3828ac1b1b5b189431d7d18852fa4f16f47926a431ef0c9b732e8e8daa` (computed via canonical Solweaver recipe over 13 candidate paths)
- **Deterministic Dependency Snapshot:**
  - File: `.local/verification/antigravity-d1/dependency_snapshot.json` (SHA-256: `623ec708bf917f10e3d2cbe2a580cc2bd31dbfef5412cf10ea404488bc7a888c`)
  - Snapshot Digest: `sha256:b8eae3475ba3b067a6bd910a1f0dcebb38c61875db1baa12fa3d1e1e56905596`
  - Bound Scope: 22 shared read-only dependencies (canonical API routes/schemas/services/domain/dependencies/repositories, runtime CHAT parser, clinical report template, pytest configs, requirements, and D1 repository regression test).
  - Dirty Dependencies: Bound by exact content SHA-256 (not git HEAD).
  - Delivery Artifact Manifest: Justified as `not-applicable` (pure in-tree Python source candidate executed directly in virtualenv; no separate distribution bundle delivered).
- **Machine Readiness Proof:**
  - Proof File: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/final-strict-readiness-proof.json` (SHA-256: `2824b9a70961aaa37fac81bec7a025898080b654a654c3d300476ef7a76ca030`)
  - Readiness Record: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/final-strict-readiness.json` (SHA-256: `9e8825cf20d11f50e60de4ae72b02d8690d9e6ba16ef50c6dd510c2514dfce6b`)
  - Candidate Manifest: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/candidate-manifest.json` (SHA-256: `16b314053a5b4566070196383acf3ce38368aa4b876e580c8f2d03a108b19f3a`)
  - Ledger: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/ledger.md` (SHA-256: `bf77cb2c5da009df34b90502c40925dc2d7cee6d55d70caa8dbf7a13a8722708`)
  - Reviewer Packet: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/reviewer-packet.md` (SHA-256: `3c7accb0e47847ad42e8bccb984f189c0fa43d17e1e2e35980e047deb46db65e`)
  - Attempt Journal: `.git/solweaver/lingualens-assessment-v2-desktop-stage1/attempts.json` (SHA-256: `f71d4208243c929ff6fc9ee6e0eaf916c094898cfa4539d0d07228e0290417c8`)
  - Validation Tool: `python3 /Users/porschecaa/.agents/skills/solweaver/scripts/validate_final_strict_packet.py` (Exit Code: 0, `readinessGate: pass`)
- **Receipt Reconciliation & Verification Evidence:**
  - Current Combined Client Gate: `.local/verification/antigravity-d1/current_client_suite_189_pass.log` (SHA-256: `51020bc591dbe5ad369f259d93f520afa502daafcf157c3b833085cc621d9505`, exit code: 0, 189 passed in 26.55s).
  - Current D1 Applicable Backend Gate: `.local/verification/antigravity-d1/current_backend_d1_applicable_gate.log` (SHA-256: `50e1518b6cf816dcfbb033d59acf60acf106ac13de01eda21dce7bd85d2123ed`, exit code: 0, 55 passed in 3.02s).
  - Historical 189-pass Client Receipt: `.local/verification/antigravity-d1/subtask_c_cancellation_and_selection_green.log` (SHA-256: `3af059fd082c5423daaa0f7409ad8f99769a29a2c28f1d5ebfc7c5f5360a7bfc`), classified as process evidence.
  - Historical 433-pass Backend Receipt: `.local/verification/antigravity-d1/backend_v2_regression_subtask_c_closure.log` (SHA-256: `c0d3dea776e8b22a92ea81f354fd9a90ba8e645cd1957479c140dd5cc8f6efba`), classified as unproven point-in-time binding and retained as process evidence.
- **Reviewer Capability Analysis:**
  - `solweaver_reviewer` configuration inspected at `/Users/porschecaa/.codex/agents/solweaver-reviewer.toml`.
  - Required runtime: OpenAI Codex child agent with model `gpt-5.6-sol` and reasoning effort `max`.
  - Current Antigravity IDE environment does not support Codex child subagents or rollout `turn_context` inspection; reservation and Call 1 must be executed via the authentic Codex channel.
- **Next Smallest Task:**
  - Perform atomic reservation (`mkdir reviewer.lock`) and dispatch Call 1 independent review for assurance unit `lingualens/assessment-v2/desktop-stage1`.

---

## D1 Parent Readiness Review & Candidate 2 Preparation Audit (2026-09-13 15:52:17 UTC)

- **Status:** Candidate 2 prepared / Parent acceptance & adversarial audit completed; **STOPPED BEFORE REVIEWER RESERVATION / CALL 2**.
- **1. Parent Acceptance Decision:**
  - **TUI Assessment List/Detail Exclusion:** Fully audited against approved Stage 1 plan (`docs/superpowers/plans/2026-09-12-stage1-desktop-consumer-implementation.md`, Table line 39 & Task C lines 164-320). Confirmed that TUI Stage 1 approved scope is strictly child intake menu, consent status/grant wizard, assessment creation wizard, and main error loop recovery. TUI assessment list and detail inspection were deliberately excluded from Stage 1 scope. GUI implements full assessment listing (`tree_assessments`).
  - **Historical TDD Gaps:** Audited per Solweaver skill. Pre-Call-1 TDD gaps remain preserved as permanent historical limitations for parent readiness decision; no retroactive REDs fabricated or claimed filled. All post-Call-1 findings B1-B6 have verifiable RED and GREEN receipts on disk.
  - **Behavioral Blocker Identification:** Full candidate gate run against all 11 test files uncovered a behavior contract discrepancy in `tests/test_tui_canonical_integration.py::test_canonical_validation_error_422`: test expects HTTP 422 string from `LinguaLensApiError`, but client input validation in `packages/tui/client.py` and `packages/tui/validation.py` intercepts invalid birth month client-side and raises `LinguaLensValidationError("birth_month must be between 1 and 12")` with zero HTTP dispatch. Stopping before freeze/full gates to report this exact behavioral gap.
- **2. Draft Consistency Reconciliation:**
  - Verified exact test files in `b2_residual_regression_suite_20260913.log`: exactly 10 test files (319 passed), not 11 (`tests/test_tui_canonical_integration.py` was omitted from that run).
  - Uncovered 23rd read-only dependency via AST import audit: `apps/api/app/schemas/clinical.py` (34,420 B | `sha256:8a1e40b2...`), imported by `tests/test_tui_legacy_b3a_contract.py` and `tests/test_tui_legacy_b4_contract.py`.
  - Added `docs/readiness/D1_DRAFT_CONSISTENCY_CHECK.md` (4th assurance metadata file).
  - Preserved Call 1 artifacts in `.git/solweaver/lingualens-assessment-v2-desktop-stage1/` with zero overwrites.
- **3. Parent Adversarial Pass:**
  - Mapped risk surfaces: auth-session identity, cancellation, late workers, busy ownership, mode transitions, residual displays, mock/live constraints, error-row selection.
  - Executed focused counterexample suites: 138 passed in 8.18s across 7 focused risk suites.
- **4. Candidate 2 Manifest:**
  - Prepared versioned Candidate 2 manifest (`docs/readiness/D1_CANDIDATE2_MANIFEST.json`) using canonical recipe (`sha256:f9c7feed15661d71f5c72a8ab4095efb35cfa56c5de772286d52385698a6d0db`).
  - Separated `FROZEN_CANDIDATE_ID` from `ASSURANCE_PACKET_ID`.
- **5. Gate Receipts & Platform Gate:**
  - Receipt recorded at `.local/verification/antigravity-d1/candidate2_full_gate_20260913.log`.
  - Candidate test suite: 326 passed, 1 failed (`test_canonical_validation_error_422`) in 19.97s.
  - Backend gate: 1 passed (consent sequence isolation) in 2.58s.
  - Runtime platform gate (`observedAgentPath` / worktree cwd execution) remains **OPEN**.
- **Strict Guardrails Preserved:**
  - Review budget: 1/3 used, 2 remaining.
  - Active reservation: `none`.
  - `REVIEW_READY: no`.
  - Zero reviewer probes or Call 2 dispatches.
  - Worktree, branch, terminal unit A2, and Stage 2 untouched.

---

## D1 Validation Integration-Test Reconciliation (2026-09-13 16:17:20 UTC)

- **Status:** Focused integration tests reconciled and passing; **REQUIRES CANDIDATE REFREEZE**; stopped before Call 2 reservation.
- **Contract Split in `tests/test_tui_canonical_integration.py`:**
  - Retired ambiguous test `test_canonical_validation_error_422`.
  - Added Contract 1: `test_client_create_child_validation_error_fails_closed_zero_dispatch`:
    - Tests `client.create_child(..., birth_month=13)`.
    - Proves `LinguaLensValidationError` is raised specifically with message `"birth_month must be between 1 and 12"`.
    - Proves zero transport dispatch (`http_calls == 0`).
    - Proves mock data and backend service state remain unmutated (`children == 0`).
  - Added Contract 2: `test_canonical_backend_validation_error_422_rejection`:
    - Dispatches malformed payload directly through `client._http_request("POST", "/api/v2/children", ...)`, bypassing public client validator.
    - Proves FastAPI route returns HTTP 422, mapped to `LinguaLensApiError` containing `"422"`.
    - Proves zero child created in backend service / repository state (`len(service.children) == initial_service_children`).
- **Focused Verification Evidence:**
  - `tests/test_tui_canonical_integration.py`: 9/9 passed in 2.78s (exit code: 0).
  - `tests/test_canonical_v2_b6_constraints.py`: 81/81 passed in 2.20s (exit code: 0).
  - Total focused suite: 90 passed, 0 failed.
  - Receipt: `.local/verification/antigravity-d1/validation_integration_reconciliation_20260913.log` (SHA-256: `cff2bb25d92cd6275ec46bf6493a51a197398e2eeb3196fbeed1d8646f704b26`).
- **Candidate & Metadata Status:**
  - Previous Candidate 2 manifest (`docs/readiness/D1_CANDIDATE2_MANIFEST.json`, `sha256:f9c7feed...`) and failed receipt `.local/verification/antigravity-d1/candidate2_full_gate_20260913.log` are preserved as authentic historical records and NOT overwritten.
  - Current candidate state requires refreeze (candidate hash changed due to `tests/test_tui_canonical_integration.py` update from 15,874 bytes to 17,870 bytes, `sha256:8cfffaf0...`).
  - Backend gate note: `apps/api/tests/assessment_v2/` run with `-k test_consent_versioning_per_purpose_sequence_and_child_isolation` ran 1 test and deselected 54 because of the `-k` filter; full applicable backend gate profile needs reconciliation before refreeze.
- **Strict Guardrails Preserved:**
  - D1 remains OPEN.
  - Review budget: 1/3 used, 2 remaining.
  - Active reservation: `none`.
  - `REVIEW_READY: no`.
  - Zero reviewer probes or Call 2 dispatches.

---

## D1 Candidate Refreeze & Full Applicable Verification Gates Run (2026-09-13 16:38:13 UTC)

- **Status:** Candidate 2 Refreeze manifest created; Full applicable client and backend gates **PASSED (100%)**; **STOPPED BEFORE REVIEWER RESERVATION / CALL 2**.
- **1. Preflight & Verification Profile:**
  - Full client gate: 11 candidate test files (328 test items).
  - Full applicable backend gate: 4 files (`test_routes.py`, `test_schemas.py`, `test_services.py`, `test_repository.py`: 55 test items) run in full without `-k` filter.
  - Exclusions rationale: Audio/capture (`test_capture_*.py`), segment review (`test_segment_*.py`), longitudinal (`test_longitudinal_*.py`), and web/Compose tests were excluded because they belong to Stage 2 / web consumer layers outside the approved Stage 1 desktop consumer boundary.
- **2. Candidate Refreeze Manifest:**
  - Manifest path: `docs/readiness/D1_CANDIDATE2_REFREEZE_MANIFEST.json`
  - Frozen Candidate ID: `sha256:4076c39d5d7e8063423c3512f4c960d54f3ea8c6caec4fa70382ac892242a651`
  - Predecessor Candidate ID (`sha256:f9c7feed15661d71f5c72a8ab4095efb35cfa56c5de772286d52385698a6d0db`) and predecessor failed receipt (`candidate2_full_gate_20260913.log`) are strictly preserved as historical records.
- **3. Gate Execution & Receipt:**
  - Test Execution Interpreter: `.venv/bin/python` (Python 3.12.14, pytest 9.1.1).
  - Client Gate: **328 passed** in 36.00s (Exit code: 0).
  - Backend Gate: **55 passed** in 3.55s (Exit code: 0).
  - Pre/Post Source and Dependency Hashes: **100% match (0 mutations during run)**.
  - Receipt path: `.local/verification/antigravity-d1/candidate2_refreeze_full_gate_20260913.log` (SHA-256: `ae2ea0a5e0796ccf47e6fbee5ea560ce82b413845103711dc3cad8568e307b7e`).
- **4. Readiness Handoff Discipline:**
  - Candidate gates: **PASSED (328 client + 55 backend = 383 tests passed)**.
  - Parent adversarial readiness: **PASSED (138 counterexample tests passed)**.
  - Historical assurance gaps: **Documented & Visible** (pre-Call-1 TDD gaps preserved as known limitations; B1-B6 verified).
  - Platform runtime binding gate: **REMAINS OPEN** (Call 1 platform runner execution for `observedAgentPath` / worktree cwd is unproven).
  - Canonical final-strict readiness: **NOT READY / NOT CLAIMED**.
- **Strict Guardrails Preserved:**
  - D1 remains OPEN.
  - Review budget: 1/3 used, 2 remaining.
  - Active reservation: `none`.
  - `REVIEW_READY: no`.
  - Zero reviewer probes or Call 2 dispatches.
  - Worktree, branch, terminal unit A2, and Stage 2 untouched.

---

## D1 Immutable Verification Evidence Closure (2026-09-13 17:06:12 UTC)

- **Status:** Complete contemporaneous immutable verification bundle created; **STOPPED BEFORE REVIEWER RESERVATION / CALL 2**.
- **1. Prior Evidence Audit:**
  - Audited existing verification receipts: confirmed that prior receipt `.local/verification/antigravity-d1/candidate2_refreeze_full_gate_20260913.log` was an authentic GREEN execution that proved candidate stability, but lacked contemporaneous sidecar snapshots of explicit package pins and 46-file hash records. Classified as historical green execution with incomplete binding.
  - Prior receipts and predecessor manifests (`D1_CANDIDATE2_MANIFEST.json`) preserved without overwriting.
- **2. Contemporaneous Verification Bundle:**
  - Bundle Directory: `.local/verification/antigravity-d1/bundle_candidate2_refreeze_20260914`
  - Bundle Index: `BUNDLE_INDEX.json` (SHA-256: `54dc460cc606fda789622042025e75ca091b4f4a2ef67f4f52401a824fdef3df`)
  - Bound Frozen Candidate ID: `sha256:4076c39d5d7e8063423c3512f4c960d54f3ea8c6caec4fa70382ac892242a651`
  - Manifest Hash: `9b80eebbaea051d4434358e9ab4393a1d84a1803c2cfaa0c9435c999c7aca6a9`
  - Artifacts:
    - Pre-run file snapshot (46 records): `pre_run_source_snapshot.json` (SHA-256: `34729397b16ee36229e760ef8880ab263d5340f67092447d3bef50285c6eb65e`)
    - Post-run file snapshot (46 records): `post_run_source_snapshot.json` (SHA-256: `6f6876b1d2727e8690de810f8a789bfb632109996de1779e0b52eda7f4ab8dac`)
    - Environment pins (43 frozen packages, git branch/HEAD, interpreter): `environment_pins.json` (SHA-256: `9d85e9561f96255f2517c2f6e9931c1081f57627428fe44234ce42f6eb1ce59b`)
    - Gate execution receipt: `gate_execution_receipt.log` (SHA-256: `7e826578300e6c473d1185020252fd8d37ab59bd893c6d579efc41d5c091349d`)
- **3. Test Results:**
  - Gate 1 (Client Candidate Test Suite, 11 files, 328 items): **328 passed** in 57.84s (Exit code: 0).
  - Gate 2 (Applicable Backend Stage 1 Suite, 4 files, 55 items, full without -k): **55 passed** in 9.74s (Exit code: 0).
  - Total: **383 passed (100%)**, 0 failures, 0 errors.
  - Source stability: **STABLE (0 mutations across all 46 files during run)**.
- **4. Readiness Handoff Discipline:**
  - Candidate verification evidence: **FULLY BOUND & CONTEMPORANEOUSLY VERIFIED**.
  - Historical assurance gaps: **DOCUMENTED** (pre-Call-1 TDD gaps preserved as known limitations; B1-B6 verified).
  - Platform runtime binding gate: **REMAINS OPEN** (Call 1 platform runner execution for `observedAgentPath` / worktree cwd is unproven).
  - Canonical final-strict readiness: **NOT READY / NOT CLAIMED**.
  - Next Action: Submit runtime capability audit to actual Codex runner for read-only evaluation.
- **Strict Guardrails Preserved:**
  - D1 remains OPEN.
  - Review budget: 1/3 used, 2 remaining.
  - Active reservation: `none`.
  - `REVIEW_READY: no`.
  - Zero reviewer probes or Call 2 dispatches.
  - Worktree, branch, terminal unit A2, and Stage 2 untouched.
