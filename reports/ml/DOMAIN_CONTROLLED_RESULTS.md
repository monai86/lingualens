# LinguaLens Domain-Controlled Classification Results
**Generated Date:** 2026-08-23  
**Status:** Historical exploratory benchmark; not clinical validation  

---

## 1. Primary Benchmark: Eigsti Within-Corpus (ASD 16 vs TD 16)

Evaluated via Repeated Stratified 4-Fold Cross-Validation (5 repeats, 20 folds total) on 32 unique children under identical toyplay collection protocol:

```text
               model  AUROC     AUROC_95CI  balanced_accuracy      bacc_95CI  sensitivity  specificity     F1  Brier
               Dummy 0.3750 (0.308, 0.456)             0.3750 (0.308, 0.456)       0.3750       0.3750 0.3750 0.6250
         Elastic-Net 0.6234 (0.535, 0.712)             0.5688 (0.497, 0.648)       0.5875       0.5500 0.5767 0.2581
       Random Forest 0.5406  (0.455, 0.63)             0.5625  (0.491, 0.64)       0.5625       0.5625 0.5625 0.2649
HistGradientBoosting 0.5454 (0.457, 0.636)             0.5625 (0.494, 0.637)       0.6250       0.5000 0.5882 0.3987
```

---

## 2. Replication Benchmark: Nadig Within-Corpus (ASD 9 vs TD 23)

Evaluated via Repeated Stratified 4-Fold Cross-Validation on 32 unique children:

```text
               model  AUROC     AUROC_95CI  balanced_accuracy      bacc_95CI  sensitivity  specificity     F1  Brier
               Dummy 0.4773 (0.396, 0.567)             0.4773 (0.396, 0.567)       0.3111       0.6435 0.2800 0.4500
         Elastic-Net 0.3946 (0.292, 0.505)             0.4517 (0.368, 0.535)       0.3556       0.5478 0.2832 0.3168
       Random Forest 0.3241 (0.223, 0.429)             0.4729 (0.422, 0.529)       0.1111       0.8348 0.1449 0.2623
HistGradientBoosting 0.3306 (0.227, 0.455)             0.4372 (0.367, 0.511)       0.2222       0.6522 0.2105 0.4475
```

---

## 3. Retrospective Group Comparison: Eigsti ASD (16) vs DD (16)

Tests whether canonical speech-language features distinguish Autism Spectrum Disorder from general developmental delay / Down syndrome:

```text
               model  AUROC     AUROC_95CI  balanced_accuracy      bacc_95CI  sensitivity  specificity     F1  Brier
               Dummy 0.4375 (0.358, 0.519)             0.4375 (0.358, 0.519)       0.4375       0.4375 0.4375 0.5625
         Elastic-Net 0.7730 (0.696, 0.842)             0.6812  (0.606, 0.75)       0.7000       0.6625 0.6871 0.2006
       Random Forest 0.7141 (0.635, 0.794)             0.6438 (0.568, 0.716)       0.6375       0.6500 0.6415 0.2168
HistGradientBoosting 0.7197 (0.649, 0.792)             0.6250 (0.544, 0.696)       0.5750       0.6750 0.6053 0.3440
```

### Research interpretation:
- This small, corpus-specific comparison does not establish clinical specificity or participant-level markers.
- Apparent feature contributions may reflect corpus composition, elicitation, age, or annotation artifacts and require independent validation.

---

## 4. Benchmark: Eigsti TD (16) vs DD (16)

```text
               model  AUROC     AUROC_95CI  balanced_accuracy      bacc_95CI  sensitivity  specificity     F1  Brier
               Dummy 0.3875 (0.317, 0.471)             0.3875 (0.317, 0.471)       0.3875       0.3875 0.3875 0.6125
         Elastic-Net 0.8266 (0.757, 0.885)             0.7563 (0.692, 0.822)       0.7125       0.8000 0.7451 0.1659
       Random Forest 0.7659 (0.693, 0.834)             0.6937 (0.625, 0.761)       0.7250       0.6625 0.7030 0.2017
HistGradientBoosting 0.7147 (0.628, 0.791)             0.6500 (0.574, 0.714)       0.6500       0.6500 0.6500 0.3457
```
