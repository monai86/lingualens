# LinguaLens: Data Inventory, Feature Extraction, and ML Training Strategy
**Document Version:** 1.0
**Generated Date:** 2026-08-23
**Target Audience:** Machine Learning Engineers, Clinical NLP Researchers, Product Planners
**Purpose:** Research data inventory and evidence-constrained roadmap. This document does not describe an active product ML deployment path.

---

## 1. Executive Summary & Project Context

**LinguaLens** is a research and education prototype for therapist review of conversational and narrative child-language samples. The retrospective corpus labels below support methodology research; they do not establish a diagnostic model or a clinically validated reference population.

### System Components:
- **Web Application:** Next.js + React + TypeScript ([`apps/lingualens-app/`](../apps/lingualens-app))
- **Canonical Therapist Product:** Next.js frontend ([`apps/lingualens-app/`](../apps/lingualens-app)) and FastAPI backend ([`apps/api/`](../apps/api))
- **Legacy Research Clients:** Tkinter and terminal utilities under [`scripts/`](../scripts); these are compatibility surfaces, not canonical product clients
- **Research & ML Pipelines:** Python modules ([`src/`](../src), [`packages/`](../packages), [`scripts/`](../scripts))

---

## 2. Complete Data Inventory (`data/`)

The repository aggregates and curates transcripts from international standard **TalkBank / CHILDES** corpora stored in CHAT (`.cha`) format.

```text
data/
├── Eigsti/                       # 3 Subgroups: ASD, DD, TD
├── Nadig/                        # Semi-naturalistic conversation: ASD & Typical
├── Rollins/                      # Longitudinal ASD development (one folder per child)
├── NYU-Emerson/                  # ASD cohort (30 children)
├── QuigleyMcNally/               # Longitudinal & risk-based: HR (ASD) vs LR (TD)
├── Flusberg/                     # Longitudinal ASD (6 children across multiple sessions)
│
├── combined_features.csv         # Aggregated 15-feature table for ML classification (122 rows)
├── longitudinal_features.csv     # Multi-session feature table for progress tracking (87 rows)
├── curated_group_features.csv    # Large-scale multi-class curated features (2,301 rows, 44 cols)
├── rollins_features.csv          # Rollins-specific feature extraction
├── metadata.example.csv          # Standard metadata template
│
├── curated/                      # 14 standardized English CHAT transcript corpora
├── raw/                          # Raw TalkBank/CHILDES archive downloads
├── manifests/                    # Quality Control (QC), download, and pipeline run manifests
├── reference/                    # Reference cohorts, readiness indices, and normative data
├── evaluation/                   # ASR (Whisper) evaluation scaffold (audio, gold, hypothesis)
├── demo/                         # Demo session .cha files and reports
└── uploads/                      # Transient user-uploaded audio and transcript storage
```

---

## 3. Clinical Diagnostic Groups & Sample Sizes

The dataset encompasses **7 distinct clinical and developmental profiles**:

| Diagnostic Group | Clinical Description | Current Ready Samples (Reference) | Primary Source Corpora |
| :--- | :--- | :---: | :--- |
| **`TD`** | Typically Developing (เด็กพัฒนาการตามวัย) | **980** (or 1,376 curated) | EllisWeismer, ENNI, Gillam, Rescorla, NewEngland, Eigsti, Nadig |
| **`LT`** | Late Talkers (เด็กเริ่มพูดช้าโดยไม่มีภาวะออทิซึม) | **408** (or 423 curated) | EllisWeismer, Rescorla |
| **`NH`** | Normal Hearing Controls (กลุ่มควบคุมการได้ยินปกติ) | **170** | Ambrose, Nicholas |
| **`HL`** | Hearing Impairment / Hard of Hearing (กลุ่มบกพร่องทางการได้ยิน) | **138** (or 206 curated) | Ambrose, Nicholas |
| **`ASD`** | Autism Spectrum Disorder (กลุ่มออทิซึมสเปกตรัม) | **136** | NYU-Emerson, Eigsti, Flusberg, Nadig, Rollins, QuigleyMcNally |
| **`SLI` / `STI`** | Specific / Speech-Language Impairment (บกพร่องทางภาษาเฉพาะด้าน) | **113** (or 263 curated) | ENNI, Gillam, EisenbergGuo |
| **`DD`** | Developmental Delay (พัฒนาการล่าช้าทั่วไป ไม่ใช่ออทิซึม) | **16** | Eigsti |
| **TOTAL** | **All Analysis-Ready Transcripts** | **1,961** (2,301 features) | **13–14 Corpora** |

