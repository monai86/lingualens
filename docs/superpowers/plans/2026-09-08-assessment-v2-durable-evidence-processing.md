# Assessment V2 Durable Evidence Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยนการสร้าง Evidence V2 จากงาน synchronous ใน FastAPI request ให้เป็นงาน durable background processing ที่ retry, reclaim, cancel และติดตามสถานะได้ โดยยังคง consent, care-team, transcript attestation, provenance และ non-diagnostic safety boundary เดิม

**Architecture:** ขยายตาราง `processing_runs` และ worker process ที่มีอยู่ แทนการเพิ่ม Redis, Celery หรือ queue service ใหม่ งาน evidence จะผูกกับ assessment และ transcript revision ที่รับรองแล้ว ใช้ tenant-scoped lease เพื่อกัน worker ซ้ำ และ persist evidence กับสถานะงานใน transaction เดียวกัน Web เป็น thin client ที่อ่านสถานะจาก FastAPI เท่านั้น; Docker เป็น optional packaging check ส่วน native FastAPI + PostgreSQL เป็น acceptance path หลัก

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL/Supabase RLS, Python 3.13, Next.js 16, React 19, TypeScript, pytest, Vitest, Playwright, Figma handoff artifacts

---

## ตำแหน่งของแผนนี้

แผนนี้คือ **Slice A1** หลัง Evidence V2 parent recovery ผ่านแล้ว และต้องเปิด
assurance unit ใหม่เมื่อเริ่ม implementation:

```text
lingualens/assessment-v2/durable-evidence-processing
```

assurance unit เดิม `lingualens/assessment-v2/evidence-profile-v2` จบที่
`parent-completed` แล้ว ห้ามแก้ ledger, reviewer packet หรือ review budget ของ
unit เดิมเพื่อรองรับงานนี้

งานที่ยังไม่อยู่ใน A1:

- A2: transcript segments, timestamps, speaker attribution และ uncertain-only review
- B: longitudinal compatibility และ trend
- C: clinician disposition และ signed report
- D: GUI/TUI contract parity
- production Supabase credentials, deployment, migration ของข้อมูลจริง หรือ clinical validation

GUI และ TUI เดิมต้องไม่ถูกลบหรือเพิ่ม business rule ใหม่ใน A1 ทั้งสอง surface
จะย้ายมาใช้ contract สุดท้ายใน Slice D หลัง API state model คงที่

ไม่มี commit, push, merge หรือ deploy ในแผนนี้จนกว่า owner จะอนุญาตโดยตรง

## Execution preflight

worktree `assessment-web-capture-v2` ยังมี candidate รอบก่อนทั้ง tracked และ
untracked อยู่บน branch `codex/assessment-web-capture` ส่วนไฟล์แผนนี้เป็น
post-phase planning artifact และไม่ใช่การเปิด assurance unit เดิมอีกครั้ง

ก่อนเริ่ม Task 1 ให้หยุดที่ขอบเขต authorization แล้วทำตามลำดับนี้:

1. ตรวจว่า complete diff รอบก่อนยังตรงกับ verification receipts ที่รายงานไว้
2. ขอ owner อนุญาต checkpoint/commit candidate เดิมโดยระบุไฟล์และ commit message
3. หลัง checkpoint เท่านั้น จึงสร้าง branch/worktree ใหม่จาก baseline นั้น เช่น
   `codex/durable-evidence-processing` และเปิด assurance unit A1 ใหม่

ถ้า owner เลือกทำ A1 ต่อใน dirty worktree เดิม ต้องบันทึกเป็นการยอมรับ combined
diff โดยชัดเจน; ห้ามถือว่าเป็นค่าเริ่มต้น เพราะจะทำให้ rollback และ candidate
identity ของสอง slice ปะปนกัน

## เหตุผลที่ทำ A1 ก่อน A2

ปัจจุบัน `POST /api/v2/assessments/{assessment_id}/evidence-runs` เรียก extractor
และเขียนผลทั้งหมดภายใน HTTP request เดียว หน้าเว็บจึงรู้เพียงสำเร็จ/ล้มเหลว
และใช้ local boolean `evidenceReady` ชั่วคราว ขณะเดียวกัน Capture V2 มี
`processing_runs`, idempotency, attempt count และ PostgreSQL worker อยู่แล้ว
แต่ยังขาด lease expiry, result linkage, clinician retry/cancel และ evidence stage

A1 จึงเพิ่มเฉพาะกลไกที่จำเป็นให้ processing state เป็น backend-owned ก่อน
จากนั้น A2 จะเพิ่ม segment data โดยไม่ต้องออกแบบ queue และ recovery ซ้ำ

## Contract ที่ต้อง freeze ก่อนเขียนโค้ด

### Processing stages และ states

```text
stage:
  upload_verification | quality_analysis | cleanup | evidence_extraction

state:
  queued | running | succeeded | failed | cancelled

queued --claim--> running --complete--> succeeded
  |                  |
  |                  +--retryable failure--> queued (available_at + backoff)
  |                  +--terminal failure----> failed
  |                  +--cancel request------> cancelled
  +--cancel-------------------------------> cancelled

running + expired lease --reclaim--> running with a new lease token
```

ห้ามเพิ่ม state ชื่อ `normal`, `negative`, `diagnosed` หรือ state ที่ตีความ
clinical outcome งาน processing บอกเฉพาะสถานะปฏิบัติการ

### HTTP contract

```text
POST /api/v2/assessments/{assessment_id}/evidence-runs
  -> 202 EvidenceProcessingResponse

GET /api/v2/assessments/{assessment_id}/evidence-processing-run
  -> 200 EvidenceProcessingResponse | 404 processing_run_not_found

GET /api/v2/processing-runs/{processing_run_id}
  -> 200 ProcessingRunResponse

POST /api/v2/processing-runs/{processing_run_id}/retry
  body: {"expected_version": 4}
  -> 200 ProcessingRunResponse

POST /api/v2/processing-runs/{processing_run_id}/cancel
  body: {"expected_version": 4}
  -> 200 ProcessingRunResponse

GET /api/v2/assessments/{assessment_id}/evidence
  -> contract เดิม; 404 จนกว่า worker จะ persist ผลสำเร็จ
```

