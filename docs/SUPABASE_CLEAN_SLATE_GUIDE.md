# คู่มือการรื้อระบบ Supabase และเริ่มต้นนับ 1 ใหม่ (Supabase Clean-Slate Guide)

เอกสารฉบับนี้อธิบายวิธีการรีเซ็ตฐานข้อมูล Supabase ของโปรเจกต์ **LinguaLens** ทั้งหมดแบบ Clean-Slate (รื้อระบบเดิมทิ้งทั้งหมด แล้วเริ่มนับ 1 ใหม่) เพื่อให้โครงสร้างฐานข้อมูลตรงตามสถาปัตยกรรม **Assessment V2** ล่าสุดอย่างสมบูรณ์แบบ

---

## 📁 ไฟล์ Master SQL Script สำหรับรัน
- ตำแหน่งไฟล์ใน repository:
  - [`scripts/supabase/clean_slate_supabase.sql`](file:///Users/porschecaa/lingualens/scripts/supabase/clean_slate_supabase.sql)
  - [`docs/sql/clean_slate_supabase.sql`](file:///Users/porschecaa/lingualens/docs/sql/clean_slate_supabase.sql)

---

## 🚀 ขั้นตอนการดำเนินการใน Supabase Dashboard

### 1. เข้าสู่ Supabase Dashboard
1. เปิดเบราว์เซอร์ไปที่ [Supabase Dashboard](https://supabase.com/dashboard)
2. เลือกโปรเจกต์ **LinguaLens**

### 2. เปิด SQL Editor
1. ที่แถบเมนูด้านซ้าย ให้คลิกที่ **SQL Editor** (ไอคอน `>_`)
2. คลิกปุ่ม **+ New query** ด้านบน

### 3. รัน Master Script
1. เปิดไฟล์ [`scripts/supabase/clean_slate_supabase.sql`](file:///Users/porschecaa/lingualens/scripts/supabase/clean_slate_supabase.sql) แล้วคัดลอก (Copy) เนื้อหาทั้งหมด (73 KB)
2. วาง (Paste) ลงในช่องคำสั่งของ SQL Editor
3. กดปุ่ม **Run** (หรือคีย์ลัด `Ctrl + Enter` / `Cmd + Enter`)
4. รอระบบประมวลผลประมาณ 3-5 วินาที จนกระทั่งปรากฏข้อความ:
   ```text
   Success. No rows returned
   NOTICE: LinguaLens Assessment V2 clean-slate initialization completed successfully.
   ```

---

## 🛠️ สิ่งที่ระบบจะติดตั้งใหม่อัตโนมัติ (Automated Setup)

### 1. ล้าง Schema เดิมอย่างหมดจด (Clean Drop)
- ทำการ `DROP SCHEMA IF EXISTS public CASCADE;` เพื่อล้างตารางเก่า, view, enum, trigger และ policy เดิมทั้งหมดออก
- สร้าง `public` schema ใหม่พร้อมกำหนดสิทธิ์มาตรฐานให้แก่ role `postgres`, `anon`, `authenticated`, และ `service_role`
- ติดตั้ง PostgreSQL Extension: `uuid-ossp` และ `pgcrypto`

### 2. ตาราง Assessment V2 ครบทั้ง 28 ตาราง + Version Stamp
สร้างตารางพร้อม Primary Key, Foreign Key (Cascade/Tenant-scoped), Constraints, และ Index ทั้ง 100 ตัวตามมาตรฐานระบบ:
1. **องค์กรและผู้ใช้งาน (Identity & Tenant):**
   - `organizations` — องค์กร/คลินิก
   - `user_profiles` — ข้อมูลผู้ใช้/นักบำบัด
   - `organization_memberships` — ความเป็นสมาชิกและบทบาทในคลินิก
2. **เด็กและทีมดูแล (Pediatric & Care Team):**
   - `children` — ข้อมูลเด็กและการเข้ารหัสปกปิดตัวตน (display code)
   - `care_team_assignments` — ทีมสหวิชาชีพที่รับผิดชอบเด็ก
   - `consent_records` — หนังสือยินยอมตามกฎหมาย/PDPA
3. **การประเมินและโปรโตคอล (Assessment & Protocols):**
   - `assessments` — รอบการประเมินทางคลินิก
   - `protocol_versions` — แคตตาล็อกโปรโตคอลการเก็บตัวอย่างภาษา
   - `protocol_activities` — กิจกรรมการประเมิน (เช่น Free Play, Shared Book, Turn Taking)
   - `assessment_protocol_selections` — โปรโตคอลที่เลือกใช้ในการประเมิน
4. **การบันทึกเสียงและการถอดความ (Audio & Transcript Pipeline):**
   - `recordings` — ข้อมูลไฟล์เสียงที่บันทึก
   - `processing_runs` — ประวัติและสถานะการประมวลผล (VAD, Diarization, Transcription, Cleanup)
   - `recording_quality_results` — ผลการตรวจคุณภาพเสียง (SNR, Clipping, Silence)
   - `transcript_revisions` — ประวัติการตรวจแก้ถอดความของนักบำบัด
   - `transcript_segment_sets` — ชุดท่อนเสียงถอดความแบบคงรูป (immutable snapshot)
   - `transcript_segments` — ท่อนเสียงถอดความระดับ utterance พร้อม timestamp และ speaker role
5. **หลักฐานทางภาษาและการวิเคราะห์ (Clinical Evidence):**
   - `evidence_runs` — รอบการวิเคราะห์หลักฐานภาษา
   - `evidence_feature_values` — ค่าตัววัดทางภาษา 22 ตัวพร้อม percentile และ benchmark
   - `evidence_domain_profiles` — ผลสรุป 6 โดเมนพัฒนาการ (Pragmatics, Syntax, Lexicon, Phonology, Speech Sound, Fluency)
6. **การสังเกตและแบบประเมินเสริม (Observations & Standardized Instruments):**
   - `assessment_observations` — การสังเกตพฤติกรรมทางคลินิก
   - `assessment_instruments` — การบันทึกแบบประเมินมาตรฐานเสริม
   - `assessment_instrument_items` — รายการข้อย่อยของแบบประเมิน
7. **การเปรียบเทียบเชิงพัฒนาการ (Longitudinal Comparisons):**
   - `assessment_comparisons` — การเปรียบเทียบพัฒนาการระหว่าง Baseline กับ Follow-up
   - `assessment_comparison_features` — ค่าความเปลี่ยนแปลงของตัวชี้วัดแต่ละตัว
8. **การทบทวนทางคลินิกและรายงาน (Review & Signed Reports):**
   - `assessment_clinical_reviews` — การทบทวนและกำหนดแนวทางของนักบำบัด
   - `assessment_attention_cues` — ข้อสังเกตที่ควรให้ความสนใจ (Attention Cues)
   - `assessment_reports` — รายงานสรุปผลการประเมินพร้อมการลงนามดิจิทัล (Digital Signature Snapshot)
9. **ระบบตรวจสอบและไมเกรชัน:**
   - `audit_events` — บันทึกประวัติการกระทำทั้งหมด (Audit Trail)
   - `alembic_version` — บันทึกเวอร์ชันฐานข้อมูลที่ `0012_clinical_review_reports`

### 3. ระบบ Row Level Security (RLS) ที่เชื่อมกับ Supabase Auth
- **Tenant Isolation:** แยกข้อมูลตามองค์กร (`organization_id`) อย่างเด็ดขาด
- **ฟังก์ชัน `public.is_org_member(target_org_id text)`:**
  - รองรับทั้งการเรียกผ่าน FastAPI backend (ที่ใช้ session setting `app.current_organization_id`)
  - รองรับ Supabase Auth JWT (`auth.uid()`) โดยตรวจสอบสิทธิ์ใน `organization_memberships` อัตโนมัติ
  - รองรับ Supabase `service_role` สำหรับงาน background worker
- มีการ **ENABLE** และ **FORCE ROW LEVEL SECURITY** ในทุกตารางของระบบ

### 4. Supabase Auth Automatic Sync Trigger
- สร้าง Trigger `on_auth_user_created` บนตาราง `auth.users`:
  - เมื่อมีนักบำบัดสมัครสมาชิกใหม่หรือเข้าสู่ระบบผ่าน Supabase Auth ระบบจะสร้าง `user_profiles` และมอบหมายให้อยู่ในคลินิกเริ่มต้น `org_alpha` (บทบาท `therapist`) อัตโนมัติทันที
  - พร้อมคำสั่ง Sync ผู้ใช้ที่มีอยู่แล้วในระบบ Supabase Auth ให้เข้าสู่ระบบโดยอัตโนมัติ

### 5. Private Storage Bucket (`audio-recordings`)
- สร้าง Bucket ส่วนตัวชื่อ `audio-recordings` (public = false)
- กำหนดขนาดไฟล์สูงสุด 100 MB
- รองรับประเภทไฟล์: `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`
- ติดตั้ง Storage RLS Policies:
  - อนุญาตให้ authenticated user อัปโหลดและดาวน์โหลดไฟล์เสียงได้
  - อนุญาตให้ `service_role` เข้าถึงไฟล์เพื่อส่งเข้า ML Pipeline

### 6. ข้อมูลตั้งต้นทางคลินิก (Seed Data)
- องค์กรตัวอย่าง: `org_alpha` ("LinguaLens Clinical Pilot Clinic")
- โปรโตคอลมาตรฐานภาษาไทย: `thai_guided_language_sample:v0`
- กิจกรรมมาตรฐาน:
  1. `free_play` — การเล่นอิสระ (180 วินาที)
  2. `shared_book` — การอ่านหนังสือนิทานร่วมกัน (120 วินาที)
  3. `turn_taking` — กิจกรรมผลัดกันพูด (120 วินาที)

---

## 🔍 การตรวจสอบผลลัพธ์หลังรันเสร็จ

1. **ตรวจสอบ Table Editor:**
   - ไปที่เมนู **Table Editor** ด้านซ้าย
   - คุณจะพบตารางใหม่ 28 ตารางปรากฏขึ้นอย่างเป็นระเบียบ
   - คลิกดูตาราง `organizations` จะพบแถว `org_alpha`
   - คลิกดูตาราง `protocol_versions` และ `protocol_activities` จะพบข้อมูลกิจกรรมมาตรฐาน
2. **ตรวจสอบ Storage:**
   - ไปที่เมนู **Storage**
   - จะพบบักเก็ต `audio-recordings` พร้อมสถานะ Private (มีรูปกุญแจ)
3. **ตรวจสอบ Authentication Integration:**
   - ไปที่ **Authentication** -> **Users**
   - หากเชิญหรือสร้างผู้ใช้ใหม่ ผู้ใช้คนนั้นจะปรากฏใน `user_profiles` และ `organization_memberships` ใน Table Editor โดยอัตโนมัติ
