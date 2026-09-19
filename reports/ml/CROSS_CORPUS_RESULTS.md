# LinguaLens Cross-Corpus Generalization Report
**Generated Date:** 2026-08-23  
**Status:** Historical exploratory benchmark; not clinical validation  

---

## 1. Bidirectional Cross-Corpus Evaluation Table

| Direction | Model | AUROC (95% CI) | Balanced Acc | Sensitivity | Specificity | F1 | Brier Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cross-Corpus Eigsti->Nadig** | Dummy | **0.4952** (0.283, 0.677) | 0.4952 | 0.5556 | 0.4348 | 0.3704 | 0.5312 |
| **Cross-Corpus Eigsti->Nadig** | Elastic-Net | **0.4879** (0.234, 0.782) | 0.5097 | 0.8889 | 0.1304 | 0.4324 | 0.4416 |
| **Cross-Corpus Eigsti->Nadig** | Random Forest | **0.3478** (0.129, 0.539) | 0.4106 | 0.7778 | 0.0435 | 0.3684 | 0.3435 |
| **Cross-Corpus Eigsti->Nadig** | HistGradientBoosting | **0.5072** (0.250, 0.758) | 0.5072 | 0.6667 | 0.3478 | 0.4000 | 0.4840 |
| **Cross-Corpus Nadig->Eigsti** | Dummy | **0.5000** (0.375, 0.631) | 0.5000 | 0.1875 | 0.8125 | 0.2727 | 0.5000 |
| **Cross-Corpus Nadig->Eigsti** | Elastic-Net | **0.5586** (0.333, 0.776) | 0.5000 | 0.0625 | 0.9375 | 0.1111 | 0.3920 |
| **Cross-Corpus Nadig->Eigsti** | Random Forest | **0.3398** (0.154, 0.530) | 0.5625 | 0.1250 | 1.0000 | 0.2222 | 0.3042 |
| **Cross-Corpus Nadig->Eigsti** | HistGradientBoosting | **0.4023** (0.223, 0.607) | 0.5312 | 0.1250 | 0.9375 | 0.2105 | 0.4338 |

---

## 2. Authoritative Cross-Corpus Generalization Findings

1. **Eigsti → Nadig Generalization Failure:**
   - Models trained strictly on Eigsti ASD vs TD (N=32) fail to generalize above chance when applied to the untouched held-out Nadig cohort (N=32, 9 ASD vs 23 TD).
   - Elastic-Net achieves AUROC **0.4879** (95% CI: [0.234, 0.782]), Random Forest achieves AUROC **0.3478** (95% CI: [0.129, 0.539]), and HistGradientBoosting achieves AUROC **0.5072** (95% CI: [0.250, 0.758]).
   - Elastic-Net exhibits extreme specificity collapse (13.04%), overpredicting the positive class due to differing baseline productivity and examiner interaction styles between laboratories.
2. **Nadig → Eigsti Generalization Failure:**
   - Models trained on the smaller Nadig ASD sample (9 ASD vs 23 TD) and evaluated on Eigsti (16 ASD vs 16 TD) also perform near chance.
   - Elastic-Net achieves AUROC **0.5586** (95% CI: [0.333, 0.776]), Random Forest achieves AUROC **0.3398** (95% CI: [0.154, 0.530]), and HistGradientBoosting achieves AUROC **0.4023** (95% CI: [0.223, 0.607]).
   - Elastic-Net in this direction exhibits extreme sensitivity collapse (6.25%), classifying nearly all Eigsti participants as negative (Specificity 93.75%).
3. **Scientific Conclusion:**
   - **No generalizable speech-language ASD vs TD signal is demonstrated by `features-basic-v1` across these independent interactive speech corpora.**
   - High headline performance in naive pooled evaluations was an artifact of dataset-level confounding and age discrepancies rather than genuine cross-domain speech-language markers.
