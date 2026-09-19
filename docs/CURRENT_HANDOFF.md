# LinguaLens Current Handoff

Last verified: 2026-09-09 (A2 Task 8 full candidate gate)
Handoff base: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`
Working branch: `codex/assessment-v2-segment-review` in
`.worktrees/assessment-v2-segment-review` — carries the uncommitted A2 segment
review candidate; no owner checkpoint commit has been requested in this task

เอกสารนี้เป็น snapshot สำหรับส่งต่องาน ไม่ใช่ architecture authority หากข้อมูล
ขัดกัน ให้ยึด `docs/PROJECT_SOURCE_OF_TRUTH.md`, `AGENTS.md` และโค้ดบน `main`
ก่อนเสมอ

## Executive summary

LinguaLens มี canonical therapist product เพียงชุดเดียว:

- Next.js frontend: `apps/lingualens-app/`
- FastAPI workflow and clinical-policy API: `apps/api/`
- Supabase: Auth/PostgreSQL/private Storage target
- Scientific/research code: `packages/` และ `src/`
- Analysis-only transcript boundary: `packages/analysis_contract/` และ
  `packages/cha/`

เว็บและ API deploy และตอบสนองได้ แต่ระบบยังเป็น research/education prototype
ไม่ใช่ diagnostic tool และยังไม่ผ่าน production security/legal/Thai clinical
validation gates

Owner-approved direction is now the A2 segment-review slice on top of the A1
durable evidence boundary: therapists attest a transcript, review immutable
timestamped segments, edit uncertain segments as new revisions, attest the
current segment set, request bounded replay when storage is available, and read
descriptive evidence only after segment-bound processing succeeds. FastAPI owns
state and policy; the Web client is thin; GUI/TUI are preserved as compatibility
surfaces. The system remains research/education decision support, not diagnosis.

## Verified local candidate state

- A2 implementation remains uncommitted on the owner worktree; base A1 commit is
  `5fb37457167b079d63d5ffe10d63a1cd2cd88706`.
- Assessment V2 suite: 369 passed, 10 skipped, 3 existing warnings; migration
  smoke reaches `0009_segment_evidence_provenance` and downgrades cleanly.
- Frontend suite: 544 passed; typecheck and lint passed; isolated-port
  Playwright transcript/processing smoke passed 1 test.
- Native PostgreSQL gate: 10 tests passed, including migration preservation
  through `0009`, segment v1 → v2 revision/attestation, bounded unavailable
  replay, evidence provenance, transcript staleness, tenant/consent/role
  denial, worker success, lease/RLS checks, and temporary database cleanup.
- Full candidate gate: core non-audio tests, migration smoke, assessment-v2
  suite (369 passed, 10 deselected), frontend suite (544 passed), and Next
  production build passed. The isolated-port Playwright smoke passed 1 test;
  the native PostgreSQL/RLS walkthrough passed 10 tests.
- The final-strict assurance review remains pending for the complete A2
  candidate; do not claim a clean audit or final-strict `ship` status.

The separate frontend dependency audit currently reports 8 advisories from the
existing lockfile tree (2 moderate, 5 high, 1 critical) in `@vitest/mocker`,
`js-yaml`, `next` and `sharp`. Neither package-lock changed in A1, and no
breaking `npm audit fix --force` was applied; treat this as a visible baseline
dependency follow-up rather than a clean audit claim.

Reachability and smoke tests do not prove tenant isolation, production Auth,
private Storage policy, backup, legal, or clinical readiness

## Recently completed work

| PR | Merge commit | Result |
| --- | --- | --- |
| #4 | `af662c97` | Frontend runtime, CI audits, and security alignment |
| #5 | `e5de62fc` | Extraction Phase 1: deterministic CHAT and reviewed-transcript scientific contracts |
| #6 | `538c0944` | Status/source-of-truth cleanup; Redis/Celery no longer treated as an automatic requirement |
| #7 | `4771ab0b` | Extraction Phase 2: synchronous reviewed-transcript execution seam |
| A1 checkpoint | `7a37fe8a` | Evidence V2 checkpoint and durable-processing plan |

The preceding A1 checkpoint established the separate Assessment V2 boundary
with `0007_durable_evidence_jobs`, backend-owned queue state, lease/reclaim,
retry/cancel actions, a shared native capture/evidence worker, and a Web polling
client. The current A2 candidate extends that boundary with immutable segment
review and segment-bound evidence provenance. No GUI/TUI business rule changed.

## Last verification evidence

For the A1 parent-recovery candidate:

- backend focused processing/worker/capture runtime regressions pass; complete
  Assessment V2 suite: 326 passed, 10 deselected, 2 warnings
- frontend full suite: 540 passed; `tsc --noEmit`, ESLint and Next production
  build passed
- Playwright `assessment-v2-transcript.smoke.spec.ts`: 1 passed on isolated
  ports `3128/8128`
- native gate: 10 PostgreSQL/RLS/migration/lease tests passed and the full async
  workflow receipt ended with `assessment-v2 native runtime check passed`
- repository-wide gate: `bash scripts/check_project.sh` passed with core 1139
  passed, 10 skipped, 3 deselected, Assessment V2 326 passed, 10 deselected,
  frontend 540 passed, and production build success. A narrowly scoped
  quarantine wrapper moved macOS `.DS_Store` metadata out of the worktree while
  Finder recreated it during consistency scanning

The final independent review call completed with `fix-first` (B1-B4) and the
fixed review budget is exhausted. Parent recovery then fixed and reverified all
four behavior blockers. The candidate is parent-completed but not final-strict
`ship`, committed, pushed, merged, deployed, or applied to a shared Supabase
database.

Parent-recovery closure:

- Capture jobs now persist a lease and reclaim expired `RUNNING` work after a
  worker crash.
- The shared worker services capture and evidence work across all configured
  tenants before returning, preventing a busy capture tenant from starving
  evidence or later tenants.
- Current evidence reads require the latest transcript and active pipeline /
  feature-schema contract.
- Running cancellation is surfaced as an acknowledged request while the
  worker settles safely.

## Current architecture boundary

```text
Browser / Next.js
  -> Supabase Auth session
  -> FastAPI /api/v1 for clinical reads, writes, authorization, consent,
     storage mediation, audit, and workflow transitions
       -> PostgreSQL / Supabase
       -> private Storage through server-mediated signed URLs

