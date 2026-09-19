# Clinician Balancing & Confounder Prevention Plan
**Document Identifier:** `LL-PLAN-CLINICIAN-BALANCE-v1`  
**Document Date:** 2026-08-24  
**Target:** Prospective Multicenter Clinical Data Collection  

---

## 1. The Clinician Shortcut Vulnerability

Retrospective dataset audits revealed that when clinical tasks or participant cohorts are confounded with individual examiners, machine learning models learn to classify the examiner's questioning tempo and vocal pitch rather than the child's communication disorder.

```text
CONFOUNDED CLINICAL DESIGN (Vulnerable to Shortcuts):
Clinician 1 (High questioning tempo) ──────► 90% ASD Children
Clinician 2 (Low questioning tempo)  ──────► 90% TD Children
[Result: ML model classifies Clinician 1 vs Clinician 2, NOT ASD vs TD]

BALANCED CLINICAL DESIGN (LinguaLens Standard):
Clinician 1 ──────► 33% ASD | 33% DD | 33% TD
Clinician 2 ──────► 33% ASD | 33% DD | 33% TD
Clinician 3 ──────► 33% ASD | 33% DD | 33% TD
[Result: Examiner effects are orthogonal to diagnostic phenotype]
```

---

## 2. Mandatory Balancing Requirements

1. **Minimum Clinician Count:** Every participating clinical pilot site must engage a minimum of **$N \ge 3$ independent speech-language pathologists**.
2. **Cross-Diagnostic Allocation:** Each clinician must assess an approximately equal proportion of children from each diagnostic group (ASD, DD, TD).
3. **Hardware Uniformity:** Clinicians must utilize identical standardized microphone kits to avoid clinician-device collinearity.
4. **Prospective Balance Auditing:** The project audit script (`scripts/ml/audit_thai_clinical_pilot.py`) will automatically compute a Chi-Square test of independence on `clinician_uid` $\times$ `diagnostic_group`. If $p < 0.05$ (indicating significant imbalance), a data collection pause is triggered.

---

## 3. Repeatability Subset (Test-Retest Design)

To estimate test-retest reliability and clinician style stability, a planned subset ($20\text{--}30\%$ of Pilot 1 participants, $\approx 10\text{--}12\text{ children}$) will complete a second session:
- **Condition 1 (Intra-Clinician Stability):** Same child assessed by the same clinician 7–14 days later using equivalent stimulus sets.
- **Condition 2 (Inter-Clinician Invariance):** Same child assessed by a different clinician 7–14 days later to quantify examiner-induced feature variance.
