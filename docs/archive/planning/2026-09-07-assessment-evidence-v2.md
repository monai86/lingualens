# Assessment Evidence V2 Implementation Plan

**Date:** 2026-09-07
**Status:** Transcript review and explicit extraction worker slice implemented; reviewer round 1 fix-first findings resolved in the candidate, final-strict re-review pending
**Parent design:** [Developmental Profile Workflow Redesign](../specs/2026-09-06-developmental-profile-workflow-redesign.md)

## Objective

Add the first Evidence slice after Capture V2. The slice must let the system
represent reviewed transcript-derived measurements and developmental domains
with provenance, quality, limitations, and partial availability. It must never
turn one feature or one model output into an ASD diagnosis, a developmental
delay diagnosis, or a numeric probability.

## Current boundary

- Capture V2 is the active prerequisite: consent, protocol, private upload,
  quality result, and resumable assessment already exist in `apps/api` and the
  therapist web app.
- `/api/v1`, `src/therapist_backend`, and `src/clinical_workflow` remain
  compatibility/research surfaces; no new product endpoint is added there.
- The analysis packages remain analysis-only. A versioned adapter must translate
  their output into the v2 evidence contract before persistence or UI use.
- No live ASR provider, Thai clinical reference band, or diagnostic classifier
  is introduced in this slice.

## Current checkpoint

Steps 1–5 are implemented as an additive v2 boundary: the contract, reviewed
transcript revisions and attestation, provenance adapter, persisted domain
profile, read endpoint, therapist transcript/evidence workspaces, and an
explicit reviewed-transcript extraction worker endpoint are present. The worker
computes only descriptive values, uses the maintained analysis contract, passes
through the v2 provenance adapter, and requires attestation before persistence.
The first final-strict review returned `fix-first`; the candidate now includes
the required role/care-team boundaries, consent serialization, optimistic
transcript concurrency, provenance parity, missing-channel semantics, and
first-transcript/resume flow. The independent final-strict re-review remains
pending.

## Delivery steps

### 1. Evidence contract (first implementation checkpoint)

Write failing tests first for:

- typed measured features with unit, source, quality state, limitation, and
  provenance;
- opaque input references and SHA-256 validation;
- unavailable, insufficient, and stale measurements carrying no fabricated
  value;
- domain profiles supporting multiple domains and separate supporting,
  conflicting, and limitation evidence;
- explicit `not_diagnostic` and `decision_support_only` invariants, with no
  diagnosis or numeric ASD-probability field.

Implement the smallest pure domain module under
`apps/api/app/assessment_v2/` and keep it independent of HTTP and storage.

### 2. Reviewed transcript boundary

Add v2 persistence for transcript revisions, review status, content checksum,
and therapist attestation. The server must preserve revisions and invalidate
dependent derived artifacts when the current transcript changes. Consent,
tenant, clinician-role, and version checks are required for every mutation.

Acceptance: an unattested or stale transcript cannot become report-eligible
evidence; a withdrawn consent blocks new review/analysis work.

### 3. Feature adapter and provenance

Create an adapter from the existing reviewed-transcript analysis contract to
v2 measured features. Preserve feature values only when the analysis result is
completed; map insufficient/failed results to explicit unavailable states.
Store pipeline version, feature schema version, input checksum, protocol
version, extractor identity, analysis timestamp, and limitations.

Acceptance: adapter tests cover completed, partial, failed, checksum mismatch,
and schema-version mismatch results; no raw transcript or storage key appears in
operational logs.

### 4. Developmental domain profile

Map measured features and structured evidence into independently readable
domains:

- expressive language;
- speech clarity and production;
- conversational interaction;
- social communication;
- repetitive-language patterns;
- prosody and temporal organization; and
- evidence quality and sufficiency.

Without a validated, compatible reference cohort, profiles remain descriptive
or explicitly unavailable/insufficient. A missing feature channel is not
converted into negative evidence. Multiple domain concerns may coexist.

### 5. FastAPI read model and therapist workspace

Expose the versioned evidence read model through `/api/v2`, then add the web
client and a result workspace that shows processing state, transcript review
requirements, measured features, provenance on demand, domain evidence,
conflicts, and next evidence actions. Every API failure must remain visible;
the browser must not create local clinical results or silently fall back.

### 6. Verification gate

Run focused contract/API/UI tests after each step. Before closing the slice,
run the v2 migration smoke test, backend assessment-v2 suite, frontend full
suite, typecheck, lint, production build, and a synthetic tenant-isolated
runtime walkthrough. Review the complete diff and update the source of truth,
README, and changelog only where the user-facing contract changes.

### Current implementation checkpoint

- RED/GREEN: `reviewed_transcript_worker.py` extracts descriptive values only
  from explicitly labelled, attested transcript tiers.
- RED/GREEN: `POST /api/v2/assessments/{assessment_id}/evidence-runs` invokes
  the worker, applies the adapter, and persists an idempotent evidence run.
- RED/GREEN: `/assessments/{assessmentId}/transcript` supports edit, append-only
  draft save, explicit attestation, and evidence-run handoff.
- Focused API route integration covers the complete transcript → attestation →
  worker → evidence flow and blocks unattested input.
- The live PostgreSQL/RLS adversarial pass covers the new transcript/evidence
  tenant policies and forced-RLS tables; the Compose fixture seeds required
  timestamps and tenant context explicitly.
- Transcript mutation now requires the expected `(revision, version)` pair for
  existing revisions; supersession increments the old revision version and
  writes an audit event. Consent withdrawal, transcript mutation, attestation,
  and evidence creation serialize on the child row.
- The browser covers an assessment with no transcript, creates the first draft,
  and continues into transcript review. Processing, review-required, and
  ready-for-clinician assessments link back to that review boundary.
- The candidate-wide gate is green: core 1085 passed, assessment-v2 272 passed
  (8 PostgreSQL tests deselected in the local run), frontend 62 files/532 tests
  passed, typecheck/lint/build passed, `npm audit --audit-level=high` reports
  zero vulnerabilities, migration smoke passed, Compose runtime passed, live
  PostgreSQL/RLS passed 8/8, and Playwright passed 4/4.
- Next slice after final review: background queue execution, richer
  timestamp/speaker review, and longitudinal comparison.

## Verification evidence

The focused post-fix backend suite passed 54 tests. The full assessment-v2
suite passed 272 tests with 8 PostgreSQL tests deselected locally. The complete
frontend suite passed 62 files/532 tests; typecheck, lint, and production build
passed. Migration smoke reached `0006_evidence_profiles` and downgraded to
base. The Compose runtime check passed against fresh PostgreSQL with a
non-superuser/NOBYPASSRLS application role. The live PostgreSQL/RLS suite
passed 8/8, and the Playwright smoke run passed 4/4, including first-transcript
creation and review continuation. The locked frontend dependency audit reports
zero vulnerabilities at the high-severity threshold.

The repository-wide `bash scripts/check_project.sh` passed with 1085 core
tests, 272 assessment-v2 tests, frontend 62 files/532 tests, build, migration,
consistency, import, and secret checks. The first final-strict reviewer found
six behavior blockers; they were resolved in the current candidate and require
one fresh refreeze plus independent re-review before this slice is considered
final-strict accepted.

## Out of scope

- automated ASD or developmental-delay diagnosis;
- numeric risk/probability output;
- new Thai clinical norms or validation claims;
- replacing the existing v1 session workflow;
- native GUI/TUI redesign (those remain thin clients after the API contract is
  stable); and
- destructive deletion or migration of the existing v1 database/storage.
