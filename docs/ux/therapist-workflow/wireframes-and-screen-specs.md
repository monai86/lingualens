# Therapist Assessment Workflow: Wireframes & Screen Specifications

This document provides complete local UX/UI wireframe specifications for the 5-step therapist research prototype workflow, including edge cases, access barriers, and comparison states.

---

## 1. Step 1: Child Selection, Protocol & Consent Gate

### Frame `H01`: Child Selection & Case History
- **Header**: LinguaLens Therapist Portal | Clinician: Dr. Smith (ID: `usr_123`) | Organization: Child Dev Clinic
- **Main View**:
  - Search bar: Filter by display code (e.g. `CH-8821`, no real names)
  - Caseload table:
    - Child Display Code | Age Context | Language Context | Last Assessed | Action
    - `CH-8821` | 42 mos | th-TH / Central | 2026-08-15 | [Start Assessment]
- **Safety Badge**: "Research / Educational Demo Only — Not a Diagnostic Tool"

### Frame `H02`: Protocol & Activity Selection
- **Context**: Child `CH-8821` (42 mos, th-TH)
- **Selection**:
  - Protocol: `elicitation_protocol_v1` (Play-based interaction & narrative)
  - Activities enabled:
    - [x] Semi-structured Play (Free conversation)
    - [x] Picture Description (Narrative elicitation)
- **Action**: [Continue to Consent Gate]

### Frame `H03`: Explicit Consent Gate (Blocking)
```
+-------------------------------------------------------------+
| Consent Verification                                        |
|                                                             |
| Protocol: elicitation_protocol_v1                           |
| Child Display Code: CH-8821                                 |
|                                                             |
| [X] Informed guardian consent on file                       |
|     - Purpose: Research assessment and educational pilot    |
|     - Audio retention: 90 days, private encrypted storage   |
|     - Scope: Non-diagnostic clinical decision support       |
|                                                             |
| Consent Timestamp: 2026-09-12 09:00 UTC                     |
| Verified By: Clinician (usr_123)                            |
|                                                             |
| [ Cancel ]                         [ Confirm & Proceed ]    |
+-------------------------------------------------------------+
```
- **Error State (`E03`)**: If consent is withdrawn or missing, the session cannot proceed to recording; upload and processing remain locked.

---

## 2. Step 2: Guided Activity Recording & Audio Quality Control

### Frame `H04`: Guided Recording Screen
- **Timer**: `00:04:15` / Recommended: `05:00`
- **Audio Level Meter**: Dynamic dB visualizer (green/amber/red)
- **Guidance Prompts**:
  - Prompt 1: Encourage open-ended child queries (e.g., "What is the dog doing?")
  - Prompt 2: Pause 3–5 seconds to allow child response initiation
- **Controls**: [ Pause ] [ Finish & Verify Upload ]

### Frame `H05`: Processing & Audio Quality Feedback
- **Status Indicator**: Processing Run (`run_4412`, stage: `quality_analysis`)
- **Metrics Table**:
  - Duration: 278.4s (Pass > 120s)
  - Loudness: -21.4 dBFS (Pass -26 to -14 dBFS)
  - Silence Ratio: 0.18 (Usable < 0.40)
  - Decodability / SNR: 0.88 (Adequate)
- **Quality Status**: `USABLE` (or `INSUFFICIENT_DATA` / `UNAVAILABLE` with explicit reason)
- **Action**: [ Proceed to Transcript Review ]

---

## 3. Step 3: Transcript Segment Review & Attestation

### Frame `H11-S`: Full Ordered Segment Timeline
- Segment list with start/end ms, speaker tag (`CHI`, `INV`, `MOT`), transcribed text, confidence, and uncertainty flags.

### Frame `H11-U`: Uncertain-Only Segment Filter
- Filter active: Showing 3 of 42 segments needing review.
- Focus list:
  1. `[00:45.200 - 00:48.100] CHI: xxx ไปไหน [Uncertain: acoustic_overlap]`
  2. `[01:12.000 - 01:14.500] CHI: กิน ขนม [Uncertain: low_confidence]`
  3. `[02:05.100 - 02:07.800] CHI: ตัว นู้น [Uncertain: speaker_overlap]`

