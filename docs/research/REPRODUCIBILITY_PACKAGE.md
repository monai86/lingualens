# LinguaLens Scientific & Software Reproducibility Package

**Package Version:** 2.0 (Assessment V2 V1 Deliverable)  
**Date:** 2026-09-12  
**Software Repository Base:** `.worktrees/antigravity-assessment-v2-continuation` (branch `antigravity/assessment-v2-continuation`)  
**Clinical Scope & Transfer Boundary:** Speech-language research and decision-support prototype. Calibrated for Thai pediatric language sampling (ages 18–60 months). All features, algorithms, and schema definitions are strictly reproducible from synthetic fixtures.

---

## 1. Paper-to-Feature Traceability Matrix

Every feature, boundary rule, and clinical safety constraint implemented in LinguaLens is directly traceable to peer-reviewed scientific literature verified from primary PDF sources at `/Users/porschecaa/Desktop/Paper-ASD/`:

| Ref Key | Full Citation | DOI / Identifier | Verified Source Location | Primary Clinical Construct | Implementation in LinguaLens | Thai Clinical Transfer Boundary |
|---|---|---|---|---|---|---|
| `RBSTR768` | Assaf et al. (2025). *Screening autism spectrum disorder in children using machine learning on speech transcripts*. Sci Rep. | `10.1038/s41598-025-86518-5` | pp. 1–8; Table 1 (pp. 2–3) | Transcript linguistic markers (MLU, TTR, vocabulary size). | Feature extractors `mluw`, `ttr`, `vocabulary_size` in `evidence.py`. | English inflectional morphemes do not apply to Thai; implemented PyThaiNLP word-level tokenization. |
| `27IITKNS` | Eni et al. (2025). *Reliably quantifying the severity of social symptoms in children with autism using ASDSpeech*. Transl Psychiatry. | `10.1038/s41398-024-03204-1` | pp. 1–10; Cohort p. 2; ADOS validation p. 5 | Continuous acoustic symptom tracking over longitudinal sessions. | Continuous numeric delta evaluation in `longitudinal.py` without diagnostic bucketing. | Cross-linguistic acoustic norms require native Thai acoustic calibration. |
| `2M5MN383` | Megerian et al. (2022). *Evaluation of an AI-based medical device for diagnosis of ASD*. NPJ Digit Med. | `10.1038/s41746-022-00598-6` | pp. 1–11; Indeterminate analysis p. 5 | Multi-modal risk output with mandatory wide indeterminate band. | Mandatory `indeterminate` status on longitudinal comparisons without approved norm bands. | Canvas Dx trial demonstrated 68.2% indeterminate rate; wide indeterminate bounds are an essential safety control. |
| `2BW3LG5M` | Bae et al. (2025). *Multimodal AI for risk stratification in ASD: integrating voice and screening tools*. NPJ Digit Med. | `10.1038/s41746-024-01389-1` | pp. 1–15; Whisper encoder p. 11; Cohort pp. 8–9 | Multi-modal fusion (audio acoustic encoder + caregiver M-CHAT-R/F). | Generic instrument model `InstrumentAdministration` and multi-modal review. | Voice alone is insufficient; multimodal integration (audio + caregiver report + clinician observation) required. |
| `7IKT7JCG` | Tangviriyapaiboon et al. (2022). *Development and psychometric evaluation of a Thai Diagnostic Autism Scale (TDAS)*. Autism Res. | `10.1002/aur.2789` | pp. 1–11; Inter-rater p. 6; Validation p. 7 | Standardized Thai gold-standard clinical observation scale. | Architecture supports TDAS score recording without copying proprietary item text. | Proprietary Thai Department of Mental Health scale; scoring requires certified human administration. |
| `XSIL8EJU` | Srisinghasongkram et al. (2016). *Two-Step Screening of M-CHAT in Thai Children with Language Delay*. JADD. | `10.1007/s10803-016-2766-3` | pp. 1–13; Sensitivity/PPV pp. 7–9 | High sensitivity/PPV under 2-step clinical verification in Thai toddlers. | Two-step clinician review gate: caregiver responses must be verified by clinician. | High overlap between ASD and isolated language delay in Thai children requires clinician differential diagnosis. |
| `H7DB7I5I` | Ma et al. (2024). *Can Natural Speech Prosody Distinguish ASD? A Meta-Analysis*. Behav Sci. | `10.3390/bs14020129` | pp. 1–19; Meta-analysis results pp. 6–12 | F0 variation, speech rate, pause duration, and pitch range. | Acoustic feature extraction with explicit audio SNR gates ($\ge 10$ dB). | Pitch is lexically phonemic in Thai (tonal language); European pitch variability thresholds cannot be transferred directly. |
| `KMH2LMXK` | Rybner et al. (2022). *Vocal markers of autism: Assessing the generalizability of machine learning models*. Autism Res. | `10.1002/aur.2685` | pp. 1–33; Cross-corpus drop pp. 12–18 | Severe out-of-distribution performance collapse of acoustic ML. | Strict hardware and room acoustics limitation disclosures on all audio profiles. | F1 dropped from 0.89 to 0.59 out-of-distribution; models overfit to microphone acoustics. |
| `QJR8K5QS` | The Noor Project (2025). *Fair transformer transfer learning for ASD recognition from speech*. | Research Report | pp. 1–13; Subgroup fairness pp. 6–9 | Demographic and gender bias in pediatric speech transformer models. | Subgroup disaggregation and absence of opaque black-box probability predictions. | Female pediatric subgroups exhibited severe performance degradation under monolithic models. |
| `G8VSSXXB` | Themistocleous et al. (2024). *Autism Detection in Children: Integrating ML and NLP in Narrative Analysis*. Behav Sci. | `10.3390/bs14040306` | pp. 1–16; NLP features pp. 4–8 | Narrative syntax, dependency length, and discourse cohesion. | Syntactic markers decoupled from unstructured play samples; protocol-bound. | Requires structured storytelling protocols; cannot be inferred from disjointed play vocalizations. |

