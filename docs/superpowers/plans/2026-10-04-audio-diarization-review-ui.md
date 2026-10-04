# Audio & Diarization Review Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the high-performance 2026 Audio & Diarization Review Workbench in `apps/lingualens-app` and supporting API routes in `apps/api`, featuring dual-view waveforms (Mini-map + Detail Canvas), binary `Int8Array` peaks, signed playback URLs, keyboard-first clinical shortcuts, and Rule 9 downstream invalidation.

**Architecture:** A dual-track interactive review workbench inside `SessionTranscriptView`. Audio peaks are streamed as lightweight binary octets from FastAPI, while actual audio streams via signed storage URLs directly to native `<audio>`. Interactive waveform scrubbing is rendered via Canvas with smart VAD snapping, and all speaker role modifications instantly recalculate conversational cues and enforce optimistic concurrency locking.

**Tech Stack:** Next.js 16.3.5, React 19, TypeScript, HTML5 Canvas / Web Audio API, FastAPI (Python 3.13), Vitest / Jest, Pytest.

---

### Task 1: Backend Binary Waveform Peaks & Direct Storage Grant Routes

**Files:**
- Create: `apps/api/app/api/v1/routes/audio_review.py`
- Modify: `apps/api/app/main.py:40-70`
- Test: `apps/api/tests/test_audio_review_api.py`

- [ ] **Step 1: Write the failing API test**

```python
# apps/api/tests/test_audio_review_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_waveform_peaks_returns_binary_stream():
    response = client.get("/api/v1/sessions/mock-session-1/audio/waveform-peaks")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "x-points-per-second" in response.headers
    assert len(response.content) > 0

def test_playback_grant_requires_consent_and_returns_signed_url():
    response = client.post("/api/v1/sessions/mock-session-1/audio/playback-grant")
    assert response.status_code == 200
    data = response.json()
    assert "playback_url" in data
    assert "expires_at" in data
    assert "audio_sha256" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/api:src pytest apps/api/tests/test_audio_review_api.py -v`  
Expected: FAIL with 404 Not Found

- [ ] **Step 3: Write minimal implementation**

Create `apps/api/app/api/v1/routes/audio_review.py` implementing:
- `GET /api/v1/sessions/{session_id}/audio/waveform-peaks`: Returns binary packed `int8` peaks array for CH1 and CH2.
- `POST /api/v1/sessions/{session_id}/audio/playback-grant`: Validates consent and returns short-lived signed URL with SHA-256 hash.

Register router in `apps/api/app/main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/api:src pytest apps/api/tests/test_audio_review_api.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/api/v1/routes/audio_review.py apps/api/app/main.py apps/api/tests/test_audio_review_api.py
git commit -m "feat(api): add binary waveform peaks and signed playback grant endpoints

Co-Authored-By: Gemini <gemini@google.com>"
```

---

### Task 2: Backend Optimistic Concurrency & Transcript Attestation Seal

**Files:**
- Modify: `apps/api/app/api/v1/routes/workflow.py:120-180`
- Modify: `apps/api/app/services/transcript_service.py:50-90`
- Test: `apps/api/tests/test_transcript_attestation.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_transcript_attestation.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_transcript_update_optimistic_concurrency_conflict():
    # Update with wrong base version
    payload = {
        "base_version": 999,
        "lines": [{"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2000, "text": "hello"}],
        "review_status": "IN_REVIEW"
    }
    response = client.put("/api/v1/sessions/mock-session-1/transcript", json=payload)
    assert response.status_code == 409
    assert "conflict" in response.json()["detail"].lower()

def test_transcript_update_sets_downstream_stale():
    # Update with matching version
    payload = {
        "base_version": 1,
        "lines": [{"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2000, "text": "แก้คำพูด"}],
        "review_status": "IN_REVIEW"
    }
    response = client.put("/api/v1/sessions/mock-session-1/transcript", json=payload)
    assert response.status_code == 200
    assert response.json()["findings_stale"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/api:src pytest apps/api/tests/test_transcript_attestation.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Update `workflow.py` and `transcript_service.py` to:
- Compare incoming `base_version` with current `transcript.version`; raise 409 if mismatched.
- Set `session.findings_stale = True` and `session.report_stale = True` on mutation per Source of Truth Rule 9.
- Implement `/api/v1/sessions/{session_id}/transcript/attest` which computes canonical CHAT text hash and sets status to `CLINICIAN_CONFIRMED`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=apps/api:src pytest apps/api/tests/test_transcript_attestation.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/api/v1/routes/workflow.py apps/api/app/services/transcript_service.py apps/api/tests/test_transcript_attestation.py
git commit -m "feat(api): enforce optimistic concurrency and Rule 9 stale findings invalidation

Co-Authored-By: Gemini <gemini@google.com>"
```

