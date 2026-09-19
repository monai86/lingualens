# LinguaLens Canonical Baseline v1 Benchmark Freeze
**Freeze Date:** 2026-08-23  
**Status:** Frozen internal reference benchmark for Feature Schema v1; not clinical validation  
**Dataset Artifact:** `data/ml/canonical_features.parquet` (1,961 rows × 28 columns)  
**Participant Registry:** `data/ml/participant_registry.csv` (1,144 unique `participant_uid`s)  
**Companion Machine-Readable Results:** `data/ml/results/baseline_v1_frozen.csv`  

---

## 1. Specification & Protocol

- **Feature Schema Version:** `features-basic-v1`
- **Core Predictor Features (13 non-demographic lexical/pragmatic features):**
  - Productivity: `total_utterances`, `total_words`
  - Complexity: `mlu`, `mluw`, `ttr`
  - ASD Markers / Speech Clarity: `unintelligible_count`, `unintelligible_ratio`, `zero_vocalization_count`, `nonverbal_vocalization_count`
  - Pragmatic: `question_ratio`, `echolalia_count`, `echolalia_ratio`, `pronoun_reversal_count`
- **Confounder Negative Controls (Non-predictive):** `age_months`
- **Models & Configurations:**
  - `Elastic-Net`: `LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, C=1.0, max_iter=2000, random_state=42, class_weight='balanced')`
  - `Random Forest`: `RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42, class_weight='balanced')`
  - `HistGradientBoosting`: `HistGradientBoostingClassifier(max_iter=100, max_depth=4, min_samples_leaf=2, random_state=42, class_weight='balanced')`
  - `Dummy Baseline`: `DummyClassifier(strategy='stratified', random_state=42)`
- **Evaluation Protocols:**
  - Within-Corpus: Repeated Stratified 4-Fold CV (5 repeats = 20 folds, `random_state=42`)
  - Cross-Corpus: Train on 100% source corpus, evaluate on 100% untouched held-out target corpus
  - Confidence Intervals: 1,000 participant-level cluster bootstrap iterations (95% CI)

---

## 2. Frozen Benchmark Results Matrix