---

## 4. Ready-to-Train Datasets Available Right Now

### Tier A: Immediate ML Classification Baseline (`data/combined_features.csv`)
* **Total Rows:** **122 samples** (100% English, fully labeled, zero missing values)
* **Classes:** `ASD`: 65, `TD`: 41, `DD`: 16
* **Extracted Features (15 columns):**
  1. `age_months`: Age in months
  2. `total_utterances`: Total child utterances
  3. `mlu`: Mean Length of Utterance (morphemes)
  4. `mluw`: Mean Length of Utterance (words)
  5. `ttr`: Type-Token Ratio (lexical diversity)
  6. `total_words`: Total tokens spoken by child
  7. `unintelligible_count`: Count of unintelligible utterances (`xxx`)
  8. `unintelligible_ratio`: Ratio of unintelligible utterances
  9. `zero_vocalization_count`: Instances of zero vocalization
  10. `nonverbal_vocalization_count`: Crying, laughing, nonverbal sounds
  11. `question_ratio`: Proportion of questions asked by child
  12. `echolalia_count`: Immediate / delayed repetition of conversational partner
  13. `echolalia_ratio`: Ratio of echolalic utterances
  14. `pronoun_reversal_count`: Confusion of personal pronouns (e.g., "you" for "I")
  15. `pronoun_reversal_ratio`: Ratio of pronoun reversal occurrences

### Tier B: Large-Scale Multi-Class & Reference Dataset (`data/curated_group_features.csv`)
* **Total Rows:** **2,301 samples**
* **Columns:** **44 linguistic metrics** (including CLAN, KIDEVAL, POS tags, syntactic complexity)
* **Class Distribution:** `TD`: 1,376 | `LT`: 423 | `STI`/`SLI`: 263 | `HL`: 206 | `ASD`: 17 | `DD`: 16

### Tier C: Full Quality-Controlled CHAT Transcripts (`data/curated/english_child_transcripts/`)
* **Total Transcripts:** **1,961 `.cha` files** (all passed strict automated QC)
* **Eligible for:** Batch custom feature extraction, LLM fine-tuning, sequence modeling (LSTM/Transformer), or AST/audio-text alignment.

### Tier D: Longitudinal Growth Dataset (`data/longitudinal_features.csv`)
* **Total Rows:** **87 multi-session records** with chronological `session_order` (1, 2, 3...)
* **Eligible for:** Retrospective aggregate measurement-stability research only; not treatment-response forecasting, therapy-progress scoring, or prognosis.

---

## 5. Feature Parity & System Architecture

### Is the research feature extraction deployed across every product surface?
**No.** The repository now has a deterministic research seam, but it is not an active therapist-product ML integration:

1. **Canonical research interface:** [`packages/features/transcript_features.py`](../packages/features/transcript_features.py) exposes v1 and v2 extraction for CHAT paths, parsed CHAT objects, and normalized transcript lines.
2. **Deterministic v2 parity:** [`tests/ml/test_features_v2.py`](../tests/ml/test_features_v2.py) verifies the research export across those supported inputs and checks semantic parity across local CSV, Parquet, and XLSX artifacts. The export contains 13 non-age v1 fields, `age_months`, and 8 conversational fields; experiments use 21 non-age inputs when v1 and v2 are combined.
3. **Product boundary:** `apps/api/` and `apps/lingualens-app/` do not currently expose or consume the v2 research vector. The Tkinter/TUI utilities are not evidence of product parity.

