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

---

## 4. Target Feature Battery & Audio-Review Alignment

The variance analysis targets features extracted and reviewed via the **Audio & Diarization Review Workbench**:

| Feature Category | Continuous Metric | Verification & Quality Control Method | Expected Role |
| :--- | :--- | :--- | :--- |
| **Conversational Timing** | Response Latency (IQR, s) | Verified speaker boundaries (`INV` ➔ `CHI` transition) via Dual-view Waveform | Primary child signal (contingent response) |
| **Conversational Timing** | Clinician Prompt Rate (prompts/min) | Clinician speech segments flagged with clinical tags | Dyadic environmental covariate |
| **Acoustic Profiling** | Speaker-Centered F0 Range (semitones) | Voiced frame pitch contour overlay ($\ge 30\%$ voiced frames required) | Child prosodic variability marker |
| **Acoustic Profiling** | Within-Turn Pause Ratio | Acoustic silence detection within contiguous `CHI` turns | Fluency / speech-motor signal |
| **Thai Pragmatics** | Particle Density (`ครับ`/`ค่ะ`/`นะ`) | Lexical transcript verified by therapist attestation | Pragmatic marker of social intent |
| **Thai Pragmatics** | Mitigated vs Verbatim Echolalia Ratio | Immediate utterance repetition comparison | Social communication differentiation |

### Data Integrity & Leakage Prevention:
1. **Therapist Attestation Ground Truth:** Only transcripts verified and digitally attested through the Audio Review Workbench (with optimistic locking `base_version`) are eligible for variance analysis.
2. **Rule 9 Downstream Invalidation:** Any transcript edits automatically mark previously extracted features and reports as stale, preventing contaminated metrics from entering statistical partitions.
3. **No Direct Identifiers:** All variance datasets use isolated pseudonymized participant IDs (`child_id`), omitting names, HN numbers, or raw audio paths.

---

## 5. Clinical Safety & Non-Diagnostic Boundary

> [!IMPORTANT]
> The variance component analysis plan is an **epidemiological and psychometric validation protocol**. It does not constitute, authorize, or validate an automated diagnostic algorithm. All extracted metrics represent descriptive observational aids intended to assist licensed speech-language pathologists in therapeutic goal setting and progress monitoring.

