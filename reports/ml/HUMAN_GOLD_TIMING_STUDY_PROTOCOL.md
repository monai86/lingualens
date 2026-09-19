# LinguaLens Human Gold Timing & Boundary Validation Study Protocol
**Protocol Identifier:** `LL-STUDY-TIMING-GOLD-v1`  
**Protocol Version:** 1.0.0-RESEARCH  
**Document Date:** 2026-08-24  
**Status:** Methodological Validation Protocol (Measurement Development)  

---

## 1. Study Objective & Primary Research Question

### Primary Research Question:
> *"How accurately does the LinguaLens acoustic timing pipeline estimate adult speech offset, child speech onset, and derived conversational response latency compared with manually annotated reference boundaries produced by trained human phoneticians?"*

### Scientific Purpose:
Text-only transcripts cannot capture millisecond turn-taking dynamics. However, automated alignment pipelines (VAD, diarization, WhisperX, MFA) carry measurement error on pediatric conversational recordings. This study establishes empirical measurement accuracy and inter-annotator agreement before acoustic features enter clinical or predictive models.

---

## 2. Study Endpoints & Error Metrics

```text
┌─────────────────────────────────────────────────────────────┐
│                    STUDY ENDPOINT HIERARCHY                 │
│                                                             │
│  [PRIMARY ENDPOINT]                                         │
│  ├── Mean Absolute Error (MAE) of Response Latency (ms)     │
│  └── Median Absolute Error of Speech Onset / Offset (ms)    │
│                                                             │
│  [SECONDARY ENDPOINTS]                                      │
│  ├── Signed Mean Bias (ms) [Systematic over/under estimation]│
│  ├── 95th Percentile Absolute Error (P95 AE)               │
│  ├── Descriptive Tolerance Bands (±20ms, ±50ms, ±100ms, ±200ms)│
│  ├── Catastrophic Failure Rate (% errors > 250 ms)          │
│  ├── Inter-Annotator Agreement (ICC(2,1) & Bland-Altman)    │
│  └── Diarization Error Rate (DER)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Operational Definitions for Human Phonetic Annotation

Annotators must adhere to standardized acoustic criteria in Praat / ELAN:

1. **Adult Speech Onset:** The earliest acoustic evidence of speech produced by the adult examiner (e.g. initial stop burst, frication onset, or first glottal pulse of voicing). Excludes pre-speech inhalation or ambient room clicks.
2. **Adult Speech Offset:** The point where adult speech energy ceases (e.g. final frication end, vocal fold vibration cessation, or closure silence). Excludes trailing room reverberation.
3. **Child Speech Onset:** The first reliable acoustic evidence of speech produced by the target child.
4. **Child Speech Offset:** The termination of child acoustic speech activity.
5. **Child Non-Speech Vocalization (`CHILD_NONSPEECH`):** Non-lexical vocal sounds produced by the child, including laughs, cries, squeals, grunts, sighs, and vegetative sounds. **Non-speech vocalizations must NOT be coded as verbal speech turns.**
6. **Overlap (`OVERLAP`):** Simultaneous active acoustic phonation from both adult and child.
7. **Unintelligible Speech (`UNINTELLIGIBLE_SPEECH`):** Acoustic signal is unambiguously speech, but phonemes/words cannot be transcribed with confidence.
8. **Exclude (`EXCLUDE`):** Intervals containing severe external acoustic contamination (e.g. door slam, parent interruption, dropped microphone).

---

## 4. Vocal vs. Verbal Response Latency Separation

LinguaLens formally distinguishes two separate response timing constructs:

$$\text{Verbal Response Latency} = t_{\text{child\_lexical\_onset}} - t_{\text{adult\_speech\_offset}}$$
$$\text{Vocal Response Latency} = t_{\text{child\_first\_vocal\_onset}} - t_{\text{adult\_speech\_offset}}$$

*Construct Boundary:* A child who laughs immediately (50 ms) and then speaks after 800 ms exhibits low vocal latency but moderate verbal latency. Feature Schema v3a currently measures **Verbal Response Latency**; non-speech vocal latencies are tracked separately in the annotation gold set.

---

## 5. Praat / ELAN TextGrid Multi-Tier Specification

Gold annotations must be recorded across standardized multi-tier TextGrids:

```text
Tier 1 (Interval): ADULT_SPEECH          ["What color is this?"]
Tier 2 (Interval): CHILD_SPEECH          ["Red car"]
Tier 3 (Interval): CHILD_NONSPEECH       ["[gasp]"]
Tier 4 (Interval): OVERLAP               ["[overlap_01]"]
Tier 5 (Interval): NOISE                 ["[toy_drop]"]
Tier 6 (Interval): UNINTELLIGIBLE_SPEECH ["[unintelligible]"]
Tier 7 (Interval): EXCLUDE               ["[parent_entered]"]
Tier 8 (Interval): ADULT_PROMPT_LEVEL    ["LEVEL_3_WH_QUESTION"]
Tier 9 (Interval): TASK_BLOCK            ["BLOCK_B_SEMI_STRUCTURED"]
Tier 10 (Text):    ANNOTATOR_NOTE        ["Whispered child onset"]
```

---

## 6. Two-Independent-Annotator Study Design

```text
                       PEDIATRIC RECORDINGS
                                │
               ┌────────────────┴────────────────┐
               ▼                                 ▼
       [CALIBRATION SET]                 [VALIDATION SET]
       5–8 Recordings                    20–30 Recordings
       (~80-100 turn transitions)        (~300-500 turn transitions)
               │                                 │
       Joint Practice                    Independent Blinded Coding
       & Rule Alignment                  (Annotator A vs Annotator B)
                                                 │
                                        Inter-Rater Agreement
                                        (MAE, ICC, Bland-Altman)
                                                 │
                                        Disagreement Identification
                                        (|Diff| > 100 ms)
                                                 │
                                        Senior Expert Adjudication
                                        (Third Senior Phonetician)
                                                 │
                                        LOCKED GOLD REFERENCE
```

### Blinding Requirements:
- Annotator A and Annotator B work independently without cross-communication.
- Annotators are blinded to:
  1. Diagnostic group (ASD vs TD vs DD).
  2. Model predictions and automated transcript text.
  3. Automated boundary placements.

---

## 7. Statistical Analysis & Bland–Altman Agreement Framework

1. **Inter-Annotator Reliability:** Evaluated via $\text{ICC}(2,1)$ (Two-way random effects, absolute agreement, single measures) on derived response latency.
2. **Bland–Altman Agreement Analysis:**
   - Mean Bias: $\bar{d} = \frac{1}{N} \sum (t_{\text{auto}} - t_{\text{manual}})$
   - Standard Deviation of Differences: $s_d$
   - 95% Limits of Agreement (LoA): $[\bar{d} - 1.96 s_d, \, \bar{d} + 1.96 s_d]$
3. **Quality Stratification:**
   Errors will be stratified across technical conditions:
   - Clean (SNR $\ge 20\text{ dB}$) vs Noisy (SNR $< 15\text{ dB}$)
   - Isolated Turns vs Overlapping Turns
   - Clear Speech vs Partially Unintelligible Speech
   - Toddlers (< 36 months) vs Older Children ($\ge 36$ months)
