# LinguaLens Audio & Diarization Review UI Specification (2026 Modern Standard)
**Document Identifier:** `LL-SPEC-AUDIO-REVIEW-UI-v1`  
**Date:** 2026-10-04  
**Author:** LinguaLens Core Engineering Team & Clinical AI Working Group  
**Status:** Approved Architectural Design  
**Target Surface:** `apps/lingualens-app/` & `apps/api/`  

---

## 1. Executive Summary & Clinical Intent

Naturalistic pediatric speech recordings in speech-language therapy (L-SLSP-v1 standardized sampling) present inherent acoustic challenges: female adult and pediatric voices can overlap in fundamental frequency ($F_0$), room reverberation can shift acoustic turn boundaries, and automated diarization/ASR pipelines can misattribute speakers.

Under LinguaLens clinical governance ([PROJECT_SOURCE_OF_TRUTH.md](file:///Users/porschecaa/lingualens/docs/PROJECT_SOURCE_OF_TRUTH.md) and [AUDIO_REVIEW_UI_REQUIREMENTS.md](file:///Users/porschecaa/lingualens/reports/ml/AUDIO_REVIEW_UI_REQUIREMENTS.md)), **automated ASR/diarization outputs may never be passed directly into finalized clinical progress reports without human clinician oversight**.

This specification defines the modern (2026) **Audio & Diarization Review Workbench** inside the Next.js Therapist Application (`apps/lingualens-app`), providing:
1. **Synchronized Dual-View Waveform:** A top-level Mini-map Overview (20–25 min) coupled with a Zoomed Detail Canvas (10–30 s) with sub-second drag handles.
2. **High-Performance Audio Pipeline:** Binary `ArrayBuffer` waveform decimation and short-lived signed direct-storage URLs (ADR 0015 compliant).
3. **Keyboard-First Clinical Ergonomics:** Hotkeys designed to reduce session review friction to under 5 minutes per patient.
4. **Smart VAD Energy Snapping & Overlap Detection:** Preventing truncation of Thai final consonants/tones while highlighting vocal turn collisions.
5. **Cryptographic Attestation & Downstream Invalidation:** Strict enforcement of Source of Truth Rule 9 (invalidating downstream findings on edit) and SHA-256 multi-hash seal attestation.

---

## 2. Architectural Boundaries & Regulatory Compliance

1. **Clinical Decision Support Boundary:**
   LinguaLens is a research and educational decision-support prototype. It does not provide automated diagnoses of Autism Spectrum Disorder (ASD). All quantitative metrics (MLU-w, TTR, Echolalia ratios, Prosodic pitch IQR) serve as observational speech-language cues for licensed professionals.
2. **ADR 0015 & Storage Direct Streaming:**
   The browser never streams gigabyte-scale audio through the Python FastAPI web process. FastAPI serves strictly as an authenticated gatekeeper verifying patient consent and issuing a short-lived (15-minute) signed playback URL directly to object storage.
3. **Rule 9 Downstream Invalidation:**
   Any modification to transcript text, speaker roles, or segment boundaries immediately invalidates pre-computed downstream findings and report drafts, marking them as `stale`. Stale findings cannot be exported or signed off until regenerated.
4. **Optimistic Concurrency Control:**
   Every transcript edit utilizes monotonic version locking (`base_version` + `If-Match`). Concurrent overwrites are rejected with `409 Conflict`.

---

## 3. UI/UX & Layout Architecture

The layout adopts the **Integrated Stacked Workbench** pattern, optimized for standard 13–16" clinician laptops:

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     SessionContextHeader (Case & Session ID)                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ AudioScrubberBar:                                                               │
│ [ ▶ Play/Pause ]  01:24.400 / 22:15.000  [0.75x][1.0x][1.25x]  [🔁 Loop: ON]    │
│ [ 📈 F0 Pitch: ON ]  [ 🔍 - ][ Fit ][ 🔍 + ]                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Mini-map Overview Strip (Full 20-25 min session overview with viewport box)     │
│ [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Zoomed Detail Canvas (10-30s window around active utterance):                   │
│ Time Ruler:  01:22s          01:24s (Cursor ▼)    01:26s          01:28s       │
│ CH1 (CHI):   [       [=== "รถ สี แดง" ===]                                   ]  │
│ CH2 (INV):   [                                 [=== "ใช่แล้ว รถวิ่งเร็วไหม" ===] ]  │
│ Quality: SNR 22.4 dB (Optimal) | Diarization Conf: 88.5% | Latency: 420 ms      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ UtteranceReviewList (Feed of editable turns):                                   │
│ ┌─────┬───────────┬──────────────┬───────────────────────────────┬────────────┐ │
│ │ #   │ Time      │ Speaker Role │ Utterance Text                │ Clinical   │ │
│ ├─────┼───────────┼──────────────┼───────────────────────────────┼────────────┤ │
│ │ 01  │ 01:24.4s  │ [CHI ▼]      │ รถ สี แดง                     │ Spontaneous│ │
│ │ 02  │ 01:28.1s  │ [INV ▼]      │ ใช่แล้ว รถวิ่งเร็วไหม           │ Prompt     │ │
│ │ 03  │ 01:31.4s  │ [CHI ▼]      │ วิ่งเร็วไหม                   │ ⚠️ Echo 60%│ │
│ └─────┴───────────┴──────────────┴───────────────────────────────┴────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ReviewAttestationBar:                                                           │
│ Status: [ ⚠️ IN_REVIEW (Unsaved Edits) ]  [ 💾 Save Draft ]  [ 🛡️ Attest & Seal ]│
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Hierarchy & Responsibilities

The workbench is implemented in `apps/lingualens-app/src/components/audio-review/`:

1. **`AudioReviewWorkbench.tsx` (Root Orchestrator):**
   * Manages audio playback state, active utterance tracking, and optimistic metrics.
   * Dispatches keyboard shortcuts to child components.
2. **`AudioScrubberBar.tsx`:**
   * Time display (`hh:mm:ss.mmm`).
   * Playback rate selector (`0.75x`, `1.0x`, `1.25x`) with pitch compensation.
   * Loop toggle button (`isLooping`).
   * F0 pitch contour toggle (`showPitch`).
3. **`DualViewWaveform.tsx`:**
   * **`WaveformMinimap.tsx`:** Renders full-session decimated audio profile. Displays a draggable shaded viewport box indicating the current detail zoom window.
   * **`WaveformDetailCanvas.tsx`:** Renders high-resolution waveform via `OffscreenCanvas` in a Web Worker. Displays multi-track lanes (`CHI`, `INV`, `MOT/FAT/OTH`), draggable boundary handles, playhead cursor, and pitch curve.
4. **`UtteranceReviewList.tsx`:**
   * Virtualized or paginated list of utterances.
   * Inline 1-click speaker badge selector.
   * Synchronized focus on currently playing utterance.
   * Real-time Thai LSA tags (Verbatim/Mitigated Echolalia, Pronoun Reversal).
5. **`ReviewAttestationBar.tsx`:**
   * Displays audit state (`AUTO_GENERATED` $\rightarrow$ `IN_REVIEW` $\rightarrow$ `CLINICIAN_CONFIRMED`).
   * Downstream staleness warning banner.
   * Attestation action triggering SHA-256 seal calculation.

---

## 5. High-Performance Audio Engine & Keyboard Ergonomics

### 5.1 Binary Peaks Transport & OffscreenCanvas Worker
* The client requests pre-computed audio peaks from `/api/v1/sessions/{id}/audio/waveform-peaks`.
* Data is received as an `application/octet-stream` and instantiated as `new Int8Array(response.arrayBuffer())`.
* Peak rendering is offloaded to a Web Worker (`waveform-worker.ts`) using `OffscreenCanvas.transferControlToOffscreen()`. Waveform redrawing and playhead animations run at 60–120 Hz completely decoupled from the React main thread.

### 5.2 Keyboard Shortcuts (Transcriptionist Speed Flow)
To ensure compliance with the $< 5\text{ minute}$ therapist review friction benchmark:
* `Spacebar`: Toggle Play / Pause.
* `Cmd / Ctrl + Space`: Replay active utterance from `start_ms`.
* `Cmd / Ctrl + L`: Toggle utterance loop mode.
* `Cmd / Ctrl + 1`: Assign active utterance to `CHI` (Child).
* `Cmd / Ctrl + 2`: Assign active utterance to `INV` (Examiner/Clinician).
* `Cmd / Ctrl + 3`: Assign active utterance to `MOT` (Mother/Parent).
* `Cmd / Ctrl + 4`: Assign active utterance to `FAT` (Father/Parent).
* `Tab` / `Shift + Tab`: Navigate to next / previous utterance text input.
* `Cmd / Ctrl + Enter`: Mark active line verified and advance cursor.

### 5.3 Smart VAD Boundary Snapping
* Waveform detail canvas analyzes local energy envelopes in a $\pm 150\text{ ms}$ window around drag handles.
* Dragging near speech pauses automatically snaps to the nearest energy valley ($< -30\text{ dBFS}$), preventing accidental truncation of Thai final plosives and falling/rising tone glides.

---

## 6. Backend API Contracts & Data Flow

### 6.1 Waveform Peaks Endpoint
* **Endpoint:** `GET /api/v1/sessions/{session_id}/audio/waveform-peaks`
* **Headers:**
  ```http
  Content-Type: application/octet-stream
  X-Sample-Rate: 16000
  X-Duration-Ms: 1500000
  X-Points-Per-Second: 50
  X-Channels: 2
  ```
* **Payload:** Packed binary `Int8Array` containing alternating min/max amplitudes for CH1 and CH2.

### 6.2 Signed Playback Grant
* **Endpoint:** `POST /api/v1/sessions/{session_id}/audio/playback-grant`
* **Access Control:** Requires active session consent and authorized therapist role.
* **Response Body:**
  ```json
  {
    "playback_url": "https://storage.lingualens.clinic/audio/raw/sess_123.wav?token=...",
    "expires_at": "2026-10-04T19:25:00Z",
    "audio_sha256": "4a7d...3f21"
  }
  ```

### 6.3 Optimistic Concurrency Transcript Update
* **Endpoint:** `PUT /api/v1/sessions/{session_id}/transcript`
* **Headers:** `If-Match: "v3"`
* **Request Body:**
  ```json
  {
    "base_version": 3,
    "lines": [
      {
        "line_id": "L1",
        "speaker": "CHI",
        "start_ms": 84400,
        "end_ms": 87200,
        "text": "รถ สี แดง"
      }
    ],
    "review_status": "IN_REVIEW"
  }
  ```
* **Response `200 OK`:** Returns new transcript record with `version: 4` and sets downstream `findings_stale: true`.
* **Response `409 Conflict`:** Returned if `base_version` does not match backend head, accompanied by conflict payload for diffing.

### 6.4 Attestation & Cryptographic Seal
* **Endpoint:** `POST /api/v1/sessions/{session_id}/transcript/attest`
* **Action:**
  1. Computes canonical CHAT transcript formatting.
  2. Runs `src/clinical_speech/thai_lsa.py` to extract finalized clinical LSA metrics.
  3. Generates cryptographic SHA-256 seal combining `audio_sha256`, `chat_sha256`, pipeline version, and therapist identity.
  4. Transitions status to `CLINICIAN_CONFIRMED`.

---

## 7. Error Handling & Edge Cases

| Scenario | System Behavior |
|---|---|
| **Audio File Missing or Unverified** | Graceful fallback to `Text-Only Editor` mode. Informational banner: *"Audio streaming unavailable. Full text review and role reassignment available in fallback mode."* |
| **Network Loss During Review** | Uncommitted edits persisted to encrypted `sessionStorage`. Banner displays *"Offline edits stored locally. Click to sync when reconnected."* |
| **Inverted Boundary Drag (`start >= end`)** | UI clamps duration to minimum 100 ms and warns with amber outline. |
| **Simultaneous Overlap Collision** | Detected intervals where both CH1 and CH2 have active speech are shaded in amber with an `⚠️ Speech Overlap` tag. |
| **Consent Revocation** | Immediate `403 Forbidden` on `/playback-grant`. Audio player unmounts and purges buffered media. |

---

## 8. Verification & Testing Strategy

1. **Frontend Tests (`apps/lingualens-app/src/__tests__/audio-review.test.tsx`):**
   * Verification of keyboard shortcuts (`Spacebar`, `Cmd+1`, `Cmd+2`, `Tab`).
   * Verification of dual-view synchronization (moving viewport in Mini-map updates detail canvas).
   * Verification of optimistic metric recalculation when changing speaker roles.
   * Verification of downstream `stale` warning display upon text mutation.
2. **Backend Contract Tests (`apps/api/tests/test_audio_review.py`):**
   * Binary peak endpoint generation and `Content-Type` validation.
   * Signed playback URL generation and consent gating.
   * Optimistic concurrency validation (successful update on matching version, `409 Conflict` on stale version).
   * Downstream findings invalidation check (Rule 9 compliance).
   * Full attestation flow producing SHA-256 seal.
3. **Clinical Non-Overclaiming Gate:**
   * Automated verification confirming no automated ASD diagnostic scores or validation claims are presented to the clinician.