`ProcessingRunResponse` ต้องไม่ส่ง lease token, transcript content, storage key,
provider credential หรือ raw exception:

```json
{
  "id": "opaque_processing_run_id",
  "stage": "evidence_extraction",
  "state": "queued",
  "attempt_count": 0,
  "max_attempts": 3,
  "available_at": "2026-09-08T13:00:00Z",
  "error_code": null,
  "result_available": false,
  "can_retry": false,
  "can_cancel": true,
  "version": 1
}
```

`result_available` เป็น `true` เฉพาะ evidence job ที่มี `evidence_run_id`
ซึ่ง persist สำเร็จแล้ว; capture stages เดิมคืน `false` และยังใช้ `state` เป็น
contract หลัก ส่วน `can_retry`/`can_cancel` คำนวณโดย backend เพื่อไม่ให้ Web,
GUI หรือ TUI ทำซ้ำ business rule เอง การกด action ยังต้องส่ง `expected_version`
เพราะสิทธิ์และสถานะอาจเปลี่ยนหลังการอ่าน

### Idempotency identity

FastAPI สร้าง canonical identity ฝั่ง server จากข้อมูลที่ versioned แล้ว:

```text
[assessment_id, transcript_revision_id, pipeline_version, feature_schema_version]

idempotency_key = "evidence:v1:" + sha256(canonical_json(identity)).hexdigest()
```

POST ซ้ำสำหรับ identity เดิมต้องคืน processing run เดิม ไม่สร้าง job หรือ
evidence ซ้ำ ถ้า run จบแบบ `failed` therapist ต้องกด retry อย่างชัดเจน ถ้า
ผู้ใช้ยกเลิกเองสามารถกดเริ่มใหม่อย่างชัดเจนบน run เดิม ส่วน system-cancelled
run จาก consent/transcript/analysis-contract supersession ห้ามเริ่มใหม่
pipeline/schema ที่เปลี่ยนทำให้ identity ใหม่และ cancel งาน contract เก่าที่ยัง
ไม่เสร็จ key ที่ persist ต้องยาวไม่เกินคอลัมน์ `String(128)` เดิม

### Retry และ lease policy

```text
max_attempts = 3
attempt 1 failure -> available_at = now + 5 seconds
attempt 2 failure -> available_at = now + 30 seconds
attempt 3 failure -> state = failed
lease duration = 120 seconds
```

`attempt_count` นับ claim ที่เริ่มทำจริงและ `version` เพิ่มทุก state mutation
ถ้า lease หมดหลัง claim ครั้งสุดท้ายให้จบเป็น `failed` แทนการ reclaim ไม่จำกัด
ข้อผิดพลาดชั่วคราว เช่น worker/process interruption ใช้ retry policy นี้ ส่วน
`consent_revoked`, `transcript_superseded`, `transcript_not_attested`,
`analysis_contract_superseded` และ `cancel_requested` เปลี่ยนเป็น `cancelled`
โดยไม่ automatic retry; เฉพาะ `cancel_requested` ที่ผู้ใช้สั่งเองเท่านั้นที่
explicit retry สามารถ requeue run เดิมได้

## Definition of done

1. HTTP request ไม่รัน extractor โดยตรงและตอบ `202` หลัง durable enqueue
2. POST ซ้ำคืน run เดิม และ worker ซ้ำไม่สร้าง evidence ซ้ำ
3. worker crash หลัง claim สามารถ reclaim หลัง lease หมด; worker token เก่าปิดงานไม่ได้
4. consent withdrawal, transcript revision ใหม่ หรือ analysis contract ใหม่ cancel งานเก่าที่ไม่เสร็จ
5. failed job และงานที่ผู้ใช้ยกเลิกเองเริ่มใหม่ได้; queued/running job cancel ได้
6. partial/insufficient analysis ยัง persist เป็น explicit evidence limitation ไม่กลายเป็น zero/negative
7. reload หน้าเว็บแล้วยังติดตาม run เดิมได้โดยไม่พึ่ง local/session storage
8. Figma/API map ครอบคลุม H10, H11, E07 และ E09 ก่อน freeze frontend state
9. native PostgreSQL gate รัน enqueue → worker → evidence read และ RLS ผ่าน
10. ไม่มี Docker, Redis หรือ Celery เป็น requirement ของ acceptance
11. ไม่มี diagnosis, ASD probability หรือ Thai clinical-validation claim
12. final-strict parent verification และ fresh read-only reviewer ให้ verdict `ship`

## โครงสร้างไฟล์

### Backend contract และ persistence

- Modify: `apps/api/app/assessment_v2/domain/models.py`
- Modify: `apps/api/app/assessment_v2/db/models.py`
- Add: `apps/api/app/assessment_v2/db/migrations/versions/0007_durable_evidence_jobs.py`
- Modify: `apps/api/app/assessment_v2/db/repositories.py`
- Add: `apps/api/app/assessment_v2/evidence_worker.py`
- Modify: `apps/api/app/assessment_v2/worker_runtime.py`
- Modify: `apps/api/app/assessment_v2/services.py`
- Modify: `apps/api/app/assessment_v2/schemas.py`
- Modify: `apps/api/app/assessment_v2/routes.py`

### Backend tests

- Add: `apps/api/tests/assessment_v2/test_processing_contract.py`
- Add: `apps/api/tests/assessment_v2/test_processing_db_models.py`
- Add: `apps/api/tests/assessment_v2/test_evidence_processing_repository.py`
- Add: `apps/api/tests/assessment_v2/test_evidence_processing_worker.py`
- Add: `apps/api/tests/assessment_v2/test_postgres_processing_leases.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_db_models.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_repository.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_routes.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_upload_service.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_runtime.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_route_integration.py`
- Modify: `apps/api/tests/assessment_v2/test_schemas.py`
- Modify: `apps/api/tests/assessment_v2/test_migrations.py`
- Modify: `apps/api/tests/assessment_v2/test_native_runtime_contract.py`
- Modify: `apps/api/tests/assessment_v2/test_postgres_rls.py`

