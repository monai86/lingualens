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
| **4. Repetition & Atypical Patterns** | Immediate Echolalia Count, Pronoun Reversal | การพูดทวนคำพูดของคู่สนทนาทันที (Echolalia) และการใช้สรรพนาม |
| **5. Acoustic Prosody & Pitch** | F0 Median (Hz), F0 IQR (Hz), Voiced/Pause Ratio | ระดับเสียงสูง-ต่ำ และความกว้างของทำนองเสียงพูด (Intonation/Prosody) |
| **6. Thai Language Structure (LSA Engine)** | คำถาม, คำปฏิเสธ, คำสรรพนาม, คำลงท้ายสุภาพ | โครงสร้างวากยสัมพันธ์เฉพาะของภาษาไทยเพื่อติดตามการพัฒนาหน้าที่ทางภาษา |

---

## 3. สถาปัตยกรรม Thai Clinical LSA Engine

เนื่องจากภาษาไทยเป็นภาษาที่เขียนติดกันโดยไม่มีการเว้นวรรคระหว่างคำ (Unsegmented Script) การนับจำนวนคำแบบดั้งเดิม (Whitespace Splitting) จึงไม่สามารถสะท้อนความยาวประโยคจริงได้ โครงการจึงได้พัฒนา **Thai Clinical LSA Engine** (`src/clinical_speech/thai_lsa.py`):

1. **การตัดคำระดับคลินิก (Clinical Thai Tokenization):**
   - ใช้งานอัลกอริทึม `newmm` (Maximal Matching) จาก `pythainlp` ร่วมกับพจนานุกรมคำศัพท์ภาษาไทย
   - คัดกรองรหัสไม่สมบูรณ์ เช่น `xxx`, `yyy`, `www` (Unintelligible speech markers ตามมาตรฐาน TalkBank CHAT)
2. **การตรวจจับหน้าที่ของประโยค (Syntactic & Pragmatic Markers):**
   - **ประโยคคำถาม:** คำแสดงคำถามภาษาไทย (`อะไร`, `ไหน`, `ทำไม`, `ใคร`, `ไหม`, `หรือยัง`, `กี่`, `หรือเปล่า`)
   - **ประโยคปฏิเสธ:** คำปฏิเสธ (`ไม่`, `ไม่อยาก`, `ไม่ใช่`, `มิได้`, `อย่า`)
   - **คำสรรพนาม:** (`ผม`, `หนู`, `เธอ`, `เขา`, `น้อง`, `พี่`)
   - **คำลงท้ายสุภาพ:** (`ครับ`, `ค่ะ`, `ฮะ`, `จ้ะ`, `ขา`)
   - **Immediate Echolalia:** การเปรียบเทียบ n-gram คำศัพท์ระหว่างประโยคของเด็กกับประโยคของผู้บำบัดก่อนหน้าทันที

---

## 4. ปรับปรุงกระบวนการทำงาน Desktop GUI (Guided Workflow & Live Audio)

เพื่อให้นักบำบัดใช้งานได้สะดวก รวดเร็ว และเป็นธรรมชาติในห้องฝึกบำบัดจริง:

1. **แถบนำทาง 5 ขั้นตอน (5-Step Stepper Bar):**
   - `Step 1: Open Case` ➔ `Step 2: Add Session` ➔ `Step 3: Ingest Material` ➔ `Step 4: Review Transcript` ➔ `Step 5: Progress Report`
   - แสดงสถานะชัดเจน (`Completed ✓`, `Current ●`, `Upcoming ○`)
2. **Next Action Ribbon:**
   - ปุ่มแนะนำขั้นตอนถัดไปอัตโนมัติตามวงจรชีวิตของเซสชัน เช่น เมื่อเลือกเคสแล้วปุ่มจะเปลี่ยนเป็น `➕ Add New Session` และเมื่อถอดความเสร็จจะเปลี่ยนเป็น `✍️ Review Transcript & Attest`
