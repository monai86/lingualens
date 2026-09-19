# LinguaLens Feature Schema v1 vs v2 Experimental Comparison
**Generated Date:** 2026-08-26  
**Status:** Exploratory retrospective benchmark; not clinical validation  
**Comparison Source:** `data/ml/results/v1_vs_v2_comparison.csv`  
**Boundary:** Corpus- and protocol-specific results; no automated-diagnosis or Thai clinical claim  
**Execution note:** scikit-learn reported `max_iter=2000` convergence warnings for some Elastic-Net fits; treat all affected estimates as exploratory pending a preregistered convergence-sensitivity rerun.  

---

## 1. Primary Model Comparison Matrix (Elastic-Net Logistic Regression)

| Experiment | Comparison | Metric | V1 Only (13 feat) | V2 Only (8 feat) | V1 + V2 (21 feat) | Δ (V1+V2 vs V1) | Age Only (Control) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Eigsti Within-Corpus** | ASD vs TD | **AUROC** | 0.6234 | 0.4798 | 0.6080 | **-0.0154** | 0.8536 |
| | | **Bal Acc** | 0.5688 | 0.4750 | 0.5875 | +0.0187 | 0.7625 |
| **Nadig Within-Corpus** | ASD vs TD | **AUROC** | 0.3946 | 0.6158 | 0.4810 | **+0.0864** | 0.9782 |
| | | **Bal Acc** | 0.4517 | 0.7087 | 0.5362 | +0.0845 | 0.9227 |
| **Eigsti ASD vs DD** | ASD vs DD | **AUROC** | 0.7730 | 0.4749 | 0.6687 | **-0.1043** | 0.4164 |
| | | **Bal Acc** | 0.6812 | 0.5125 | 0.6125 | -0.0687 | 0.4625 |
| **Eigsti TD vs DD** | TD vs DD | **AUROC** | 0.8266 | 0.4754 | 0.7928 | **-0.0338** | 0.8995 |
| | | **Bal Acc** | 0.7563 | 0.5062 | 0.7125 | -0.0438 | 0.8500 |
| **Cross-Corpus Eigsti->Nadig** | ASD vs TD | **AUROC** | 0.4879 | 0.6715 | 0.5556 | **+0.0677** | 0.9855 |
| | | **Bal Acc** | 0.5097 | 0.5918 | 0.5097 | +0.0000 | 0.9227 |
| **Cross-Corpus Nadig->Eigsti** | ASD vs TD | **AUROC** | 0.5586 | 0.5547 | 0.6016 | **+0.0430** | 0.8828 |
| | | **Bal Acc** | 0.5000 | 0.5938 | 0.5625 | +0.0625 | 0.8125 |

---

## 2. Corpus Identity Prediction Audit

Tests whether feature sets unintentionally encode research site / laboratory protocol (Eigsti vs Nadig classifier AUROC):

| Feature Set | Features | Corpus Prediction AUROC | Interpretation |
| :--- | :---: | :---: | :--- |
| **V1 Only** | 13 | **0.9936** | Encodes session duration differences |
| **V2 Only** | 8 | **0.7465** | Conversational dynamics show protocol differences |
| **V1 + V2** | 21 | **0.9819** | Combined feature set distinguishes lab protocol |

---

## 3. Evidence-Constrained Conclusions

1. **Mixed benchmark impact:**
   - V1+V2 changes performance unevenly across comparisons. Positive and negative deltas must be reported individually; these results do not support a uniform improvement or a "without degradation" claim.
2. **Protocol and confounding sensitivity:**
   - Corpus-prediction AUROC shows that both feature families encode collection-site or interaction-protocol differences. Age-only controls can also expose major cohort imbalance.
3. **No generalization or clinical claim:**
   - Bidirectional cross-corpus results do not establish transportability. Prospective, participant-safe, protocol-standardized evaluation and independent measurement validation are required before clinical interpretation, including any Thai deployment.