### Therapist web

- Modify: `apps/lingualens-app/src/services/assessment-v2-client.ts`
- Add: `apps/lingualens-app/src/features/assessment-v2/components/assessment-processing-status.tsx`
- Modify: `apps/lingualens-app/src/features/assessment-v2/components/assessment-transcript-review-workspace.tsx`
- Modify: `apps/lingualens-app/src/features/assessment-v2/components/assessment-evidence-workspace.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-v2-client.test.ts`
- Add: `apps/lingualens-app/src/__tests__/assessment-processing-status.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-capture-workspace.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-recording-upload.test.ts`
- Modify: `apps/lingualens-app/src/__tests__/assessment-transcript-review-workspace.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-evidence-workspace.test.tsx`
- Modify: `apps/lingualens-app/e2e/assessment-v2-transcript.smoke.spec.ts`

### Design, docs และ runtime proof

- Modify: `docs/ux/therapist-workflow/frame-inventory.csv`
- Modify: `docs/ux/therapist-workflow/api-screen-contract-map.md`
- Modify: `docs/ux/therapist-workflow/prototype-scenarios.md`
- Modify: `docs/ux/therapist-workflow/figma-delivery-manifest.md`
- Modify: Figma file `YOh8m47gDzPuX2EBZsPCcy`, frames H10/H11/E07/E09
- Modify: `scripts/check_assessment_v2_native.py`
- Modify: `README.md`
- Modify: `DEVELOPER_SETUP.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Modify: `docs/CURRENT_HANDOFF.md`
- Modify: `CHANGELOG.md`

---

### Task 1: Freeze Figma and API processing states

**Files:**

- Modify: `docs/ux/therapist-workflow/frame-inventory.csv`
- Modify: `docs/ux/therapist-workflow/api-screen-contract-map.md`
- Modify: `docs/ux/therapist-workflow/prototype-scenarios.md`
- Modify: `docs/ux/therapist-workflow/figma-delivery-manifest.md`
- Modify: Figma frames `H10`, `H11`, `E07`, `E09`

- [ ] **Step 1: Add the exact processing variants to the frame inventory**

Add H10 variants for desktop, tablet and mobile:

```text
queued: งานถูกบันทึกแล้วและกำลังรอ worker
running: กำลังประมวลผล พร้อม attempt count
retry_scheduled: ระบุว่าจะลองใหม่โดยไม่แสดง raw exception
failed: ระบุสิ่งที่ยังถูกเก็บไว้ พร้อมปุ่ม “ลองประมวลผลอีกครั้ง”
cancelled: ระบุเหตุผลเชิง workflow, ทางกลับไป transcript และแสดง “เริ่มใหม่”
           เฉพาะเมื่อ backend ส่ง can_retry=true
succeeded: แสดงปุ่มเปิดโปรไฟล์หลักฐาน
```

- [ ] **Step 2: Update the API-screen contract map**

H10 ต้อง map ไปยัง enqueue/current-run/get-run/retry/cancel endpoints ข้างต้น
H11 ต้อง map transcript attestation ไปยัง enqueue เท่านั้น และ E07/E09 ต้อง
ระบุว่า browser ห้ามสร้างหรือเติม evidence เอง

- [ ] **Step 3: Update the working Figma frames**

ใน Figma file `YOh8m47gDzPuX2EBZsPCcy` ให้ H10 ใช้ component state เดียวกัน
ทุก viewport, มี `aria-live` equivalent annotation, action สูงอย่างน้อย 44px,
และไม่ใช้สีเพียงอย่างเดียวแยก state

- [ ] **Step 4: Walk the five recovery paths before frontend code**

ใช้ synthetic assessment เท่านั้นและบันทึกผลใน `prototype-scenarios.md`:

```text
queued -> reload -> same run
running -> cancel -> cancelled
user-cancelled -> explicit retry -> queued
failed -> retry -> queued -> succeeded
transcript superseded -> E07 -> old run cancelled -> enqueue current revision
```

Expected: ผู้ทดสอบบอกได้ว่างานถูกบันทึกหรือยัง, อะไรยังอยู่, อะไรถูกบล็อก และ
ต้องทำอะไรต่อ โดยไม่เห็น diagnosis/probability wording

- [ ] **Step 5: Keep the Figma manifest honest**

หาก Presentation-mode walkthrough หรือ export ยังไม่ครบ ให้คง
`Manifest status: working skeleton` และ `Accepted version: not frozen`; ห้าม
mark accepted จาก repository docs เพียงอย่างเดียว

---

### Task 2: Define the durable processing contract

**Files:**

- Modify: `apps/api/app/assessment_v2/domain/models.py`
- Add: `apps/api/tests/assessment_v2/test_processing_contract.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that require an evidence stage, versioned public snapshot and
lease-bearing private work item:

```python
def test_processing_snapshot_exposes_recovery_state_without_lease_token() -> None:
    snapshot = ProcessingRunSnapshot(
        id="processing_run_opaque_01",
        organization_id="org_opaque_01",
        recording_id=None,
        assessment_id="assessment_opaque_01",
        transcript_revision_id="transcript_revision_opaque_01",
        stage=ProcessingRunStage.EVIDENCE_EXTRACTION,
        state=ProcessingRunState.QUEUED,
        attempt_count=0,
        max_attempts=3,
        available_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        error_code=None,
        result_available=False,
        can_retry=False,
        can_cancel=True,
        version=1,
    )

    assert snapshot.stage is ProcessingRunStage.EVIDENCE_EXTRACTION
    assert snapshot.result_available is False
    assert not hasattr(snapshot, "lease_token")
```