---

### Task 3: Frontend Dual-View Waveform & Scrubber Component

**Files:**
- Create: `apps/lingualens-app/src/components/audio-review/audio-scrubber-bar.tsx`
- Create: `apps/lingualens-app/src/components/audio-review/waveform-minimap.tsx`
- Create: `apps/lingualens-app/src/components/audio-review/waveform-detail-canvas.tsx`
- Create: `apps/lingualens-app/src/components/audio-review/dual-view-waveform.tsx`
- Test: `apps/lingualens-app/src/__tests__/waveform-components.test.tsx`

- [ ] **Step 1: Write the failing frontend test**

```tsx
// apps/lingualens-app/src/__tests__/waveform-components.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AudioScrubberBar } from "@/components/audio-review/audio-scrubber-bar";

describe("AudioScrubberBar", () => {
  it("renders playback controls and toggles speeds", () => {
    const onSpeedChange = vi.fn();
    const onPlayPause = vi.fn();
    render(
      <AudioScrubberBar
        isPlaying={false}
        currentTimeMs={84400}
        durationMs={300000}
        speed={1.0}
        isLooping={false}
        showPitch={false}
        onPlayPause={onPlayPause}
        onSpeedChange={onSpeedChange}
        onToggleLoop={vi.fn()}
        onTogglePitch={vi.fn()}
      />
    );

    expect(screen.getByText(/01:24.400/)).toBeDefined();
    fireEvent.click(screen.getByText("0.75x"));
    expect(onSpeedChange).toHaveBeenCalledWith(0.75);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/waveform-components.test.tsx`  
Expected: FAIL with module not found

- [ ] **Step 3: Write minimal implementation**

Implement:
- `audio-scrubber-bar.tsx`: Time formatter, speed toggle buttons (0.75x, 1.0x, 1.25x), Loop toggle, F0 toggle, Play/Pause.
- `waveform-minimap.tsx`: Canvas rendering full-session peaks array with draggable viewport rectangle.
- `waveform-detail-canvas.tsx`: Canvas rendering high-resolution multi-track segments (`CHI` in blue, `INV` in green, `MOT` in purple), playhead cursor, and drag handles for onset/offset.
- `dual-view-waveform.tsx`: Combining minimap and detail canvas with synchronized viewport state.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/waveform-components.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/components/audio-review/ apps/lingualens-app/src/__tests__/waveform-components.test.tsx
git commit -m "feat(ui): implement dual-view waveform minimap and detail canvas

Co-Authored-By: Gemini <gemini@google.com>"
```

---

### Task 4: Frontend Keyboard Navigation & Utterance Review List

**Files:**
- Create: `apps/lingualens-app/src/components/audio-review/use-keyboard-review.ts`
- Create: `apps/lingualens-app/src/components/audio-review/utterance-review-list.tsx`
- Test: `apps/lingualens-app/src/__tests__/utterance-review-list.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// apps/lingualens-app/src/__tests__/utterance-review-list.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UtteranceReviewList } from "@/components/audio-review/utterance-review-list";

