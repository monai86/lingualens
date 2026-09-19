# Human Action Checklist: Gold Timing & Phonetic Annotation
**Document Identifier:** `LL-ACTION-GOLD-TIMING-v1`  
**Document Date:** 2026-08-24  
**Target Audience:** Principle Investigators, Phonetic Annotators, and Clinical Research Coordinators  

---

## 1. Explicit Boundaries: What AI / Codex CANNOT Do

Under LinguaLens scientific governance, the AI assistant (Codex/Antigravity) is strictly prohibited from fabricating or simulating human clinical judgments. The following actions **MUST be performed by qualified human professionals**:

- [ ] **Annotator Recruitment & Credentialing:** Selecting and credentialing trained phonetic annotators (e.g. SLP graduate students or phoneticians).
- [ ] **Ethics & IRB Verification:** Verifying data-use permissions, child assent, and caregiver consent before acoustic inspection.
- [ ] **Acoustic Listening & Annotation:** Listening to raw pediatric recordings in Praat / ELAN and marking auditory-acoustic onsets and offsets.
- [ ] **Clinical Boundary Judgments:** Deciding whether an ambiguous vocalization is non-speech crying vs vegetative grunt vs lexical speech.
- [ ] **Entering Reference Gold Data:** Populating the manual timing columns in `data/ml/validation/audio_alignment_gold_template.csv`.
- [ ] **Expert Disagreement Adjudication:** Reviewing boundary discrepancies ($> 100\text{ ms}$) between Annotator A and Annotator B and making final adjudications.
- [ ] **Approving Clinical Measurement-Error Thresholds:** Establishing whether observed MAE is clinically acceptable for diagnostic screening.

---

## 2. Step-by-Step Instructions for the Human Research Team

```text
Human Annotation Workflow
├── Step 1: Calibration Phase (5-8 Practice Audio Files)
│   ├── Annotators A & B jointly annotate calibration files in Praat
│   └── Reconcile interpretation of disfluencies and whispers
├── Step 2: Independent Blinded Annotation (20-30 Validation Files)
│   ├── Annotator A marks onset/offset in TextGrid Tier 1 & 2
│   └── Annotator B independently marks same files in blinded TextGrid
├── Step 3: Run Agreement Script
│   └── Execute: `python3 scripts/ml/evaluate_alignment_gold.py --check-agreement`
├── Step 4: Senior Adjudication
│   └── Senior phonetician reviews segments where |Diff| > 100 ms
└── Step 5: Lock Master Gold Reference
    └── Commit adjudicated CSV to `data/ml/validation/`
```

---

## 3. Human Sign-Off Form

| Task | Responsible Role | Name / ID | Date Completed | Signature / Status |
| :--- | :--- | :--- | :---: | :---: |
| **Annotator Calibration** | Lead Phonetician | | | [ ] COMPLETED |
| **Annotator A Coding** | Annotator A | | | [ ] COMPLETED |
| **Annotator B Coding** | Annotator B | | | [ ] COMPLETED |
| **Senior Adjudication** | Senior Phonetician | | | [ ] COMPLETED |
| **Gold Dataset Freeze** | Principal Investigator | | | [ ] LOCKED |