Browser / Next.js
  -> FastAPI /api/v2 assessment boundary
       -> fresh Assessment V2 PostgreSQL database / RLS
       -> processing_runs durable queue
  native worker -> capture + evidence stages -> same PostgreSQL database

packages/analysis_contract + packages/cha
  -> deterministic scientific computation only
  -> no auth, CRUD, storage, queue, report finalization, or product API ownership
```

Do not add product endpoints to `src/therapist_backend/` or
`src/clinical_workflow/`. Do not recreate the removed Vite/Capacitor therapist
app

## Important deployment constraint

The current API imports the analysis-only contract from repository-root
`packages/` and the compatibility parser from `src/`. The canonical staging
configuration therefore uses repository root as the Render service root and
declares `PYTHONPATH=apps/api:.:src`; local startup uses the equivalent
`PYTHONPATH=.:../..:../../src` from `apps/api`. This boundary is exercised by
the API import check and the native FastAPI/PostgreSQL smoke check. Docker
Compose remains an optional container-packaging check.

Do not add a `sys.path` hack or duplicate the scientific code inside
`apps/api`. When product wiring is actually required, choose one small explicit
packaging/deployment change and verify API startup on Render before merge

## Recommended next work

### Priority 1: owner checkpoint and final-strict preparation

Tasks 6-8 are implemented and verified in the uncommitted
`codex/assessment-v2-segment-review` worktree. The local candidate is ready for
owner checkpoint review; final-strict preparation remains:

- preserve the existing frontend dependency-audit baseline (8 advisories; no
  forced update)
- start the new A2 final-strict assurance unit only when the owner requests the
  independent review boundary
- keep the candidate uncommitted until the owner explicitly authorizes the
  checkpoint

Do not commit, merge, deploy, or mutate a shared Supabase database until the
owner explicitly authorizes the checkpoint. GUI/TUI business rules remain
unchanged.

### Priority 2: later slices

After A2 acceptance, plan B for compatible longitudinal comparison, C for
clinician disposition/report sign-off, and D for Web/GUI/TUI thin-client parity.
Keep business rules in FastAPI and preserve the GUI/TUI surfaces.

### Supabase security evidence (deferred by owner; UI assessment now complete)

The owner deferred this while UI usability was assessed; that assessment is now
done (phases A-E above), so this resumes as the gate before real clinical
production use. The local half is verified — the backend tenant-isolation smoke
(`GET /api/v1/organizations/current/tenant-isolation-smoke`, org-admin only)
returns `status=passed` with all application-guard checks green — but the
staging evidence itself cannot be produced locally. It requires the real
staging Supabase project and staging API deployment, exactly as
`docs/STAGING_TENANT_SAFETY_VERIFICATION.md` specifies (local mock results are
explicitly not a substitute):

- real-claim two-organization RLS verification
- JWT/JWKS and custom-claim verification
- invitation and TOTP MFA lifecycle verification
- private Storage, signed URL expiry, completion, and retention verification
- secret rotation, backup/restore, observability, privacy/legal/vendor approval

Follow `docs/PHASE1_EXTERNAL_BLOCKERS.md` and
`docs/STAGING_TENANT_SAFETY_VERIFICATION.md` when this work resumes.
Staging credentials/environment are not available in this local checkout.

## Do not do next

- Do not merge `codex/v1.7.0-speech-to-chat` wholesale
- Do not drop the recovery stash without explicit owner approval
- Do not add Redis/Celery because it appears in historical deployment docs
- Do not add realtime, GraphQL, Kubernetes, vector databases, LLM/RAG, or new ML
- Do not move ordinary CRUD or clinical workflow policy into the analysis layer
- Do not weaken non-diagnostic wording or therapist review gates for UI clarity

## Preserved recovery state

- Worktree: `.worktrees/v1.7.0-speech-to-chat`
- Branch: `codex/v1.7.0-speech-to-chat`
- Recovery stash: `stash@{0}: phase1-recovery-2026-08-15-before-main-cleanup`

The old speech-to-CHAT branch is large and contains over-scoped product/queue
work. Reuse only reviewed pieces through small extractions; do not merge the
branch as a unit

## Environment and secret handling

Expected frontend variable names include:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SITE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Backend configuration uses the `LINGUALENS_*` names documented in
`apps/api/README.md` and the deployment runbooks. Never place values, bearer
tokens, service-role keys, database passwords, child identifiers, transcript
text, audio content, storage keys, or raw clinical URLs in commits, fixtures,
handoff notes, logs, or issue trackers

## Commands for the next engineer

```bash
# Work only in the A2 linked worktree
cd /Users/porschecaa/lingualens/.worktrees/assessment-v2-segment-review
git status --short --branch

# Read current authority and boundaries
sed -n '1,260p' docs/PROJECT_SOURCE_OF_TRUTH.md
sed -n '1,240p' docs/CURRENT_HANDOFF.md

# A2 backend and native gates
PYTHONPATH=apps/api:src python3.13 -m pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_migrations.py
LINGUALENS_NATIVE_ADMIN_DATABASE_URL=postgresql+psycopg://<local-admin>:<password>@127.0.0.1:5432/postgres \
  PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
bash scripts/check_project.sh

# Active API
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000

# Active frontend
cd apps/lingualens-app
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Copy/paste continuation brief

```text
Read `AGENTS.md`, `docs/PROJECT_SOURCE_OF_TRUTH.md`, and this handoff.
Continue A2 only in `.worktrees/assessment-v2-segment-review`. Tasks 6-7 are
green: immutable segment review, replay safety, evidence provenance and native
PostgreSQL/RLS walkthrough are verified. Task 8 is complete locally; keep the
worktree uncommitted until owner authorization, and do not migrate a shared
Supabase database, deploy, merge, or change GUI/TUI business rules.
```
