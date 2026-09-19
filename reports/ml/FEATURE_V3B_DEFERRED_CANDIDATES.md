# LinguaLens Feature Schema v3b: Deferred Acoustic Candidates
**Document Date:** 2026-08-24  
**Status:** Methodological Deferral & Technical Justification  
**Schema Scope:** Higher-Risk Acoustic & Complex Prosodic Candidates  

---

## 1. Executive Summary

To maintain measurement validity and prevent premature integration of unverified acoustic metrics, LinguaLens explicitly defers high-risk, noise-sensitive, and phoneme-dependent features from the core `features-acoustic-v3a` schema to `features-acoustic-v3b`.

Each deferred feature is listed below with the specific technical and clinical reasons for deferral, along with prerequisite research gates required for future adoption.

---

## 2. Inventory of Deferred Candidates & Deferral Rationale

### 1. Vowel Space Area (VSA) & Formant Dispersion (F1 / F2 / F3)
- **Proposed Construct:** Articulatory precision and vowel centralization.
- **Technical Dependencies:** Requires precise phoneme-level forced alignment (e.g. isolating steady-state mid-vowel frames for /i/, /u/, /a/) and vocal tract length normalization (e.g. Lobanov or Nearey scaling).
- **Deferral Reason:** High sensitivity to microphone frequency response and acoustic room coloration. Forced alignment on spontaneous pediatric child speech has high boundary error on vowel onsets.
- **Prerequisite Gate:** Empirical validation of formant tracking algorithms (e.g. Burg vs DeepFormants) on child speech with ground-truth acoustic phonetics.

### 2. Micro-Perturbation Measures (Jitter, Shimmer, HNR)
- **Proposed Construct:** Laryngeal stability and voice dysphonia / roughness.
- **Technical Dependencies:** Requires high SNR (> 30 dB), zero room reverberation, high sample rates ($\ge 44.1\text{ kHz}$), and sustained phonation (e.g. sustained vowel /a/).
- **Deferral Reason:** Highly unreliable on naturalistic conversational audio recorded with ambient room noise and moving microphones. Background toys, room echoes, and movement artifacts severely distort cycle-to-cycle perturbation calculations.
- **Prerequisite Gate:** Protocol-restricted sustained vowel elicitation task with standardized calibrated close-talk microphone.

### 3. Naive Prosodic Entrainment
- **Proposed Construct:** Dyadic vocal accommodation and pitch matching between child and examiner.
- **Technical Dependencies:** Requires speaker-normalized pitch trajectories, paired turn alignment, minimum dyadic turn count ($N \ge 15$), and outlier filtering.
- **Deferral Reason:** Simple Pearson correlation of raw child F0 and adult F0 ($r(\text{Child}_{F0}, \text{Adult}_{F0})$) is methodologically invalid because baseline pitch differs by speaker sex, age, and anatomical vocal fold length.
- **Prerequisite Gate:** Development of a speaker-standardized, turn-lagged cross-correlation or continuous wavelet transform entrainment metric validated on controlled dyadic interaction data.

### 4. Phoneme-Specific Articulation Rate & Formant Transition Slopes
- **Proposed Construct:** Motor speech coordination and co-articulation dynamics.
- **Technical Dependencies:** Accurate consonant-vowel transition boundary estimation.
- **Deferral Reason:** Requires language-specific phonetic aligners and extensive manual phonetic calibration.
- **Prerequisite Gate:** Multi-annotator gold phonetic timing validation on Thai and English pediatric speech corpora.

---

## 3. Summary Deferral Matrix

| Candidate Feature | Target Construct | Primary Technical Risk | Required Prerequisites Before Implementation |
| :--- | :--- | :--- | :--- |
| `vowel_space_area` | Articulatory precision | Formant tracking errors, vowel boundary drift | Validated phonetic forced alignment + vocal tract normalization |
| `jitter_local` | Vocal fold perturbation | Extreme sensitivity to room noise & reverberation | Sustained vowel task + calibrated head-mounted mic |
| `shimmer_local` | Vocal amplitude stability | Highly corrupted by distance-to-mic variations | Standardized acoustic environment + fixed mic distance |
| `hnr_mean_db` | Glottal noise / breathiness | Unreliable in naturalistic conversational audio | Calibrated acoustic environment |
| `prosodic_entrainment` | Dyadic vocal synchrony | Inadequate construct validity if unnormalized | Speaker-centered, turn-lagged dyadic modeling framework |
