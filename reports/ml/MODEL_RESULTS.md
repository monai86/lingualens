# LinguaLens ML Model Results & Evaluation Report
**Generated Date:** 2026-08-23  
**Status:** Historical exploratory benchmark; not clinical validation  

---

## 1. Domain-Controlled Primary Benchmark (Eigsti ASD 16 vs TD 16, N=32)

Evaluated via Repeated Stratified 4-Fold Cross-Validation (5 repeats, 20 folds total on 32 unique independent participants):

| Model | AUROC (95% CI) | Balanced Acc (95% CI) | Sensitivity (95% CI) | Specificity (95% CI) | F1 | Brier Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Elastic-Net** | **0.6234** (0.535, 0.712) | **0.5688** (0.497, 0.648) | **0.5875** (0.493, 0.695) | **0.5500** (0.440, 0.654) | 0.5767 | 0.2581 |
| **Random Forest** | **0.5406** (0.455, 0.630) | **0.5625** (0.491, 0.640) | **0.5625** (0.456, 0.673) | **0.5625** (0.439, 0.674) | 0.5625 | 0.2649 |
| **HistGradientBoosting** | **0.5454** (0.457, 0.636) | **0.5625** (0.494, 0.637) | **0.6250** (0.527, 0.731) | **0.5000** (0.388, 0.609) | 0.5882 | 0.3987 |
| **Dummy (Baseline)** | **0.3750** (0.308, 0.456) | **0.3750** (0.308, 0.456) | **0.3750** (0.273, 0.494) | **0.3750** (0.274, 0.483) | 0.3750 | 0.6250 |

---

## 2. Exploratory Threshold Sensitivity Analysis

> [!NOTE]
> The tables below represent **160 out-of-fold prediction instances** generated across 5 repeats of 4-fold cross-validation on **32 unique independent children** (16 ASD, 16 TD). 
> They do not represent 160 independent participants. These values are exploratory sensitivity analyses on development data; **no production or clinical threshold is selected or recommended during this research phase.**

### Elastic-Net Sensitivity Table:
```text
 threshold  sensitivity  specificity  precision     f1  balanced_accuracy  true_positives  false_positives  true_negatives  false_negatives
       0.2       0.8875       0.1750     0.5182 0.6544             0.5312              71               66              14                9
       0.3       0.8250       0.3625     0.5641 0.6701             0.5938              66               51              29               14
       0.4       0.7250       0.4875     0.5859 0.6480             0.6062              58               41              39               22
       0.5       0.5875       0.5500     0.5663 0.5767             0.5688              47               36              44               33
       0.6       0.4750       0.7000     0.6129 0.5352             0.5875              38               24              56               42
       0.7       0.3625       0.7875     0.6304 0.4603             0.5750              29               17              63               51
       0.8       0.2000       0.9125     0.6957 0.3107             0.5563              16                7              73               64
```

### Random Forest Sensitivity Table:
```text
 threshold  sensitivity  specificity  precision     f1  balanced_accuracy  true_positives  false_positives  true_negatives  false_negatives
       0.2       0.9625       0.0500     0.5033 0.6609             0.5062              77               76               4                3
       0.3       0.9250       0.1250     0.5139 0.6607             0.5250              74               70              10                6
       0.4       0.7750       0.3250     0.5345 0.6327             0.5500              62               54              26               18
       0.5       0.5625       0.5625     0.5625 0.5625             0.5625              45               35              45               35
       0.6       0.3000       0.6750     0.4800 0.3692             0.4875              24               26              54               56
       0.7       0.1375       0.8625     0.5000 0.2157             0.5000              11               11              69               69
       0.8       0.0250       0.9875     0.6667 0.0482             0.5062               2                1              79               78
```

---

## 3. Exploratory Feature Attribution & Permutation Importance

Standardized model contributions and permutation importance on the domain-controlled interactive speech cohort:

```text
                     feature  elastic_net_coef  elastic_net_odds_ratio  rf_gini_importance  rf_permutation_importance_mean
              question_ratio         -0.621908                0.536919            0.133710                        0.004375
                        mluw          0.000000                1.000000            0.118825                        0.013125
                         mlu         -0.073571                0.929070            0.116433                        0.005625
                         ttr          0.278709                1.321422            0.103148                        0.015000
        unintelligible_ratio          0.214046                1.238680            0.088849                       -0.003750
                 total_words         -0.120336                0.886622            0.080979                       -0.013125
             echolalia_count          0.605398                1.831981            0.079908                       -0.010000
             echolalia_ratio          0.000000                1.000000            0.077462                       -0.001250
        unintelligible_count          0.555609                1.743002            0.066822                       -0.002500
            total_utterances          0.000000                1.000000            0.065990                       -0.015000
nonverbal_vocalization_count         -0.184083                0.831867            0.056043                        0.003750
      pronoun_reversal_count         -0.002995                0.997010            0.011831                        0.000000
     zero_vocalization_count          0.000000                1.000000            0.000000                        0.000000
```

### Evidence-constrained observations:
1. Coefficients and importances are unstable exploratory associations in one small retrospective corpus comparison; they are not participant-level markers or explanations.
2. Session length and elicitation protocol affect raw counts and ratios, so neither family is assumed transportable without independent validation.

---

## 4. Research-use prohibition

No threshold, abstention rule, probability, predicted class, ranking, or feature attribution from this historical benchmark is approved for participant-level use, therapist-product display, API output, clinical interpretation, or Thai deployment.
