# Assessment V2 Parent-Recovery and Next Delivery Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ปิดประเด็นค้างของ Evidence V2 ให้รันได้จริงผ่าน FastAPI native process และ PostgreSQL ที่ติดตั้งบนเครื่องหรือ endpoint ที่จัดการแยกต่างหาก, รักษาขอบเขตสิทธิ์และความถูกต้องของข้อมูล, แล้วส่งต่อเข้าสู่ slice ถัดไปโดยไม่อ้างว่าได้ final-strict review ใหม่

**Architecture:** Web, GUI และ TUI ยังคงเป็น thin clients ของ FastAPI เดียวกัน การวิเคราะห์จะรับเฉพาะ reviewed/attested transcript และส่งผลกลับเป็น measured features กับ developmental evidence ที่ระบุสถานะข้อมูลไม่พอได้ ระบบใช้ Supabase/PostgreSQL ใหม่เป็น source of truth และไม่ย้ายข้อมูลจากระบบเดิม

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PostgreSQL/Supabase RLS, Python venv, Next.js/React/TypeScript, Vitest, Playwright และ pytest; Docker Compose เป็น optional container smoke test

---

## สถานะก่อนเริ่ม

- Evidence V2 มี contract, transcript revision/attestation, evidence adapter, profile endpoint และ therapist workspace แล้ว
- การแก้จาก reviewer รอบล่าสุดส่วนใหญ่ถูกใส่ไว้ใน worktree นี้แล้ว: role boundary, lock order, partial-channel semantics, 404 handling, dirty-attested UI และ API base derivation
- งานที่ยังต้องปิดจริงคือ native PostgreSQL/FastAPI runtime ที่ต้องทดสอบ API process จริง, canonical import path ของ Render/local docs, API-only runtime dependencies และ parent-recovery evidence
- review budget ใช้ครบแล้ว ดังนั้นห้ามเรียก reviewer เพิ่มหรืออ้าง final-strict acceptance ใหม่ งานนี้จบได้ที่ `parent-completed` เท่านั้นถ้า acceptance ผ่าน
- ห้ามลบหรือ migrate ข้อมูลจากระบบเดิมในแผนนี้ และห้ามเพิ่ม endpoint ลง `src/therapist_backend/` หรือ `src/clinical_workflow/`

**สถานะการดำเนินงานปัจจุบัน:** source fix, focused/full verification, API-only dependency check และ native PostgreSQL/FastAPI runtime gate ผ่านแล้ว เหลือเพียงการ refreeze manifest และปิด parent-recovery โดยไม่อ้าง final-strict review ใหม่

## ขอบเขตไฟล์

ไฟล์ runtime และ test ที่เกี่ยวข้อง:

- `docker-compose.yml` — runtime path ของ API และ worker
- `docker-compose.assessment-check.yml` — optional port สำหรับ Compose smoke check
- `scripts/check_assessment_v2_compose.py` — optional smoke check ที่เรียก API container จริง
- `scripts/check_assessment_v2_native.py` — primary no-Docker smoke check ที่เรียก native FastAPI process และ PostgreSQL จริง
- `apps/api/app/assessment_v2/services.py` — role/care-team authorization
- `apps/api/app/assessment_v2/db/repositories.py` — transcript lock order
- `apps/api/app/assessment_v2/evidence_adapter.py` — partial/unavailable feature mapping
- `apps/lingualens-app/src/lib/api.ts` — v1-to-v2 API base derivation
- `apps/lingualens-app/src/features/assessment-v2/components/assessment-transcript-review-workspace.tsx` — transcript state and evidence handoff

ไฟล์ test ที่ต้องเป็น executable acceptance evidence:

- `apps/api/tests/assessment_v2/test_compose_contract.py`
- `apps/api/tests/assessment_v2/test_native_runtime_contract.py`
- `apps/api/tests/assessment_v2/test_services.py`
- `apps/api/tests/assessment_v2/test_transcript_contract.py`
- `apps/api/tests/assessment_v2/test_evidence_adapter.py`
- `apps/lingualens-app/src/__tests__/assessment-v2-client.test.ts`
- `apps/lingualens-app/src/__tests__/assessment-transcript-review-workspace.test.tsx`

เอกสารและ assurance records:

- `AGENTS.md`
- `apps/api/README.md`
- `docs/DEVELOPMENT.md`
- `docs/CURRENT_HANDOFF.md`
- `docs/RENDER_BACKEND_STAGING_RUNBOOK.md`
- `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/ledger.md`
- `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/attempts.json`
- `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/candidate-manifest.json`

---

