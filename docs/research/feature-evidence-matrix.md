# LinguaLens Research Inventory & Feature-Evidence Matrix

**Version:** 2.0 (Assessment V2 E1 Comprehensive Specification)  
**Date:** 2026-09-12  
**Target Audience:** Clinical Researchers, Speech-Language Pathologists, Machine Learning Engineers, API Architects  
**Clinical Safety Boundary:** LinguaLens is a research and educational prototype for speech-language therapists. It is **not a diagnostic instrument**, has **no automated ASD diagnosis or clinical validation**, and must strictly decouple measured numeric changes from clinician-authored clinical impressions. If any evidence source or quality requirement is not met, the system must return explicit `unavailable` or `insufficient_data` states rather than simulating or imputing values.

---

## 1. Verified Literature Foundation (`/Users/porschecaa/Desktop/Paper-ASD/`)

All 10 core papers below were examined directly from local PDF files on disk at `/Users/porschecaa/Desktop/Paper-ASD/`:

| Paper Key | Citation & Resolved Title | Exact Pages | Cohort Details | Language & Task | Measured Construct | Clinical Limitations & Thai Transfer Boundary |
|---|---|---|---|---|---|---|
| **`RBSTR768`** | Assaf, Shehabeddine & Ramesh (2025). *Screening autism spectrum disorder in children using machine learning on speech transcripts*. Scientific Reports. | pp. 1–8 (Table 1, pp. 2–3) | $N=110$ children from TalkBank CHILDES corpora (Eigsti, Flusberg, Rollins); ASD vs TD controls (ages 2–6 yrs). | English; naturalistic parent-child dialogue & semi-structured play. | Transcript linguistic markers: MLU, TTR, total utterances, echolalia, pronoun reversal, vocabulary size. | English morphosyntactic inflection rules (e.g. past tense `-ed`, plural `-s`) cannot be transferred to isolating Thai morphology. Word segmentation in Thai requires certified tokenizers. |
| **`27IITKNS`** | Eni et al. (2025). *Reliably quantifying the severity of social symptoms in children with autism using ASDSpeech*. Translational Psychiatry. | pp. 1–10 (Cohort, p. 2; ADOS validation, p. 5) | $N=197$ children with ASD; 99,193 vocalizations across multiple longitudinal assessment sessions. | Hebrew; naturalistic caregiver-child interaction and ADOS-2 sessions. | Continuous acoustic severity quantification vs ADOS-2 Calibrated Severity Score (CSS) across time. | Supports continuous symptom tracking over binary classification; cross-linguistic acoustic norms require native calibration; does not justify automated diagnostic labels. |
| **`2M5MN383`** | Megerian et al. (2022). *Evaluation of an artificial intelligence-based medical device for diagnosis of autism spectrum disorder*. NPJ Digital Medicine. | pp. 1–11 (Endpoints, pp. 2–3; Indeterminate rate, p. 5) | $N=425$ intent-to-diagnose toddlers (ages 18–72 mos; mean 40.5 mos); FDA-cleared Canvas Dx device trial. | English; multi-source: caregiver questionnaire + video analysis + clinician review. | Multi-modal risk output with mandatory **indeterminate/uncertainty band** as a primary safety control. | Crucial finding: 68.2% of subjects received an **indeterminate** result; only 31.8% were determinate completers. Proves that wide indeterminate bands are an essential clinical risk control, not a system failure. |
| **`2BW3LG5M`** | Bae et al. (2025). *Multimodal AI for risk stratification in autism spectrum disorder: integrating voice and screening tools*. NPJ Digital Medicine. | pp. 1–15 (Cohort, p. 2, 8–9; Whisper encoder, p. 11) | $N=1,242$ toddlers (ages 18–48 mos). Stage 1 ($N=818$, TD vs non-TD); Stage 2 ($N=515$, ASD vs other developmental delays). | Korean; Whisper fine-tuned voice encoder + screening tools (M-CHAT-R/F, SCQ-L, SRS). | Multi-modal risk stratification (AUROC 0.942 in Stage 1, 0.914 in Stage 2). | Emphasizes that voice alone is insufficient; multimodal integration (audio + caregiver report + clinician observation) is required for robust stratification. Korean language models require retraining for Thai. |
| **`7IKT7JCG`** | Tangviriyapaiboon et al. (2022). *Development and psychometric evaluation of a Thai Diagnostic Autism Scale for the early diagnosis of Autism Spectrum Disorder*. Autism Research. | pp. 1–11 (Construct validity $N=170$, p. 7; Diagnostic trial $N=130$, p. 11; Inter-rater $N=21$, p. 6) | $N=130$ Thai children (ages 12–48 mos; 85.7% male in inter-rater cohort). | Thai; standardized observation scale (TDAS) administered by certified clinicians. | Gold standard Thai clinical scale across DSM-5 domains (social reciprocity, communication, repetitive behaviors). | Proprietary Thai Department of Mental Health scale. Scoring thresholds ($\ge 5$ points across $\ge 5$ domains) require certified human administration; item content must NOT be copied without copyright license. |
| **`XSIL8EJU`** | Srisinghasongkram et al. (2016). *Two-Step Screening of the Modified Checklist for Autism in Toddlers in Thai Children with Language Delay and Typically Developing Children*. JADD. | pp. 1–13 (Cohort, pp. 3–4; Sensitivity/PPV, pp. 7–9) | $N=109$ high-risk Thai children with language delay ($41.3\%$ ASD, $48.6\%$ language disorder, $7.3\%$ GDD) + $N=732$ typically developing Thai toddlers (ages 18–48 mos). | Thai; parent-completed M-CHAT Thai followed by clinical interview follow-up. | Sensitivity ($90.7\%$), Specificity ($99.7\%$), PPV ($96.1\%$), NPV ($99.4\%$) under total scoring ($\ge 3$ items failed). | Parent report alone has a high false positive rate; two-step clinical verification is essential in Thai clinical settings. High overlap between ASD and isolated language delay. |
| **`H7DB7I5I`** | Ma et al. (2024). *Can Natural Speech Prosody Distinguish Autism Spectrum Disorders? A Meta-Analysis*. Behavioral Sciences. | pp. 1–19 (Meta-analysis results, pp. 6–12) | Meta-analysis of 28 international natural speech studies across pediatric and adolescent ASD cohorts. | Multiple languages; naturalistic conversation and narrative speech. | Fundamental frequency (F0 mean, F0 SD/IQR), speech rate, pause duration, and pitch range. | High heterogeneity between recording hardware and environments. In tonal languages like Thai, pitch excursions carry lexical identity, so English/European prosodic thresholds cannot be applied directly. |
| **`KMH2LMXK`** | Rybner et al. (2022). *Vocal markers of autism: Assessing the generalizability of machine learning models*. Autism Research. | pp. 1–33 (Cross-corpus drop, pp. 12–18) | Multi-corpus benchmark across distinct acoustic recording settings and languages. | English and Scandinavian languages; semi-structured speech samples. | Generalizability of acoustic ML classifiers across independent datasets. | F1 scores collapsed from 0.89 within-corpus down to 0.59 out-of-distribution. Proves acoustic ML features overfit to room acoustics, microphones, and background noise without cross-corpus normalization. |
| **`QJR8K5QS`** | *The Noor Project: fair transformer transfer learning for autism spectrum disorder recognition from speech* (2025). | pp. 1–13 (Subgroup fairness, pp. 6–9) | Pediatric speech recordings across diverse linguistic and demographic groups. | Arabic and English speech samples. | Transformer-based acoustic feature transfer; fairness audits across sex and age subgroups. | Discovered that overall model accuracy masked severe degradation in female pediatric subgroups. Demonstrates why disaggregated subgroup reporting is required before deploying speech AI. |
| **`G8VSSXXB`** | Themistocleous, Andreou & Peristeri (2024). *Autism Detection in Children: Integrating Machine Learning and Natural Language Processing in Narrative Analysis*. Behavioral Sciences. | pp. 1–16 (NLP features, pp. 4–8) | $N=60$ children (ages 6–9 yrs; 30 ASD, 30 TD). | Greek; narrative generation (story retelling from wordless picture books). | Narrative cohesion, syntactic dependency length, lexical diversity, and discourse markers. | Requires a standardized narrative elicitation protocol; cannot be computed from short, disjointed conversational play utterances. |