Also test that `max_attempts < 1`, `version < 1`, both target IDs missing, or a
recording target combined with an evidence target raises `ValueError`.

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_processing_contract.py -q
```

Expected: fail because `EVIDENCE_EXTRACTION` and the new snapshot fields do not
exist

- [ ] **Step 3: Add the minimal domain types**

Implement this public shape:

```python
class ProcessingRunStage(StrEnum):
    UPLOAD_VERIFICATION = "upload_verification"
    QUALITY_ANALYSIS = "quality_analysis"
    CLEANUP = "cleanup"
    EVIDENCE_EXTRACTION = "evidence_extraction"


@dataclass(frozen=True, slots=True)
class ProcessingRunSnapshot:
    id: str
    organization_id: str
    recording_id: str | None
    assessment_id: str | None
    transcript_revision_id: str | None
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int
    max_attempts: int
    available_at: datetime
    error_code: str | None
    result_available: bool
    can_retry: bool
    can_cancel: bool
    version: int
```

The `__post_init__` implementation must require exactly one target family:
recording for capture stages, or assessment plus transcript revision for
`evidence_extraction`. Capture snapshots always expose both action flags as
false; evidence flags follow the server-owned state/reason policy above

- [ ] **Step 4: Run GREEN and refactor**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_processing_contract.py \
  apps/api/tests/assessment_v2/test_transcript_contract.py \
  apps/api/tests/assessment_v2/test_evidence_contract.py -q
```

Expected: all selected tests pass; public snapshots contain no lease token or
transcript content

---

### Task 3: Migrate `processing_runs` without breaking Capture V2

**Files:**

- Add: `apps/api/app/assessment_v2/db/migrations/versions/0007_durable_evidence_jobs.py`
- Modify: `apps/api/app/assessment_v2/db/models.py`
- Add: `apps/api/tests/assessment_v2/test_processing_db_models.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_db_models.py`
- Modify: `apps/api/tests/assessment_v2/test_migrations.py`
- Modify: `apps/api/tests/assessment_v2/test_postgres_rls.py`

- [ ] **Step 1: Write failing model and migration tests**

Require these columns on `processing_runs`:

```text
assessment_id nullable
transcript_revision_id nullable
evidence_run_id nullable
max_attempts not null default 3
lease_token nullable
lease_expires_at nullable
cancel_requested_at nullable
completed_at nullable
pipeline_version nullable
feature_schema_version nullable
version not null default 1
```

Require PostgreSQL constraints for stage/target consistency, `max_attempts >= 1`,
`version >= 1`, tenant-composite foreign keys, and the existing organization
idempotency uniqueness. Preserve the capture index and add claim-path indexes
covering `(organization_id, stage, state, available_at)` and expired leases;
assert every index/constraint name fits PostgreSQL's 63-character limit

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_processing_db_models.py \
  apps/api/tests/assessment_v2/test_capture_db_models.py \
  apps/api/tests/assessment_v2/test_migrations.py \
  apps/api/tests/assessment_v2/test_postgres_rls.py -q
```

Expected: fail because revision `0007_durable_evidence_jobs` and the new columns
do not exist

- [ ] **Step 3: Implement migration 0007**

Use revision identifiers shorter than 32 characters:

```python
revision = "0007_durable_evidence_jobs"
down_revision = "0006_evidence_profiles"
```

Alter `recording_id` to nullable, add the columns above, extend the stage check,
and add a target check equivalent to:

```sql
(
  stage IN ('upload_verification', 'quality_analysis', 'cleanup')
  AND recording_id IS NOT NULL
  AND assessment_id IS NULL
  AND transcript_revision_id IS NULL
)
OR
(
  stage = 'evidence_extraction'
  AND recording_id IS NULL
  AND assessment_id IS NOT NULL
  AND transcript_revision_id IS NOT NULL
)
```

The downgrade must remove only 0007 additions and never delete evidence jobs.
Before restoring `recording_id` as non-null, explicitly abort downgrade with a
clear migration error when any `evidence_extraction` row exists. Prove both the
safe refusal on a populated database and successful downgrade on an empty fresh
database

- [ ] **Step 4: Update the ORM model**

Add matching nullable foreign keys and private lease fields to
`ProcessingRunRecord`. Do not add transcript content, raw provider payload or
storage URL columns

- [ ] **Step 5: Preserve and extend RLS**

The existing `processing_runs` organization policy must continue to enforce
`app.current_organization_id`. Add adversarial rows for evidence jobs and prove
that another organization cannot read, claim, retry, cancel or link a result

- [ ] **Step 6: Run GREEN plus fresh upgrade/downgrade**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_processing_db_models.py \
  apps/api/tests/assessment_v2/test_capture_db_models.py \
  apps/api/tests/assessment_v2/test_migrations.py -q
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_migrations.py
```

Expected: model/migration tests pass; populated downgrade refuses without data
loss, while the empty migration smoke upgrades through 0007, downgrades to base
and upgrades again

---

### Task 4: Add atomic enqueue, lease, retry and cancellation repository behavior

**Files:**

- Modify: `apps/api/app/assessment_v2/db/repositories.py`
- Modify: `scripts/check_assessment_v2_native.py`
- Add: `apps/api/tests/assessment_v2/test_evidence_processing_repository.py`
- Add: `apps/api/tests/assessment_v2/test_postgres_processing_leases.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_repository.py`
- Modify: `apps/api/tests/assessment_v2/test_native_runtime_contract.py`

- [ ] **Step 1: Write repository RED tests for enqueue and idempotency**

Test this sequence with synthetic IDs/content:

```python
first = repo.enqueue_current_evidence_processing(scope, assessment.id, correlation_id)
second = repo.enqueue_current_evidence_processing(scope, assessment.id, correlation_id)

assert first.id == second.id
assert first.state is ProcessingRunState.QUEUED
assert count_processing_runs(session, stage="evidence_extraction") == 1
```