### Task 1: Establish the parent-recovery baseline

**Files:**

- Read: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Read: `docs/superpowers/specs/2026-09-06-developmental-profile-workflow-redesign.md`
- Inspect: current worktree diff and Solweaver sidecar

- [x] **Step 1: Confirm the active worktree and candidate boundary**

Run:

```bash
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
```

Expected: the work is on `codex/assessment-web-capture`; unrelated user changes in the main worktree are not copied into this candidate.

- [x] **Step 2: Record the reviewer findings as the parent-recovery checklist**

Use these seven behavior checks as the acceptance map:

1. API starts under the declared Compose and Render import boundary.
2. Frontend `/api` configuration resolves to `/api/v2`, not `/api/v2/api` or `/api`.
3. `org_admin` cannot mutate capture or obtain signed audio access.
4. Transcript attestation and transcript revision use assessment → child → transcript lock order.
5. Attested transcript edits cannot generate evidence until the draft is saved.
6. Only the typed `transcript_not_found` error opens a first-draft editor.
7. A missing feature channel becomes `INSUFFICIENT_DATA`, never a completed feature with `None`.

Keep the existing review attempt count at three. Do not create a new reviewer reservation.

---

### Task 2: Keep the container runtime optional and preserve its contract

**Files:**

- Modify: `docker-compose.assessment-check.yml`
- Modify: `scripts/check_assessment_v2_compose.py`
- Test: `apps/api/tests/assessment_v2/test_compose_contract.py`
- Verify: `docker-compose.yml`, `docs/RENDER_BACKEND_STAGING_RUNBOOK.md`

- [x] **Step 1: Keep the red contract test for the actual runtime boundary**

`test_compose_contract.py` must assert all of the following strings/behaviors:

```python
assert '"8002:8000"' in check_override
assert '"5434:5432"' in check_override
assert '_run("up", "-d", "--force-recreate", "postgres", "api")' in check_script
assert "_start_host_api" not in check_script
```

Run the focused contract test before changing the script. If it passes before the runtime change, inspect the script and add an integration assertion that would fail if the API service were omitted.

- [x] **Step 2: Expose the API container only in the assessment check override**

`docker-compose.assessment-check.yml` must contain:

```yaml
services:
  api:
    ports: !override
      - "8002:8000"
  postgres:
    ports: !override
      - "5434:5432"
```

This keeps the regular Compose ports unchanged while making the smoke check reach the actual API container.

- [x] **Step 3: Remove the host API substitute from the smoke script**

In `scripts/check_assessment_v2_compose.py`:

1. Remove `_start_host_api()` and its `os`/`sys` imports.
2. In `main()`, start both services:

```python
_run("up", "-d", "--force-recreate", "postgres", "api")
_wait_for_postgres()
_wait_for_api()
_assert_runtime_role()
_seed_probe_membership()
_probe_v2()
```

3. In `finally`, only run:

```python
_run("down", "--volumes", "--remove-orphans", check=False)
```

Do not use `subprocess.Popen` for uvicorn. The smoke check must fail if the API image, container command, `PYTHONPATH`, migrations, or health dependency is wrong.

- [x] **Step 4: Keep the API container independent from research/ML dependencies**

The `api` service must install only the API runtime set from its working directory:

```yaml
command: sh -c "pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

Do not add `../../requirements.txt` to the API service command. The root file
contains research/audio packages such as PyTorch and CUDA wheels that are not
needed to import or run this policy/API boundary and can make a fresh smoke
environment exhaust its disk before health becomes available. The analysis
contract remains available through the repository-root `PYTHONPATH`; it does
not require the heavy extractor stack for the descriptive transcript worker.

- [x] **Step 5: Verify the package boundary directly**

Run:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src python3.13 -c 'import app.main; print("canonical API import passed")'
cd ../..
```

Expected: no `ModuleNotFoundError: No module named 'packages'`.

- [x] **Step 6: Verify API-only dependencies in a clean environment**

Run:

```bash
RUNTIME_VENV=$(mktemp -d /tmp/lingualens-api-runtime.XXXXXX)
python3.13 -m venv "$RUNTIME_VENV"
"$RUNTIME_VENV/bin/pip" install --disable-pip-version-check --no-cache-dir -r apps/api/requirements.txt
PYTHONPATH=apps/api:src "$RUNTIME_VENV/bin/python" -c 'import app.main; print("API-only dependency import passed")'
```

Expected output includes `API-only dependency import passed` without installing
the root research/audio requirements.

- [x] **Step 7: Keep the Compose check optional**

