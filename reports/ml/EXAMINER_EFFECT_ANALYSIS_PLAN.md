# Statistical Analysis Plan for Examiner & Site Variance
**Document Date:** 2026-08-24  
**Status:** Methodological Statistical Framework  
**Target:** Prospective Clinical Trials & Multicenter Validation  

---

## 1. Objective

This Statistical Analysis Plan (SAP) defines the mixed-effects regression framework to formally partition feature variance into:
1. **Clinical / Phenotypic Variance** (Target signal: ASD vs TD vs DD).
2. **Examiner / Clinician Random Effects** (Elicitation style differences).
3. **Site / Environmental Random Effects** (Acoustic room & hardware differences).
4. **Task / Protocol Block Effects** (Free play vs Structured vs Narrative).

---

## 2. Linear Mixed-Effects Model Specification

For any continuous candidate feature $Y_{ijkl}$ (e.g. `response_latency_median_ms`, `speaker_balance_ratio`, `pitch_f0_sd_semitones`):

$$Y_{ijkl} = \beta_0 + \beta_1 \text{Group}_i + \beta_2 \text{Age}_i + \beta_3 \text{TaskBlock}_j + \beta_4 (\text{Group}_i \times \text{TaskBlock}_j) + u_{\text{Clinician}, k} + v_{\text{Site}, l} + \epsilon_{ijkl}$$

Where:
- $\text{Group}_i$: Fixed effect for diagnostic group ($\text{ASD} = 1, \text{TD} = 0$).
- $\text{Age}_i$: Fixed effect covariate for child age in months (centered).
- $\text{TaskBlock}_j$: Fixed effect for protocol block (Block A, B, C).
- $u_{\text{Clinician}, k} \sim \mathcal{N}(0, \sigma_{\text{Clinician}}^2)$: Random intercept for clinician $k$.
- $v_{\text{Site}, l} \sim \mathcal{N}(0, \sigma_{\text{Site}}^2)$: Random intercept for site $l$.
- $\epsilon_{ijkl} \sim \mathcal{N}(0, \sigma_{\epsilon}^2)$: Residual observation error.

---

## 3. Variance Partitioning & Intraclass Correlation Coefficient (ICC)

To determine whether a feature is dominated by examiner behavior rather than child phenotype, we compute the Clinician Intraclass Correlation Coefficient ($\text{ICC}_{\text{Clinician}}$):

$$\text{ICC}_{\text{Clinician}} = \frac{\sigma_{\text{Clinician}}^2}{\sigma_{\text{Clinician}}^2 + \sigma_{\text{Site}}^2 + \sigma_{\epsilon}^2}$$

### Decision Rules:
- **$\text{ICC}_{\text{Clinician}} < 0.15$:** Low examiner dependency. Feature is robust to clinician changes.
- **$0.15 \le \text{ICC}_{\text{Clinician}} \le 0.35$:** Moderate examiner dependency. Feature requires examiner covariate adjustment.
- **$\text{ICC}_{\text{Clinician}} > 0.35$:** High examiner dependency. Feature primarily reflects adult prompting style; must be treated as a Dyadic Interaction / Examiner-Context metric rather than an intrinsic child trait.

---

## 4. Cross-Validation Schemes for Prospective ML Evaluation

Prospective evaluations must test three complementary cross-validation topologies:

1. **Participant-Group CV (Standard Within-Site Baseline):** 5-repeat Stratified 4-Fold CV splitting on `participant_uid`.
2. **Leave-One-Clinician-Out (LOCO-CV):** Train on $K-1$ clinicians, test on 1 held-out clinician. Evaluates resilience to clinician style shifts.
3. **Leave-One-Site-Out (LOSO-CV):** Train on $S-1$ clinical hospital sites, test on 1 held-out hospital site. Evaluates full cross-institutional generalization.
