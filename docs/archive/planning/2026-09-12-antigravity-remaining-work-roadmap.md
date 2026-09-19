# LinguaLens Remaining Work and Antigravity Handoff Plan

> **For agentic workers:** Use the repository's `writing-plans` and `executing-plans` skills for each implementation slice when available. This is the master delivery plan; expand each slice into a code-level plan after inspecting its actual baseline. Track progress with the checkboxes below. The owner has selected Antigravity as the next executor.

**Goal:** Complete the assessment-centred research prototype: guided recording, reviewed evidence, developmental profiles, comparable follow-up, clinician decisions and signed reports, with Web/GUI/TUI consuming FastAPI.

**Architecture:** Extend the existing Assessment V2 in `apps/api/app/assessment_v2` and the primary Next.js app. Supabase supplies identity, PostgreSQL and private storage; FastAPI owns clinical policy and state. Preserve research libraries and existing GUI/TUI, and reuse versioned adapters rather than duplicating extraction or client-side clinical logic.

**Tech Stack:** Next.js/React/TypeScript, FastAPI/Pydantic/SQLAlchemy/Alembic, PostgreSQL/Supabase, Python venv/pip, npm, pytest/Vitest/Playwright, Figma. Native local development; Docker is not required.

## 1. Read this before starting

Prepared 2026-09-12 from local files and worktree inventory. Test counts below are historical receipts, not fresh test runs in this planning task. Research implications are inherited from the approved spec; this task did not reread or independently validate all selected PDFs.

| Item | Observed state | Consequence |
|---|---|---|
| Main folder | `/Users/porschecaa/lingualens`, branch `codex/ml-workflow-hardening`, HEAD `a60aa2df`, numerous existing modifications | Do not treat it as the A2 baseline or stage its changes wholesale |
| A2 worktree | `/Users/porschecaa/lingualens/.worktrees/assessment-v2-segment-review`, branch `codex/assessment-v2-segment-review`, HEAD `5fb37457167b079d63d5ffe10d63a1cd2cd88706` | A2 implementation is uncommitted; checking out its branch from HEAD alone loses A2 changes |
| A2 candidate | 51 files; frozen ID `sha256:19f144e944e768982412cec31397b3e7bb62ac9241dc66a9a9f43fb646304ef3` | Preserve the original candidate and its review history |
| A2 assurance | `parent-completed`, `review-exhausted`, `final-strict-not-achieved` | No fourth review or new label to reset this unit; historical RED evidence missing for three fixes |
| Figma | Manifest says working skeleton; acceptance/export pending | Local frame specifications do not prove the remote prototype is complete |
| GUI/TUI | Existing `packages/gui/app.py`, `packages/tui/client.py`, `workflow.py`, `ui.py` | Retained, but final V2 parity is future work |
| Feature/domain model | Existing `evidence.py`, `MeasuredFeature`, `DomainProfile`, versioned provenance | Extend existing contracts; do not rebuild them from zero |

A2 historic verification: Assessment V2 382 tests, core 1,195, frontend 545, native PostgreSQL 10, one isolated Playwright smoke, typecheck/build and lint with an existing warning. Previous frontend audit recorded 8 advisories, including high/critical; recheck before using those numbers as current evidence. Software tests do not establish clinical validation.

The two source-of-truth files differ across branches. Read both, then reconcile against the intended integration base. In particular, the main checkout correctly describes `check_project.sh` as a focused local gate, while the A2 copy calls it full verification. Use actual CI/package scripts for the complete candidate gate. Never replace the main source-of-truth file wholesale with the older A2 copy.

## 2. Target user journey and completion boundary

Select child → confirm purpose/protocol/consent → record guided activity → review uncertain transcript segments → inspect feature/domain evidence and comparable history → document clinician decision → review/sign/export report → plan follow-up.

Clinical concern, measured change and clinician-authored diagnosis are separate fields and views. Concurrent language, speech-production, social-communication and other developmental concerns are allowed. Missing evidence is not a normal result. Automated ASD probabilities, diagnosis, or invented reference thresholds remain outside this project scope.

“Complete prototype” means the full workflow, all three client contracts, test evidence and reproducible research documentation work with synthetic data. “Pilot ready” additionally requires real managed-environment evidence and therapist usability checks. Clinical validation is a separate research programme and cannot be declared complete by implementation.

## 3. Dependency and priority map

