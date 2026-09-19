# Prospective Thai Clinical Pilot: Variance Component Analysis Plan
**Document Identifier:** `LL-SAP-VARIANCE-THAI-v1`  
**Document Date:** 2026-08-24  
**Statistical Methodology:** Mixed-Effects Variance Partitioning & Leave-One-Clinician-Out Robustness  

---

## 1. Variance Partitioning Model

To quantify the sources of variance in extracted speech-language and acoustic features, continuous metrics will be analyzed using a Linear Mixed-Effects Model (LMM):

$$Y_{ijkm} = \mu + \text{Group}_i + \text{Age}_j + \text{Block}_k + u_{\text{Participant}} + v_{\text{Clinician}} + w_{\text{Site}} + \epsilon_{ijkm}$$

Where:
- $\text{Group}_i$: Fixed effect of diagnostic category (ASD, DD, TD).
- $\text{Age}_j$: Fixed effect of age in months.
- $\text{Block}_k$: Fixed effect of protocol block (Block A, B, C).
- $u_{\text{Participant}} \sim \mathcal{N}(0, \sigma_{\text{Child}}^2)$: Random effect of child individual differences (Signal).
- $v_{\text{Clinician}} \sim \mathcal{N}(0, \sigma_{\text{Clinician}}^2)$: Random effect of clinician elicitation style (Confounder).
- $w_{\text{Site}} \sim \mathcal{N}(0, \sigma_{\text{Site}}^2)$: Random effect of clinical site acoustics.
- $\epsilon_{ijkm} \sim \mathcal{N}(0, \sigma_{\epsilon}^2)$: Residual within-session variance.

---

## 2. Intraclass Correlation & Reliability Metrics

For each candidate feature, the **Signal-to-Clinician Ratio** will be computed:

$$\text{Variance Proportion}_{\text{Child}} = \frac{\sigma_{\text{Child}}^2}{\sigma_{\text{Child}}^2 + \sigma_{\text{Clinician}}^2 + \sigma_{\text{Site}}^2 + \sigma_{\epsilon}^2}$$
$$\text{Variance Proportion}_{\text{Clinician}} = \frac{\sigma_{\text{Clinician}}^2}{\sigma_{\text{Child}}^2 + \sigma_{\text{Clinician}}^2 + \sigma_{\text{Site}}^2 + \sigma_{\epsilon}^2}$$

### Feature Selection Gate for Measurement Research:
- **Eligible for further aggregate measurement study:** Features where $\text{Variance Proportion}_{\text{Child}} > 0.60$ and $\text{Variance Proportion}_{\text{Clinician}} < 0.20$. This threshold does not establish clinical validity or authorize participant-level modeling.
- **Classified as Dyadic / Environmental Covariate:** Features where $\text{Variance Proportion}_{\text{Clinician}} \ge 0.20$.

---

## 3. Leave-One-Clinician-Out (LOCO) Evaluation Strategy

If a separately governed future research study evaluates historical group-label models, examiner sensitivity will be audited using **Leave-One-Clinician-Out Cross-Validation (LOCO-CV)**. This plan does not authorize diagnostic modeling or therapist-product integration:

```text
Iter 1: Train on Clinicians B, C, D ──────► Test on Held-Out Clinician A
Iter 2: Train on Clinicians A, C, D ──────► Test on Held-Out Clinician B
Iter 3: Train on Clinicians A, B, D ──────► Test on Held-Out Clinician C
Iter 4: Train on Clinicians A, B, C ──────► Test on Held-Out Clinician D
```

This ensures that the model cannot achieve high accuracy by memorizing a specific clinician's interactive style.
