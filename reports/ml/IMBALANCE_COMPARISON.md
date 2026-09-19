# LinguaLens Class Imbalance Strategy Benchmark
**Generated Date:** 2026-08-23  
**Status:** Historical exploratory benchmark; not clinical validation  

---

## 1. Cross-Corpus Imbalance Strategy Comparison (Random Forest)

```text
imbalance_strategy  eig_to_nad_auroc  eig_to_nad_bacc  eig_to_nad_sens  eig_to_nad_spec  eig_to_nad_brier  nad_to_eig_auroc  nad_to_eig_bacc  nad_to_eig_sens  nad_to_eig_spec  nad_to_eig_brier
              none            0.3478           0.4106           0.7778           0.0435            0.3435            0.3281           0.5312           0.0625           1.0000            0.3257
      class_weight            0.3478           0.4106           0.7778           0.0435            0.3435            0.3398           0.5625           0.1250           1.0000            0.3042
 random_oversample            0.3478           0.4106           0.7778           0.0435            0.3435            0.3672           0.5312           0.1250           0.9375            0.3152
             smote            0.3478           0.4106           0.7778           0.0435            0.3435            0.3438           0.5000           0.0625           0.9375            0.3103
```

---

## 2. Retrospective methodological observation

1. **Class Weighting (`class_weight='balanced'`)** was the least invasive strategy in this historical experiment:
   - Avoids generating synthetic clinical feature samples (unlike SMOTE).
   - Its relative Brier scores do not establish probability calibration or cross-corpus stability.
2. **SMOTE** provides slight marginal sensitivity increases in some within-corpus splits but increases probability calibration error (higher Brier score) and offers no consistent advantage under strict cross-corpus evaluation.