---

## 2. Measured Features Specification (Speech, Audio & Transcript)

The canonical feature schema version is `features_v2` (`pipeline_v1`). All measured features are scalar values belonging to an immutable `MeasuredFeature` dataclass with explicit units, sources, states, and provenance.

### 2.1 Canonical Feature Inventory

| # | Feature Key | Domain | Unit | Extractor / Method | Input Modality | Speaker Gate | Missing / Incomplete Behavior | Limitations & Thai Clinical Transfer |
|---|---|---|---|---|---|---|---|---|
| 1 | `mluw` | Expressive Language | words/utt | Word count / child turns | Reviewed transcript segments | Yes (`CHI` only) | `insufficient_data` if turns $< 10$ | Requires certified Thai word tokenizer (PyThaiNLP). Morpheme-based MLU is non-standard in Thai. |
| 2 | `ttr` | Expressive Language | ratio (0–1) | Unique word tokens / total tokens | Reviewed transcript segments | Yes (`CHI` only) | `insufficient_data` if tokens $< 50$ | Highly sensitive to transcript length; non-comparable across assessments with differing total word counts. |
| 3 | `vocabulary_size` | Expressive Language | words | Count of distinct lexical items | Reviewed transcript segments | Yes (`CHI` only) | `0` | Bounded by session duration and elicitation activity. |
| 4 | `total_utterances` | Expressive Language | count | Count of child turn segments | Reviewed transcript segments | Yes (`CHI` only) | `0` | Activity duration context required to interpret volume. |
| 5 | `total_words` | Expressive Language | count | Sum of tokens spoken by child | Reviewed transcript segments | Yes (`CHI` only) | `0` | Excludes punctuation and transcriber nonverbal annotations. |
| 6 | `unintelligible_count` | Speech Clarity | count | Regex count of `xxx` and `[unintelligible]` | Reviewed transcript segments | Yes (`CHI` only) | `0` | Heavily affected by ambient background noise and audio SNR. |
| 7 | `unintelligible_ratio` | Speech Clarity | ratio (0–1) | Unintelligible count / total child turns | Reviewed transcript segments | Yes (`CHI` only) | `insufficient_data` if turns $< 10$ | Does not differentiate between articulatory dyspraxia and microphone clipping. |
| 8 | `nonverbal_vocalizations` | Speech Clarity | count | Annotation count of laughter, cries, grunts | Reviewed transcript segments | Yes (`CHI` only) | `0` | Requires transcriber fidelity in tagging non-speech vocalizations. |
| 9 | `child_adult_turn_ratio` | Conversational | ratio | Child turns / Adult turns | Multi-speaker segments | Multi-speaker | `unavailable` if adult turns $= 0$ | Influenced by whether therapist adopts an active prompting vs passive play posture. |
| 10 | `turn_taking_count` | Conversational | count | Alternating `INV`/`MOT` $\to$ `CHI` sequences | Multi-speaker segments | Multi-speaker | `0` | Requires accurate speaker diarization boundary attestation. |
| 11 | `response_latency_avg` | Conversational | seconds | Audio silence gap between adult and child | Aligned audio + millisecond timestamps | Multi-speaker | `unavailable` (`no_aligned_audio`) | **Acoustic boundary**: Transcript text alone cannot supply latency. Unavailable without forced alignment. |
| 12 | `question_ratio` | Social Communication | ratio (0–1) | Question turns / total child turns | Reviewed transcript segments | Yes (`CHI` only) | `0.0` | In Thai, questions use grammatical particles (ไหม, หรือ, อะไร, ใช่ไหม). Punctuation marks alone will fail. |
| 13 | `echolalia_count` | Repetitive Language | count | Immediate verbatim word overlap | Multi-speaker segments | Multi-speaker | `0` | Detects immediate echolalia only; delayed or mitigated echolalia cannot be detected from brief segments. |
| 14 | `echolalia_ratio` | Repetitive Language | ratio (0–1) | Echolalia turns / child turns | Multi-speaker segments | Multi-speaker | `insufficient_data` if turns $< 10$ | Low base rate in spontaneous play. |
| 15 | `speech_rate_wpm` | Prosody & Temporal | wpm | Child words / child vocalization duration | Audio duration + transcript | Yes (`CHI` only) | `unavailable` (`no_audio_duration`) | Requires pause subtraction from vocalization intervals. |