Also require active consent, current care-team access, assigned therapist or
supervisor role, current transcript state `attested`, and current protocol
selection. Test the canonical JSON hash directly: identical material is stable,
changing any one identity field changes the key, and the persisted key is at
most 128 characters

- [ ] **Step 2: Write state-machine RED tests with an injected clock**

Do not sleep in tests. Advance a fake clock through:

```text
expired running lease -> new token and incremented attempt
expired lease at max_attempts -> failed, not reclaimed
old token completes after reclaim -> rejected, no evidence row
retryable failure attempt 1 -> queued + 5 seconds
retryable failure attempt 2 -> queued + 30 seconds
retryable failure attempt 3 -> failed
queued cancel -> cancelled immediately
running cancel -> cancel_requested_at set; completion cancels without evidence
user-cancelled -> explicit retry resets attempt/error/cancel fields -> queued
system-cancelled -> explicit retry rejected
new transcript revision -> queued/running old-revision jobs cancelled
consent withdrawal -> queued/running evidence jobs cancelled
pipeline/schema change -> old-contract job cancelled
```

- [ ] **Step 3: Write a real PostgreSQL concurrency RED test**

In `test_postgres_processing_leases.py`, use two independent SQLAlchemy sessions
against the temporary native database. Hold the first claimant's transaction
open, attempt the second claim, and prove `FOR UPDATE SKIP LOCKED` gives exactly
one lease owner without blocking. Also prove expired-lease reclaim and stale
token rejection on PostgreSQL, not SQLite

Add this test file to the PostgreSQL target list in
`scripts/check_assessment_v2_native.py`; update `test_native_runtime_contract.py`
first so omission from the native gate is itself a failing contract

- [ ] **Step 4: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_evidence_processing_repository.py -q
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
```

Expected: unit tests fail because enqueue/lease/recovery methods do not exist;
the native gate reaches the new PostgreSQL lease test and fails for the same
missing behavior

- [ ] **Step 5: Implement enqueue with the established lock order**

Use this order in every protected mutation:

```text
assessment row -> child row -> current transcript row -> processing run row
```

Serialize `[assessment_id, transcript_revision_id, pipeline_version,
feature_schema_version]` as canonical JSON and persist
`evidence:v1:{sha256_hex}`. If an existing row has the same key, return it.
Do not silently requeue a failed or cancelled row; explicit recovery owns that
transition. Enqueueing a new analysis contract cancels old-contract queued or
running jobs before inserting the new identity

- [ ] **Step 6: Implement private lease methods**

Add repository methods with these signatures:

```python
def claim_next_evidence_processing_run(self) -> EvidenceWorkItem | None: ...
def complete_evidence_processing_run(
    self, item: EvidenceWorkItem, adapted: AdaptedEvidence
) -> EvidenceRunSnapshot | None: ...
def fail_evidence_processing_run(
    self, item: EvidenceWorkItem, error_code: str, *, retryable: bool
) -> ProcessingRunSnapshot: ...
```

`EvidenceWorkItem` carries a private random lease token and transcript content
with `repr=False`. Completion must compare run ID, organization, state, lease
token, current transcript ID/checksum, attestation, active consent and protocol
plus current pipeline/schema constants before writing any evidence. Claim uses
`SELECT ... FOR UPDATE SKIP LOCKED`, increments `attempt_count` and `version`,
and issues a new token. Completion writes evidence/result linkage and marks the
run succeeded in one transaction; stale-token completion or failure performs no
mutation

- [ ] **Step 7: Implement therapist recovery methods**

```python
def retry_evidence_processing_run(
    self, scope: AccessScope, run_id: str, expected_version: int, correlation_id: str
) -> ProcessingRunSnapshot: ...

def request_evidence_processing_cancellation(
    self, scope: AccessScope, run_id: str, expected_version: int, correlation_id: str
) -> ProcessingRunSnapshot: ...
```

Only evidence jobs are allowed. Retry accepts terminal `failed` or `cancelled`
with `error_code=cancel_requested`, then resets attempt/error/cancel/lease fields.
System-cancelled runs are not retryable. Cancel accepts `queued` or `running`;
stale expected version returns `stale_processing_run_version`. Every capture and
evidence processing-run mutation increments `version`; snapshots derive
`can_retry` and `can_cancel` from server state and safe cancellation reason

- [ ] **Step 8: Preserve audit privacy**

Emit only actions and safe fields:

```text
processing_run.queued
processing_run.claimed
processing_run.retry_scheduled
processing_run.retry_requested
processing_run.cancel_requested
processing_run.cancelled
processing_run.failed
processing_run.succeeded
```

Audit detail must exclude assessment ID, child ID, transcript ID/content,
storage key, provider payload and raw exception

- [ ] **Step 9: Run GREEN, PostgreSQL concurrency and Capture V2 regressions**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_evidence_processing_repository.py \
  apps/api/tests/assessment_v2/test_capture_repository.py -q
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
```

Expected: unit and native PostgreSQL lease tests pass; existing upload/quality/
cleanup behavior remains green; no test uses wall-clock sleep

---

### Task 5: Move extraction into the one database-backed worker process

**Files:**

- Add: `apps/api/app/assessment_v2/evidence_worker.py`
- Modify: `apps/api/app/assessment_v2/worker_runtime.py`
- Add: `apps/api/tests/assessment_v2/test_evidence_processing_worker.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_runtime.py`

- [ ] **Step 1: Write worker RED tests**

Require successful extraction, explicit insufficient data, retryable failure,
cancel-before-persist and stale lease rejection:

