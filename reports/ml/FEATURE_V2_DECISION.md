# LinguaLens Decision Gate 2: Feature Schema v2 Evidence Review
**Generated Date:** 2026-08-25  
**Status:** Candidate for descriptive research use; not clinical validation  
**Decision Authority:** Repository evidence and documented project safety boundary  

---

## 1. Epistemological and Validity Framework

To prevent scientific overclaiming, all feature assessments in LinguaLens are evaluated against distinct validity tiers:

1. **Deterministic Extraction:** The algorithmic extraction process is designed to generate identical feature values for identical ordered inputs. (Status: **TESTED** across supported path, parsed-object, and normalized-line inputs; synchronized exports are checksum-bound).
2. **Operational Definition:** The computational rules conform to explicit formulas (e.g. `speaker_balance_ratio = N_CHI / (N_CHI + N_Adult)`). (Status: **DEFINED AND TESTED**).
3. **Construct Validity:** The extracted numbers genuinely measure the intended psychological/clinical construct (e.g. conversational reciprocity, pragmatic interaction).  
   > *Crucial Scientific Distinction:* **"Feature Schema v2 demonstrates deterministic and operationally defined extraction. Construct validity as a measure of social-communication behavior requires independent human/reference validation."**
4. **Predictive Validity:** The corrected features produce mixed positive and negative benchmark deltas and do not establish a consistent improvement. (Status: **NOT ESTABLISHED**).
5. **Clinical Validity:** The features provide meaningful, actionable, and safe utility in real-world clinical decision-making across diverse settings. (Status: **NOT CLAIMED / PENDING PROSPECTIVE STANDARDIZED TRIALS**).

---

## 2. Decision Summary & Empirical Evidence

| Criterion | Evaluation Result | Status |
| :--- | :--- | :---: |
| **Deterministic Extraction** | Supported input paths agree; 0 missing conversational-feature values across 1,961 transcripts; exports are checksum-bound | **PASS (ENGINEERING)** |
| **Backward Compatibility** | `features-basic-v1` unaltered; existing pipelines continue to function without modification | **PASS** |
| **Operational Definition** | 8 conversational features precisely formulated in `FEATURE_V2_SPEC.md` | **PASS** |
| **Within-Domain ASD vs TD (Eigsti)** | AUROC changed from **0.6234** (V1) to **0.6089** (V1+V2) ($\Delta = -0.0145$) | **NO IMPROVEMENT** |
| **Differential comparison (ASD vs DD)** | V1 AUROC is **0.7730**; V1+V2 AUROC is **0.6708** ($\Delta = -0.1022$) | **DEGRADATION DOCUMENTED** |
| **Cross-Corpus Generalization** | Corrected V1+V2 AUROC is **0.5845** Eigsti→Nadig and **0.5938** Nadig→Eigsti; this does not establish transportability | **NOT ESTABLISHED** |
| **Corpus Prediction Audit** | Site classification remains high (**AUROC 0.7679 on V2, 0.9817 on V1+V2**), showing protocol/site information | **CONFOUNDING RISK** |

---

## 3. Evidence-Constrained Outcome: Descriptive Research Candidate

1. **Limited use of Feature Schema v2 (`features-conversation-v2`):**
   - Feature Schema v2 may be used for descriptive research characterization and exploratory interaction analysis only.
   - The 8 deterministic conversational features (`speaker_balance_ratio`, `turn_alternation_rate`, `child_run_length_mean`, `child_response_rate`, `adult_response_rate`, `partner_repetition_exact_ratio`, `partner_repetition_overlap_mean`, `self_repetition_exact_ratio`) capture operational turn dynamics.
2. **Preservation of Benchmark Freeze v1:**
   - Feature Schema v1 (`features-basic-v1`) remains frozen at `data/ml/results/baseline_v1_frozen.csv` as the internal comparison reference.
3. **Differential-comparison transparency:**
   - The corrected Feature Schema v2 does **not** improve ASD vs DD separation (V1 **0.7730** versus V1+V2 **0.6708**, $\Delta = -0.1022$). This retrospective comparison is not a diagnostic-performance claim.
4. **Scientific Realism & Non-Overclaiming Mandate:**
   - Text-only transcript analysis cannot overcome examiner interaction protocol disparities across academic laboratories.
   - No automated diagnostic claims shall be made on clinical populations.
5. **Transition to Feature Schema v3a (Acoustic Measurement):**
   - All millisecond response latency and intonation prosodic features are formally assigned to Feature Schema v3 (`features-acoustic-v3a`), requiring standardized audio elicitation and acoustic measurement validation.

---

## 4. Candidate Research Mapping

```text
Research Architecture:
  ├── src/feature_schema.py                      --> v1: 13 non-age + age; v2 adds 8 conversational fields
  ├── src/chat_feature_extractor.py              --> extract_conversational_features_v2()
  ├── packages/features/transcript_features.py   --> canonical_features (v1), canonical_features_v2 (v2)
  ├── data/ml/canonical_features_v2.parquet      --> local export: 1,961 records, 22 numeric fields including age
  ├── data/ml/results/baseline_v1_frozen.csv      --> Frozen internal comparison reference
  ├── data/ml/results/v1_vs_v2_comparison.csv     --> 120 standardized model comparisons
  └── reports/ml/                                --> Full audit, quality, and comparison documentation suite
```
