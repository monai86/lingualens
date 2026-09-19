# LinguaLens Phase 4 Baseline Verification Report
**Verification Date:** 2026-08-24  
**Author:** LinguaLens Scientific ML Audit Team  
**Status:** Historical checkpoint reconciled on 2026-08-26; not a clinical-readiness approval  

---

## 1. Environment & Provenance Record

| Component | Verified Specification |
| :--- | :--- |
| **Git Commit Hash** | `3278cd6d995a763fe94dee741a64089b2f226d32` |
| **Git Branch** | `main` |
| **Python Runtime** | `3.13.12` / `3.12.13` (Production supported) |
| **scikit-learn** | `1.8.0` |
| **NumPy** | `2.4.4` |
| **Pandas** | `3.0.2` |
| **PyTorch / Silero** | `2.x` |
| **Global Random Seed** | `42` |

---

## 2. Feature Schema & Benchmark Freeze Audit

1. **Feature Schema v1 (`features-basic-v1`):**
   - 14 canonical features (13 non-age linguistic features + `age_months`).
   - Frozen benchmark at `data/ml/results/baseline_v1_frozen.csv`.
   - **Reproducibility Delta:** Exactly **0.0000** across all 6 domain-controlled experiments.
2. **Feature Schema v2 (`features-conversation-v2`):**
   - V2 adds 8 conversational fields; the benchmark uses 21 non-age inputs (13 v1 + 8 v2), while the local export has 22 numeric fields including `age_months`.
   - Fully extracted across **1,961 analysis-ready transcripts** in `data/ml/canonical_features_v2.parquet` with **0 missing values**.
   - Retained as a descriptive offline research candidate; not integrated into therapist-facing product paths.
3. **Feature Schema v3a (`features-acoustic-v3a`):**
   - Prospective research helpers exist in `packages/features/acoustic_features.py`; they are not wired into the therapist API or product artifact path.
   - Focused measurement tests cover formulas and insufficiency behavior; empirical measurement validation remains pending.
4. **Project Verification Suite:**
   - Python core tests: **834/834 passed**.
   - Frontend Vitest suites: **512/512 passed**.
   - Next.js production build: **Clean (0 errors)**.

---

## 3. Phase 4 Readiness Gate

The Phase 3 files remain an internal comparison checkpoint. Phase 4 work is exploratory and may change candidate extractors under versioned tests; it does not establish clinical validity or production readiness.
