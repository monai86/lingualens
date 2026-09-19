# LinguaLens Leakage & Confounding Audit
**Generated Date:** 2026-08-23  
**Evaluated Cohort:** 1,961 Transcripts (740 Unique Participants in ASD/TD Binary Subset)  
**Status:** Historical exploratory audit; not clinical validation  

---

## 1. Participant-Level Leakage Risk & Splitting Protocol

| Validation Strategy | Grouping Parameter | AUROC | Delta AUROC (Naive - Group) | 95% Bootstrap CI |
| :--- | :--- | :---: | :---: | :---: |
| **Naive K-Fold** | Row-level random shuffle | **0.9699** | — | — |
| **GroupKFold** | Grouped by `participant_uid` | **0.9674** | **+0.0024** | [-0.0024, +0.0070] |

### Methodological Interpretation:
- **Structural Integrity:** Because multi-session children exist in longitudinal research collections (e.g. `Flusberg` with up to 13 sessions per child, `Rollins` with up to 5 sessions per child), row-level random train/test splitting structurally violates subject independence.
- **Protocol Mandate:** Although the empirical $\Delta\text{AUROC}$ on this specific pooled dataset is modest (+0.0024), **`GroupKFold(groups=participant_uid)`** remains non-negotiably mandatory to guarantee zero participant leakage between train and test folds.

---

## 2. Negative-Control Model (Demographic & Corpus Shortcut Detection)

Can a machine-learning model predict ASD vs TD using **ONLY metadata** (`age_months`, `sex`, `corpus`, `task_type`), without access to any linguistic features?

| Model Inputs | Validation Scheme | AUROC | Balanced Accuracy | Finding |
| :--- | :--- | :---: | :---: | :--- |
| **Metadata Only (`age`, `sex`, `corpus`, `task`)** | 5-Fold GroupKFold | **0.9990** | **0.9639** | **Severe Confounding Detected** |

### Confounding Mechanisms Identified:
1. **Corpus Identity Shortcut:** Because several research collections (`NYU-Emerson`, `Flusberg`, `Rollins`) contribute exclusively ASD samples, any pooled model can achieve near-perfect discrimination by memorizing recording site artifacts rather than clinical speech features.
2. **Age Skew Confounding:** In naturalistic CHILDES corpora, TD reference cohorts skew significantly younger than ASD recruitment cohorts.
3. **Primary ML Directive:** Pooled multi-corpus GroupKFold results must be recognized strictly as an **internal pooled-corpus benchmark under substantial corpus/task confounding**. They must NOT be claimed as generalizable clinical accuracy or diagnostic efficacy.

---

## 3. Linguistic Features to Corpus Classifier (Site Specificity Audit)

Can canonical linguistic features predict which research site recorded the session?

| Model Target | Features Used | Overall Accuracy | Balanced Accuracy | Chance Level (1/13) |
| :--- | :--- | :---: | :---: | :---: |
| **Predict Research Corpus** | 13 Canonical Linguistic Features | **70.42%** | **58.27%** | ~7.7% |

### Findings & Domain Control Mandate:
- Speech features strongly correlate with corpus identity primarily because elicitation protocols differ dramatically across studies (e.g. structured narrative retellings in `ENNI`/`Gillam` vs semi-structured toy play in `Eigsti`/`Nadig`).
- **Research Mandate:** Subsequent ML validation must focus on **domain-controlled cohorts** (`Eigsti` and `Nadig`) collected under compatible interactive play protocols and validate via **bidirectional cross-corpus testing** (`Eigsti` ↔ `Nadig`).