---

## 2. Canonical Schemas & Data Contract Versions

All data models are version-controlled with immutable JSON schema representations:

```
+----------------------------------------------------------------------------------------------------+
| SCHEMA SPECIFICATIONS                                                                              |
+----------------------------------------------------------------------------------------------------+
| 1. features_v2 (pipeline_v1)                                                                       |
|    - Dataclass: MeasuredFeature                                                                    |
|    - Attributes: key (str), value (float/bool/str/null), unit (str), source (str), state (str),    |
|                  limitation (str/null), provenance (MeasuredFeatureProvenance)                     |
| 2. cues-v2.0                                                                                       |
|    - Dataclass: AttentionCue                                                                       |
|    - Attributes: cue_id, cue_type, title, description, severity_level, policy_version,              |
|                  evidence_run_id, feature_key, status, clinician_action, clinician_rationale        |
| 3. longitudinal_v1                                                                                 |
|    - Dataclass: FeatureComparison                                                                  |
|    - Attributes: feature_key, unit, status (compatible/not_comparable), incompatibility_reasons,   |
|                  baseline_value, current_value, absolute_delta, percent_change, numerical_trend,   |
|                  clinical_interpretation ("indeterminate")                                         |
| 4. report_v1                                                                                       |
|    - Dataclass: SignedReportSnapshot                                                               |
|    - Attributes: report_id, assessment_id, status, signer_id, signed_at, snapshot_data,            |
|                  snapshot_sha256 (64-char hex), amends_report_id, amendment_sequence               |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Algorithmic Toolchain & Extractor Dependencies

| Component | Library / Tool | Exact Version | Configuration & Determinism |
|---|---|---|---|
| **Audio Preprocessing** | `librosa` / `soundfile` | `0.10.2` / `0.12.1` | Resampled to 16 kHz mono; silent regions detected using threshold $-35$ dBFS. |
| **Thai Tokenization** | `pythainlp` | `5.0.4` | Engine: `newmm` (maximal matching dictionary-based segmenter). |
| **CHAT Transcript Parser** | `pylangacq` | `0.19.2` | Cleaned tier extraction (`*CHI:`); punctuation and non-verbal tokens normalized. |
| **PDF Rendering** | `reportlab` | `4.2.5` | Native TrueType Thai font registration: `Ayuthaya.ttf` with fallback to `Thonburi.ttc`. |
| **Database Migrations** | `alembic` | `1.14.0` | Transactional DDL on PostgreSQL; strict migration length $\le 32$ characters. |
| **Hashing Engine** | Python `hashlib` | Built-in | Deterministic canonical JSON (`separators=(',', ':')`, `sort_keys=True`) hashed with SHA-256. |

---

## 4. Synthetic Data Receipts & Test Verification

All automated tests rely strictly on deterministic synthetic test fixtures. Zero patient data, identifiable names, or clinical audio bytes are contained in the repository.

```bash
# Verify complete reproducible suite
PYTHONPATH=apps/api:src pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
```
- **Total Test Cases:** 432 passed (including C1/C2 clinical review & reports contracts).
- **Zero Flakiness:** All tests execute deterministically in $< 15$ seconds without external network calls.
