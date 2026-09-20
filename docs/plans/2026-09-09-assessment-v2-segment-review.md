# Assessment V2 Segment Transcript Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** เพิ่ม transcript segment review ที่ตรวจสอบย้อนกลับได้ระดับช่วงเสียง ให้ therapist แก้เฉพาะจุดที่ไม่แน่ใจ เปิดฟังเสียงช่วงนั้น และส่งต่อข้อมูลที่ attested แล้วไปยัง evidence processing ได้ โดยยังคงขอบเขตว่าเป็น research/education prototype ไม่ใช่ระบบวินิจฉัย

**Architecture:** คง transcript_revisions แบบทั้งฉบับไว้เป็น source snapshot แล้วเพิ่ม immutable transcript_segment_sets และ transcript_segments ที่ผูกกับ transcript checksum, assessment, consent และ recording ที่ตรวจสอบแล้ว ทุกการแก้ไขสร้าง segment set revision ใหม่ ไม่มี update/delete ของ snapshot เดิม FastAPI เป็นเจ้าของ state และ GUI/TUI เดิมยังไม่ถูกลบ

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL/Supabase RLS, Python 3.13, Next.js 16, React 19, TypeScript, pytest, Vitest, Playwright และ private signed-storage URLs

## Scope and safety

- Base checkpoint: 5fb37457167b079d63d5ffe10d63a1cd2cd88706.
- Worktree/branch: assessment-v2-segment-review / codex/assessment-v2-segment-review.
- Canonical product paths are apps/api and apps/lingualens-app. Do not add new product endpoints under legacy src surfaces.
- Preserve consent gates, tenant isolation, role checks, signed URLs, auditability and non-diagnostic language.
- Do not put child identifiers, transcript text, audio bytes or storage keys in logs, fixtures or committed sample data.
- Dependency audit is a prerequisite gate. The current frontend audit reports existing advisories including one critical Next advisory. Record the finding and review safe updates separately; do not run npm audit fix --force as part of A2.
- Existing A1 evidence rows remain readable as historical records. A2 must not rewrite or silently migrate them into fabricated segment provenance.

## Acceptance criteria

1. A segment set is tied to one organization, assessment, current transcript revision/checksum, optional verified recording and explicit revision/version.
2. Segment snapshots are immutable. Draft edits create a new segment set; there are no update/delete endpoints for historical segment rows.
3. Each segment has ordinal, start/end offsets, controlled speaker role, text, confidence and controlled uncertainty reason. Server validation rejects invalid time ranges, duplicate ordinals, unsupported enums and empty text.
4. The server computes a deterministic SHA-256 checksum from the canonical ordered segment payload and never trusts a client-provided checksum.
5. A therapist can create a draft, filter uncertain segments, edit the focused segment, save a new revision and attest the expected version. Attestation binds actor, time, transcript checksum, recording identity and segment checksum.
6. Audio replay uses a short-lived server-created signed grant with start/end offsets. The client never receives a permanent storage key or credential. Missing audio is explicit and non-fatal.
7. A newer current segment set makes older segment-linked evidence/processing stale while preserving all historical rows.
8. New evidence enqueue requires the current attested segment set and persists segment-set id/checksum provenance. A1 rows remain backward compatible as historical rows.
9. Cross-tenant, wrong-role, missing-consent, stale-version, stale-transcript and unavailable-recording paths fail safely without leaking data.
10. The frontend uses backend-owned state and has loading, full timeline, uncertain-only filter, focused edit, replay available/unavailable, save/attest, stale/error and reload states.
11. API, DB/RLS, evidence provenance, UI and native PostgreSQL walkthroughs are covered by tests and the relevant Figma/API contract artifacts are updated.

## Explicit non-goals

- No live ASR, diarization, audio clipping or model training.
- No ASD diagnosis, probability, clinical score or Thai clinical validation claim.
- No longitudinal B, disposition/report C or thin-client D work in this slice.
- No rewrite of v1, GUI/TUI, raw research datasets or historical transcript content.

## TDD and assurance

Use RED-GREEN-REFACTOR for every behavior task. Observable seams are: pure segment validation/checksum, repository state transitions, API responses, evidence provenance and UI interaction. Record the observed failing test, minimal implementation, green focused tests and refactor result in the plan/handoff.

A2 is a wide data-integrity, authorization and public-API refactor, so use final-strict assurance for the final candidate. Start a new assurance unit; do not reuse the exhausted A1 unit. Keep source changes uncommitted until the owner checkpoint is explicitly requested.

## Task 0 — Baseline and dependency gate

Read the source-of-truth and relevant A1 files. Install only the worktree-local frontend dependencies with npm ci, verify Python test availability, run the focused A1 API/frontend tests, and record the existing npm audit result. Do not modify lockfiles or dependencies in this task.

