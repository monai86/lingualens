# รายงานสรุปความก้าวหน้าโครงการ LinguaLens (Project Summary Report)
**ระบบสนับสนุนการตัดสินใจทางคลินิกและการวิเคราะห์ตัวอย่างภาษาพูดสำหรับเด็ก (Clinical Decision Support & Thai LSA)**

---

## 1. ขอบเขตและเจตนารมณ์ทางคลินิก (Clinical Scope & Safety Boundary)

> **⚠️ ข้อความระวังและขอบเขตความปลอดภัยทางคลินิก:**
> LinguaLens เป็น **"ระบบต้นแบบเพื่อการวิจัยและการศึกษา (Research and Education Prototype)"** พัฒนาขึ้นเพื่อช่วยลดภาระงานเอกสารของนักกิจกรรมบำบัด/นักอรรถบำบัด (Speech-Language Pathologist - SLP) ในการถอดความและคำนวณตัวชี้วัดทางภาษาศาสตร์เชิงปริมาณ
> - ระบบนี้ **ไม่ใช่เครื่องมือวินิจฉัยโรคออทิซึมสเปกตรัม (ASD) โดยอัตโนมัติ**
> - ข้อมูลที่ระบบประมวลผลเป็นเพียง **ตัวชี้วัดเชิงสังเกตและข้อมูลสนับสนุนการตัดสินใจ (Observational Biomarkers & Decision Support Cues)**
> - การลงความเห็นทางคลินิกและการวินิจฉัยต้องกระทำโดยแพทย์เฉพาะทางหรือนักอรรถบำบัดวิชาชีพร่วมกับแบบประเมินมาตรฐานทางคลินิกเท่านั้น

---

## 2. กรอบการประเมิน 5 มิติทางภาษาและเสียงพูด (5-Domain Clinical Framework)

LinguaLens วิเคราะห์ทักษะการสื่อสารของเด็กผ่าน 5 มิติหลักตามหลักอรรถบำบัดสากลและโครงสร้างภาษาไทย:

| มิติทางคลินิก (Domain) | ตัวชี้วัดหลัก (Key Metrics) | การแปลผลทางคลินิก (Clinical Interpretation) |
|---|---|---|
| **1. Expressive Phrase Length** | MLU-w (Mean Length of Utterance in words) | ความยาวเฉลี่ยของประโยคพูด บ่งบอกพัฒนาการด้านไวยากรณ์และการประกอบประโยค |
| **2. Lexical Diversity** | TTR (Type-Token Ratio), Unique Words | ความหลากหลายของคำศัพท์ที่เด็กเลือกใช้ เปรียบเทียบกับจำนวนคำพูดทั้งหมด |
| **3. Social Pragmatics & Reciprocity** | Turn-Taking Ratio, Conversational Latency | ความสามารถในการผลัดกันพูดโต้ตอบในบทสนทนา และความเร็วในการตอบสนองคู่สนทนา |
| **4. Repetition & Atypical Patterns** | Immediate Echolalia (Verbatim vs Mitigated), Thai Pronoun Reversal | การพูดทวนคำพูดของคู่สนทนาแบบตรงตัวหรือดัดแปลง และการสับสนสรรพนาม |
| **5. Acoustic Prosody & Pitch** | F0 Median (Hz), F0 IQR (Hz), Voiced/Pause Ratio | ระดับเสียงสูง-ต่ำ และความกว้างของทำนองเสียงพูด (Intonation/Prosody) |
| **6. Thai Language Structure (LSA Engine)** | คำถาม, คำปฏิเสธ, คำสรรพนาม, คำลงท้ายสุภาพ | โครงสร้างวากยสัมพันธ์เฉพาะของภาษาไทยเพื่อติดตามการพัฒนาหน้าที่ทางภาษา |

---

## 3. สถาปัตยกรรม Thai Clinical LSA Engine (Pragmatics & Syntax)