---

## 3. Structured Clinical & Caregiver Observations (Qualitative & Behavioral)

Observations represent qualitative clinical judgments and behavioral observations that complement transcript measurements. They are modeled in `app.assessment_v2.domain.observations.AssessmentObservation` and persisted with tenant RLS:

### 3.1 Observation Architecture & Lifecycle
1. **Observation Categories**:
   - `communication`: Gesture usage, pointing, gaze shifting during requests.
   - `social_engagement`: Shared enjoyment, eye contact, reciprocal social smiling.
   - `play_behavior`: Functional toy play, symbolic/pretend play, repetitive object manipulation.
   - `sensory_motor`: Hyper/hypo-reactivity to sound, tactile defensiveness, motor mannerisms.
   - `emotional_regulation`: Frustration tolerance, transitions between activities, self-soothing.
2. **Provenance & Attribution**:
   - `observer_role`: `clinician`, `caregiver`, or `educator`.
   - `activity_context`: Linked to protocol activity (e.g., `free_play`, `snack_routine`).
   - `time_offset_ms`: Optional millisecond reference linking observation to a specific recording interval.
3. **Immutable Corrections & Stale Propagation**:
   - Observations are append-only.
   - When an observation is amended, the previous version is superseded (`amended_by_id`), preserving full audit provenance.
   - Amending an observation triggers stale propagation on dependent clinical review cues.

---

