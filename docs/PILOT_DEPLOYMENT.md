# LinguaLens Clinical Pilot Deployment & Operational Guide

This document outlines the deployment and local execution workflows for the **LinguaLens v1.6.3** speech-language assessment decision-support system during clinical evaluator trials.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Clinician Workstation                    │
├──────────────────────────────┬──────────────────────────────┤
│    Next.js Web Workbench    │      Desktop Power Tool      │
│  http://localhost:3000       │      (Tkinter / macOS)       │
│  • AI Assistant (/assistant) │  • Waveform Audio Slicing    │
│  • 5-Tab Canonical Workflow  │  • Radar & Growth Corridors  │
│  • Modern Flat Light UI      │  • Print-ready Vector PDF    │
└───────────────┬──────────────┴───────────────┬──────────────┘
                │                              │
                └──────────────┬───────────────┘
                               │ JSON REST API
                ┌──────────────▼───────────────┐
                │       FastAPI Backend        │
                │  http://127.0.0.1:8000       │
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

### Option C: Desktop GUI Power Tool
For standalone clinical workstation speech analysis, audio waveform slicing, and PDF export:
```bash
python scripts/lingualens_gui.py
```

---

## 3. Clinical Trial Verification Checklist

Before attesting reports for pilot research cases:
1. **Consent Gate:** Verify patient consent status is active for clinical decision support.
2. **Audio Waveform Integrity:** Ensure microphone levels remain within optimal LED segments (Green `-24` to `-12 dBFS`) without clipping alerts.
3. **Pragmatics Verification:** Review flagged Echolalia (verbatim vs mitigated) and Thai Pronoun Reversal (`เธอ`/`คุณ`) instances against the original recording before accepting narrative suggestions.
4. **Digital Attestation Stamp:** Sign-off generates a SHA-256 seal embedded in both the database record and the vector PDF export.

---

## 4. Clinical Safety & Non-Diagnostic Disclaimer

> [!WARNING]
> LinguaLens is a **decision-support research and educational prototype**. It does **not** provide automated autism spectrum diagnoses or replace standardized medical evaluations. All quantitative biomarkers and AI-generated narratives require review and formal attestation by a licensed clinician.
