# LinguaLens Audio & Diarization Review UI Requirements
**Document Date:** 2026-08-24  
**Target Surface:** `apps/lingualens-app/`  
**Status:** UI/UX Specification for Clinician Audio/Transcript Correction Workflow  

---

## 1. Clinical Context & Need

Automated speech recognition (ASR) and speaker diarization can make errors on naturalistic pediatric recordings (e.g. confusing adult female voices with child voices, misclassifying crying/laughter, or shifting turn boundaries). 

To ensure clinical trustworthiness, speech-language therapists must be able to review, adjust, and confirm audio boundaries and speaker roles before finalized clinical reporting.

---

## 2. Core Functional Requirements

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AUDIO & DIARIZATION REVIEW UI                   │
│                                                                        │
│  [Waveform / Spectrogram Display with Segment Region Overlays]        │
│  ├── CH1 (Child)   [──Speech──]         [──Speech──]                  │
│  └── CH2 (Adult)                [──Speech──]         [──Speech──]      │
│                                                                        │
│  [Interactive Transcript List]                                         │
│  ┌────────┬───────────────┬───────────────────────────────┬─────────┐  │
│  │ Time   │ Speaker Role  │ Utterance Text                │ Actions │  │
│  ├────────┼───────────────┼───────────────────────────────┼─────────┤  │
│  │ 01:24s │ [CHI ▼]       │ "รถ สี แดง" [Re-play Audio]    │ [Edit]  │  │
│  │ 01:28s │ [INV ▼]       │ "ใช่แล้ว รถวิ่งเร็วไหม"         │ [Edit]  │  │
│  └────────┴───────────────┴───────────────────────────────┴─────────┘  │
│                                                                        │
│  [Quality Indicators Bar]                                              │
│  - Estimated SNR: 22.4 dB (Good)   - Diarization Confidence: 88%       │
│  - Response Latency: 420 ms (Valid)                                    │
└────────────────────────────────────────────────────────────────────────┘
```

### Requirement 1: Synchronized Waveform & Segment Playback
- Interactive waveform/spectrogram with visual segment boundaries.
- Clicking any transcript utterance automatically jumps audio playback to `[start_ms, end_ms]`.

### Requirement 2: One-Click Speaker Role Reassignment
- Dropdown on each turn to toggle between `CHI` (Target Child), `INV` (Examiner/Clinician), `MOT/FAT` (Parent), `OTH` (Other/Sibling), `OVERLAP`.
- Changing speaker role immediately recalculates conversational metrics (`speaker_balance_ratio`, `turn_alternation_rate`, `response_latency_median_ms`) in real time.

### Requirement 3: Boundary Snapping & Drag-to-Adjust
- Ability to drag segment onset/offset boundaries on the waveform to correct clipping or premature VAD cutoff.

### Requirement 4: Explicit Review Confirmation Status
- Every session maintains an audit flag:
  - `status: "AUTO_GENERATED"` (Unreviewed automated pipeline output)
  - `status: "CLINICIAN_CONFIRMED"` (Reviewed and approved by human therapist)
- Clinical reports clearly label whether metrics stem from unreviewed vs confirmed transcripts.
