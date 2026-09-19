# Antigravity D1/R1 Continuation Plan

> **For agentic workers:** Use `executing-plans` for execution and the repository's bundled `test-driven-development` skill before behavior changes. This is the continuation delivery plan; expand each bounded implementation task against the inspected source before coding. Repository assurance and owner authority override generic skill commit/review suggestions.

**Goal:** Complete GUI/TUI parity and supported local runtime verification, then prepare the remaining managed-environment and therapist acceptance gates.

**Architecture:** Keep FastAPI as the owner of clinical policy and state. Reuse one Python transport for GUI/TUI, preserve separately identified local research utilities, and map clients to the actual Assessment V2 contracts.

**Tech Stack:** Python 3.11–3.13 (3.12 preferred), pytest, urllib or the existing approved transport, Tkinter, Rich, FastAPI, PostgreSQL, Next.js, npm.

## Authority and starting point

- Workspace: `/Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation`.
- Observed branch: `antigravity/assessment-v2-continuation`; HEAD: `5fb37457167b079d63d5ffe10d63a1cd2cd88706`. Uncommitted and untracked files are part of the continuation. HEAD alone cannot reconstruct it.
- Master plan: `/Users/porschecaa/lingualens/docs/superpowers/plans/2026-09-12-antigravity-remaining-work-roadmap.md`. That file was absent in the continuation workspace at this planning checkpoint; use this explicit source path.
- Progress: `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` in the continuation workspace.
- Read applicable `AGENTS.md`, `docs/PROJECT_SOURCE_OF_TRUTH.md`, `DEVELOPER_SETUP.md`, `docs/SECURITY.md`, and actual CI/package scripts before implementation.
- Preserve accepted work; verify evidence and address a concrete newly demonstrated gap without repeating entire accepted slices. An inherited `accepted` label does not prove current source/environment identity or authorize release.
- A2 unit `lingualens/assessment-v2/segment-review` is terminal `parent-completed`, `review-exhausted`, `final-strict-not-achieved`, budget 3/3. Never reserve another A2 review, rename its unit to reset budget, or alter its terminal ledger.
- Local edits/tests/docs are authorized. Commit, push, merge, deployment, release, and shared database mutations require their existing exact authority; this plan grants none.

## Task 0 — Reconcile receipts and establish the supported interpreter

**Files:** read progress, `pyproject.toml`, dependency files and A2 manifests under `/Users/porschecaa/lingualens/.git/solweaver/lingualens-assessment-v2-segment-review/`; append findings to progress.

- [ ] Run `git worktree list --porcelain`, `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain=v1 --untracked-files=all`, `git diff --stat`, `git diff --cached --stat`. Inventory untracked content explicitly.
- [ ] Recompute frozen A2 hashes in its original worktree and separately compare continuation files. Preserve the recorded identity recipe. Report divergence without overwriting either workspace.
- [ ] Record a current source inventory containing path, status, byte count and SHA-256, plus environment identity and dependency versions. Save logs in ignored `.local/verification/antigravity-d1/`; record their hashes and paths in progress. Do not capture secrets or clinical data.
- [ ] Select an existing supported venv; verify `python -c 'import sys; print(sys.executable); print(sys.version)'`. If none exists, create a workspace venv with Python 3.12 using repository setup instructions. Record the exact interpreter for all commands below.
- [ ] Classify the prior `21 passed` receipt as historical Python 3.14 evidence: `pyproject.toml` requires `<3.14`, so this receipt cannot establish supported-runtime readiness. Rerun the focused client suite using the supported interpreter.
- [ ] Append corrections to broad prior claims: local mock access still exists in methods that do not make HTTP requests; the prior no-fallback patch only changed existing HTTP branches. D1/R1 and remote U1/S1/V1 are still incomplete, so the inherited “100% prototype-ready” statement is not a current delivery conclusion.

Acceptance: source, environment, inherited limitations, and receipt reuse decisions are reproducible. No new product behavior in this task.

## Task 1 — Finish the D1 failure boundary

**Files:** `packages/tui/client.py`, `packages/tui/workflow.py`, `packages/tui/ui.py`, `packages/gui/app.py`, `tests/test_tui.py`, `tests/test_gui.py`; create `tests/test_tui_transport.py` if transport scenarios warrant a separate file.