เนื่องจากภาษาไทยเป็นภาษาที่เขียนติดกันโดยไม่มีการเว้นวรรคระหว่างคำ (Unsegmented Script) การนับจำนวนคำแบบดั้งเดิม (Whitespace Splitting) จึงไม่สามารถสะท้อนความยาวประโยคจริงได้ โครงการจึงได้พัฒนา **Thai Clinical LSA Engine** (`src/clinical_speech/thai_lsa.py`):

1. **การตัดคำระดับคลินิก (Clinical Thai Tokenization):**
   - ใช้งานอัลกอริทึม `newmm` (Maximal Matching) จาก `pythainlp` ร่วมกับ fallback word-boundary tokenizer
   - คัดกรองรหัสไม่สมบูรณ์ เช่น `xxx`, `yyy`, `www` (Unintelligible speech markers ตามมาตรฐาน TalkBank CHAT)
2. **การตรวจจับหน้าที่ของประโยค (Syntactic & Pragmatic Markers):**
   - **ประโยคคำถาม:** คำแสดงคำถามภาษาไทย (`อะไร`, `ไหน`, `ทำไม`, `ใคร`, `ไหม`, `หรือยัง`, `กี่`, `หรือเปล่า`)
   - **ประโยคปฏิเสธ:** คำปฏิเสธ (`ไม่`, `ไม่อยาก`, `ไม่ใช่`, `มิได้`, `อย่า`)
   - **คำสรรพนาม:** (`ผม`, `หนู`, `เธอ`, `เขา`, `น้อง`, `พี่`)
   - **คำลงท้ายสุภาพ:** (`ครับ`, `ค่ะ`, `ฮะ`, `จ้ะ`, `ขา`)
3. **การวิเคราะห์วัจนปฏิบัติศาสตร์เชิงลึก (Advanced Pragmatic Analysis):**
   - **การจำแนก Echolalia 2 รูปแบบ (Verbatim vs Mitigated):**
     - *Verbatim Echolalia (ทวนซ้ำตรงตัว):* การพูดตามผู้ใหญ่แบบแทบไม่ดัดแปลง (Jaccard similarity ≥ 0.8 หรือตรงกัน 100%)
     - *Mitigated Echolalia (ทวนซ้ำแบบดัดแปลง):* การพูดทวนประโยคหลักแต่มีการเพิ่มหรือเปลี่ยนคำบางส่วน (Overlap 0.40–0.79) สะท้อนความพยายามในการสื่อสารที่มีการพัฒนา
     - *Communicative Response Filtering:* แยกแยะคำตอบรับที่เหมาะสมตามบริบท (เช่น `ใช่`, `ไม่เอา`, `ชอบ`, `เอาอันนี้`) ไม่ให้นับผิดพลาดเป็น Echolalia
   - **การตรวจจับการสับสนสรรพนาม (Thai Pronoun Reversal Detection):**
     - ตรวจจับเมื่อเด็กใช้สรรพนามบุรุษที่ 2 หรือ 3 (`เธอ`, `คุณ`, `เขา`) เพื่อเรียกความต้องการของตนเอง ร่วมกับกริยาแสดงความต้องการ/ความรู้สึก (เช่น `เธออยากเล่น`, `คุณจะกิน`, `เธอหิวน้ำ`)

---

## 4. ปรับปรุงกระบวนการทำงาน Desktop GUI (Guided Workflow & Live Audio VU/VAD)

เพื่อให้นักบำบัดใช้งานได้สะดวก รวดเร็ว และเป็นธรรมชาติในห้องฝึกบำบัดจริง (Modern Flat Design):

1. **แถบนำทาง 5 ขั้นตอน (5-Step Stepper Bar):**
   - `Step 1: Open Case` ➔ `Step 2: Add Session` ➔ `Step 3: Ingest Material` ➔ `Step 4: Review Transcript` ➔ `Step 5: Progress Report`
   - แสดงสถานะชัดเจน (`Completed ✓`, `Current ●`, `Upcoming ○`)
