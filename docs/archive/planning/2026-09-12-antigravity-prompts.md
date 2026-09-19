# Prompts สำหรับส่งงาน LinguaLens ให้ Antigravity

ใช้ prompt หลักด้านล่างเริ่มงานหนึ่งครั้ง แล้วใช้ prompt รายช่วงเพื่อควบคุมขอบเขต ไม่จำเป็นต้องสั่งทั้งหมดในรอบเดียว แผนนี้เป็นการส่งต่อให้คุณนำไปสั่งเอง ยังไม่มีการส่งข้อความหรือแก้ Figma/Supabase จาก Codex

## Prompt หลัก — เริ่มตรวจฐานและเดินตามแผน

```text
ช่วยรับงานพัฒนา LinguaLens ต่อจาก Codex โดยอ่าน master plan นี้ให้ครบ:
/Users/porschecaa/lingualens/docs/superpowers/plans/2026-09-12-antigravity-remaining-work-roadmap.md

เป้าหมายคือ research prototype สำหรับนักบำบัด: เลือกเด็ก → assessment/protocol/consent → อัดเสียง → ตรวจ transcript segments → ดู developmental profile และการเปลี่ยนแปลงที่เปรียบเทียบได้ → บันทึกความเห็น/แผนติดตาม → signed report โดย Web/GUI/TUI ใช้ FastAPI เดียวกัน และรัน local แบบไม่ใช้ Docker

เริ่ม P0 ทันที ตรวจ AGENTS.md, PROJECT_SOURCE_OF_TRUTH.md, git worktree/status และ A2 manifest ก่อนเลือกฐาน โฟลเดอร์หลักอยู่บน codex/ml-workflow-hardening และมีงานค้าง ส่วน A2 อยู่ที่:
/Users/porschecaa/lingualens/.worktrees/assessment-v2-segment-review
branch codex/assessment-v2-segment-review
HEAD 5fb37457167b079d63d5ffe10d63a1cd2cd88706
โค้ด A2 ยังเป็น uncommitted changes จึงห้ามสร้าง worktree จาก HEAD แล้วถือว่าได้ A2 มาครบ ให้สร้าง continuation snapshot ที่ตรวจ source provenance ได้และเก็บต้นฉบับ A2 ไว้

ก่อนเขียน production code แต่ละ slice ให้สร้าง implementation plan ที่มี exact paths, API/data examples, failing tests, commands และ acceptance criteria จาก baseline จริง ใช้ TDD และเก็บ RED ก่อน implementation สำหรับ behavior changes ตาม AGENTS ทำงานตามลำดับ P0 → U1/E1 → B1 → B2 → B3 → C1 → C2 → D1 → R1/S1 → V1 ตาม dependencies ของแผน

ข้อสำคัญ:
- มี MeasuredFeature/DomainProfile และ evidence processing อยู่แล้ว ให้ต่อยอด ไม่สร้างฐานซ้ำ
- Figma ยังเป็น working skeleton ต้องตรวจของจริง ทำ prototype/export/acceptance ให้ครบก่อน UI ใหม่ อย่าอ้างว่ามีแค่เอกสารแล้ว Figma เสร็จ
- Concern, numeric change และ clinician diagnosis ต้องแยกกัน ห้ามสร้าง ASD% หรือ threshold/reference/clinical improvement ที่ไม่มีหลักฐาน
- ถ้า audio/provider/quality ไม่รองรับ ให้แสดง unavailable/insufficient_data ไม่สร้างผลจำลองเป็นผลจริง
- Preserve consent, role/care-team/tenant isolation, immutable revisions, stale propagation, signed snapshots และ privacy-safe logs
- เก็บ GUI/TUI และ research datasets เดิม ไม่แก้งาน ML ในโฟลเดอร์หลักโดยไม่ได้ตรวจความซ้ำซ้อน
- A2 เป็น parent-completed / final-strict-not-achieved และ review budget หมดแล้ว อย่า reset budget หรืออ้าง independent ship เอกสาร authority อยู่ใน common Git directory ใต้ solweaver/lingualens-assessment-v2-segment-review
- งานนี้อนุญาต local implementation/tests/docs และเตรียมผลที่ review ได้ ไม่อนุญาตลบฐานจริงหรือ commit/push/merge/deploy/release โดยอัตโนมัติ ต้องเคารพ exact owner authority ตาม AGENTS

เก็บสถานะใน docs/ANTIGRAVITY_HANDOFF_PROGRESS.md ของ continuation workspace ทุก slice พร้อม changed files, acceptance result, test receipts, assurance limits และ next task หาก Figma/credentials/reviewer capability ขาด ให้ระบุ exact gap และทำงานอิสระที่ยังทำได้ต่อ อย่าแต่งหลักฐานหรือสรุปว่าทั้งโครงการเสร็จจาก unit tests

เริ่มด้วยรายงาน P0 แบบสั้น แล้วทำ safe local work ต่อจนถึง checkpoint ที่ตรวจรับได้ ไม่ต้องถามซ้ำเรื่องรายละเอียด routine ที่ตัดสินได้จากแผน
```

## Prompt 1 — Figma และแหล่งข้อมูล

