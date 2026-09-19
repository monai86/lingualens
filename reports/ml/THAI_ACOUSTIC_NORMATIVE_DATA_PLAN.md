# Thai Acoustic & Prosodic Normative Reference Development Plan
**Document Identifier:** `LL-PLAN-THAI-NORMS-v1`  
**Document Date:** 2026-08-24  
**Status:** Prospective research roadmap; no validated Thai norms or product integration  

---

## 1. Non-Transferability of English Acoustic Thresholds

**Strict Scientific Mandate:**  
*English-derived acoustic, pitch variability, or conversational response-latency cutoffs shall NEVER be applied directly to Thai pediatric speech-language samples.*

### Scientific Rationale:
1. **Tonal Pitch Modulation:** Thai lexical tones fundamentally alter F0 variance and trajectory distributions compared to non-tonal English speech.
2. **Cultural Interaction Rhythms:** Pragmatic turn-taking pacing and back-channeling behaviors differ between Western conversational samples and Thai caregiver-child clinical interactions.
3. **Phonetic Inventory:** Thai vowel length distinctions (short vs long vowels) and syllable final stop unreleased codas (/p̚/, /t̚/, /k̚/) create unique duration and pause profiles.

---

## 2. Normative Development Sequence

The following sequence is a research-governance proposal. It does not authorize a clinical percentile or normative score to be displayed:

```text
STAGE 1: Accurate Measurement Validation (Gold Timing MAE < 100 ms)
   ↓
STAGE 2: Test-Retest Measurement Stability (ICC > 0.70)
   ↓
STAGE 3: Protocol-Controlled Multicenter Collection (L-SLSP-v1, N ≥ 150 TD Children)
   ↓
STAGE 4: Age- & Sex-Stratified Reference Distribution Modeling (GAMLSS Curves)
   ↓
STAGE 5: Separate clinical-validation and product-governance decision
```

**Anti-Pattern Prohibited:** Collecting a small convenience sample of 20 children and immediately labeling metrics as "normal vs abnormal".

---

## 3. Research-Only Output Boundary

Current Thai acoustic candidates must remain offline research measurements and must not appear in therapist-product reports. The example below is an illustrative research-summary format only, not a current or approved product output:

```text
┌─────────────────────────────────────────────────────────────┐
│              ILLUSTRATIVE THAI RESEARCH SUMMARY             │
│                                                             │
│  [PROHIBITED OVERCLAIMING OUTPUT]                           │
│  ❌ "Response Latency: Abnormal (ASD Risk: High)"           │
│  ❌ "Pitch Variation: Severely Flat Intonation"             │
│                                                             │
│  [RESEARCH-ONLY DESCRIPTIVE EXAMPLE]                        │
│  ✅ "ระยะเวลาการตอบสนอง (Response Latency):                     │
│      - ค่ามัธยฐาน (Median): 580 ms                          │
│      - ช่วงการกระจาย (IQR): 210 ms                          │
│      - จำนวนรอบการสนทนาที่คำนวณได้: 16 คู่ (Valid)         │
│      - สถานะการวัดผล: VALID"                                │
│                                                             │
│  ✅ "ความผันแปรของระดับเสียง (F0 Pitch SD):                 │
│      - ค่าเบี่ยงเบนมาตรฐาน: 3.8 semitones (Ref 50 Hz)       │
│      - ความครอบคลุมเสียงพูด: 84.5% (Valid)"                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Prospective Multi-Language Research Contract

The following prospective contract illustrates what a separately reviewed research pipeline could require. It is not implemented in the active therapist product:

```python
@dataclass(frozen=True)
class LanguageContext:
    language_code: str  # "th" or "en"
    dialect: str        # "central_thai", "northern_thai", "en_us"
    is_tonal: bool      # True for "th", False for "en"
    syllable_tokenizer: str
    alignment_model_id: str
    normative_reference_id: Optional[str]
```