| Order | Slice | Depends on | Deliverable |
|---|---|---|---|
| 0 | P0 baseline and handoff | None | Verified A2 inventory, integration strategy, resumable progress file |
| 1 | U1 Figma and therapist flow | P0 | Complete prototype, error branches, accessible states, exports and acceptance record |
| 2 | E1 evidence completeness | P0; U1 before new therapist UI | Structured observations/instruments and verified feature capabilities |
| 3 | B1 comparison contract | P0 + E1 feature/context inventory | Explicit per-feature compatibility and interpretation policy |
| 4 | B2 longitudinal API/persistence | B1 | Auditable same-child comparisons with stale/incompatible handling |
| 5 | B3 longitudinal UI | B2 + accepted U1 frames | History, pair selection, values/limitations and evidence drill-down |
| 6 | C1 attention and clinician review | E1 + B1; consume B2 where available | Reviewable non-exclusive cues and clinician-authored disposition |
| 7 | C2 reports/sign-off | C1 + B2 | Versioned draft, readiness gates, immutable signed export and amendment |
| 8 | D1 GUI/TUI parity | Stable E/B/C API contracts | Shared behaviour, explicit offline errors, no silent mock fallback |
| 9 | R1 native/package/dependency readiness | Starts after P0, closes after D1 | Reproducible supported runtime and resolved release audit gate |
| 10 | S1 managed Supabase rehearsal | R1 + complete backend candidate | Real tenant/auth/storage/worker/restore evidence in authorized staging |
| 11 | V1 therapist pilot and research package | U1 + C2 + S1 | Observed usability, reproducible experiment/report package and pilot decision |

Do not split B and C into simultaneous writes to the same routes/models/repositories. U1 design, research inventory, and R1 investigation may proceed independently. Use focused modules for new concerns; avoid turning `services.py` or `db/repositories.py` into an even larger all-domain implementation.

## 4. P0 — Make the starting point reproducible

Files to read: both `AGENTS.md` and `docs/PROJECT_SOURCE_OF_TRUTH.md`; A2 `docs/plans/2026-09-09-assessment-v2-segment-review.md`; original redesign spec; `.git/solweaver/lingualens-assessment-v2-segment-review/{ledger.md,attempts.json,candidate-manifest.json}`. Resolve the common Git directory with `git rev-parse --git-common-dir`.

- [ ] Run `git worktree list`, and `git status --porcelain=v1 --untracked-files=all` plus `git rev-parse HEAD` in each relevant worktree.
- [ ] Recompute all A2 manifest file hashes and the manifest's recorded identity recipe; list new divergence separately.
- [ ] Record the existing root ML changes as another workstream. Inspect its `docs/DATA_INVENTORY_AND_ML_ROADMAP.md` before proposing overlapping extractor work; preserve raw data and existing edits.
- [ ] Create a separate continuation workspace using a verified tracked/untracked source snapshot or an authorized checkpoint. Do not copy credentials, private records, caches or dependency directories. Do not assume a worktree created from A2 HEAD contains its uncommitted work.
- [ ] Record the snapshot provenance and chosen integration base in `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` in that continuation workspace. Keep the frozen A2 workspace untouched.
- [ ] Carry A2's terminal limitation forward. Release/merge of that candidate requires the exact owner acceptance specified by AGENTS; a general “continue” is not a substitute. New independent slices may have their own assurance units but cannot erase A2 history.

Acceptance: a newcomer can locate all A2 files, reproduce the source snapshot and explain which branch owns each change without overwriting the root workstream. P0 is operations/docs-only; no retroactive TDD claim is needed.

## 5. U1 — Finish the design artifact

Read `docs/ux/therapist-workflow/{task-model.md,evidence-matrix.md,frame-inventory.csv,prototype-scenarios.md,api-screen-contract-map.md,figma-delivery-manifest.md,usability-protocol.md}` and the Figma plan in `docs/superpowers/plans/2026-09-06-therapist-ux-figma-prototype.md`.

- [ ] Inventory the current Figma file from the manifest when authenticated access is available. Treat recorded quota/account restrictions as historical until checked.
- [ ] Map all five workflow steps and new B/C views to named frames; include no-history, incompatible comparison, unavailable audio, consent withdrawal, stale edits, conflicting evidence and report-not-ready states.
- [ ] Finish low/high fidelity flows and clickable links; support keyboard navigation, legible Thai text, focus/error feedback and small screens.
- [ ] Have the therapist-facing design reviewed, record actual feedback and iteration; do not fabricate participant observations.
- [ ] Export the required synthetic-data figures and record frame IDs, version/date, file hashes and acceptance in the manifest.

Acceptance: all required prototype paths can be walked through and artifacts exist. If Figma is unavailable, prepare local wireframes and an exact node/edit/export checklist, mark remote delivery blocked, and continue backend work. New therapist UI waits for its design acceptance.

## 6. E1 — Complete inputs and identify what is actually measurable

