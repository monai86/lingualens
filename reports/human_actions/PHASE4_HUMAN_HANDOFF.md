# LinguaLens Phase 4 Human Expert Handoff Package
**Document Identifier:** `LL-HANDOFF-PHASE4-v1`  
**Date:** 2026-08-24  
**Status:** Mandatory Governance Document  

---

## 1. Executive Summary: What AI / Codex Completed

Codex has completed the computational, structural, and methodological specifications required for Phase 4:

1. **Baseline Reconciliation & Freeze:** Established exact mathematical reproducibility ($\Delta = 0.0000$ AUROC) on frozen v1 benchmarks.
2. **Measurement Validation Framework:** Designed the Human Gold Timing Protocol (`reports/ml/HUMAN_GOLD_TIMING_STUDY_PROTOCOL.md`) and automated evaluation script (`scripts/ml/evaluate_alignment_gold.py`).
3. **Prospective Clinical Protocol:** Specified the 3-block standardized sampling protocol (`L-SLSP-v1`) and pilot roadmap (`reports/clinical/THAI_PROSPECTIVE_PILOT_PROTOCOL.md`).
4. **Confounder Protection:** Established the Clinician Balancing Plan (`reports/clinical/CLINICIAN_BALANCE_PLAN.md`) and automated audit engine (`scripts/ml/audit_thai_clinical_pilot.py`).
5. **Thai Tone-Aware Architecture:** Defined the 5-tone acoustic representation, speaker-centered normalization, and draft Block T stimulus structure (`reports/ml/THAI_TONE_AWARE_ACOUSTIC_SPEC.md`).
6. **Descriptive Normative Plan:** Formally prohibited transferring English acoustic cutoffs to Thai.

---

## 2. Explicit Human Role Assignments

```text
┌─────────────────────────────────────────────────────────────┐
│                 HUMAN EXPERT ROLE MAPPING                   │
│                                                             │
│  [PHONETICS & LINGUISTICS EXPERTS]                          │
│  ├── Mark manual speech onsets/offsets in Praat TextGrids   │
│  ├── Adjudicate boundary discrepancies > 100 ms             │
│  └── Validate Thai Block T word list & phonetic balance     │
│                                                             │
│  [SPEECH-LANGUAGE PATHOLOGISTS (SLPs)]                      │
│  ├── Conduct standardized sessions per L-SLSP-v1 protocol   │
│  ├── Verify developmental appropriateness of stimuli        │
│  └── Review interactive transcript outputs in UI            │
│                                                             │
│  [BIOSTATISTICIAN / STATISTICAL TEAM]                       │
│  ├── Formally power the clinical pilot sample size          │
│  └── Fit linear mixed-effects variance partitioning models  │
│                                                             │
│  [ETHICS COMMITTEE & INSTITUTIONAL AUTHORITIES]             │
│  ├── Review and approve human subjects protocol (IRB)       │
│  └── Ratify parental consent and child assent forms         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Mandatory Milestones Required BEFORE Predictive ML May Resume

Under LinguaLens scientific governance, **no machine learning classifiers or ASD risk scores may be trained** until all of the following empirical criteria are fulfilled:

- [ ] **Milestone 1 (Gold Timing Validation):** At least 20 pediatric recordings independently double-annotated by human phoneticians with inter-rater agreement established ($\text{ICC} > 0.85$) and automated boundary MAE empirically measured.
- [ ] **Milestone 2 (Clinical Protocol Feasibility):** Pilot 0 completed across $\ge 5$ clinical sessions demonstrating $< 5\text{ min}$ therapist review friction.
- [ ] **Milestone 3 (Examiner Confounder Verification):** Pilot 1 dataset verified by `scripts/ml/audit_thai_clinical_pilot.py` showing no significant clinician-caseload confounding.
- [ ] **Milestone 4 (Thai Tone Acoustic Calibration):** Human SLP/phonetics approval of Block T stimuli and validation of tone-conditioned F0 normalization on Thai pediatric samples.
