# LinguaLens Feature Schema v2 Research Integration Boundary
**Document Date:** 2026-08-24  
**Status:** Research-only candidate; not integrated into therapist product  
**Applies To:** `apps/api/`, `apps/lingualens-app/`, `packages/features/`, `src/`

---

## 1. Core Architectural Boundary

To uphold clinical safety and scientific integrity, LinguaLens strictly decouples:

```text
┌──────────────────────────────────────────────┐
│       RESEARCH EXTRACTION CANDIDATE          │
│  - Deterministic mathematical extraction     │
│  - Zero runtime crashes or unhandled NaNs    │
│  - Batch artifact parity and tests           │
│  - No therapist-product integration          │
└──────────────────────┬───────────────────────┘
                       │
       [STRICT ARCHITECTURAL SEPARATION]
                       │
┌──────────────────────▼───────────────────────┐
│         PREDICTIVE CLINICAL VALIDITY         │
│  - Diagnostic classification / risk scores   │
│  - Automated screening recommendations       │
│  - Clinical decision support thresholds      │
└──────────────────────────────────────────────┘
```

**Policy Statement:**  
*Feature Schema v2 (`features-conversation-v2`) is limited to offline descriptive research. It is not approved for therapist-facing UI, clinical summaries, production API responses, predictive automation, or clinical decision support.*

---

## 2. Permitted Use Cases (Offline Research Only)

The following analyses are permitted only in research notebooks, auditable batch reports, and synthetic demonstrations:

1. **Session Interaction Visualization:**
   - Visualizing the proportion of child vs adult contributions (`speaker_balance_ratio`).
   - Displaying conversational responsiveness (`child_response_rate`, `adult_response_rate`).
   - Tracking turn transitions and back-and-forth conversational rhythm (`turn_alternation_rate`).
2. **Repetition & Echolalia Descriptive Analytics:**
   - Displaying verbatim repetition rates (`partner_repetition_exact_ratio`, `self_repetition_exact_ratio`).
   - Comparing lexical token overlap metrics (`partner_repetition_overlap_mean`) with human annotation.
3. **Session Transcript Navigation:**
   - Characterizing contiguous child runs (`child_run_length_mean`) across research samples.

None of these uses authorizes display in `apps/lingualens-app/` or return from `apps/api/`.

---

## 3. Prohibited Use Cases (Predictive Clinical Overclaiming)

The following behaviors are strictly prohibited across all frontend UIs, backend API endpoints, and export reports:

1. **Automated Diagnostic Scoring:**
   - Do NOT compute, display, or infer an "ASD Probability Score", "Autism Index", or "Risk Level" based on v2 conversational features.
2. **Clinical Severity Grading:**
   - Do NOT map conversational features (e.g. `speaker_balance_ratio < 0.3`) to diagnostic severity cutoffs (e.g. "Severe Pragmatic Impairment").
3. **Automated Differential Triage:**
   - Do NOT use conversational features to automatically triage between ASD, Developmental Delay (DD), or Typical Development (TD).
4. **Normative Overclaiming:**
   - Do NOT present conversational feature values as normalized clinical percentiles without prospective, standardized normative data.

---

## 4. Future Integration Gate

Any future therapist-facing integration requires a separate behavior change, clinical-safety review, prospective evidence, versioned API contract, and explicit approval. A disclaimer alone is not sufficient authority.

> **Clinical Notice:**  
> *Conversational metrics are offline descriptive research measurements only. Construct validity and individual clinical utility are not established; do not use them for participant-level interpretation, therapy planning, product display, or automated decisions.*

---

## 5. Summary Table: Feature Boundary Status

| Feature Name | Type | Research Extraction | Production UI/API | Predictive ML Status |
| :--- | :--- | :---: | :---: | :---: |
| `speaker_balance_ratio` | Conversational Dyadic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `turn_alternation_rate` | Conversational Dyadic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `child_run_length_mean` | Conversational Child | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `child_response_rate` | Conversational Dyadic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `adult_response_rate` | Conversational Dyadic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `partner_repetition_exact_ratio` | Repetition / Pragmatic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `partner_repetition_overlap_mean` | Repetition / Pragmatic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
| `self_repetition_exact_ratio` | Repetition / Pragmatic | **CANDIDATE** | **NOT INTEGRATED** | **RESTRICTED** |
