# LinguaLens Thai Tone-Aware Acoustic & Prosodic Specification
**Document Identifier:** `LL-SPEC-THAI-TONE-v1`  
**Document Date:** 2026-08-24  
**Status:** Methodological & Computational Acoustic Specification  
**Applies To:** Thai Pediatric Speech-Language Analysis (`language = "th"`)  

---

## 1. Linguistic Foundation: Lexical Tone vs. Affective Prosody

In non-tonal languages (such as English), pitch fundamental frequency ($F0$) variation primarily signals sentence-level intonation, emphasis, question marking, and emotional affect. 

In **Standard Thai**, $F0$ is dual-functional:
1. **Lexical Tone (Phonemic Contrast):** Differentiates word meanings across five tones:
   - Tone 0 (Mid / สามัญ): Flat mid-pitch contour ($\approx 33$).
   - Tone 1 (Low / เอก): Low-falling pitch contour ($\approx 21$).
   - Tone 2 (Falling / โท): High-rising then steep-falling contour ($\approx 51$).
   - Tone 3 (High / ตรี): High-rising or high-level contour ($\approx 45$).
   - Tone 4 (Rising / จัตวา): Low-dipping then rising contour ($\approx 24$).
2. **Affective / Interactional Prosody:** Modulates overall pitch baseline, phrase-final boundary tones, and turn-taking intonation.

**Core Methodological Principle:**  
*In Thai, unconditioned pitch variance (`pitch_f0_sd_semitones`) reflects lexical tone word choice in addition to affective prosody. LinguaLens therefore establishes a **Tone-Decomposed Acoustic Architecture**.*

---

## 2. Tone-Decomposed Acoustic Pipeline

```text
THAI SPEECH RECORDING
         │
         ▼
Syllable / Word Forced Alignment (Language = "th")
         │
         ▼
Lexical Tone Attribution (T0: Mid, T1: Low, T2: Falling, T3: High, T4: Rising)
         │
         ▼
Raw F0 Pitch Contour Extraction (YIN / pYIN / CREPE)
         │
         ▼
Speaker-Centered Normalization: s_st = 12 * log2(F0 / speaker_median_F0)
         │
         ├───────────────────────────────┬───────────────────────────────┐
         ▼                               ▼                               ▼
TONE-CONDITIONED TRAJECTORIES     TIME-NORMALIZED CONTOURS         TONE-RESIDUAL PROSODY
F0 start, mid, end, slope per     10-point normalized contour      Observed F0 minus
tone category (T0-T4)             (0%, 10%, ... 100% syllable)     Expected F0 for tone
```

---

## 3. Speaker-Centered Normalization Math

To enable cross-speaker comparison across male examiners, female examiners, and young children with high vocal pitch baselines:

$$s_{\text{speaker\_centered\_st}}(t) = 12 \times \log_2\left(\frac{F0(t)}{\text{Median}(F0_{\text{child\_voiced}})}\right)$$

Where $\text{Median}(F0_{\text{child\_voiced}})$ is the child's session-level median voiced pitch in Hz (minimum $1.0\text{ s}$ voiced speech required).

---

## 4. Syllable-Level Tone Representation Schema

For each eligible voiced syllable $k$:

| Field Name | Type | Operational Definition |
| :--- | :---: | :--- |
| `tone_category` | Enum | `T0_MID`, `T1_LOW`, `T2_FALLING`, `T3_HIGH`, `T4_RISING` |
| `syllable_duration_ms` | Float | Duration of voiced syllable segment in ms |
| `f0_start_st` | Float | Normalized semitones at 10% syllable duration |
| `f0_mid_st` | Float | Normalized semitones at 50% syllable duration |
| `f0_end_st` | Float | Normalized semitones at 90% syllable duration |
| `f0_slope_st_per_sec` | Float | Linear regression slope across voiced syllable points |
| `normalized_contour_10pt` | Array[10] | Interpolated F0 values at $[0\%, 10\%, \dots, 100\%]$ of duration |
| `context_onset_consonant` | Enum | `HIGH_CLASS`, `MID_CLASS`, `LOW_CLASS` |
| `context_vowel_length` | Enum | `SHORT_VOWEL`, `LONG_VOWEL` |
| `context_syllable_structure`| Enum | `LIVE_SYLLABLE` (คำเป็น), `DEAD_SYLLABLE` (คำตาย) |

---

## 5. Tone-Residual Prosodic Modeling (Research Feature)

To isolate pragmatic/affective prosody from lexical tone demands:

$$\text{ExpectedF0}(t \mid \text{tone}_c, \text{age}_m, \text{sex}, \text{block}) = \text{Population Mean Contour for Tone } c$$
$$\text{ResidualF0}(t) = \text{ObservedF0}(t) - \text{ExpectedF0}(t)$$

### Derived Tone-Residual Research Metrics:
- `residual_f0_sd`: Standard deviation of F0 after removing lexical tone trajectories.
- `residual_f0_range`: Dynamic pitch range unexplained by lexical tone requirements.
- `tone_target_undershoot_ratio`: Degree to which child fails to achieve canonical tone targets.

*Clinical Boundary:* Tone-residual metrics are designated as **Exploratory Research Candidates** and must never be used as automated clinical diagnostic scores.