Expected checks:
- git status --short
- cd apps/lingualens-app && npm ci
- npm audit --json
- A1 assessment-v2 focused pytest suite
- focused frontend tests, typecheck and lint

## Task 1 — Pure segment contract

Files:
- apps/api/app/assessment_v2/domain/models.py
- apps/api/app/assessment_v2/domain/segments.py
- apps/api/tests/assessment_v2/test_segment_contract.py

Define controlled speaker roles and uncertainty reasons, immutable segment input/output models, offset/confidence validation and deterministic canonical checksum. Tests must cover valid ordering, supported values, malformed ranges, duplicate ordinals, empty text, checksum stability and client-checksum rejection behavior at the service boundary.

TDD sequence:
1. Add failing contract tests and run only that file.
2. Implement the smallest domain contract.
3. Run the file and relevant transcript contract tests.
4. Refactor without changing the public contract.

## Task 2 — Segment persistence and migration

Files:
- apps/api/app/assessment_v2/db/models.py
- apps/api/app/assessment_v2/db/migrations/versions/0008_transcript_segments.py
- apps/api/tests/assessment_v2/test_segment_db_models.py
- apps/api/tests/assessment_v2/test_segment_migration_rls.py
- apps/api/tests/assessment_v2/test_migrations.py

Add transcript_segment_sets and transcript_segments with tenant-safe foreign keys, revision uniqueness, immutable snapshot fields, ordered segment uniqueness and checks for offsets/empty text. Add PostgreSQL RLS policies matching A1 tenant patterns, safe upgrade/downgrade behavior and SQLite compatibility used by unit tests. Verify that A1 rows survive and that no destructive rewrite occurs.

TDD sequence:
1. Write model/migration/RLS tests against the current schema.
2. Observe RED.
3. Add models and migration.
4. Run focused SQLite tests, migration tests and native RLS checks.
5. Refactor naming/indexes only after green.

## Task 3 — Repository and service transitions

Files:
- apps/api/app/assessment_v2/db/repositories.py
- apps/api/app/assessment_v2/services/segments.py
- apps/api/tests/assessment_v2/test_segment_repository.py
- apps/api/tests/assessment_v2/test_segment_service.py

Implement current-read, draft-create, edit-as-new-revision, supersede, attestation and stale detection. The first draft must bind to the latest transcript revision checksum. Attestation requires current transcript, consent, authorized therapist/care-team membership, expected segment version and optional recording validity. Use one documented lock order for assessment, child, transcript, segment set and recording. Prove cross-tenant and stale-write rejection.

## Task 4 — FastAPI segment review and replay grants

Files:
- apps/api/app/assessment_v2/schemas.py
- apps/api/app/assessment_v2/routes.py
- apps/api/app/assessment_v2/services/segments.py
- apps/api/app/assessment_v2/storage.py
- apps/api/tests/assessment_v2/test_segment_routes.py

Add:
- GET /api/v2/assessments/{assessment_id}/transcript-segment-set
- POST /api/v2/assessments/{assessment_id}/transcript-segment-sets
- POST /api/v2/transcript-segment-sets/{segment_set_id}/attest
- POST /api/v2/transcript-segments/{segment_id}/audio-replay-grant

Responses expose ordered segments, checksum, revision/state and attestation metadata. Replay returns only segment id, bounded offsets, short-lived signed URL, expiry and availability. Cover 201/200/403/404/409/503 and consent/tenant/role failures.

## Task 5 — Evidence provenance

Files:
- apps/api/app/assessment_v2/db/models.py
- apps/api/app/assessment_v2/db/migrations/versions/0009_segment_evidence_provenance.py
- evidence repositories/workers/adapters/schemas
- focused evidence provenance tests

Add nullable tenant-safe segment_set_id and segment_set_sha256 to processing/evidence records. New enqueue requires the current attested set; idempotency includes transcript checksum, segment checksum, pipeline and schema versions. Workers re-check both checksums and mark stale inputs safely. Preserve A1 lease, retry, tenant and audit behavior.

## Task 6 — Therapist UI and Figma/API artifacts

Files:
- apps/lingualens-app/src/features/assessment-v2/
- apps/lingualens-app/src/__tests__/
- relevant Playwright tests
- docs/ux/therapist-workflow/api-screen-contract-map.md
- docs/ux/therapist-workflow/figma-delivery-manifest.md
- docs/ux/therapist-workflow/prototype-scenarios.md
- docs/ux/therapist-workflow/frame-inventory.csv

Replace the whole-text-only review interaction with a segment timeline/list while preserving explicit save and attestation. Implement uncertain-only filtering, focused editor, replay availability/unavailability, revision conflict and reload states. Keep clinical interpretation outside this component.

## Task 7 — Native PostgreSQL walkthrough