Existing anchors: `evidence.py`, `evidence_adapter.py`, `reviewed_transcript_worker.py`, `quality.py`, `protocols.py`, `packages/features/transcript_features.py`. Proposed focused modules: `observations.py`, `instruments.py`, and corresponding `*_repository.py` under Assessment V2. Migration names/numbers must follow the actual head, not a guessed `0010`.

- [ ] Inventory every existing feature: definition/unit, input, extractor/schema/tokenizer version, child-speaker requirement, missing state, limitations and current test.
- [ ] Write a paper-to-feature matrix under `docs/research/feature-evidence-matrix.md`: local PDF key/page, population/language/task, measured construct, applicability and transfer limits. Read actual PDFs in `/Users/porschecaa/Desktop/Paper-ASD/`; the approved spec's shortlist is a starting point, not a substitute. Resolve the recorded `QJR8K5QS` title discrepancy from the PDF.
- [ ] Add versioned clinician/caregiver observations with source, assessment, activity/time context and immutable corrections. Amendments stale affected derived current records.
- [ ] Add generic instrument administration/response contracts. Enable named instrument content/scoring only after verifying use rights, version and applicable interpretation. Do not copy protected forms from papers into the product.
- [ ] Audit the recording-to-transcript path: identify manual and real provider capabilities. Unsupported ASR/diarization stays explicit; any provider integration must preserve consent, failure states and reviewed transcript attestation.
- [ ] Inventory acoustic/timing features against available timestamps and quality. Add only documented, reproducible adapters needed by accepted scope; otherwise return `unavailable` with reason. Transcript text alone cannot supply measured pitch or response latency.

Tests: proposed `apps/api/tests/assessment_v2/test_observations.py` and `test_instruments.py`, plus existing evidence/worker tests. Cover amendments, observer versus editor roles, cross-tenant access, withdrawal, missing channel, partial success and idempotency. Extraction tests use synthetic samples with known expected values, never real participant content.

Acceptance: the profile tells the therapist what was measured, who supplied other evidence, and what was not assessed; no domain silently claims a capability absent from the pipeline.

## 7. B1–B3 — Comparable follow-up

Proposed files: `apps/api/app/assessment_v2/longitudinal.py`, `longitudinal_repository.py`, focused schemas/routes alongside existing patterns; tests `test_longitudinal_contract.py`, `test_longitudinal_repository.py`, `test_longitudinal_routes.py`; web component `assessment-longitudinal-workspace.tsx`, client extensions and corresponding unit/E2E tests.

### B1: Contract and policy

- [ ] Write a per-feature compatibility table for same child/tenant, language, age context, activity/protocol version, speaker attribution, capture conditions, units, extractor/schema/tokenizer version and quality. Each field is required, explicitly irrelevant for that feature, or an approved conversion; unknown required fields block comparison.
- [ ] Define immutable comparison inputs: two evidence run IDs and hashes, assessment IDs, feature key, units, source values, compatibility decision/reasons, policy version and creation time. Link each evidence run to its attested source and segment provenance.
- [ ] Separate numerical change from clinical interpretation. For compatible values 10 and 12, delta is 2. Without a validated direction/meaningful-change policy, the interpretation is `indeterminate`, not automatically `improved`.
- [ ] Set percent change unavailable when baseline is zero. Missing values remain missing, not zero. Reference bands require a matching approved cohort; within-child comparison alone creates no norm.

Observable tests: compatible numeric inputs expose delta; incompatible language/protocol or required unknown context yields `not_comparable` and no trend arrow; matching values do not imply clinically `stable` without a policy; schema changes require explicit equivalence.

### B2: API and durable comparisons

- [ ] Extend existing model and migration patterns for versioned comparisons, tenant-safe references and RLS. Preserve historical evidence and signed snapshots.
- [ ] Add child assessment-history reads and comparison operations under `/api/v2`; choose final route names after inspecting existing routes, and document request/response/error examples in the slice plan before coding clients.
- [ ] Enforce same-child/tenant/care-team scope, current consent, current input eligibility and server-generated hashes. Use consistent locking and idempotent keys over both evidence identities and policy version.
- [ ] Stale affected comparisons when either source is superseded; do not rewrite their historical values. Consent loss blocks new access/processing as required by policy.
- [ ] Test reversed/duplicate pair requests, stale races, pagination/order, tenant mismatch, revoked membership, zero baseline and partially available features on native PostgreSQL.

### B3: Therapist history view