The Compose check remains available for CI or environments that want a
container-packaging rehearsal, but it is not the primary local acceptance gate
and no acceptance claim depends on Docker being available:

```bash
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_compose.py
```

When run, the command must exercise the `api` service and clean its own volumes
on exit. The prior post-fix Compose attempt remains recorded as unavailable due
to the Docker VM I/O failure; it is not reused as native runtime evidence.

### Task 2B: Establish the primary native runtime gate

**Files:**

- Add: `scripts/check_assessment_v2_native.py`
- Test: `apps/api/tests/assessment_v2/test_native_runtime_contract.py`
- Verify: local PostgreSQL installation and native FastAPI process

- [x] **Step 1: Write the native runtime contract test first**

The test initially failed with 2 failures because the native runner did not
exist. A follow-up documentation assertion also failed once, before the setup
docs were updated. These are the recorded RED observations for this new gate.

- [x] **Step 2: Implement the native runtime runner**

The runner creates a uniquely named temporary PostgreSQL database and limited
application role, applies the assessment migrations, starts `uvicorn` as a
native subprocess, probes `/health` and `/api/v2/children`, runs the existing
PostgreSQL RLS suite, and removes only its temporary database and role.

- [x] **Step 3: Verify the native contract and API-only package boundary**

The native contract test passes 3/3; the canonical API import and clean
API-only dependency import also pass. The runner contains no Docker lifecycle
dependency.

- [x] **Step 4: Run the real native runtime gate**

PostgreSQL 16 was installed natively and the gate was run against the local
`postgres` database. The runner used its default local admin connection because
the local cluster uses trusted local development authentication:

```bash
LINGUALENS_NATIVE_ADMIN_DATABASE_URL=postgresql+psycopg://<local-admin>:<password>@127.0.0.1:5432/postgres \
  PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
```

Expected output:

```text
assessment-v2 native runtime check passed
```

Observed receipt: migrations `0001` through `0006` applied, the live RLS suite
passed `8/8`, `/health` and `POST /api/v2/children` passed through a native
FastAPI subprocess, and the temporary database and role were removed.

---

### Task 3: Make every documented startup path agree with the runtime

**Files:**

- Modify: `AGENTS.md`
- Modify: `apps/api/README.md`
- Modify: `docs/CURRENT_HANDOFF.md`
- Verify: `docs/DEVELOPMENT.md`, `docs/RENDER_BACKEND_STAGING_RUNBOOK.md`, `README.md`

- [x] **Step 1: Use the repository-root import boundary for local API startup**

The canonical local command must be:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000
```

Update any stale `PYTHONPATH=.` or bare `uvicorn` instruction that claims to start the current API.

- [x] **Step 2: Keep Render on the same boundary**

The runbook must continue to declare:

```text
Root Directory: .
Build Command: pip install -r requirements.txt -r apps/api/requirements.txt
Start Command: PYTHONPATH=apps/api:.:src uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Do not document `apps/api` as Render root while `packages.analysis_contract` is imported by the API.

- [x] **Step 3: Add a documentation consistency check to the verification notes**

Record the two commands used for proof:

```bash
cd apps/api && PYTHONPATH=.:../..:../../src python3.13 -c 'import app.main'
LINGUALENS_NATIVE_ADMIN_DATABASE_URL=postgresql+psycopg://<local-admin>:<password>@127.0.0.1:5432/postgres \
  PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
```

This prevents a green host-only test from being mistaken for deployment evidence.

---

### Task 4: Verify authorization, concurrency, and evidence semantics

**Files:**

- Verify/modify: `apps/api/app/assessment_v2/services.py`
- Verify/modify: `apps/api/app/assessment_v2/db/repositories.py`
- Verify/modify: `apps/api/app/assessment_v2/evidence_adapter.py`
- Test: `apps/api/tests/assessment_v2/test_services.py`
- Test: `apps/api/tests/assessment_v2/test_transcript_contract.py`
- Test: `apps/api/tests/assessment_v2/test_evidence_adapter.py`

- [x] **Step 1: Run the security regression test first**

Run:

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_services.py \
  -q
```

Expected: the `org_admin` test proves that capture mutation and signed-audio intent are rejected, while metadata/quality reads retain their declared read policy.

- [x] **Step 2: Preserve the role split in the service layer**

Capture mutations and signed audio access must call `_require_authorized_role(_CLINICAL_MUTATION_ROLES)`. Metadata/quality reads may use `_require_clinical_role()` only when the route contract explicitly allows read access. Do not broaden `_CLINICAL_ROLES` to solve a mutation authorization failure.

- [x] **Step 3: Run the lock-order contract test**

Run:

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_transcript_contract.py \
  -q
```