```python
def test_worker_persists_one_result_for_an_attested_revision() -> None:
    result = worker.run_once()
    assert result.status == "evidence_recorded"
    assert repository.completed_count == 1
    assert repository.failed_count == 0


def test_worker_preserves_insufficient_data_as_a_completed_job() -> None:
    result = worker.run_once()
    assert result.status == "evidence_recorded"
    assert repository.saved_evidence.state is EvidenceState.INSUFFICIENT_DATA
```

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_evidence_processing_worker.py -q
```

Expected: fail because `EvidenceProcessingWorker` does not exist

- [ ] **Step 3: Implement the narrow worker**

Use the existing scientific boundaries only:

```python
analysis = extract_reviewed_transcript(
    item.transcript,
    protocol_version_key=item.protocol_version_key,
)
adapted = adapt_analysis_result(
    analysis,
    input_sha256=item.transcript.content_sha256,
    protocol_version_key=item.protocol_version_key,
    expected_feature_schema_version=item.feature_schema_version,
)
saved = repository.complete_evidence_processing_run(item, adapted)
```

The worker must not catch an insufficient/partial analysis and replace it with
zero values. It must not log `item`, transcript content or raw exceptions

- [ ] **Step 4: Run capture and evidence handlers in one supervised loop**

Keep `python -m app.assessment_v2.worker_runtime` as the entrypoint. One cycle
may process at most one capture job and one evidence job per configured tenant,
then sleep only if both handlers are idle. Keep
`LINGUALENS_CAPTURE_WORKER_ORGANIZATION_IDS` as the explicit PostgreSQL RLS
allowlist until a separately reviewed service-identity design exists

- [ ] **Step 5: Run GREEN**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_evidence_processing_worker.py \
  apps/api/tests/assessment_v2/test_reviewed_transcript_worker.py \
  apps/api/tests/assessment_v2/test_capture_worker.py \
  apps/api/tests/assessment_v2/test_capture_runtime.py -q
```

Expected: all worker tests pass; no Redis/Celery requirement appears in the
Assessment V2 runtime

---

### Task 6: Replace the synchronous API action with durable enqueue and recovery endpoints

**Files:**

- Modify: `apps/api/app/assessment_v2/services.py`
- Modify: `apps/api/app/assessment_v2/schemas.py`
- Modify: `apps/api/app/assessment_v2/routes.py`
- Modify: `apps/api/tests/assessment_v2/test_transcript_routes.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_routes.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_upload_service.py`
- Modify: `apps/api/tests/assessment_v2/test_capture_route_integration.py`
- Modify: `apps/api/tests/assessment_v2/test_schemas.py`

- [ ] **Step 1: Write API RED tests**

Test the exact external behavior:

```python
response = client.post("/api/v2/assessments/assessment_opaque_01/evidence-runs")
assert response.status_code == 202
assert response.json()["processing_run"]["state"] == "queued"
assert "lease_token" not in response.text
assert "content" not in response.text

repeat = client.post("/api/v2/assessments/assessment_opaque_01/evidence-runs")
assert repeat.json()["processing_run"]["id"] == response.json()["processing_run"]["id"]
```

Also test current-run lookup after reload, authorized retry/cancel, explicit
restart after user cancellation, rejected restart after system cancellation,
cross-tenant 404, org-admin mutation denial, stale expected version and consent
withdrawal. Existing capture endpoint tests must accept the additive scheduler/
version/action fields while preserving their prior values

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_transcript_routes.py \
  apps/api/tests/assessment_v2/test_capture_routes.py \
  apps/api/tests/assessment_v2/test_capture_upload_service.py \
  apps/api/tests/assessment_v2/test_capture_route_integration.py -q
```

Expected: fail because the existing POST returns a completed evidence profile
with status 201 and recovery endpoints do not exist

- [ ] **Step 3: Add strict schemas**

Implement:

```python
class ProcessingRunActionRequest(_StrictModel):
    expected_version: int = Field(strict=True, ge=1)


class ProcessingRunResponse(_StrictModel):
    id: str = Field(min_length=1, max_length=64)
    stage: ProcessingRunStage
    state: ProcessingRunState
    attempt_count: int = Field(strict=True, ge=0, le=1000)
    max_attempts: int = Field(strict=True, ge=1, le=1000)
    available_at: datetime
    error_code: str | None = Field(default=None, min_length=1, max_length=64)
    result_available: bool
    can_retry: bool
    can_cancel: bool
    version: int = Field(strict=True, ge=1)


class EvidenceProcessingResponse(_StrictModel):
    processing_run: ProcessingRunResponse
```

- [ ] **Step 4: Add service methods and safe errors**

`AssessmentService` must expose enqueue/current/retry/cancel methods and reuse
the existing evidence-run role boundary. Add safe mappings for:

```text
processing_run_not_found -> 404
processing_run_not_retryable -> 409
processing_run_not_cancellable -> 409
stale_processing_run_version -> 409
```

- [ ] **Step 5: Change the POST route to 202**

The route must call enqueue only; remove direct calls to
`extract_reviewed_transcript()` and `adapt_analysis_result()` from the HTTP
request path. Keep `GET /evidence` unchanged

- [ ] **Step 6: Run GREEN and inspect OpenAPI**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_transcript_routes.py \
  apps/api/tests/assessment_v2/test_capture_routes.py \
  apps/api/tests/assessment_v2/test_capture_upload_service.py \
  apps/api/tests/assessment_v2/test_capture_route_integration.py \
  apps/api/tests/assessment_v2/test_schemas.py -q
PYTHONPATH=apps/api:src python3.13 -c \
  'from app.main import app; schema=app.openapi(); assert schema["paths"]["/api/v2/assessments/{assessment_id}/evidence-runs"]["post"]["responses"].get("202")'
```

Expected: focused tests pass and OpenAPI declares 202

---

### Task 7: Make the therapist web follow backend-owned processing state

**Files:**

- Modify: `apps/lingualens-app/src/services/assessment-v2-client.ts`
- Add: `apps/lingualens-app/src/features/assessment-v2/components/assessment-processing-status.tsx`
- Modify: `apps/lingualens-app/src/features/assessment-v2/components/assessment-transcript-review-workspace.tsx`
- Modify: `apps/lingualens-app/src/features/assessment-v2/components/assessment-evidence-workspace.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-v2-client.test.ts`
- Add: `apps/lingualens-app/src/__tests__/assessment-processing-status.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-capture-workspace.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-recording-upload.test.ts`
- Modify: `apps/lingualens-app/src/__tests__/assessment-transcript-review-workspace.test.tsx`
- Modify: `apps/lingualens-app/src/__tests__/assessment-evidence-workspace.test.tsx`