Extend the native migration/runtime checks and add a focused integration test covering: verified recording, transcript v1, segment draft v1, uncertain edit to v2, attestation, replay grant, evidence enqueue with provenance, transcript supersession staleness, second-tenant denial, consent denial, unassigned-role denial and downgrade row preservation. Run through migration 0009 on native PostgreSQL/Supabase-compatible RLS.

## Task 8 — Documentation and final gates

Update PROJECT_SOURCE_OF_TRUTH.md, README.md, CHANGELOG.md only for real behavior, and docs/CURRENT_HANDOFF.md. Record TDD receipts and the dependency-audit decision.

Final candidate checks:
- assessment-v2 focused suite and core non-audio suite
- frontend test, typecheck, lint and production build
- native PostgreSQL/RLS migration gate
- Playwright smoke
- scripts/check_project.sh
- git diff --check and complete tracked/untracked diff review

Recommended execution batches are Tasks 0-2, then 3-5, then 6-8. After each batch report the checkpoint and stop for feedback if the user has not already asked to continue.

## Execution receipts — Batch 1

- Task 0 baseline: frontend 540 tests passed, typecheck passed, lint passed, assessment-v2 baseline 326 passed/10 skipped. npm ci completed. npm audit recorded 8 existing advisories: 2 moderate, 5 high and 1 critical; no forced dependency change was made.
- Task 1 RED: the new contract test initially failed during collection because the segment domain contract did not exist.
- Task 1 GREEN: segment contract and transcript compatibility tests passed, 17 tests total. Server-side canonical SHA-256, supported enums, ordered ordinals, monotonic timestamps and client checksum mismatch rejection are covered.
- Task 2 RED: metadata/migration tests initially failed because 0008 and the two segment tables did not exist.
- Task 2 GREEN: segment model/migration/RLS tests passed, 4 tests; migration smoke passed through 0008 and downgrade preserved transcript_revisions. The segment set stores transcript_content_sha256 and segments_sha256 separately.
- Batch regression: assessment-v2 suite passed with 342 passed, 10 skipped and 3 existing warnings. Current worktree remains uncommitted for owner checkpoint review.
- Task 3 RED/GREEN: repository/service transition tests covered current reads, draft revisions, supersession, attestation, stale versions, tenant/consent/role gates, recording validity and client checksum mismatch. Focused repository/service tests passed after the immutable segment snapshot read/write seam was added.
- Task 4 RED: the new route tests initially returned 404 for the four segment-review/replay endpoints. GREEN: schemas, response mapping and FastAPI routes passed 6 focused tests, including signed replay and explicit unavailable audio.
- Task 5 RED: evidence provenance tests initially showed that enqueue accepted an attested transcript without a segment set, the idempotency key lacked transcript/segment checksums, and processing snapshots exposed no segment provenance. GREEN: migration 0009, nullable tenant-safe provenance columns, checksum-bound v2 idempotency, current-attested-set enqueue, worker claim/complete rechecks, stale/cancel transitions and evidence response provenance were added. Assessment-v2 suite passes with 369 passed, 10 skipped and 3 existing warnings; migration smoke reaches 0009 and downgrades cleanly on empty SQLite.
- Batch 2 checkpoint: Tasks 3-5 are complete and the worktree remains uncommitted for owner checkpoint review. Task 6 is the next batch: therapist segment timeline UI and Figma/API contract artifacts.
- Task 6 RED: the new UI attestation-status assertion initially failed because the segment workspace did not preserve the transcript prerequisite state, and the first browser smoke run reused unrelated services on ports 3100/8000 and reached a 404. A later smoke attempt exposed a strict locator collision between timeline text and the focused editor.
- Task 6 GREEN: the segment workspace now displays the backend-owned transcript attestation state, scopes the browser assertion to the timeline article, and passes the focused client/workspace tests (9 tests), the full frontend suite (544 tests), typecheck, lint, and isolated-port Playwright smoke (1 passed). Figma/API manifest, frame inventory and prototype scenario artifacts were updated without remote Figma mutation.
- Task 7 RED: the first native PostgreSQL walkthrough exposed a real FK ordering defect: SQLAlchemy attempted to insert `transcript_segments` before its immutable `transcript_segment_sets` parent. The walkthrough also corrected its public denial expectations from internal policy codes to the externally returned `403 forbidden` and `409 consent_revoked` contracts.
- Task 7 GREEN: the repository now explicitly flushes the segment-set parent before child rows. Native PostgreSQL runtime verification passes migrations through `0009`, segment draft v1 → edited/attested v2, bounded unavailable replay, verified-recording binding, evidence provenance, idempotent enqueue, transcript staleness, second-tenant denial, consent denial, unassigned-role denial, RLS and lease checks, and cleanup (`10 passed`). Assessment-v2 regression remains green at 369 passed, 10 skipped; migration smoke reaches 0009 and downgrades cleanly.
- Batch 3 checkpoint: Tasks 6-7 are complete and the worktree remains uncommitted for owner checkpoint review. Task 8 is next: source-of-truth/handoff documentation, dependency-audit decision, final verification and assurance preparation.
- Task 8 GREEN: source-of-truth, setup, development, changelog, handoff, and UX/API/Figma artifacts are synchronized. `bash scripts/check_project.sh` passed the core non-audio suite, migration smoke, assessment-v2 suite (369 passed, 10 deselected), frontend suite (544 passed), and Next production build. After the final Web evidence-provenance type sync, frontend tests (544), typecheck, lint, and production build passed again. Isolated-port Playwright smoke remains green (1 passed), native PostgreSQL/RLS runtime remains green (10 passed), and `git diff --check` passed. The existing npm audit baseline remains 8 advisories (2 moderate, 5 high, 1 critical); no dependency or lockfile change was made. The consistency gate needed a narrow temporary local quarantine for macOS `.DS_Store` files recreated by Finder; the checker was restored exactly and the metadata is outside the source candidate.
- A2 final candidate checkpoint: implementation and docs are complete but remain uncommitted in the linked worktree. Final-strict assurance metadata/reviewer call and owner checkpoint authorization are still pending; no shared Supabase database, deployment, merge, or GUI/TUI business-rule change was performed.
- Final-strict call 1 fix cycle RED: the reviewer identified that the worker analyzed the whole transcript instead of attested segment text, populated segment tables could be removed on downgrade, idempotency omitted immutable segment-set identity, legacy unbound jobs could remain claimable, replay needed a shared consent lock order, transport validation was incomplete, and attestation collisions were not reloadable. Focused RED evidence was observed before fixes: missing `extract_reviewed_segment_set` import, idempotency-key arity failure, duplicate-ordinal schema acceptance, and missing migration downgrade guard. A Task 3 repository seam was also re-established against the base checkpoint in an isolated temporary worktree: `test_task3_segment_repository_red.py` failed because `AssessmentRepository.create_transcript_segment_set` did not exist.
- Final-strict call 1 fix cycle GREEN: the worker now renders the exact attested segment snapshot, evidence identity includes transcript checksum + immutable segment-set id/checksum, unbound queued/running jobs are cancelled before processing, replay locks assessment → child → consent/segment/transcript through the request transaction, Pydantic rejects duplicate/non-contiguous ordinals and newline text, stale attestation versions win over state conflicts, and 0008/0009 downgrade guards are RLS-aware. Focused checks passed 61 tests before the final additions; the complete Assessment V2 suite now passes 379 passed, 10 skipped, 3 warnings. Added route validation, unexpired-lease legacy cancellation, and populated downgrade regression coverage. The existing npm audit baseline remains unchanged and is still a release gate requiring remediation or explicit owner risk acceptance; no forced dependency update was made.
- Native lease compatibility RED/GREEN: after the worker correctly stopped claiming A1 jobs without segment provenance, the native PostgreSQL lease fixture still seeded the pre-A2 shape and failed two claim assertions. The fixture now creates an attested immutable segment set and ordered segment rows, and teardown removes those rows before their transcript parent. The native PostgreSQL/RLS walkthrough then passed again with 10 tests, including lease ownership/reclaim and parent-lock contention.
- Final-strict call 2 fix cycle RED: the reviewer found four reachable contract gaps: draft segment sets could not request bounded replay, a first segment set after transcript replacement incorrectly compared against only the latest superseded historical revision, observer care-team assignments could mutate segment sets, and draft transcripts could create a segment set that could never be attested. New repository tests failed before production changes with replay returning `None`, `stale_segment_set_version`, observer mutation succeeding, and draft creation succeeding. The existing evidence supersession test also exposed the required new token contract: a new transcript's first segment set starts without an active segment-set concurrency token.
- Final-strict call 2 fix cycle GREEN: replay now permits the current non-superseded draft or attested set while retaining current transcript, consent, care-team access and recording checks; segment creation separates the latest historical revision counter from the active current-transcript concurrency token; segment mutation requires an active `assigned_clinician` or `supervisor` assignment in addition to organization membership; and segment creation requires an attested current transcript. The segment workspace already keeps transcript attestation ahead of segment review, now covered by a focused UI test. Focused repository tests pass (13), the complete Assessment V2 suite passes (382 passed, 10 deselected), native FastAPI/PostgreSQL/RLS passes (10), frontend tests pass (545), typecheck/lint/build pass, and isolated-port Playwright smoke passes (1). The existing frontend test was made deterministic by awaiting the processing-status transition before querying its action button. The npm audit baseline remains unchanged at 8 advisories (2 moderate, 5 high, 1 critical); no dependency update or deployment action was taken.
