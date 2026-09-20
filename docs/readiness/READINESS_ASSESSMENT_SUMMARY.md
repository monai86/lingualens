# LinguaLens Readiness Assessment & Governance Summary

**Document Version:** 2.0 (Assessment V2 S1/V1 Preparation Deliverable)  
**Date:** 2026-09-12  
**Authority Boundary:** Research Prototype. No Production Promotion or External Deployment Authorized.  
**Core Safety Rule:** Separate Prototype-Ready, Pilot-Ready, and Clinical-Validation status explicitly. Do not represent local software completion as clinical validation.

---

## 1. Categorized Readiness Matrix

```
+----------------------------------------------------------------------------------------------------+
|                                    READINESS CLASSIFICATION                                        |
+------------------------------------+-----------------------------------+---------------------------+
| PROTOTYPE-READY                    | PILOT-READY                       | CLINICAL-VALIDATION       |
| Status: 100% VERIFIED (PASSED)     | Status: BLOCKED ON PREREQUISITES  | Status: NOT VALIDATED     |
| Local software contracts, APIs,    | Controlled clinic deployment      | Diagnostic claims and     |
| migrations, and UI components.     | and operational infrastructure.   | Thai medical clearance.   |
+------------------------------------+-----------------------------------+---------------------------+
```

---

## 2. Tier 1: Prototype-Ready Status (Verified)

### Status: **100% COMPLETE & VERIFIED**

The local software baseline on branch `antigravity/assessment-v2-continuation` is fully implemented, verified, and passing all automated test gates:

### What Is Verified and Operational:
1. **Child & Consent Foundation (Slice P0 / Foundation):**
   - Tenant-scoped child records with pseudonymized display codes (`LL-XXXXXX`).
   - Granular consent tracking with immediate fail-closed revocation.
2. **Audio Capture & Elicitation Protocol (Slice P0 / Capture):**
   - Guided activity definitions under protocol `thai_guided_language_sample:v0`.
   - Recording quality gates (duration, loudness $-26$ to $-14$ dBFS, SNR $\ge 10$ dB, turn counts).
3. **Reviewed Transcript Segments (Slice A2 / E1):**
   - Speaker role attestation (`CHI`, `INV`, `MOT`).
   - Immutable segment snapshot sets binding evidence runs to verified inputs.
4. **Measured Features & Domain Profiles (Slice E1):**
   - Canonical `features_v2` extraction across 15 linguistic/acoustic markers.
   - Descriptive developmental domain profiles with explicit limitation disclosures.
5. **Longitudinal Assessment Comparisons (Slices B1–B3):**
   - Strict same-child and tenant boundary checks.
   - Incompatibility detection for protocol and language mismatches (`H14-Incompatible`).
   - Numerical delta evaluation with mandatory `indeterminate` clinical interpretation.
6. **Reviewable Attention Cues & Clinician Disposition (Slice C1):**
   - Non-exclusive attention cues referenced to policy `cues-v2.0` (zero ASD probabilities).
   - Clinician actions (`acknowledged`, `disagreed`, `more_evidence_requested`) requiring rationale.
   - Human-in-the-loop guarantee: computed cues **never** auto-populate report conclusions.
   - Standardized disposition (5 tiers) and structured follow-up plans.
7. **Report Draft, Immutable Sign-Off, PDF Export & Amendment Lineage (Slice C2):**
   - Server-side readiness check (consent active, evidence current, zero unreviewed cues, disposition present, authorized signer match, safety text checks).
   - Immutable signed snapshot with deterministic SHA-256 hash.
   - Repeated sign idempotency.
   - Post-sign edits create traceable amendment drafts (`amends_report_id`, `amendment_sequence`).
   - Authorized private PDF export with native Thai TrueType font rendering (`Ayuthaya.ttf`).
8. **Database & Native PostgreSQL RLS:**
   - Additive migrations through `0012_clinical_review_reports.py` (28 chars $\le 32$).
   - 11/11 tests pass in `scripts/check_assessment_v2_native.py` with forced RLS on all 24 tables.
