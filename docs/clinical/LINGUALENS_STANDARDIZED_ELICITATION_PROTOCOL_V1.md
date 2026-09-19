# LinguaLens Standardized Language-Sampling Protocol v1.0 (L-SLSP-v1)
**Protocol Version:** 1.0.0-PROSPECTIVE-RESEARCH  
**Document Status:** Standardized Research Specification (Not a Validated Clinical Diagnostic Instrument)  
**Target Population:** Children aged 24–72 months undergoing exploratory speech-language assessment  

---

## 1. Scope & Objective

Retrospective corpus analyses showed strong site/protocol predictability (exploratory corpus-prediction AUROC: v1 **0.9936**, v2 **0.7679**, combined **0.9817**), warning that models can exploit laboratory-specific elicitation artifacts rather than invariant traits.

The **LinguaLens Standardized Language-Sampling Protocol (L-SLSP-v1)** establishes a reproducible, cross-site standardized language-sampling procedure to minimize examiner variance, standardize acoustic recording fidelity, and provide auditable task/block metadata for prospective research.

---

## 2. Environmental & Acoustic Setup

```text
┌─────────────────────────────────────────────────────────────┐
│                    RECORDING ENVIRONMENT                    │
│                                                             │
│      [Child] ◄──────── 60-90 cm ────────► [Examiner]       │
│         │                                    │              │
│         └──────────────┐      ┌──────────────┘              │
│                        ▼      ▼                             │
│                  [Dual/Stereo Mic]                          │
│                (or Calibrated Array)                        │
│                                                             │
│   Room Requirements:                                        │
│   - Ambient Noise: < 40 dBA (HVAC/windows damped)           │
│   - Reverberation: Carpeted floor / acoustic wall panels    │
└─────────────────────────────────────────────────────────────┘
```

1. **Room Acoustics:**
   - Quiet examination room with minimal reverberation (soft flooring, soft furnishings).
   - Baseline ambient sound level must be logged for 15 seconds before child entry.
2. **Microphone Setup:**
   - **Recommended:** High-quality boundary microphone or dual-capsule stereo microphone placed equidistant (60–90 cm) between child and examiner.
   - **Alternative:** Discrete lavalier / head-mounted wireless microphones with channel 1 = Child, channel 2 = Examiner.
   - **Recording Format:** Lossless PCM WAV, 44.1 kHz or 48.0 kHz, 24-bit (minimum 16-bit), uncompressed.
3. **Seating:**
   - Low table with child and examiner seated at a 90° angle or directly across, ensuring natural eye contact and mutual toy access.

---

## 3. Standardized Session Structure (Tri-Block Architecture)

A standard LinguaLens session consists of three distinct, separable blocks totaling 20–25 minutes. **Blocks must NOT be merged silently; every transcript utterance and acoustic segment must retain its `task_block` tag.**

```text
Session Timeline (Total: ~20-25 min)
├─ Block A: Naturalistic Free Interaction (~5-7 min)
│  └─ Child-led exploration with standard open-ended toys
├─ Block B: Semi-Structured Play (~10-12 min)
│  └─ Joint routine / problem-solving play with structured materials
└─ Block C: Standardized Narrative / Picture Elicitation (~5-6 min)
   └─ Scripted picture-book or sequential story task
```

### Block A — Naturalistic Free Interaction (5–7 min)
- **Goal:** Establish rapport and observe spontaneous child-initiated communication.
- **Examiner Role:** Follow the child's attentional focus. Do not direct play. Use low-level prompts (Levels 0–1).
- **Standard Materials (Set A1):** Farm set / animal figures, cars with ramp, wooden blocks.

### Block B — Semi-Structured Joint Play (10–12 min)
- **Goal:** Elicit conversational reciprocity, requests, and comments during shared routines.
- **Examiner Role:** Introduce scripted communicative temptations (e.g. bubbles with tight lid, wind-up toy, tea set routine). Use progressive prompt hierarchy (Levels 1–3).
- **Standard Materials (Set B1):** Play-food/tea set, bubbles, wind-up toys, interactive box with latch.