- [ ] Add an assessment history and explicit baseline/current selection. Show dates, measured values, units, deltas, quality and compatibility reasons.
- [ ] Plot only usable observations; show gaps and incompatible points without implying a continuous trend. Make chronology and selected baseline clear.
- [ ] Provide evidence drill-down and clinician notes; calculations remain server-owned. Support loading, empty, offline, stale and permission-denied states.
- [ ] Test a synthetic child with three visits including one incompatible visit, keyboard interaction, reload and responsive layout.

Acceptance: a therapist can explain both the change and why a comparison is or is not permitted. No feature change becomes an ASD severity claim.

## 8. C1–C2 — Review, decisions and reports

Proposed focused modules: `attention.py`, `clinical_review.py`, `reports.py` with repository companions inside Assessment V2. Reuse patterns from existing v1 reports, but do not route new product ownership into legacy `src` modules. Proposed UI: `assessment-clinical-review-workspace.tsx` and `assessment-report-workspace.tsx`.

### C1: Reviewable cues and disposition

- [ ] Define versioned cue records with supporting/conflicting evidence IDs, limitations and clinician review state. Rules require documented evidence and applicability; unvalidated conditions stay descriptive or request more evidence.
- [ ] Represent multiple concerns independently. Do not rank ASD and developmental delay as exclusive percentages.
- [ ] Persist clinician acknowledgement/disagreement/more-evidence requests separately from computed cues, including actor/time/rationale and concurrency version.
- [ ] Add clinician-authored disposition, follow-up plan and optional next assessment context. Evidence insufficiency must still permit a documented “collect more evidence” decision.
- [ ] Test stale cues, disagreement preservation, wrong clinician, concurrent review and missing evidence; ensure automated cues do not silently become report conclusions.

### C2: Draft → sign-off → amendment

- [ ] Generate editable drafts linked to exact evidence/comparison/review versions. Include purpose, observations, descriptive profile, comparisons, limitations, clinician action and review provenance.
- [ ] Enforce server-side readiness: current eligible inputs, required cue review, assigned authorized signer, consent and expected version. Define an explicit limited-evidence report path when appropriate; it must disclose omissions rather than fabricate completed findings.
- [ ] Store immutable signed content, hash, signer/time/version. Repeated sign requests are idempotent; post-sign edits create linked drafts. Historical exports must reproduce the signed snapshot even after later assessments.
- [ ] Support private authorized PDF export with Thai font rendering, pagination and visible limitations; secure any stored output and short-lived download grant.
- [ ] Test withdrawn consent, stale draft, concurrent sign/edit, unauthorized export, deterministic signed snapshot, amendment lineage and PDF text/layout with synthetic data.

Acceptance: therapist judgement is explicit and attributable; signatures bind exactly what was reviewed, and later input edits never rewrite an earlier signed report.

## 9. D1 — Retained GUI/TUI as thin clients

Modify `packages/gui/app.py`, `packages/tui/client.py`, `packages/tui/workflow.py`, `packages/tui/ui.py` after inspecting their actual commands and dependencies. Extract one shared Python API client only if needed; avoid two independent policy implementations.

- [ ] Inventory current GUI/TUI workflows and map supported actions to V2 contracts: assessment selection, capture/upload, review, processing status, evidence, history and clinician actions where role permits.
- [ ] Preserve intentionally local research utilities, explicitly separate them from clinical API operations.
- [ ] Implement authentication/session expiry, retry boundaries, cancellation and generic server errors; no service-role credentials in clients and no silent successful fallback on API failure.
- [ ] Run the same contract fixtures through Web, GUI and TUI adapters. Test offline/auth expiry, consent denial, stale version and processing retry, plus normal workflow parity.

Acceptance: all clinical state transitions are owned by the same FastAPI policy; client presentation may differ without changing the clinical rules.

## 10. R1 + S1 — Runtime and managed environment

- [ ] Reconcile supported Python/Node versions and native setup. Verify API and worker can import packaged analysis dependencies from the deployment working directory; no ad hoc `sys.path` duplication.
- [ ] Audit npm and Python dependencies; address current high/critical findings with bounded changes and tests. Record unresolved baseline risk honestly; do not use forced upgrades or erase audit output to pass gates.
- [ ] Verify native startup/shutdown, queue leases, retry/cancel, worker restart, port isolation, upload cleanup and a new disposable database migration to head. Keep the existing database-backed worker unless measured demand justifies more infrastructure.
- [ ] Prepare staging scripts/runbook using `docs/STAGING_TENANT_SAFETY_VERIFICATION.md`, `docs/SUPABASE_AUTH_CONTRACT.md`, `docs/PHASE1_EXTERNAL_BLOCKERS.md` and relevant backup/incident docs.
- [ ] On an explicitly authorized staging target, verify real JWT/JWKS/claim lifecycle, two-organization RLS, same-org care-team isolation, revocation/MFA/invitation, private storage, signed URL expiry and consent races.
- [ ] Prove migration integrity, backup/restore, managed secrets, telemetry redaction, retention/legal hold and worker recovery. Object-level signed audio URLs do not enforce cryptographic segment clipping; record whether the accepted pilot requires server-side clipping.