9. **Therapist Web UI & Frontend Build:**
   - Full Next.js production build compiled cleanly with dynamic routes `/review` and `/report`.
   - 10 Vitest component tests pass; TypeScript typecheck has 0 errors.

---

## 3. Tier 2: Pilot-Ready Status (Prerequisites & Blockers)

### Status: **BLOCKED (Pending External Environment Authority & Ethics Approval)**

Controlled pilot deployment in a partner clinical setting requires resolving the following external prerequisites. None of these blockers can be resolved inside a local git repository:

### Exact External Blockers:

| Blocker ID | Prerequisite / Blocker Description | Required External Action | Current Status |
|---|---|---|---|
| **BLK-S1-01** | **Managed Supabase Staging Authority & Tokens** | Provision active staging project (`cbhwxklvcpgizeqriqxi`) with non-mock RS256 JWTs matching `docs/SUPABASE_AUTH_CONTRACT.md`. | **Pending Operator Action** |
| **BLK-S1-02** | **Live Two-Tenant RLS Staging Evidence** | Run `scripts/run_staging_review_bundle.sh` against live Render/Supabase staging to prove cross-tenant read/write blocking with real tokens. | **Pending Staging Env** |
| **BLK-S1-03** | **Private Bucket Storage & URL Expiry** | Provision managed Supabase S3-compatible private bucket; verify signed upload expiry ($\le 900$s) and public-access block. | **Pending Infrastructure Setup** |
| **BLK-V1-01** | **Institutional Ethics (IRB) Determination** | Obtain written Institutional Review Board (IRB) approval or exemption determination from Mahidol University / partner clinic for therapist usability testing and caregiver audio collection. | **Pending IRB Submission** |
| **BLK-V1-02** | **Live Therapist Formative Usability Sessions** | Execute the 5-participant usability protocol (`USABILITY_EVALUATION_PLAN.md`) with licensed SLPs. Record real task completion, assistance, SUS, and the safety probe question. | **Pending Ethics & Scheduling** |
| **BLK-V1-03** | **Thailand Personal Data Protection Act (PDPA) Agreement** | Execute formal clinical data processing agreement, caregiver consent disclosure, and data retention policy with the pilot clinic. | **Pending Legal / Clinic Approval** |

---

## 4. Tier 3: Clinical-Validation Status (Non-Diagnostic Boundary)

### Status: **NOT VALIDATED (Explicitly Out of Scope for Research Prototype)**

LinguaLens is an educational and research prototype designed to support therapists in organizing evidence. It is **NOT** a diagnostic instrument, medical device, or diagnostic decision maker.

### Absolute Clinical Boundaries:
1. **No Automated Autism Diagnosis:**
   - The platform does **not** compute autism risk scores, ASD classification probabilities, diagnostic cutoffs, or percentile severity rankings.
   - Any machine learning outputs are restricted to low-level acoustic and linguistic feature measurements (e.g. pitch stability, turn-taking latency, lexical count).
2. **No Automated Developmental Delay Staging:**
   - The platform does not assign developmental age equivalents or classify children as "delayed" vs "typical".
   - Longitudinal deltas are strictly numeric with units and signs, accompanied by an explicit `indeterminate` clinical interpretation tag.
3. **No Substitute for Multi-Disciplinary Evaluation:**
   - A diagnosis of Autism Spectrum Disorder in Thailand requires a comprehensive clinical evaluation by a certified pediatric developmental specialist or child psychiatrist, utilizing standardized diagnostic instruments (such as the Thai Diagnostic Autism Scale [TDAS], ADOS-2, or CARS-2) in conjunction with extensive developmental history.
4. **Future Clinical Validation Requirements:**
   - Achieving clinical validation would require prospective multi-center clinical trials ($N \ge 1,000$ Thai children), formal representative Thai normative data across regional socio-economic strata, double-blinded inter-rater reliability trials, and medical device regulatory clearance from the Thai Food and Drug Administration (Thai FDA).
   - Such activities are strictly outside the scope of this research prototype.