- [ ] Inspect all public client methods, including `ingest_audio_file`, `update_utterance`, `auto_refine_speakers`, `swap_speakers`, and GUI/TUI direct `_mock_data` accesses. Produce an operation inventory before editing; these local-only paths were not closed by the previous patch.
- [ ] Read `writing-good-tests.md`. Record `TDD_REQUIRED: yes`, the exact observable seam, and which production defect each new test should catch. Existing passing tests are regression evidence, not a fresh RED cycle.
- [ ] Parameterize the existing failure regression so every operation runs independently. Add missing ingestion and attestation cases. Assert the whole local state is unchanged after failures, using a deep-copied synthetic fixture.
- [ ] Exercise real transport code against a loopback test HTTP server: success, 401, 403, 409, 429, 500, malformed JSON, missing required response fields, and unavailable server. Assert caller-visible results and request counts; never contact real services or print request clinical bodies.
- [ ] Observe and persist RED before fixing each uncovered behavior. Preserve successful API responses; return explicit unavailable/error states for failed or unsupported clinical actions. Do not turn malformed responses into empty successful lists.
- [ ] Test GUI/TUI failure presentation: an error does not terminate the interactive workflow unexpectedly, display a success notice, create a local report/signature, or replace existing state with fabricated results. Generic messages must omit raw URL, response body, token, file path, and clinical identifiers.
- [ ] Preserve explicit research/demo utilities under clearly identified local mode. Live operations with no implemented backend equivalent must report unsupported operation before local mutation or audio processing.
- [ ] Run focused tests to GREEN, inspect the full task diff, then refactor only duplication exposed by these changes. Update the client module description, README and CHANGELOG for actual changed behavior.

Commands from the continuation root with the selected venv activated:

```bash
PYTHONPATH=.:src python -m pytest tests/test_tui.py tests/test_tui_transport.py -q
PYTHONPATH=.:src python -m pytest tests/test_gui.py -q
git diff --check -- packages/tui packages/gui tests/test_tui.py tests/test_tui_transport.py tests/test_gui.py
```

Run the transport filename only after it is created. GUI skips must be disclosed and followed by a supported display run before claiming GUI acceptance.

Acceptance: failed live requests and unsupported clinical operations never produce local clinical success; both clients show actionable generic errors. This checkpoint is not yet V2 parity.

## Task 2 — Auth and session lifecycle for the shared transport

**Depends on:** Task 1. **Files:** shared client/transport, GUI/TUI entrypoints and tests; read `apps/api/app/assessment_v2/dependencies.py` if present, actual auth dependencies reached from routes, and `docs/SUPABASE_AUTH_CONTRACT.md`.

- [ ] Inspect actual backend session/token and organization-context requirements; document the contract and examples before adding headers. Do not invent auth modes or embed service-role credentials.
- [ ] Write a bounded implementation plan covering token injection, expiry, redirects, retries and UI recovery. Use an injected current access-token provider with an explicit session-clear operation; never log or persist tokens in fixtures or source.
- [ ] Test with synthetic tokens at the transport boundary: bearer header reaches only the configured API origin; cross-origin redirects never receive credentials; expired-session 401 clears session state and requests sign-in; 403 remains permission denial; 409 requests reload; 429 permits explicit retry guidance.
- [ ] Do not automatically replay clinical writes after timeouts or token refresh. A lost response may follow a successful write; reconcile through server state/idempotency where the actual route supports it. Bound any read retries and test request counts.
- [ ] Execute RED → minimal implementation → GREEN and GUI/TUI recovery checks. Follow final-strict requirements for auth/secrets changes, including independent review only when a valid reviewer capability and readiness packet exist. Record capability gaps truthfully and keep external actions unexecuted.

Acceptance: real user sessions can be supplied safely, expired sessions recover visibly, and transport failures cannot bypass backend decisions.

## Task 3 — Map and implement V2 parity in small vertical slices

**Depends on:** Tasks 1–2 and verified E/B/C contracts. **Files:** `packages/tui/{client.py,workflow.py,ui.py}`, `packages/gui/app.py`, client tests; read `apps/api/app/assessment_v2/{routes.py,schemas.py,services.py}` and `apps/lingualens-app/src/services/assessment-v2-client.ts`.