describe("UtteranceReviewList", () => {
  it("renders utterances with 1-click speaker badge and triggers role change", () => {
    const onLineChange = vi.fn();
    const lines = [
      { lineId: "L1", speaker: "CHI", text: "รถ สี แดง", startMs: 1000, endMs: 2500 }
    ];
    render(
      <UtteranceReviewList
        lines={lines}
        activeLineId="L1"
        onSelectLine={vi.fn()}
        onLineChange={onLineChange}
        onPlayUtterance={vi.fn()}
      />
    );

    expect(screen.getByDisplayValue("รถ สี แดง")).toBeDefined();
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "INV" } });
    expect(onLineChange).toHaveBeenCalledWith(0, expect.objectContaining({ speaker: "INV" }));
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/utterance-review-list.test.tsx`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Implement:
- `use-keyboard-review.ts`: Global key listener for `Space`, `Cmd+1` (CHI), `Cmd+2` (INV), `Cmd+3` (MOT), `Cmd+L` (Loop), `Cmd+Enter` (Mark verified and advance).
- `utterance-review-list.tsx`: List of utterance rows with speaker selector, time markers, inline text input, clinical badges (Mitigated Echolalia, Pronoun Reversal), and play buttons.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/utterance-review-list.test.tsx`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/components/audio-review/use-keyboard-review.ts apps/lingualens-app/src/components/audio-review/utterance-review-list.tsx apps/lingualens-app/src/__tests__/utterance-review-list.test.tsx
git commit -m "feat(ui): add keyboard navigation and utterance review list with clinical tags

Co-Authored-By: Gemini <gemini@google.com>"
```

---

### Task 5: Frontend Integration & Attestation into `SessionTranscriptView`

**Files:**
- Create: `apps/lingualens-app/src/components/audio-review/audio-review-workbench.tsx`
- Modify: `apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx:90-130`
- Test: `apps/lingualens-app/src/__tests__/audio-review-integration.test.tsx`

- [ ] **Step 1: Write integration test**

```tsx
// apps/lingualens-app/src/__tests__/audio-review-integration.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SessionTranscriptView } from "@/features/sessions/transcript/session-transcript-view";

describe("SessionTranscriptView with AudioReviewWorkbench", () => {
  it("renders audio review workbench when audio is present and falls back gracefully", () => {
    render(
      <SessionTranscriptView
        sessionContext={{ sessionId: "sess-1", caseId: "case-1", childId: "child-1" }}
        state={{ transcriptSaveStatus: "saved", qaStatus: "pass", transcriptAttested: false } as any}
        lines={[{ lineId: "L1", speaker: "CHI", text: "ทดสอบ", startMs: 500, endMs: 1500 }]}
        busy={false}
        onLinesChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExtractFeatures={vi.fn()}
        onGenerateReport={vi.fn()}
        onExport={vi.fn()}
        audioUrl="/api/v1/sessions/sess-1/audio/mock.wav"
      />
    );

    expect(screen.getByText(/Review Transcript/i)).toBeDefined();
    expect(screen.getByText(/ทดสอบ/)).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/lingualens-app && npm test -- src/__tests__/audio-review-integration.test.tsx`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Implement:
- `audio-review-workbench.tsx`: Orchestrating `AudioScrubberBar`, `DualViewWaveform`, `UtteranceReviewList`, and `ReviewAttestationBar`.
- Embed `AudioReviewWorkbench` inside `session-transcript-view.tsx` with fallback to text editor if audio is not yet uploaded or offline.

- [ ] **Step 4: Run full frontend and backend verification**

Run:
```bash
cd apps/lingualens-app && npm test
PYTHONPATH=apps/api:src pytest apps/api/tests -m "not assessment_postgres"
```
Expected: All tests PASS with 0 errors.

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/transcript/session-transcript-view.tsx apps/lingualens-app/src/components/audio-review/audio-review-workbench.tsx apps/lingualens-app/src/__tests__/audio-review-integration.test.tsx
git commit -m "feat(workflow): integrate AudioReviewWorkbench into canonical SessionTranscriptView

Co-Authored-By: Gemini <gemini@google.com>"
```
