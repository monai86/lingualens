# Human Action Checklist: Thai Clinical Pilot Ethics & Governance
**Document Identifier:** `LL-ACTION-ETHICS-PILOT-v1`  
**Document Date:** 2026-08-24  
**Target Audience:** Principal Investigators, Clinical Site Directors, and Ethics Review Boards (IRB)  

---

## 1. Explicit Governance Boundary: Human Responsibilities

AI tools cannot approve ethical protocols or execute legal agreements. The following governance actions **MUST be completed and verified by human research and clinical leaders**:

### A. Regulatory & Institutional Clearances
- [ ] **Institutional Review Board (IRB) Approval:** Formal ethical review and certificate of approval from the relevant Medical / University Ethics Committee (e.g. Mahidol University Central Institutional Review Board).
- [ ] **Hospital & Clinical Site Memorandums (MOU):** Formal institutional data-sharing and collaborative agreements between academic developers and hospital speech-language therapy units.
- [ ] **Child Assent Protocol:** Development of age-appropriate verbal and visual assent procedures for children aged $\ge 48\text{ months}$.

### B. Multi-Tiered Informed Consent Protocol
- [ ] **Tier 1 - Primary Clinical Care (`clinical_assessment`):** Written consent for in-session recording, speech diarization review, and clinician progress tracking.
- [ ] **Tier 2 - Secondary Research Reuse (`research_reuse`):** Separate, optional consent for de-identified secondary acoustic feature analysis and algorithm validation.
- [ ] **Non-Coercive Withdrawal Guarantee:** Explicit disclosure in Thai that declining or withdrawing secondary research consent has zero negative impact on the child's ongoing clinical therapy.
- [ ] **Immediate Purging Protocol:** Verified mechanism where consent withdrawal immediately unlinks active records, invalidates signed playback grants, and schedules derivative deletion.

### C. Audio Security & Ephemeral Playback Controls
- [ ] **Time-Limited Playback Grants:** Audio streams are accessed strictly via ephemeral, signed URLs expiring within 15 minutes, issued only to authenticated clinicians assigned to the case.
- [ ] **Tamper-Evident Audit Logging:** All audio playback events, speaker label corrections, and transcript attestations are immutably logged with clinician user ID, timestamp, and purpose.
- [ ] **Storage Encryption:** Raw audio artifacts and acoustic derivatives stored encrypted-at-rest (AES-256) on hospital servers or PDPA-compliant private storage.
- [ ] **De-Identification Oversight:** Verification that no hospital registration numbers (HN), child surnames, or clinician identities are exposed in research exports.

### D. Clinical Safety & Non-Diagnostic Disclosure
- [ ] **Mandatory Clinician Attestation:** Confirmation that no AI-generated summary or acoustic metric can be finalized without direct review and digital sign-off by a licensed speech-language pathologist.
- [ ] **Caregiver Disclosure Language:** Written explanation in patient reports stating that LinguaLens provides quantitative observational aids and is **not an automated autism diagnostic test**.

---

## 2. Institutional Sign-Off Table

| Milestone | Institutional Authority | Approval Date | Document Reference Number |
| :--- | :--- | :---: | :--- |
| **IRB / Ethics Clearance** | Institutional Ethics Committee | | |
| **Clinical Director Approval** | Department of Speech Therapy | | |
| **Data Governance Officer** | Institutional Data Protection Officer | | |
| **Consent Form Ratification** | Legal & Compliance Unit | | |