Acceptance: exact environment, commit/candidate, commands, results and limitations are recorded without secrets or clinical content. Local mocks never count as managed Supabase evidence. Missing credentials block S1 execution only; scripts and local work continue. No external database wipe, deployment, merge or release is authorized by this planning document.

## 11. V1 — Therapist pilot and research deliverables

- [ ] Walk through the complete workflow with synthetic cases first: normal, sparse evidence, conflicting cues, incompatible follow-up, withdrawn consent, offline upload and amended report.
- [ ] Run the existing usability protocol with actual therapist participants when arranged. Record task completion, errors, assistance and time; distinguish real observations from proposed targets.
- [ ] Produce research figures from the accepted Figma exports and implemented workflow; map every screenshot and feature claim to its actual status.
- [ ] Produce a reproducibility package: feature definitions, paper/page traceability, cohort applicability, data/consent inventory, experiment configuration, extraction versions and limitations. Preserve source datasets.
- [ ] If outcome evaluation is authorized and data is available, predefine labels and participant-level splits, prevent repeated-child leakage, report uncertainty/calibration/subgroups where applicable, and keep the evaluation distinct from product claims.
- [ ] Record a pilot go/no-go with unresolved operational and scientific limitations. Diagnostic probabilities require separate representative Thai validation and governance, outside this delivery plan.

Acceptance: an advisor or therapist can trace the workflow back to actual software, evidence and observed results; absent data or access is clearly labelled rather than replaced with invented evidence.

## 12. Per-slice execution and verification

Before coding each slice, write `docs/superpowers/plans/<date>-<slice>-implementation.md` containing exact existing/new paths, API/schema examples, migration strategy, observable tests with executable code, ordered RED/GREEN/REFACTOR steps, acceptance mapping and verification commands. This master roadmap deliberately does not invent full implementation code for APIs whose integration base is unresolved.

For behaviour changes record `TDD_REQUIRED`, the observable seam, actual failing command/output before implementation, focused GREEN and refactor evidence. Follow repository `writing-good-tests.md` when available. Do not reconstruct missing historic RED output after a fix. Docs-only changes need document/path/diff checks.

Use the selected venv interpreter as `python`. From the verified continuation root:

```bash
PYTHONPATH=apps/api:src python -m pytest apps/api/tests/assessment_v2/test_longitudinal_contract.py -q
PYTHONPATH=apps/api:src python -m pytest apps/api/tests/assessment_v2 -m 'not assessment_postgres' -q
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
git diff --check
```

The first command applies only after B1 creates that test file; use the matching named test for each other slice. Run native verification with the approved disposable local database configuration from `DEVELOPER_SETUP.md`:

```bash
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_native.py
```

From `apps/lingualens-app`:

```bash
npm test -- src/__tests__/assessment-segment-review-workspace.test.tsx
npm run typecheck
npm run lint
```

At the complete candidate boundary, derive all required checks from actual CI and scripts: core/API suites, frontend suite/build, native/RLS/migrations, full relevant Playwright including demo/UI audit, benchmark gates, dependency audits and Python matrix. `bash scripts/check_project.sh` is useful local evidence but not the entire release gate. Run focused checks during edits; reuse unchanged receipts only when the same candidate/environment boundary is actually verified.

Honor AGENTS assurance requirements for API/auth/data-integrity/concurrency work. Do not claim independent review when Antigravity lacks the required reviewer/runtime capability. Persist that gap and finish safe implementation/verification; protected external actions still require their acceptance boundary. Never reset the old A2 review budget.

## 13. Progress record and handoff

For each slice record in `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md`:

```text
Slice:
Status: planned | in_progress | implemented | verified | accepted | blocked
Workspace / branch / base / candidate:
Acceptance criteria and actual result:
Changed files (including untracked):
TDD_REQUIRED and RED/GREEN/REFACTOR evidence:
Commands, exit status, environment and receipt paths:
Research / Figma / external evidence:
Assurance status and inherited limitations:
Unresolved issues / exact external action needed:
Next smallest task:
```

Do not commit/push/deploy based solely on this handoff. Prepare reviewable diffs/checkpoint instructions; honor exact existing owner authority and repository release rules. Report behaviour implemented separately from design accepted, external integration verified and clinical validation.