```text
ทำ U1 และ E1 ตาม master plan 2026-09-12-antigravity-remaining-work-roadmap.md บน continuation baseline ที่ P0 ตรวจแล้ว
เริ่มจากตรวจ Figma manifest และ evidence contracts ที่มีอยู่ ทำ paper-to-feature matrix โดยอ่าน PDF จริงใน /Users/porschecaa/Desktop/Paper-ASD/ พร้อม page/cohort/language/task/limitations แยก measured features, observations และ instrument responses
ตรวจความสามารถ recording→transcript และ acoustic/timing จริง ระบุ unavailable ที่ยังทำไม่ได้ ก่อน UI ใหม่ต้องมี accepted frames สำหรับ profile/history/clinician review/error states และ prototype/export evidence; ถ้า remote Figma ยังเข้าไม่ได้ให้ทำ local handoff และ backend ต่อ โดยคง remote status ว่ายังไม่สำเร็จ
ส่ง feature capability matrix, design artifacts, implementation/test evidence และอัปเดต progress file ไม่เพิ่ม probability/diagnosis และไม่คัดลอกแบบประเมินที่ยังไม่ได้ตรวจสิทธิ์
```

## Prompt 2 — ประวัติและการเปรียบเทียบ

```text
ทำ B1–B3 ตาม master plan บน verified continuation baseline เริ่มจากเขียน code-level B1 plan และ tests ก่อน production code
ต่อยอด existing feature/provenance contracts กำหนด compatibility ต่อ feature แล้วทำ longitudinal API/persistence และ therapist history UI หลัง design acceptance
ต้องทดสอบ same-child/tenant, protocol/language/schema/quality mismatch, required context missing, zero baseline, partial data, consent withdrawal, stale source และ concurrency
แสดงค่าจริง/หน่วย/delta แต่ห้ามแปล delta เป็น improved/stable หากไม่มี approved meaningful-change policy; ต้องมี indeterminate/not_comparable พร้อมเหตุผล
ส่ง test receipts, native DB/RLS evidence, browser scenario เด็กสมมติสามครั้งที่หนึ่งครั้งเปรียบเทียบไม่ได้ และอัปเดต progress file
```

## Prompt 3 — ความเห็นนักบำบัดและรายงาน

```text
ทำ C1–C2 ตาม master plan โดย reuse verified E/B contracts และ accepted UX
ทำ non-exclusive attention cues ที่อ้าง evidence และ policy version, clinician acknowledge/disagree/request-more-evidence, disposition และ follow-up จากนั้น report draft, server readiness, immutable sign-off, authorized PDF export และ amendment lineage
ห้ามให้ computed cues เข้า report conclusion อัตโนมัติโดยไม่มีการ review ห้ามแก้ signed snapshot เดิม และห้ามเพิ่ม ASD/delay probabilities
ทดสอบ wrong clinician, stale evidence/report, consent loss, concurrent sign/edit, repeated sign idempotency, private export และ historical snapshot reproducibility พร้อม PDF ภาษาไทย ใช้ synthetic data เท่านั้น
ทำ code-level plan/TDD/verification ตาม AGENTS ก่อนอัปเดต progress ว่า verified
```

## Prompt 4 — GUI/TUI และ native runtime

```text
ทำ D1 และ R1 ตาม master plan หลัง API contracts คงที่
ตรวจ packages/gui/app.py และ packages/tui/{client.py,workflow.py,ui.py} แล้วทำให้ clinical workflows เรียก FastAPI V2 เดียวกับ Web โดยเก็บ local research utilities ที่แยกชัดเจน
ทดสอบ parity ของ success/error/consent/stale/offline/auth-expiry และห้าม silent local fallback ตรวจ API/worker import packaging, native PostgreSQL setup/restart/retry/cleanup และ supported Python/Node runtime
recheck dependency audits และแก้แบบ bounded พร้อม regression evidence อย่าใช้ audit fix --force หรือ deploy เพื่อทดสอบแทน local verification
ส่ง parity table, run instructions, current audit results และ progress update
```

## Prompt 5 — เตรียม staging/pilot และรายงานวิจัย

```text
ทำ S1/V1 preparation ตาม master plan: เตรียม reproducible staging checks, therapist walkthrough, Figma/research exports, paper traceability และ reproducibility package
รัน external staging เฉพาะเมื่อมี exact environment authority และ credentials ที่เหมาะสม ต้องมี real JWT/JWKS, two-tenant RLS, care-team, consent, private storage/expiry, worker recovery, backup/restore และ redacted telemetry evidence; ห้ามใช้ mock เป็นหลักฐานแทน
เก็บ usability results จากผู้ร่วมทดสอบจริง ถ้ายังไม่มีให้ส่ง protocol/schedule/checklist และบอกว่า execution pending ห้ามสร้างผลแทน
สรุป prototype-ready / pilot-ready / clinical-validation แยกกัน พร้อม exact blockers ไม่ลบข้อมูลจริง ไม่ merge/deploy/release เกิน authority
```

## Prompt สำหรับกลับมาทำต่อหลังเปลี่ยน session

```text
อ่าน master plan และ docs/ANTIGRAVITY_HANDOFF_PROGRESS.md ใน continuation workspace ตรวจ branch/status/diff และ receipts ว่ายังตรงกับ candidate ปัจจุบัน แล้วทำ next smallest task ที่ยังไม่ครบตาม dependencies ต่อ
อย่าทำงานที่ accepted แล้วซ้ำ อย่าเปิด review budget ของ A2 ใหม่ และอย่านำผลตรวจเก่ามาอ้างเป็นผลปัจจุบันโดยไม่ได้ตรวจว่า source/environment ยังตรงกัน รายงานสิ่งที่เสร็จในรอบนี้ พร้อม evidence และงานถัดไป
```