Expected: both transcript revision and attestation acquire locks in assessment → child → transcript order. A non-locking lookup may discover the assessment id, but the final transcript row used for mutation must be locked only after the assessment and child locks.

- [x] **Step 4: Run the partial-channel adapter test**

Run:

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_evidence_adapter.py \
  -q
```

Expected: a `None` source value yields `EvidenceState.INSUFFICIENT_DATA`, keeps the value unavailable, records a limitation, and does not crash Pydantic validation or turn the channel into negative evidence.

---

### Task 5: Verify the therapist workspace cannot analyze stale or ambiguous UI state

**Files:**

- Verify/modify: `apps/lingualens-app/src/lib/api.ts`
- Verify/modify: `apps/lingualens-app/src/features/assessment-v2/components/assessment-transcript-review-workspace.tsx`
- Test: `apps/lingualens-app/src/__tests__/assessment-v2-client.test.ts`
- Test: `apps/lingualens-app/src/__tests__/assessment-transcript-review-workspace.test.tsx`

- [x] **Step 1: Run client URL tests**

Run:

```bash
cd apps/lingualens-app
npm test -- src/__tests__/assessment-v2-client.test.ts
```

Expected: `http://localhost:8000/api` derives `http://localhost:8000/api/v2`; an existing `/api/v1` base is replaced by `/api/v2` exactly once.

- [x] **Step 2: Run transcript workspace tests**

Run:

```bash
npm test -- src/__tests__/assessment-transcript-review-workspace.test.tsx
```

Expected:

- a 404 with `error.code === "transcript_not_found"` opens the first-draft flow;
- another 404, such as `assessment_not_found`, remains visible as an error;
- a dirty attested transcript disables evidence generation and shows `บันทึกฉบับร่างก่อนสร้างหลักฐาน`;
- evidence generation uses the persisted content, not unsaved textarea content.

- [x] **Step 3: Keep the first-draft editor independent of review-only dirty state**

The first-draft textarea must use `disabled={busy}`. Only the review editor and evidence action may use `isDirty`; otherwise a first-draft render can reference state before initialization.

---

### Task 6: Run the candidate-wide verification gate

**Files:**

- Verify: complete candidate diff, tests, docs, migrations, and Compose files

- [x] **Step 1: Run the parent-recovery focused suite**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_compose_contract.py \
  apps/api/tests/assessment_v2/test_native_runtime_contract.py \
  apps/api/tests/assessment_v2/test_services.py \
  apps/api/tests/assessment_v2/test_transcript_contract.py \
  apps/api/tests/assessment_v2/test_evidence_adapter.py \
  -q
```

Expected: all focused tests pass; the current repaired baseline is 32 passed,
including the native runtime contract tests.

- [x] **Step 2: Run the complete assessment-v2 backend suite**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
```

Expected: no regression from the repaired baseline of 280 passed and 8 PostgreSQL tests deselected.

- [x] **Step 3: Run the frontend quality gate**

```bash
cd apps/lingualens-app
npm test
npm run typecheck
npm run lint
npm run build
npm audit --audit-level=high
```

Expected: all tests, typecheck, lint, and production build pass; high-severity audit reports zero vulnerabilities.

- [x] **Step 4: Run repository verification and inspect the diff**

```bash
cd ../..
bash scripts/check_project.sh
git diff --check
git diff --stat
git status --short
```

Do not include `.next/`, `dist/`, `.local/`, `node_modules/`, `*.tsbuildinfo`, real child data, audio, transcript text, storage keys, or secrets.

---

### Task 7: Close parent recovery without overstating assurance

**Files:**

- Modify under lock: `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/ledger.md`
- Modify under lock: `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/attempts.json`
- Regenerate: `.git/solweaver/lingualens-assessment-v2-evidence-profile-v2/candidate-manifest.json`

- [x] **Step 1: Persist exact TDD RED/GREEN evidence**

Record the original RED commands and observed failures, including:

```text
backend focused RED: 4 failed, 24 passed
frontend focused RED: 3 failed, including deriveAssessmentApiBase, assessment_not_found handling, and dirty attested evidence gating
```

Then record the repaired GREEN receipts:

```text
backend focused GREEN: 29 passed
frontend focused GREEN: 2 files, 11 tests passed
native runtime contract GREEN: 3 passed
```

Keep the observable seams and test names, not only aggregate counts.

- [x] **Step 2: Regenerate the candidate manifest after all source/doc changes**