| Experiment | Comparison | Model | AUROC (95% CI) | Balanced Acc (95% CI) | Sensitivity | Specificity | F1 | Brier Score |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Eigsti Within** | ASD (16) vs TD (16) | Elastic-Net | **0.6234** (0.535, 0.712) | **0.5688** (0.497, 0.648) | 0.5875 | 0.5500 | 0.5767 | 0.2581 |
| **Eigsti Within** | ASD (16) vs TD (16) | Random Forest | **0.5406** (0.455, 0.630) | **0.5625** (0.491, 0.640) | 0.5625 | 0.5625 | 0.5625 | 0.2649 |
| **Eigsti Within** | ASD (16) vs TD (16) | HistGradientBoosting | **0.5454** (0.457, 0.636) | **0.5625** (0.494, 0.637) | 0.6250 | 0.5000 | 0.5882 | 0.3987 |
| **Eigsti Within** | ASD (16) vs TD (16) | Dummy | **0.3750** (0.308, 0.456) | **0.3750** (0.308, 0.456) | 0.3750 | 0.3750 | 0.3750 | 0.6250 |
| **Nadig Within** | ASD (9) vs TD (23) | Elastic-Net | **0.3946** (0.292, 0.505) | **0.4517** (0.368, 0.535) | 0.3556 | 0.5478 | 0.2832 | 0.3168 |
| **Nadig Within** | ASD (9) vs TD (23) | Random Forest | **0.3241** (0.223, 0.429) | **0.4729** (0.422, 0.529) | 0.1111 | 0.8348 | 0.1449 | 0.2623 |
| **Nadig Within** | ASD (9) vs TD (23) | HistGradientBoosting | **0.3306** (0.227, 0.455) | **0.4372** (0.367, 0.511) | 0.2222 | 0.6522 | 0.2105 | 0.4475 |
| **Eigsti ASD vs DD** | ASD (16) vs DD (16) | Elastic-Net | **0.7730** (0.696, 0.842) | **0.6812** (0.606, 0.750) | 0.7000 | 0.6625 | 0.6871 | 0.2006 |
| **Eigsti ASD vs DD** | ASD (16) vs DD (16) | Random Forest | **0.7141** (0.635, 0.794) | **0.6438** (0.568, 0.716) | 0.6375 | 0.6500 | 0.6415 | 0.2168 |
| **Eigsti ASD vs DD** | ASD (16) vs DD (16) | HistGradientBoosting | **0.7197** (0.649, 0.792) | **0.6250** (0.544, 0.696) | 0.5750 | 0.6750 | 0.6053 | 0.3440 |
| **Eigsti TD vs DD** | TD (16) vs DD (16) | Elastic-Net | **0.8266** (0.757, 0.885) | **0.7563** (0.692, 0.822) | 0.7125 | 0.8000 | 0.7451 | 0.1659 |
| **Eigsti TD vs DD** | TD (16) vs DD (16) | Random Forest | **0.7659** (0.693, 0.834) | **0.6937** (0.625, 0.761) | 0.7250 | 0.6625 | 0.7030 | 0.2017 |
| **Eigsti TD vs DD** | TD (16) vs DD (16) | HistGradientBoosting | **0.7147** (0.628, 0.791) | **0.6500** (0.574, 0.714) | 0.6500 | 0.6500 | 0.6500 | 0.3457 |
| **Cross Eigsti→Nadig** | ASD (9) vs TD (23) | Elastic-Net | **0.4879** (0.234, 0.782) | **0.5097** (0.373, 0.627) | 0.8889 | 0.1304 | 0.4324 | 0.4416 |
| **Cross Eigsti→Nadig** | ASD (9) vs TD (23) | Random Forest | **0.3478** (0.129, 0.539) | **0.4106** (0.245, 0.542) | 0.7778 | 0.0435 | 0.3684 | 0.3435 |
| **Cross Eigsti→Nadig** | ASD (9) vs TD (23) | HistGradientBoosting | **0.5072** (0.250, 0.758) | **0.5072** (0.314, 0.699) | 0.6667 | 0.3478 | 0.4000 | 0.4840 |
| **Cross Nadig→Eigsti** | ASD (16) vs TD (16) | Elastic-Net | **0.5586** (0.333, 0.776) | **0.5000** (0.417, 0.581) | 0.0625 | 0.9375 | 0.1111 | 0.3920 |
| **Cross Nadig→Eigsti** | ASD (16) vs TD (16) | Random Forest | **0.3398** (0.154, 0.530) | **0.5625** (0.500, 0.655) | 0.1250 | 1.0000 | 0.2222 | 0.3042 |
| **Cross Nadig→Eigsti** | ASD (16) vs TD (16) | HistGradientBoosting | **0.4023** (0.223, 0.607) | **0.5312** (0.438, 0.636) | 0.1250 | 0.9375 | 0.2105 | 0.4338 |

---

## 3. Preservation Notice

These experimental results are an immutable internal comparison reference. They do not establish external generalization, clinical efficacy, automated diagnosis, or Thai clinical validity. Future schema evaluations must compare against the unchanged artifacts below and report any protocol differences explicitly.

## 4. Frozen Artifact Manifest (SHA-256)

| Artifact | SHA-256 |
| :--- | :--- |
| `data/ml/canonical_features.parquet` | `527dbf64a180d43fe14b18192b19eefdb18a55cc1e1df55f62a1afeb7fe3a952` |
| `data/ml/canonical_features.csv` | `8ba2cc95408a908cdb1ab00f66d22793ab4c63bd6743db86c641f7000f9fb5d2` |
| `data/ml/canonical_features.xlsx` | `e8167d34006e088bf551c8aef6abfa83d418dc9d9117860fbc15d700f1290641` |
| `data/ml/participant_registry.csv` | `d93eaa798c90d5f88571e30e014b45a97dface7347283e6bfe294c02e7aed09a` |
| `data/ml/results/baseline_v1_frozen.csv` | `8c2df6763f35e7f904ffc7193abe7879cd96cba444cda0c6e3d6ea6b2cd4178b` |
