# Prospective Thai Clinical Pilot Protocol: Feasibility & Measurement Reliability
**Protocol Identifier:** `LL-PILOT-THAI-v1`  
**Protocol Version:** 1.0.0-CLINICAL-PROSPECTIVE  
**Document Date:** 2026-08-24  
**Primary Investigators:** LinguaLens Clinical & Speech-Language Research Consortium  

---

## 1. Study Objective & Primary Research Question

### Primary Research Question:
> *"Can the LinguaLens standardized language-sampling protocol (`L-SLSP-v1`) and automated acoustic measurement pipeline collect reliable, reproducible, and clinically usable speech-language metrics within a routine Thai pediatric speech-language therapy setting?"*

### Critical Scope Boundary:
*This prospective clinical pilot is a **Measurement Reliability and Clinical Feasibility Study**. It is **NOT** a diagnostic classification trial, and AUROC is explicitly **NOT** a primary endpoint.*

---

## 2. Three-Stage Pilot Staging Roadmap

```text
┌─────────────────────────────────────────────────────────────┐
│                 PROSPECTIVE PILOT ROADMAP                   │
│                                                             │
│  [PILOT 0: WORKFLOW FEASIBILITY]                            │
│  ├── Sample: 5–10 Clinical Sessions (1-2 Clinicians)        │
│  ├── Focus: Consent flow, mic setup, data upload, latency   │
│  └── Output: Workflow time, SLP friction points             │
│                                                             │
│  [PILOT 1: MEASUREMENT RELIABILITY]                         │
│  ├── Sample: 30–50 Children across ≥3 Clinicians            │
│  ├── Focus: Feature yield, test-retest ICC, clinician effect│
│  └── Output: Variance component analysis & quality gates    │
│                                                             │
│  [PILOT 2: PREDICTIVE VALIDATION - EXPLICITLY DEFERRED]     │
│  └── Requires locked Pilot 1 reliability + independent power│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Pilot Participant Groups & Inclusion Criteria

To ensure broad clinical applicability beyond a narrow binary comparison, the pilot recruits four representative pediatric communication groups (Target Age: 24–72 months):

1. **Group A: Autism Spectrum Disorder (ASD)** — Clinician-confirmed diagnosis per DSM-5 criteria.
2. **Group B: Developmental Language Disorder / Speech Delay (DLD / DD)** — Significant language delay without primary autism diagnosis.
3. **Group C: Other Clinical Communication Differences** — E.g. fluency differences, selective mutism, or articulation challenges.
4. **Group D: Typically Developing Controls (TD)** — Age-matched reference cohort with no documented developmental concerns.

---

## 4. Primary & Secondary Study Endpoints

### Primary Feasibility & Measurement Endpoints:
1. **Protocol Completion Rate (%):** Proportion of sessions successfully completing all 3 protocol blocks (Block A, B, C).
2. **Valid Audio Capture Rate (%):** Proportion of sessions achieving `estimated_snr_db >= 15.0 dB` with zero catastrophic clipping.
3. **Feature Yield & Missingness Rate (%):** Proportion of feature schema v1, v2, and v3a metrics successfully extracted with status `VALID`.
4. **Test-Retest Repeatability ($\text{ICC}$):** Within-child repeatability across repeat sessions (subset of $N=10\text{--}15$ children).
5. **Clinician Usability & Friction:** Time required for therapist transcript review and UI adjustment (target: $< 5\text{ minutes}$ per session).

---

## 5. Standardized Clinical Equipment Setup

- **Microphone:** Calibrated dual-wireless boundary microphone system (e.g. Røde Wireless PRO) with dedicated Child (CH1) and Examiner (CH2) channels.
- **Recording App / Interface:** LinguaLens Web Recording Interface (`apps/lingualens-app/` with secure local memory buffer).
- **Audio Format:** Lossless 48 kHz / 24-bit WAV master asset.