3. **การบันทึกเสียงสดผ่านไมโครโฟน (Direct Speech Capture):**
   - บันทึกสัญญาณเสียงความละเอียดสูง 16kHz Mono WAV โดยตรง
   - หน้าปัดวัดระดับเสียงแบบเรียลไทม์ (Live VU Meter Canvas) ป้องกันเสียงเบาเกินไปหรือเกิด Audio Clipping
   - เมื่อกดหยุด สามารถส่งไฟล์เข้าสู่กระบวนการถอดความอัตโนมัติ (ASR Transcription) และคำนวณตัวชี้วัดเสียง/ภาษาเข้าสู่ Step 4 ทันที
4. **Collapsible Technical Details Disclosure:**
   - แยกส่วนการแสดงผลเชิงเทคนิค (Data Sources, Pipeline Versions, Cryptographic SHA-256 Hashes) ไว้ในกรอบที่พับเก็บได้ เพื่อไม่ให้บดบังผลการประเมินทางคลินิก

---

## 5. การติดตามพัฒนาการข้ามเซสชัน (Longitudinal Trajectory Analysis)

1. **การเปรียบเทียบพัฒนาการระยะยาว:**
   - บันทึกและเปรียบเทียบตัวชี้วัดสำคัญข้ามแต่ละครั้งที่นัดหมาย (เช่น สัปดาห์ที่ 1, 2, 4)
   - แสดงอัตราการเปลี่ยนแปลง (Deltas) เช่น การเพิ่มขึ้นของ MLU-w (`+1.32 คำ/ประโยค ↑`), การเพิ่มการผลัดกันพูด (`+7 รอบ ↑`), และการลดลงของ Echolalia (`-3 ครั้ง ↓`)
2. **การนำเสนอผลแบบหลายแพลตฟอร์ม:**
   - **Web App (`apps/lingualens-app`):** คอมโพเนนต์ `LongitudinalTrendCard` แสดงผล Responsive พร้อมป้ายสถานะทางคลินิก
   - **Clinical PDF Report:** ตารางประวัติพัฒนาการจัดหน้าสวยงามในรูปแบบ A4 Print Layout

---

## 6. เครื่องมือส่งออกรายงานสองภาษา (Clinical Export Engine)

1. **รายงานแบบสองภาษา (Bilingual Thai/English HTML Report):**
   - รองรับการเปิดผ่านเว็บเบราว์เซอร์พร้อมปุ่ม **"🖨️ พิมพ์รายงาน / Save as PDF"**
   - กฎการพิมพ์ `@media print` จัดหน้ากระดาษ A4 มาตรฐาน ซ่อนปุ่มควบคุม และป้องกันการตัดแบ่งตารางกลางหน้า (Avoid page-break inside)
2. **แผนภาพใยแมงมุม 5 มิติ (Spider Radar SVG Diagram):**
   - พล็อตเปรียบเทียบค่าที่วัดได้จากเด็ก (พื้นที่แรเงาสีฟ้า) กับค่าเกณฑ์พัฒนาการตามวัยปกติ (Typical Development - เส้นประสีเขียว)
   - เรนเดอร์เป็น Pure Vector SVG แบบสมบูรณ์ในตัวโดยไม่ต้องพึ่งพาโมดูลภายนอก
3. **การลงนามรับรองผล (Digital Clinician Attestation):**
   - บันทึกชื่อนักบำบัดผู้ตรวจรับรอง และประทับตรารับรองมาตรฐาน TalkBank CHAT

---

## 7. ผลการทดสอบและการตรวจสอบความถูกต้อง (Verification & Quality Assurance)

- **Python Test Suites (`.venv312`):**
  - `tests/test_thai_lsa.py`: 3/3 ผ่าน
  - `tests/test_audio_controller.py`: 3/3 ผ่าน
  - `tests/test_gui_stepper_and_recording.py`: 4/4 ผ่าน
  - `tests/test_export_engine.py`: 2/2 ผ่าน
  - `apps/api/tests/test_feature_provider.py`: 38/38 ผ่าน
  - `apps/api/tests/test_report_service_v1.py`: 22/22 ผ่าน
- **Next.js Web App Test Suites (`apps/lingualens-app`):**
  - `src/__tests__/longitudinal-trend-card.test.tsx`: 4/4 ผ่าน
  - `src/__tests__/clinical-pdf-report.test.tsx`: 10/10 ผ่าน
  - ภาพรวม Frontend: 69 test files, 569 unit tests ผ่าน 100%