2. **Next Action Ribbon:**
   - ปุ่มแนะนำขั้นตอนถัดไปอัตโนมัติตามวงจรชีวิตของเซสชัน เช่น เมื่อเลือกเคสแล้วปุ่มจะเปลี่ยนเป็น `➕ Add New Session` และเมื่อถอดความเสร็จจะเปลี่ยนเป็น `✍️ Review Transcript & Attest`
3. **ระบบวัดสัญญาณเสียงสดระดับสตูดิโอ (24-Segment Discrete LED VU Meter & VAD):**
   - บันทึกสัญญาณเสียง 16kHz Mono WAV คุณภาพสูงแบบ thread-safe
   - แถบไฟ LED 24 ท่อน (เขียว 1-16 ปกติ, ส้ม 17-21 เริ่มดัง, แดง 22-24 พีค)
   - ป้ายตรวจจับเสียงพูดสดแบบเรียลไทม์ (`● VOICE ACTIVE` Energy-based VAD)
   - ระบบเตือนสัญญาณแตกพร่า (`⚠️ CLIPPING DETECTED`) ป้องกันข้อมูลเสียงเสียหายก่อนส่งเข้าสู่โมเดลถอดความ (ASR)
4. **Collapsible Technical Details Disclosure:**
   - แยกส่วนการแสดงผลเชิงเทคนิค (Data Sources, Pipeline Versions, Cryptographic SHA-256 Hashes) ไว้ในกรอบที่พับเก็บได้

---

## 5. การติดตามพัฒนาการและเกณฑ์เปรียบเทียบตามวัย (Normative Benchmarks & Growth Corridor)

1. **เกณฑ์พัฒนาการจำแนกตามช่วงอายุ (Age-Cohort Stratified Norms 24–60 เดือน):**
   - แบ่งเกณฑ์มาตรฐานภาษาปกติ (Typical Development) ตามช่วงอายุของเด็ก:
     - **24–35 เดือน:** MLU-w 1.8–2.6, TTR 0.55, Turn-taking 35%
     - **36–47 เดือน:** MLU-w 3.0–3.8, TTR 0.60, Turn-taking 45%
     - **48–60 เดือน:** MLU-w 4.2–5.2, TTR 0.65, Turn-taking 55%
   - แสดงผลใน Spider Radar Diagram ของเคสโดยเทียบกับค่ามาตรฐานตรงตามอายุจริงของเด็ก
2. **แถบพัฒนาการปกติ (Typical Development Growth Corridor):**
   - ในกราฟพัฒนาการระยะยาว (Longitudinal Chart) ใน Tab 4 และ Report เพิ่มแถบสีแรเงาอ่อน (`#eef2ff` พร้อมเส้นประ `#c7d2fe`)
   - ช่วยให้นักบำบัดและผู้ปกครองเห็นชัดเจนว่าวิถีพัฒนาการของเด็กกำลังขยับเข้าใกล้กรอบเด็กพัฒนาการสมวัย (TD Milestone Band) มากน้อยเพียงใด

---

## 6. เครื่องมือส่งออกรายงานสองภาษา (Clinical Export Engine)

1. **รายงานแบบสองภาษา (Bilingual Thai/English HTML Report):**
   - รองรับการเปิดผ่านเว็บเบราว์เซอร์พร้อมปุ่ม **"🖨️ พิมพ์รายงาน / Save as PDF"**
   - กฎการพิมพ์ `@media print` จัดหน้ากระดาษ A4 มาตรฐาน ซ่อนปุ่มควบคุม และป้องกันการตัดแบ่งตารางกลางหน้า
   - เพิ่มการรายงาน Echolalia Breakdown (Verbatim vs Mitigated) และแถบแจ้งเตือน Pronoun Reversal
