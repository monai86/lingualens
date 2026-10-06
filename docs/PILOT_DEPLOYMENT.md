# PasaScope (ภาษา-สโคป) Clinical Pilot Deployment & Operational Guide

This document outlines the deployment and local execution workflows for the **PasaScope (ภาษา-สโคป) v1.7.0** speech-language assessment decision-support system during clinical evaluator trials.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Clinician Workstation                            │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│    Next.js Web Workbench     │      Desktop GUI Tool        │  Desktop TUI  │
│    http://localhost:3000     │      (Tkinter / macOS)       │ (Textual/CLI) │
│  • Dual-view Audio Review    │  • Waveform Audio Slicing    │ • V2 Protocol │
│  • AI Assistant (/assistant) │  • Radar & Growth Corridors  │ • Offline/Net │
│  • 5-Tab Canonical Workflow  │  • Print-ready Vector PDF    │ • Waveform API│
└───────────────┬──────────────┴───────────────┬──────────────┴───────┬───────┘
                │                              │                      │
                └──────────────────────────────┼──────────────────────┘
                                               │ JSON REST API / Binary Peaks
                                ┌──────────────▼───────────────┐
                                │       FastAPI Backend        │
                                │    http://127.0.0.1:8000     │
                                │  • Audio Waveform & Grants   │
                                │  • Thai LSA Pragmatics Engine│
                                │  • TalkBank CHAT Parser      │
                                │  • SHA-256 Seal Attestation  │
                                └──────────────────────────────┘
```

---

## 2. Fast Track Execution (Recommended for Pilot Evaluators)

### Option A: Turnkey Single-Script Orchestration
Run the pilot launcher which verifies runtimes, boots FastAPI + Next.js, and monitors health:
```bash
bash scripts/launch_pilot.sh
```
To verify dependencies and port readiness without starting servers:
```bash
bash scripts/launch_pilot.sh --check-only
```

Once running, access:
- **Therapist Workbench:** [http://localhost:3000](http://localhost:3000)
- **Audio & Diarization Review:** Toggleable in any active session transcript view
- **AI Clinician Assistant:** [http://localhost:3000/assistant](http://localhost:3000/assistant)
- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option B: Docker Containerized Deployment
For isolated staging or hospital servers with Docker installed:
```bash
docker compose up --build
```
This initializes:
- `api` on port `8000`
- `frontend` on port `3000`
- `postgres` on port `5432` with pre-configured schemas and migrations.

---

### Option C: Desktop GUI & TUI Power Tools
For standalone clinical workstation speech analysis:

- **Desktop GUI Tool:**
  ```bash
  python scripts/pasascope_gui.py
  # หรือ alias: python scripts/lingualens_gui.py
  ```
- **Desktop TUI (Terminal UI):**
  ```bash
  python scripts/pasascope_tui.py
  # หรือ alias: python scripts/lingualens_tui.py
  ```
  Supports live API mode and offline mock mode, V2 child profiles, multi-tier consent registration, and audio playback grant handling.

---

## 3. Clinical Trial Verification Checklist

Before attesting reports for pilot research cases:
1. **Consent Gate:** Verify that active patient consent is recorded (`clinical_assessment` purpose). For secondary research, verify `research_reuse` consent. If consent is withdrawn, all downstream processing stops immediately.
2. **Audio & Diarization Review:**
   - Use the **Dual-view Waveform** (Minimap overview + Detail zoom) to verify speaker turns (`CHI`, `INV`, `OTH`).
   - Use keyboard navigation (`Space` to play/pause, `Cmd+1..4` to assign speaker, `Cmd+L` to loop, `Cmd+Enter` to save edit).
   - Check optimistic concurrency status; any concurrent edits trigger an explicit conflict notification (`409 Conflict`).
   - Editing attested transcripts automatically marks downstream findings and draft reports as stale (Rule 9 invalidation) requiring re-attestation.
3. **Audio Waveform Integrity:** Ensure microphone levels remain within optimal LED segments (Green `-24` to `-12 dBFS`) without clipping alerts.
4. **Pragmatics Verification:** Review flagged Echolalia (verbatim vs mitigated) and Thai Pronoun Reversal (`เธอ`/`คุณ`) instances against the original recording before accepting narrative suggestions.
5. **Digital Attestation Stamp:** Sign-off generates a SHA-256 seal embedded in both the database record and the vector PDF export.

---

## 4. Clinical Safety & Non-Diagnostic Disclaimer

> [!WARNING]
> LinguaLens is a **decision-support research and educational prototype**. It does **not** provide automated autism spectrum diagnoses or replace standardized medical evaluations. All quantitative acoustic biomarkers, diarization boundaries, and AI-generated narratives serve strictly as observational aids requiring review and formal attestation by a licensed clinician.