### Block C — Standardized Narrative / Picture Elicitation (5–6 min)
- **Goal:** Elicit connected discourse, complex syntax, and narrative structure.
- **Examiner Role:** Present a wordless picture sequence (e.g. *Frog, Where Are You?* or standardized local equivalent) with uniform introductory framing.
- **Standard Materials (Set C1):** Standardized 12-page picture booklet (Version C1.0).

---

## 4. Examiner Prompt Hierarchy (Levels 0–4)

To prevent examiner variability from distorting conversational metrics, clinicians must adhere to a deterministic prompt hierarchy. Every clinician turn should be taggable with a prompt level:

```text
Level 0: Natural Wait / Pause
  └─ Examiner maintains expectant silence (3-5 sec) following child action/turn.

Level 1: Open General Invitation
  └─ Non-directive comment or observation ("Look at that!", "Oh wow!").

Level 2: Open Expansion Prompt
  └─ Expands child utterance with open-ended continuation ("The car went fast... and then?").

Level 3: Specific Content Prompt
  └─ Open wh-question prompting specific elaboration ("What is the bear doing now?").

Level 4: Direct / Constrained / Yes-No Prompt
  └─ Closed or binary question ("Is it red or blue?", "Do you want more?").
```

*Rule:* Examiners must always attempt lower-level prompts before escalating to Level 4. Excessive Level 4 prompts (> 40% of adult turns) will trigger an examiner-bias warning in data audits.

---

## 5. Rescue Rules & Exception Handling

When typical interaction stalls, examiners follow standardized rescue protocols:

1. **Child Non-Response (5 seconds silence):**
   - Step 1: Deliver Level 1 invitation. Wait 3 seconds.
   - Step 2: Deliver Level 3 wh-question. Wait 3 seconds.
   - Step 3: Deliver Level 4 direct choice prompt.
2. **Child Distraction / Wandering:**
   - Examiner re-anchors to table with high-salience toy; logs `distraction_event` in session metadata.
3. **Severe Agitation / Distress:**
   - Pause recording. If paused > 3 minutes, terminate session and mark session as `INCOMPLETE_PROTOCOL`.
4. **Unscheduled Interruption (e.g. parent entry, phone ring):**
   - Mark timestamp range as `EXCLUDED_INTERVAL` in session audio log.

---

## 6. Session Sufficiency Metrics (Continuous QC)

Rather than enforcing arbitrary hard cutoffs, LinguaLens logs continuous sufficiency counters:

- `duration_seconds`: Total recorded session length.
- `usable_child_speech_seconds`: Accumulated phonated child speech.
- `usable_adult_speech_seconds`: Accumulated phonated adult speech.
- `usable_child_turns`: Count of intelligible child turns.
- `usable_adult_turns`: Count of clinician prompt turns.
- `response_opportunities_count`: Count of adult turns followed by a response window.

---

## 7. Provenance & Confounder Metadata Schema

Every recording and extracted transcript must include the following metadata record:

```json
{
  "session_uid": "sess_20260824_site01_0042",
  "participant_uid": "p_042",
  "clinician_uid": "clin_07",
  "site_uid": "site_bangkok_01",
  "protocol_version": "1.0.0",
  "task_block": "BLOCK_B_SEMI_STRUCTURED",
  "material_set_version": "B1.0",
  "recording_date": "2026-08-24T09:30:00Z",
  "environment": {
    "room_type": "standard_clinic_sound_treated",
    "ambient_noise_dba": 36.5,
    "microphone_model": "Rode_Wireless_PRO_Dual",
    "channel_layout": "CH1_CHILD_CH2_CLINICIAN",
    "sample_rate_hz": 48000,
    "bit_depth": 24
  },
  "demographics": {
    "age_months": 42.5,
    "primary_language": "th",
    "secondary_language": null
  },
  "confounder_audit_flags": {
    "is_site_controlled": true,
    "is_clinician_balanced": true
  }
}
```

*Note: Demographics and clinician IDs are strictly used for provenance and confounder auditing; they must never be fed into predictive diagnostic ML models.*
