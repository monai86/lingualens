# LinguaLens Formative Usability Evaluation Plan & Checklist

**Document Version:** 2.0 (Assessment V2 V1 Deliverable)  
**Date:** 2026-09-12  
**Current Execution Status:** **EXECUTION PENDING (Awaiting Institutional Ethics & Live Therapist Cohort)**  
**Strict Integrity Rule:** No synthetic or simulated participant responses have been fabricated. Real usability evaluation metrics will only be populated after live, observed testing sessions with authorized speech-language therapists.

---

## 1. Ethics & Privacy Boundary

- **Ethics Determination:** Prior to recruiting licensed clinicians or recording test sessions, formal written institutional ethics approval (or formal exemption determination) from the Faculty of Medical Technology / Mahidol University Institutional Review Board (IRB) is required.
- **Participant Privacy:**
  - Participant names, contact numbers, clinics, or hospitals must never be committed to source code or git repositories.
  - Test participant identities are pseudonymized using identifiers `P01` through `P05`.
  - All test sessions are conducted exclusively using synthetic patient profiles (`LL-0001` through `LL-0007`). No real patient cases or clinical recordings may be loaded during testing.

---

## 2. Participant Profile & Target Cohort

| Criterion | Specification | Justification |
|---|---|---|
| **Target Population** | Licensed Speech-Language Pathologists (SLPs) / Communication Therapists in Thailand | Primary intended end-users of the clinical research prototype. |
| **Cohort Size** | $N = 5$ licensed clinicians for the formative round | Standard Nielsen-Norman sample size for discovering $\ge 85\%$ of critical usability and workflow blockers. |
| **Clinical Experience** | Range: 1 to 15+ years across pediatric developmental delay, ASD, and articulation therapy | Ensures interface is intuitive for both novice practitioners and senior clinical specialists. |
| **Language Fluency** | Native Thai speaker; proficient in reading clinical English terms | Matches the bilingual Thai/English prototype interface. |

---

## 3. Evaluation Schedule & Logistics

```
+-------------------+-------------------------------------------------------------------------+
| Stage             | Planned Duration & Activity                                             |
+-------------------+-------------------------------------------------------------------------+
| 1. Pre-Session    | 10 minutes: Welcome, informed consent briefing, non-diagnostic boundary |
|                   | explanation, demographic questionnaire (role category, experience band). |
| 2. Task Battery   | 35 minutes: Execution of 5 standardized task cards (T1 through T5).      |
| 3. Safety Check   | 5 minutes: Comprehension probe ("Does this screen diagnose ASD?").       |
| 4. Post-Session   | 10 minutes: System Usability Scale (SUS) survey & semi-structured debrief|
+-------------------+-------------------------------------------------------------------------+
| Total Session     | 60 minutes per participant                                              |
+-------------------+-------------------------------------------------------------------------+
```

---

## 4. Standardized Task Cards & Evaluation Rubric

### Task Card 1: Case Discovery & Assessment Inception (`T1`)
- **Prompt to Participant:** *"A 3-year-old child arrives for a developmental follow-up. Please locate the child in your assigned caseload and initiate a guided language sample assessment."*
- **Success Criteria:** Correctly locates `LL-0001`, selects `developmental_follow_up` purpose and protocol `thai_guided_language_sample:v0` without moderator assistance.
- **Metrics Collected:** Completion (Yes/No), Time on Task (seconds), Moderator Prompts (count), Ease Rating (1–7).

---

### Task Card 2: Safe Recovery from Consent Withdrawal (`T2`)
- **Prompt to Participant:** *"Before beginning the audio recording, the caregiver notifies you that they wish to withdraw consent for digital recording. Please demonstrate how you respond in the system."*
- **Success Criteria:** Participant halts recording process, navigates to consent management, verifies `withdrawn` status, and confirms system blocks audio capture.
- **Safety Criterion:** Participant must not attempt to bypass or record without active consent.

---

### Task Card 3: Audio Capture & Recovery from Sparse Speech (`T3`)
- **Prompt to Participant:** *"You have completed an audio recording, but the child spoke very little. Review the recording quality indicators and decide on the next clinical step."*
- **Success Criteria:** Identifies `needs_additional_sample` status, inspects turn count ($N < 10$), and selects the option to record an additional activity rather than forcing an incomplete analysis.

---

### Task Card 4: Profile Comprehension & Non-Diagnostic Boundary (`T4`)
- **Prompt to Participant:** *"Examine the extracted evidence profile and longitudinal comparison for this child. Explain what the scores tell you and what they do not tell you."*
- **Success Criteria:** Explains measured vocabulary and MLU deltas; notes that longitudinal interpretation is `indeterminate`; identifies explicit feature limitations.
- **Mandatory Safety Probe Question:**
  > Moderator: *"Does this screen indicate to you that the child has Autism Spectrum Disorder (ASD)?"*  
  > **Passing Answer:** *"No. The system displays descriptive speech-language measurements and attention flags to assist clinical review, but does not provide an automated medical diagnosis or probability score."*

---

### Task Card 5: Attention Cue Review, Disposition & Sign-Off (`T5`)
- **Prompt to Participant:** *"Review the attention cues generated for this session. Acknowledge one cue, disagree with another cue with your clinical rationale, author your disposition, and finalize the report."*
- **Success Criteria:** Acknowledges Cue 1; enters clinical rationale to disagree with Cue 2; selects standardized disposition; enters follow-up plan; completes report sign-off.
- **Integrity Rule:** Participant must understand that computed cues do not enter report conclusions without therapist review.

---

## 5. Formal Usability Metrics & Quantitative Thresholds

| Metric | Target Passing Threshold | Status |
|---|---|---|
| **Task Completion Rate** | $\ge 80\%$ unassisted completion across T1–T5 | **Pending Live Sessions** |
| **Critical Safety Error Rate** | $0\%$ tolerance (Zero instances of mistaking cues for diagnosis or signing with revoked consent) | **Pending Live Sessions** |
| **Mean System Usability Scale (SUS)** | Score $\ge 75/100$ (Grade B+ / Acceptable) | **Pending Live Sessions** |
| **Safety Comprehension Pass Rate** | $100\%$ ($5/5$ participants correctly answer "No" to the ASD diagnosis probe) | **Pending Live Sessions** |

---

## 6. Observation Sheet Location

The raw observation ledger is prepared at:  
[`docs/ux/therapist-workflow/usability-observation-sheet.csv`](file:///Users/porschecaa/lingualens/.worktrees/antigravity-assessment-v2-continuation/docs/ux/therapist-workflow/usability-observation-sheet.csv)

Header specification:
```csv
session_code,participant_role_category,experience_band,task_id,completion,moderator_assistance,critical_error,time_on_task_seconds,ease_rating_1_to_7,observed_issue_id,notes_deidentified
```
*(Will be populated strictly as live observed sessions take place.)*