**Implication for deployment:** No trained model is approved for direct backend deployment. Any future product integration requires a versioned API contract, independent measurement validation, privacy review, drift checks, and therapist-facing safety acceptance.

---

## 6. Brainstorming: Machine Learning Training Strategies

### Strategy 1: Hierarchical Classifier (Research hypothesis only)
* **Stage 1 (Triage Gate):** Binary classification of **Typical Development (`TD` ~980)** vs. **Atypical Development (Atypical Pool ~981)**.
  - *Advantage:* Perfectly balanced (50:50), high statistical power.
* **Stage 2 (Retrospective group comparison):** A multi-class experiment on historical corpus labels. It must not be described or surfaced as differential diagnosis.
  - *Models:* LightGBM / XGBoost / CatBoost with cost-sensitive weighting (`scale_pos_weight`) or Focal Loss.
  - *Boundary:* This is an experimental design candidate, not evidence of clinical workflow alignment or reduced false positives.

### Strategy 2: Multi-Class Corpus-Label Audit + Explainability
* **Objective:** Audit whether experimental models learn corpus labels and collection shortcuts; do not expose participant-level probabilities.
* **Models:** Random Forest, Extra Trees, or TabNet (for tabular feature interactions).
* **Outputs:** Aggregate research diagnostics and feature-attribution stability checks, with participant-level scores withheld from product surfaces.

### Strategy 3: Normative-Method Feasibility Research
* **Objective:** Test statistical methods on aggregate retrospective cohorts without producing individual reference scores.
* **Method:** Fit parametric / non-parametric percentile curves (e.g., Generalized Additive Models for Location, Scale and Shape - GAMLSS, or Quantile Regression) solely on the **980 Typical Children (`TD`)** across 12-month age bands.
* **Application boundary:** Do not map a new patient transcript to percentiles or concern flags. The English retrospective cohorts are not normative data; prospective Thai calibration and clinical governance are prerequisites for any descriptive reference display.

### Strategy 4: Longitudinal Measurement-Stability Research
* **Objective:** Characterize aggregate within-participant measurement stability; do not predict treatment response, recovery, or prognosis.
* **Data:** `longitudinal_features.csv` (87 multi-session records from Rollins, Flusberg, QuigleyMcNally).
* **Models:** Mixed-Effects Linear Regression, Recurrent Neural Networks (LSTM/GRU), or Hidden Markov Models (HMM) tracking rate of MLU increase and echolalia decay over time.

---

## 7. Critical Technical & Clinical Boundaries

1. **Clinical Safety & Non-Diagnostic Stance:** LinguaLens is an educational and research prototype. Current research ML outputs must not be shown as participant-level scores, cues, risk indicators, percentiles, concern flags, prognosis, or diagnosis.
2. **Cross-Corpus Data Leakage Prevention:** Different corpora vary by task type (e.g., `narrative` story retelling vs. `toyplay` free play) and acoustic environment. Cross-validation MUST use **Stratified GroupKFold** (grouped by child ID and corpus) or **Leave-One-Corpus-Out (LOCO)** validation.
3. **Class Imbalance Management:** ASD represents ~7% (136 / 1,961) of the total cohort. Use SMOTE / ADASYN, class weighting, or balanced bagging.
4. **Data Privacy (No PHI/PII):** Transcripts must remain de-identified. No personal identifiable information (names, real dates, audio recordings with biometric identifiers) may be committed to version control.

---

## 8. Suggested Next Steps for Planning

1. **Measurement validation:** Complete independent human/reference validation for v2 and audio-timing candidates before interpreting them as constructs.
2. **Confounding audit:** Continue grouped and leave-one-corpus-out experiments with explicit age, site, task, and examiner controls.
3. **Privacy-preserving artifacts:** Keep row-level, source-linked datasets local; publish only aggregates, checksum manifests, and clearly synthetic fixtures.
4. **Product gate:** Treat any API or therapist-UI integration as a separate future change requiring a versioned contract and clinical-safety review.