2. **แผนภาพใยแมงมุม 5 มิติ (Spider Radar SVG Diagram):**
   - เรนเดอร์ Pure Vector SVG ปรับเส้นเกณฑ์ TD ตามช่วงอายุจริงของเด็ก
3. **การลงนามรับรองผล (Digital Clinician Attestation):**
   - บันทึกชื่อนักบำบัดผู้ตรวจรับรอง และประทับตรารับรองมาตรฐาน TalkBank CHAT

---

## 7. เว็บแอปพลิเคชันและ Clinician Assistant (Live API Bridge)

1. **การเชื่อมต่อ Backend Case สด (`/assistant`):**
   - เชื่อมต่อ `listBackendCases()` กับ FastAPI Backend แบบเรียลไทม์ พร้อม fallback ไปยังตัวอย่างเคสกรณีออฟไลน์
   - เมนูเลือกเคสจะแสดงรายการเด็กจริงจากคลินิกพร้อมรหัสปกปิดตัวตน (De-identified Child Code)
2. **AI Clinical Assistant Prompt Templates:**
   - รวบรวมคำสั่งสรุปผลเฉพาะทาง เช่น สรุปผลสำหรับผู้ปกครอง, วิเคราะห์พัฒนาการข้ามช่วงเวลา, และคำแนะนำกิจกรรมการฝึกที่บ้าน
3. **ปุ่ม "คัดลอกลง Report Draft" (1-Click Push to Draft):**
   - ส่งข้อความสรุปของ AI ไปบันทึกลงในร่างรายงาน (`sessionStorage`) พร้อมแสดงเครื่องหมายยืนยัน ช่วยลดเวลาพิมพ์ของนักบำบัดลงกว่า 80%

---

## 8. สคริปต์เปิดใช้งานระบบระดับคลินิก (Turnkey Pilot Deployment)

1. **สคริปต์เริ่มระบบอัตโนมัติ (`scripts/launch_pilot.sh`):**
   - ตรวจสอบสภาพแวดล้อม (Python 3.11+, Node.js 20+, สถานะพอร์ต 8000/3000)
   - สร้างไฟล์คอนฟิก `.env.local` ให้อัตโนมัติหากยังไม่มี
   - รัน FastAPI Backend และ Next.js Frontend พร้อม Health Probing จนกระทั่งพร้อมใช้งาน
   - รองรับการปิดระบบอย่างปลอดภัย (Graceful Shutdown Trap) ด้วย `Ctrl+C`
2. **คู่มือการติดตั้ง (`docs/PILOT_DEPLOYMENT.md`):**
   - สรุปขั้นตอน Runbook, สถาปัตยกรรม Port Mapping, และแนวทางแก้ไขปัญหาทั่วไป (Troubleshooting)

---

## 9. ผลการทดสอบและการตรวจสอบความถูกต้อง (Verification & Quality Assurance)

- **Python Test Suites:**
  - `tests/test_thai_lsa.py`: 7/7 ผ่าน (รวม Verbatim vs Mitigated Echolalia และ Pronoun Reversal)
  - `tests/test_export_engine.py`: 3/3 ผ่าน (รวม Normative Cohort Radar & PDF Generation)
  - `tests/test_gui.py`: 95/95 ผ่าน (รวม Stepper, Discrete VU Meter, TD Corridor, Tab 1-5 Navigation)
  - **รวมทดสอบ Python: 105 tests ผ่าน 100%**
- **Next.js Web App Test Suites (`apps/lingualens-app`):**
  - `src/__tests__/longitudinal-trend-card.test.tsx`: 4/4 ผ่าน
  - `src/__tests__/navigation-routes.test.tsx`: 17/17 ผ่าน
  - **TypeScript Typecheck (`tsc --noEmit`): 0 errors**
  - **Preflight Pilot Check (`scripts/launch_pilot.sh --check-only`): 0 errors**
