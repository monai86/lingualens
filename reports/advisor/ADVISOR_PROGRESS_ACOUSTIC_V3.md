# LinguaLens Research Progress Report: Reproducibility Reconciliation, Standardized Elicitation Protocol, and Acoustic Measurement Framework (v3a)

**Author:** LinguaLens Research Team
**Date:** 2026-08-24
**Report Type:** Academic Advisor Progress Report & Methodological Synthesis
**Project Phase:** Phase 3 — Scientific Reproducibility & Acoustic Measurement System

---

## 1. Executive Summary & Research Problem

The LinguaLens project investigates research methods for auditable speech-language measurement. It is not a diagnostic system, and the current ML and acoustic work is not integrated into the therapist product.

However, rigorous scientific auditing revealed that these initial high metrics were driven by **methodological artifacts and non-clinical confounders**:
1. **Age Imbalance:** Retrospective TalkBank cohorts contain substantial age-label imbalance, so age-only controls expose shortcut risk rather than a speech-language signal.
2. **Corpus & Site Shortcuts:** Corpora originated from different institutions with divergent recording tasks and examiner styles; site-prediction audits show substantial protocol confounding.
3. **Cross-Corpus Generalization Failure:** Bidirectional held-out-site experiments do not establish transportability.

The generated [`reports/ml/V1_VS_V2_COMPARISON.md`](../ml/V1_VS_V2_COMPARISON.md) is the authoritative source for current metrics. This advisor summary intentionally does not duplicate hard-coded values that can become stale.

---

## 2. Methodological Corrections & Benchmark Freeze

Rather than attempting to rescue headline performance through complex neural networks or synthetic oversampling, the project executed systematic scientific corrections:

```text
RIGOROUS SCIENTIFIC METHODOLOGY PIPELINE:
Initial Performance
    ↓
Confounder Discovery (Age, Site, Task shortcuts)
    ↓
Invalid Claim Rejection (reconciling narrative with held-out evidence)
    ↓
V1 Reproducibility Audit (Reconciled scaling pipelines to achieve exact 0.0000 delta)
    ↓
Authoritative Benchmark Freeze (`baseline_v1_frozen.csv`)
    ↓
Feature Schema v2 Implementation (8 deterministic conversational/repetition features)
    ↓
Prospective Acoustic Helpers v3a & Draft Research Protocol (L-SLSP-v1)
```

1. **Participant-Safe Cross-Validation:** Enforced strict participant-level grouping to eliminate data leakage.
2. **Authoritative Benchmark Freeze:** Preserved the v1 internal comparison artifact at `data/ml/results/baseline_v1_frozen.csv`; this is an engineering reference, not clinical validation.
3. **Reproducibility Audit:** Documented deterministic rerun evidence in [`reports/ml/V1_REPRODUCIBILITY_AUDIT.md`](../ml/V1_REPRODUCIBILITY_AUDIT.md) without treating numerical reproducibility as construct or clinical validity.

---

## 3. Feature Schema v2 Findings & Scientific Interpretation

Feature Schema v2 adds 8 deterministic conversational and repetition fields (`speaker_balance_ratio`, `turn_alternation_rate`, `child_run_length_mean`, `child_response_rate`, `adult_response_rate`, `partner_repetition_exact_ratio`, `partner_repetition_overlap_mean`, `self_repetition_exact_ratio`). The benchmark uses 13 non-age v1 inputs, 8 v2 inputs, and 21 combined non-age inputs; `age_months` is evaluated separately as a control. See [`V1_VS_V2_COMPARISON.md`](../ml/V1_VS_V2_COMPARISON.md) for the generated current results.

### Key Scientific Insights:
- **Mixed exploratory results:** Adding v2 produces positive and negative deltas depending on the retrospective comparison; it does not establish uniform improvement.
- **No differential-diagnosis claim:** Historical group-label comparisons do not authorize individual classification, clinical interpretation, or product scoring.
- **Cross-domain limitation:** Text features remain sensitive to examiner prompting and session structure; the current evidence does not establish cross-site transportability.

---

## 4. Current Hypothesis & Acoustic Measurement System (v3a)

### Scientific Hypothesis:
*Text CHAT transcripts do not contain the validated acoustic boundaries needed for millisecond timing or prosodic measurement. Prospective audio research may test whether such measurements are reliable after human-gold validation; no clinical construct or predictive value is assumed.*

### Prospective Research Artifacts:
1. **Standardized Research Language-Sampling Protocol (`L-SLSP-v1`):** A draft 3-block prospective protocol (Free play, Semi-structured play, Narrative task) with a 5-level examiner prompt hierarchy (Levels 0–4) for future feasibility and expert review.
2. **Tripartite Feature Framework:** Methodological separation of Child-Intrinsic, Examiner-Context, and Dyadic Interaction features.
3. **Acoustic Feature Schema v3a helpers (`features-acoustic-v3a`), not product integration:**
   - Millisecond Response Latency (`response_latency_median_ms`, `response_latency_iqr_ms`)
   - Semitone Pitch Variability (`pitch_f0_sd_semitones`, `pitch_range_90_10_semitones`)
   - Within-Turn Planning Pause Ratio (`pause_duration_ratio`)
   - Continuous Audio QC (`clipping_fraction`, `silence_fraction`, `speech_fraction`, `estimated_snr_db`)
4. **Quality-Aware Helper Contract:** Research helpers return explicit `QualityStatus` values and avoid silent zero imputation. They are not wired into the therapist API, UI, or production artifact path.

---

## 5. Limitations & Prospective Mitigations

| Identified Scientific Limitation | Direct Impact | Planned Future Mitigation |
| :--- | :--- | :--- |
| **Small Retrospective Sample Size** ($N=32$ in primary cohorts) | Wide confidence intervals on cross-domain validation | Multicenter prospective data collection under `L-SLSP-v1` |
| **Age Confounding in Historical Data** | Age correlates with diagnostic label in TalkBank | Age-bin stratified recruitment ($\pm 3\text{ months}$ matching) |
| **Examiner / Protocol Variance** | Models encode research-site differences | Standardized prompt hierarchy + Leave-One-Clinician-Out CV |
| **Lack of Timestamps in Legacy CHAT** | 0.0% timestamp bullets in Eigsti/Nadig | Audio intake pipeline with VAD & forced alignment |
| **English Retrospective Data vs Thai Clinical Target** | English lexical/prosodic norms do not transfer to tonal Thai | Thai acoustic calibration; no Thai diagnostic claims without local normative validation |

---

## 6. Scientific Contribution & Next Steps

The primary research contribution of this phase is an auditable candidate measurement foundation: confounded claims are rejected, benchmark provenance is recorded, and prospective acoustic helpers fail explicitly when measurement support is insufficient. This engineering work does not establish measurement, construct, clinical, or Thai validity.

### Recommended Next Phase:
1. Conduct empirical human-annotated timing validation using the synthetic template at `data/ml/validation/audio_alignment_gold_template.csv` and an appropriately governed future study dataset.
2. Obtain ethics, privacy, Thai SLP/phonetics expert, and protocol-governance approval before any prospective feasibility study of `L-SLSP-v1`.
3. Only evaluate predictive performance of Feature Schema v3a once acoustic measurement error is empirically quantified.