- [ ] **Step 1: Write client and UI RED tests**

Require these user-visible behaviors:

```text
click create -> enqueue once -> show “บันทึกงานแล้ว กำลังรอประมวลผล”
reload -> fetch current server run -> continue polling same ID
running -> show attempt and cancel action
failed -> show safe message and explicit retry action
user-cancelled + can_retry -> show preserved transcript and explicit restart
system-cancelled + !can_retry -> show preserved transcript and next valid action
succeeded -> fetch evidence -> show profile link/content
stale transcript -> stop polling old run and offer current reprocessing
API outage -> never show success or synthesize evidence locally
```

- [ ] **Step 2: Run RED**

```bash
cd apps/lingualens-app
npm test -- \
  src/__tests__/assessment-v2-client.test.ts \
  src/__tests__/assessment-processing-status.test.tsx \
  src/__tests__/assessment-capture-workspace.test.tsx \
  src/__tests__/assessment-recording-upload.test.ts \
  src/__tests__/assessment-transcript-review-workspace.test.tsx \
  src/__tests__/assessment-evidence-workspace.test.tsx
```

Expected: fail because the client still expects a synchronous profile and the
processing status component does not exist

- [ ] **Step 3: Extend the client contract**

Add these methods with strict TypeScript return types:

```typescript
queueEvidence(assessmentId: string): Promise<AssessmentV2EvidenceProcessing>;
getCurrentEvidenceProcessingRun(assessmentId: string): Promise<AssessmentV2EvidenceProcessing>;
getProcessingRun(runId: string): Promise<AssessmentV2ProcessingRun>;
retryProcessingRun(runId: string, expectedVersion: number): Promise<AssessmentV2ProcessingRun>;
cancelProcessingRun(runId: string, expectedVersion: number): Promise<AssessmentV2ProcessingRun>;
```

Remove the synchronous `createEvidence(): Promise<AssessmentV2EvidenceProfile>`
contract after all callers and tests move to `queueEvidence`. Extend
`AssessmentV2ProcessingRun` with the evidence stage, scheduler/result fields,
backend-owned `can_retry`/`can_cancel`, and `version`; update existing capture
fixtures rather than making the new contract optional

- [ ] **Step 4: Implement `AssessmentProcessingStatus`**

The component polls only while state is `queued` or `running`, starts at a
2-second interval, backs off transient API errors to at most 15 seconds, pauses
while the document is hidden, resumes on visibility/reload, and has no arbitrary
client timeout. It uses `role="status"`/`aria-live="polite"`, clears timers on
unmount, renders actions only from `can_retry`/`can_cancel`, and maps only safe
error codes to Thai copy. It must not write evidence, run ID or clinical content
to localStorage/sessionStorage

- [ ] **Step 5: Replace `evidenceReady` local state**

`assessment-transcript-review-workspace.tsx` must render the server run state
instead of `const [evidenceReady, setEvidenceReady]`. The evidence workspace
must show queued/running/failed recovery when no completed evidence exists,
rather than treating every 404 as a generic API failure

- [ ] **Step 6: Run GREEN, accessibility checks and build**

```bash
cd apps/lingualens-app
npm test -- \
  src/__tests__/assessment-v2-client.test.ts \
  src/__tests__/assessment-processing-status.test.tsx \
  src/__tests__/assessment-capture-workspace.test.tsx \
  src/__tests__/assessment-recording-upload.test.ts \
  src/__tests__/assessment-transcript-review-workspace.test.tsx \
  src/__tests__/assessment-evidence-workspace.test.tsx
npm run typecheck
npm run lint
npm run build
```

Expected: all commands exit 0; no prohibited diagnosis/probability copy is
introduced

---

### Task 8: Prove the full async path against native PostgreSQL

**Files:**

- Modify: `scripts/check_assessment_v2_native.py`
- Modify: `apps/api/tests/assessment_v2/test_native_runtime_contract.py`
- Add: `apps/api/tests/assessment_v2/test_postgres_processing_leases.py`
- Modify: `apps/api/tests/assessment_v2/test_postgres_rls.py`
- Modify: `apps/lingualens-app/e2e/assessment-v2-transcript.smoke.spec.ts`

- [ ] **Step 1: Write native runtime RED assertions**

The contract test must require the runner to:

```text
create and attest a synthetic transcript
POST evidence-runs and receive 202 queued
run one evidence worker cycle natively
poll processing run to succeeded
GET persisted evidence and verify not_diagnostic=true
retry the POST and receive the same processing run ID
leave no temporary database or role
```