## 4. Standardized Instrument Administrations (Generic & Multimodal)

Standardized developmental instruments (e.g. M-CHAT-R/F, Vineland-3, ADOS-2, TDAS/TDLR-II) provide structured scoring benchmarks. They are modeled in `app.assessment_v2.domain.instruments.InstrumentAdministration`:

### 4.1 Copyright & Licensing Protection Rules
- **Prohibition on Unauthorized Duplication**: Protected questionnaire forms, verbatim test prompts, and copyrighted scoring sheets must **never** be copied into code, fixtures, or database schemas without verified licensing rights.
- **Generic Schema Representation**: The platform stores:
  - `instrument_key`: Normalized token (e.g., `mchat_rf_v1`, `vineland_3_survey`, `tdas_th_v1`).
  - `respondent_type`: `caregiver`, `clinician`, `teacher`.
  - `administered_date`: Date of test completion.
  - `total_score` and `domain_scores`: Normalized key-value numeric dictionaries.
  - `risk_level` or `raw_summary`: Qualitative tier (`low_risk`, `medium_risk`, `high_risk`) as published in open scoring manuals.
  - `verified_by_clinician_id`: Clinician signature verifying administration validity.

---

## 5. Recording-to-Transcript & Acoustic/Timing Capability Audit

```
+----------------------------------------------------------------------------------------------------+
|                                    RECORDING & PROCESSING PIPELINE                                 |
+----------------------------------------------------------------------------------------------------+
| 1. AUDIO UPLOAD & QUALITY GATE (quality.py)                                                        |
|    - Checks: duration >= 120s, loudness -26 to -14 dBFS, silence ratio < 0.40, SNR >= 10 dB        |
|    - Output: USABLE -> proceeds; DEGRADED/UNUSABLE -> flags INSUFFICIENT_DATA                      |
+----------------------------------------------------------------------------------------------------+
                                                |
                                                v
+----------------------------------------------------------------------------------------------------+
| 2. ASR TRANSCRIPTION & SPEAKER DIARIZATION (reviewed_transcript_worker.py)                         |
|    - ASR Engine: Whisper Large v3 (Thai acoustic model) -> produces word tokens with millisecond   |
|      timestamps and confidence scores.                                                             |
|    - Diarization: Speaker identification (CHI, INV, MOT).                                          |
|    - Human-in-the-Loop Attestation Gate: Transcripts must be verified by a therapist on            |
|      H11-S/U/E before evidence extraction can execute.                                             |
+----------------------------------------------------------------------------------------------------+
                                                |
                                                v
+----------------------------------------------------------------------------------------------------+
| 3. MULTIMODAL EVIDENCE EXTRACTION (evidence_worker.py)                                             |
|    - Transcript Metrics: MLU, TTR, vocabulary, turn counts, echolalia (COMPLETED)                 |
|    - Acoustic Features: F0 mean, F0 SD, Jitter, Shimmer, Response Latency -> UNAVAILABLE           |
|      * Reason: Uncalibrated recording hardware, lack of forced alignment, and Thai lexical tone   |
|        entanglement.                                                                               |
|    - Safety Boundary: System never fakes pitch or latency data when unavailable.                   |
+----------------------------------------------------------------------------------------------------+
```

### 5.1 Real Capabilities vs Current Unavailable Features

1. **Fully Usable & Tested (Available)**:
   - Guided audio recording capture and duration enforcement.
   - Audio loudness, silence ratio, and SNR quality validation.
   - CHAT and segment transcript parsing.
   - Lexical and structural speech features: `mluw`, `ttr`, `vocabulary_size`, `total_utterances`, `total_words`, `unintelligible_count`, `unintelligible_ratio`, `child_adult_turn_ratio`, `turn_taking_count`, `echolalia_count`, `echolalia_ratio`.
   - Structured qualitative observations with tenant RLS.
   - Generic instrument administrations.
2. **Explicitly Unavailable (Flagged with Limitation Reasons)**:
   - `pitch_mean`, `pitch_variability`: **Unavailable** (`uncalibrated_recording_device`). Consumer smartphone/laptop microphones have inconsistent frequency responses, and Thai lexical tones confound affective prosody analysis without phonemic tone modeling.
   - `response_latency_avg`: **Unavailable** (`no_aligned_audio`). Reliable conversational latency requires millisecond-accurate cross-channel acoustic diarization; raw ASR transcript timestamps have too much jitter for millisecond latency calculation.
   - `formant_dispersion`, `jitter`, `shimmer`: **Unavailable** (`acoustic_pipeline_uncalibrated`). Requires laboratory-grade acoustic capture.
   - `automated_asd_probability`: **Prohibited by Design**. Under no circumstances will the system output an ASD risk percentage or automated diagnostic classification.