Use the repository’s deterministic manifest tooling and include every staged, unstaged, and untracked in-scope file. Keep the previously reviewed candidate identity separate from the parent-recovery candidate identity.

- [x] **Step 3: Close the unit conservatively**

If all acceptance checks are green, set:

```text
WORK_STATUS: complete
ACCEPTANCE_STATUS: met
KNOWN_BLOCKERS: none
INDEPENDENT_ATTESTATION: not-obtained-within-budget
FINAL_STATUS: parent-completed
ASSURANCE_STATUS: final-strict-not-achieved
```

Do not set `REVIEW_READY: yes`, do not create a fourth reviewer call, and do not claim that the independent reviewer inspected the post-fix candidate.

The native PostgreSQL/FastAPI runtime gate is green, so the unit can close as
`parent-completed`. Compose availability is optional and is not a blocker for
native acceptance.

---

## หลัง Evidence V2 ผ่าน parent gate: ลำดับงาน product ถัดไป

ทำทีละ vertical slice และแต่ละ slice ต้องมี contract, API, UI, migration, synthetic walkthrough และ focused/full verification ของตัวเอง

### Slice A: Background processing และ richer transcript review

1. เพิ่ม `processing_runs` ที่มี idempotency key, retry state, provider version และ cancellation state
2. แยก worker queue ออกจาก request/response ของ FastAPI
3. เพิ่ม timestamp, speaker attribution และ uncertain-segment review แบบแก้เฉพาะช่วง
4. ให้ feature run อ้าง transcript attestation version และทำ stale เมื่อ transcript เปลี่ยน
5. ให้ Web/GUI/TUI อ่านสถานะเดียวกันจาก API และไม่สร้างผลลัพธ์ใน local storage

Acceptance: retry ไม่สร้าง evidence ซ้ำ, worker ล้มเหลวแสดงสถานะที่แก้ไขได้, และข้อมูลที่ยังไม่พอไม่ถูกแปลเป็น negative evidence

### Slice B: Longitudinal comparison

1. เพิ่ม compatibility decision ของ assessment pair ตาม age, language, protocol, activity, quality และ feature schema
2. เพิ่ม trend states `improved`, `stable`, `attention_suggested`, `indeterminate`, `not_comparable`
3. แสดงค่าต้นทางและเหตุผลที่เปรียบเทียบไม่ได้
4. ห้ามใช้ trend เป็น ASD severity หรือ numeric probability

Acceptance: ระบบเปรียบเทียบเฉพาะ assessment ที่ compatible และเก็บ clinician interpretation แยกจากค่าที่คำนวณได้

### Slice C: Clinical disposition และ report

1. เพิ่ม clinician-authored attention cues ที่ไม่ใช่ diagnosis
2. เพิ่ม disposition เช่น monitor, repeat assessment, collect more evidence, language/hearing evaluation, intervention plan และ specialist referral
3. สร้าง editable report draft จาก evidence ที่พร้อมเท่านั้น
4. ลงนามเป็น immutable snapshot พร้อม audit trail

Acceptance: report ที่ signed แล้วแก้ไม่ได้, evidence stale บล็อกการ sign-off, และ UI แยก concern, trend, diagnosis อย่างชัดเจน

### Slice D: Thin-client parity

1. ใช้ OpenAPI contract เดียวกับ Web, desktop GUI และ TUI
2. ย้ายเฉพาะ interaction/device-specific behavior ไว้ที่ client
3. ไม่ให้ GUI/TUI มี business rule หรือ local clinical result ที่ต่างจาก FastAPI
4. สร้าง contract tests ที่ยิง API เดียวกันจากทั้งสาม client

Acceptance: workflow state และ authorization เหมือนกันทุก client; ความต่างมีเฉพาะ presentation และอุปกรณ์บันทึกเสียง

## Definition of done สำหรับงานชุดนี้

- Native runtime smoke check เรียก FastAPI process และ PostgreSQL จริงและผ่าน
- เอกสาร local/Render ใช้ import boundary เดียวกัน
- focused และ full tests ผ่านตามคำสั่งด้านบน
- ไม่มี regression ต่อ consent, role, RLS, attestation, stale invalidation หรือ partial evidence
- candidate manifest และ parent-recovery ledger ตรงกับ diff ล่าสุด
- Compose เป็น optional และไม่มีการอ้างว่า Compose ผ่านถ้ายังไม่ได้รัน
- รายงานสถานะชัดเจนว่า `parent-completed` ได้ แต่ `final-strict-not-achieved` เพราะ review budget หมดและไม่มี reviewer ยืนยัน post-fix candidate