- [ ] Create `docs/readiness/GUI_TUI_V2_PARITY.md` mapping each action to actual HTTP method/path, request/response schema, concurrency token, consent/role gate, web consumer and Python consumer. Distinguish case/session IDs from child/assessment IDs.
- [ ] Map assessment selection and context, capture/upload, transcript/segment review, processing/retry/cancel, evidence, history/comparison, clinician review, report draft/sign/amend/export. Mark unsupported actions explicitly.
- [ ] Implement one vertical slice at a time in that order. Before each slice, document exact source files and executable test cases against inspected API schemas. Keep computations, consent decisions, currentness checks and signatures on FastAPI.
- [ ] Use the same synthetic contract examples for Web, GUI and TUI. Test normal response, missing evidence, consent denied, permission denied, stale version, auth expiry and offline state. Do not copy diagnostic/age-norm rules from the local mock into the V2 adapter.
- [ ] Consume authorized server report exports and signed snapshots. Do not recreate report hashes or final sign-off state in clients. Keep local research exports explicitly separate.
- [ ] Record parity per action; close D1 only when its full map and consumer evidence pass. Any required API correction is a bounded dependency task with its own TDD and applicable assurance, not permission to redo accepted E/B/C wholesale.

Acceptance: each supported clinical action uses the same FastAPI contract as Web; unsupported actions are explicit. UI additions requiring U1 acceptance must wait for the applicable accepted designs.

## Task 4 — R1 runtime/dependencies and complete candidate gates

**Depends on:** Task 0 for investigation; Task 3 for final acceptance. **Files:** actual runtime/package/dependency files, `DEVELOPER_SETUP.md`, `scripts/check_assessment_v2_native.py`, `scripts/check_project.sh`, CI workflows.

- [ ] Verify API/worker imports from the documented deployment working directory; inspect installed module paths and versions. Resolve packaging through the existing package setup, not `sys.path` hacks.
- [ ] Recheck npm and Python audits with exact dependency graphs and timestamps; save redacted output. Prior advisory counts are historical. Fix bounded findings with regression checks; do not use forced upgrades.
- [ ] Rehearse native startup/shutdown, worker recovery, retry/cancel, port isolation, upload cleanup and migrations using a verified disposable local database. Inspect the native runner's creation/deletion targets before execution.
- [ ] Assemble the complete verification profile from current CI/scripts. Run focused checks during fixes; freeze the complete candidate before one full applicable pass. Include supported Python matrix, core/API, frontend lint/typecheck/tests/build, native/RLS/migrations, relevant full Playwright/demo/UI audit, benchmarks and audits. `check_project.sh` alone is insufficient.
- [ ] Bind receipts to source manifest, interpreter, dependencies and runtime environment. Rerun affected gates after behavior/environment changes. Apply the repository's final-strict readiness/review rules to new qualifying work; never reopen A2.

Acceptance: supported runtime and complete candidate evidence are current, with unresolved failures and independent-review limitations explicit.

## Task 5 — Finish external U1/S1/V1 gates when authorized

- [ ] U1: inspect current authenticated Figma capability, finish links/exports, record actual frame IDs and therapist design acceptance. Local specifications alone do not prove remote completion. Preserve existing local artifacts.
- [ ] S1: after R1 and the complete backend candidate pass, execute the existing staging runbook only for an explicitly authorized target with appropriate credentials. Verify real auth/JWKS, tenants/care-team, consent, private storage/URL expiry, recovery/restore and redacted telemetry.
- [ ] V1: use the existing walkthrough and usability protocol with actual participants; record actual observations and synthetic test results separately. Complete reproducibility artifacts and give a traceable pilot decision.
- [ ] Missing external access blocks only dependent execution. Continue local independent work and report the exact needed authority/environment without inventing evidence.

## Required checkpoint report

Append to `docs/ANTIGRAVITY_HANDOFF_PROGRESS.md` after each bounded task: task/status, source manifest and branch/HEAD, changed files including untracked files, acceptance mapping, observed RED/GREEN evidence, command/exit/interpreter/log path/hash, unresolved dependencies, assurance limitation, and next smallest task.

Use `implemented` or `verified` for demonstrated local results. Use `accepted` only when the task's complete acceptance and applicable assurance have been met. Do not rewrite historical receipts as current results. No fresh tests were run while writing this plan.