- [ ] **Step 2: Run RED**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_native_runtime_contract.py -q
```

Expected: fail because the current native runner probes children and RLS only

- [ ] **Step 3: Extend the native runner with synthetic workflow data**

Use only synthetic IDs and CHAT content. Start API and worker as native Python
processes against the same temporary PostgreSQL database. Preserve the existing
limited application role, RLS checks and `finally` cleanup. Do not add Docker
commands or persist test transcript/audio outside the temporary database

- [ ] **Step 4: Extend PostgreSQL RLS adversarial coverage**

Prove that an organization cannot read or mutate another organization's evidence
processing row, including result linkage, retry and cancellation

- [ ] **Step 5: Update the browser smoke**

The Playwright scenario must observe queued/running or deterministic test-worker
state, then succeeded evidence, reload once during processing, and confirm no
local evidence object is created

- [ ] **Step 6: Run the real native gate**

```bash
brew services start postgresql@16
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
```

Expected terminal output:

```text
assessment-v2 native runtime check passed
```

The receipt must include migrations through 0007, RLS pass count, enqueue 202,
PostgreSQL lease/concurrency pass, worker success, evidence read and cleanup.
Compose may be run optionally but cannot replace this receipt

---

### Task 9: Update runtime documentation and source of truth

**Files:**

- Modify: `README.md`
- Modify: `DEVELOPER_SETUP.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Modify: `docs/CURRENT_HANDOFF.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document one worker and one database queue**

State explicitly:

```text
Assessment V2 uses processing_runs as its durable queue.
The same native worker process handles capture and evidence stages.
Redis/Celery are not part of this path.
Docker Compose is optional.
```

- [ ] **Step 2: Document the API behavior change**

Replace statements saying evidence POST returns a completed profile with the
202 enqueue → processing poll → GET evidence sequence. Keep transcript
attestation, consent and non-diagnostic boundaries visible

- [ ] **Step 3: Update migration and limitation status**

Record `0007_durable_evidence_jobs`, mark background evidence processing active,
and keep timestamp-level review, longitudinal comparison, disposition/report
and GUI/TUI parity as future slices

- [ ] **Step 4: Add a real behavior changelog entry**

Describe the durable evidence queue, recovery actions and web polling. Do not
bump the product version unless the owner separately authorizes a release

- [ ] **Step 5: Run documentation consistency checks**

```bash
rg -n "synchronous|no background queue|evidence-runs|processing_runs|Redis|Celery|Docker" \
  README.md DEVELOPER_SETUP.md docs/DEVELOPMENT.md \
  docs/PROJECT_SOURCE_OF_TRUTH.md docs/CURRENT_HANDOFF.md apps/api/README.md
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_compose_contract.py \
  apps/api/tests/assessment_v2/test_native_runtime_contract.py -q
```

Expected: no active-runtime document claims synchronous evidence completion;
Docker is optional and the native path remains primary

---

### Task 10: Candidate-wide verification and final-strict closure

**Files:**

- Verify: complete diff, staged/unstaged/untracked paths, migrations, API, web,
  native runtime and assurance sidecar for the new unit

- [ ] **Step 1: Run the focused backend suite**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2/test_processing_contract.py \
  apps/api/tests/assessment_v2/test_processing_db_models.py \
  apps/api/tests/assessment_v2/test_evidence_processing_repository.py \
  apps/api/tests/assessment_v2/test_evidence_processing_worker.py \
  apps/api/tests/assessment_v2/test_transcript_routes.py \
  apps/api/tests/assessment_v2/test_capture_routes.py \
  apps/api/tests/assessment_v2/test_capture_upload_service.py \
  apps/api/tests/assessment_v2/test_capture_route_integration.py -q
```

Expected: zero failures

- [ ] **Step 2: Run the complete Assessment V2 suite**

```bash
PYTHONPATH=apps/api:src python3.13 -m pytest \
  apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
```

Expected: zero failures; PostgreSQL-marked tests deselected here and exercised
by the native gate

- [ ] **Step 3: Run the frontend and browser gates**

```bash
cd apps/lingualens-app
npm test
npm run typecheck
npm run lint
npm run build
npm audit --audit-level=high
npx playwright test e2e/assessment-v2-transcript.smoke.spec.ts --reporter=line
cd ../..
```

Expected: all commands exit 0 and audit reports no unresolved high/critical
vulnerability

- [ ] **Step 4: Run native and repository-wide gates once on the frozen candidate**

```bash
PYTHONPATH=apps/api:src python3.13 scripts/check_assessment_v2_native.py
bash scripts/check_project.sh
git diff --check
git status --short --branch
```

Expected: native runtime and full repository verification exit 0; no `.next/`,
`dist/`, `.local/`, `node_modules/`, `*.tsbuildinfo`, `.DS_Store`, secret, real
identifier, transcript or audio enters the candidate

- [ ] **Step 5: Perform the parent adversarial pass**

Test counterexamples for:

```text
cross-tenant claim/read/retry/cancel
org-admin clinical mutation
consent withdrawal before claim and before completion
transcript supersession before claim and before completion
pipeline/schema supersession before claim and before completion
worker death and lease reclaim
lease expiry after max attempts
stale lease token completion
duplicate enqueue and duplicate worker completion
retry exhaustion and explicit clinician retry
explicit restart after user cancellation versus blocked system cancellation
API reload/offline behavior
partial/insufficient evidence semantics
old capture stages after nullable recording_id migration
```

- [ ] **Step 6: Build the new final-strict packet and request one fresh review**

Create a new assurance unit with a new ledger, journal, candidate manifest,
readiness record and atomic reviewer reservation. Bind every in-scope tracked,
modified and untracked file. The reviewer must inspect the complete A1 candidate
and return `ship`; do not reuse the exhausted Evidence V2 unit or its review
calls

- [ ] **Step 7: Stop at the authorization boundary**

After `ship`, report the branch/worktree and verification receipts. Do not
commit, push, merge, deploy, migrate a shared Supabase database or enable a
production worker without explicit owner authorization

---

## ลำดับหลัง A1

เมื่อ A1 ผ่านแล้ว ให้เขียนและทำแผนแยกตามลำดับนี้:

1. **A2 — Segment Transcript Review:** immutable segment revisions, start/end
   timestamps, speaker labels, uncertainty reason/confidence, audio replay grants,
   uncertain-only editing และ attestation ที่ bind segment set checksum
2. **B — Longitudinal Comparison:** pair compatibility ตาม age/language/protocol/
   activity/quality/schema และ states `improved`, `stable`,
   `attention_suggested`, `indeterminate`, `not_comparable`
3. **C — Clinical Disposition and Report:** clinician-authored cues, monitor/
   repeat/collect/evaluate/intervene/refer actions, editable draft และ immutable
   signed snapshot
4. **D — Thin-client Parity:** OpenAPI-generated/shared contract สำหรับ Web,
   legacy desktop GUI และ research TUI โดย business rules อยู่ใน FastAPI เท่านั้น

แต่ละ slice ต้องมี migration, API contract, therapist UI หรือ client adapter,
synthetic walkthrough, native PostgreSQL proof, focused/full verification และ
assurance unit ของตัวเอง