### Frame `H11-E`: Focused Segment Editor & Bounded Replay
```
+-------------------------------------------------------------+
| Edit Segment #14                                            |
|                                                             |
| Timing: 00:45.200 - 00:48.100 (Duration: 2.9s)              |
| [ Play Audio Slice (Signed URL - 60s grant) ]               |
|                                                             |
| Speaker Role: [ CHI v ]                                     |
| Text: [ ไปเที่ยวไหนมา                                     ] |
| Uncertainty Reason: [ Resolved / None v ]                   |
|                                                             |
| [ Revert ]                        [ Save Segment Revision ] |
+-------------------------------------------------------------+
```
- **Error State (`E11`)**: `409 Conflict - stale_segment_set_version`. Shows "Segment version has been updated by another action. Reloading latest."

### Frame `H11-A`: Explicit Segment Attestation Panel
- Therapist confirms:
  - `[X] I have reviewed flagged uncertain segments and attest that this transcript snapshot accurately represents the child's recorded utterances for clinical review.`
- **Action**: [ Attest Segment Set & Trigger Evidence Extraction ]

---

## 4. Step 4: Descriptive Evidence & Comparable Follow-Up

### Frame `H12`: Evidence Profile & Measured Features
- **Developmental Domains**:
  1. **Expressive Language**: MLU: 3.12 morphemes | TTR: 0.48 | Utterances: 42
  2. **Speech Clarity & Production**: Unintelligible ratio: 0.05 | Non-verbal vocalizations: 3
  3. **Conversational Interaction**: Child-adult turn ratio: 0.72 | Response latency: unavailable (no millisecond acoustic alignment)
  4. **Social Communication**: Question ratio: 0.14 | Pronoun reversal: 0
  5. **Repetitive Language**: Echolalia ratio: 0.02
  6. **Prosody & Temporal Organization**: Speech rate: 110 wpm | Pitch metrics: unavailable (raw audio alignment not certified)
  7. **Evidence Sufficiency**: Descriptive only — no population reference band applied.

### Frame `H14-NoHistory`: Baseline Assessment (No Previous Visits)
- "This is the child's initial recorded assessment. Longitudinal comparison will be available on subsequent assessments under matching protocols."

### Frame `H14-Incompatible`: Incompatible Protocol or Language Context
- Assessment #1: 2026-07-10 (Protocol: `screen_short_v1`, Age: 40 mos, Lang: th-TH)
- Assessment #2: 2026-09-12 (Protocol: `elicitation_protocol_v1`, Age: 42 mos, Lang: th-TH)
- **Callout**: "Notice: Comparisons are not permitted across differing protocol structures (`screen_short_v1` vs `elicitation_protocol_v1`). Delata cannot be clinically interpreted."

### Frame `H14-Compatible`: Valid Same-Child Longitudinal Comparison
- Shows delta between compatible visits with numerical difference:
  - MLU: 2.50 -> 3.12 (Delta: +0.62)
  - Interpretation: `indeterminate` (Descriptive delta only; no clinical threshold applied without longitudinal cohort validation).

---

## 5. Step 5: Clinician Cues, Review & Signed Report

### Frame `H15`: Clinician Attention Cues & Observations
- Non-exclusive reviewable cues:
  - Cue: `CUE_ECHO_LOW`: Low echolalia observed in play context. (Status: `acknowledged`)
  - Cue: `CUE_MLU_GROWTH`: Numerical increase in utterance length. (Status: `noted`)
  - Clinician Note: "Child engaged well with visual prompts; social smiling observed."

### Frame `H18`: Clinician Disposition & Report Drafting
- Required fields before signing:
  - Primary Clinical Impression (Therapist-authored text)
  - Recommended Follow-up: 3 months / Speech-Language Therapy sessions
  - Omissions & Limitations disclosure: Acoustic pitch metrics not assessed due to uncalibrated recording device.

### Frame `E18`: Report Not Ready Guard
```
+-------------------------------------------------------------+
| Report Sign-off Blocked                                     |
|                                                             |
| The report draft cannot be signed yet due to:               |
|  - [!] Current transcript segments not attested             |
|  - [!] Clinician disposition narrative is blank             |
|                                                             |
| [ Return to Edit ]                                          |
+-------------------------------------------------------------+
```

### Frame `H19`: Immutable Signed Report Snapshot
- Immutable hash generated: `SHA256: 8f2a...`
- Signer: `Dr. Smith (usr_123)` at `2026-09-12 10:30 UTC`
- PDF Download button (authorized short-lived URL, Thai font rendered)
- Post-sign amendment note: "Any changes to evidence or clinical narrative will create a linked Amendment Draft revision #2; signed snapshot #1 remains immutable."
