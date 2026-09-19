# LinguaLens Feature Schema v3a (Acoustic & Timing) Specification
**Schema Identifier:** `features-acoustic-v3a`  
**Schema Version:** 3.0.0-PROSPECTIVE-RESEARCH  
**Document Date:** 2026-08-24  
**Status:** Prospective research helper specification; not product-integrated  

---

## 1. Overview & Architectural Principles

Feature Schema v3a (`features-acoustic-v3a`) introduces a compact, lower-risk set of acoustic timing and prosodic measurements designed to overcome the temporal blindness of text-only CHAT transcripts.

### Core Principles:
1. **Additive Composition:** v3a is specified as a future addition to v1 (13 non-age fields plus `age_months`) and the 8 v2 conversational fields without altering those calculations.
2. **Quality-Aware Representation:** Every numerical feature is coupled with measurement support metrics (e.g. `n_pairs`, `valid_fraction`) and a deterministic `QualityStatus`.
3. **No Silent Zero Imputation:** If insufficient data exist (e.g. 0 turn transitions), features evaluate to `NaN` with status `INSUFFICIENT_DATA`. **Zero is never imputed for unavailable measurements.**
4. **Integration Boundary:** These helpers are not wired into the therapist API or product artifact path. Product parity requires a separately reviewed future integration.

---

## 2. Quality Status Vocabulary

Every acoustic feature group outputs an accompanying `quality_status` enum:

- `VALID`: Measurement meets all empirical sufficiency thresholds.
- `INSUFFICIENT_DATA`: Too few valid segments or turn pairs to compute a meaningful statistic.
- `LOW_VOICED_COVERAGE`: Less than 1.0 second of valid voiced frames or $< 30\%$ voiced fraction in child speech.
- `LOW_ALIGNMENT_COVERAGE`: Forced-alignment confidence or coverage is too low for reliable millisecond timing.
- `DIARIZATION_UNCERTAIN`: Speaker role assignment has low confidence or high overlap confusion.
- `UNSUPPORTED_AUDIO`: Sample rate $< 16\text{ kHz}$ or corrupted audio frames.
- `NOT_AVAILABLE`: Audio recording not provided for this session.

---

## 3. Comprehensive Feature Specification Table

| Field Name | Construct | Exact Mathematical Formula | Input Required | Timing / Source | Speaker Dependency | Normalization | Min Denominator | Valid Range | Missing / Insufficient Behavior | Implementation Status | Validation Status | Production Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `response_latency_median_ms` | Conversational timing / processing | $\text{Median}(\{t_{\text{child\_onset}}^{(i)} - t_{\text{adult\_offset}}^{(i)}\}_{i=1}^N)$ | VAD / Diarized turn boundaries | Acoustic boundary timestamps | Dyadic (Adult $\rightarrow$ Child transition) | Raw milliseconds | $N \ge 5$ valid pairs | $[-2000, 10000]$ ms | `NaN` + `INSUFFICIENT_DATA` | **RESEARCH HELPER** | MEASUREMENT_PENDING | NOT_INTEGRATED |
| `response_latency_iqr_ms` | Turn-taking latency variability | $\text{IQR}(\{t_{\text{child\_onset}}^{(i)} - t_{\text{adult\_offset}}^{(i)}\}_{i=1}^N)$ | VAD / Diarized turn boundaries | Acoustic boundary timestamps | Dyadic (Adult $\rightarrow$ Child transition) | Milliseconds ($Q_{75} - Q_{25}$) | $N \ge 5$ valid pairs | $[0, 10000]$ ms | `NaN` + `INSUFFICIENT_DATA` | **RESEARCH HELPER** | MEASUREMENT_PENDING | NOT_INTEGRATED |
| `response_latency_n_pairs` | Timing measurement support | $N = \sum \mathbb{I}(\text{valid adult}\rightarrow\text{child turn pair})$ | Diarized turn sequence | Acoustic boundaries | Dyadic | Count | None | $\ge 0$ | `0` + grouped `INSUFFICIENT_DATA` | **RESEARCH HELPER** | UNIT_TESTED | NOT_INTEGRATED |
| `pitch_f0_sd_semitones` | Intonational pitch variation | $\sqrt{\frac{1}{M}\sum_{j=1}^M (s_j - \bar{s})^2}$ where $s_j = 12 \log_2(F0_j / 50.0)$ | Voiced child speech frames | F0 pitch tracking (YIN / pYIN / CREPE) | Child-Intrinsic | Semitones (Ref: $50.0\text{ Hz}$) | $\ge 1.0\text{ s}$ and $\ge 30\%$ voiced coverage | $[0.0, 24.0]$ ST | `NaN` + `LOW_VOICED_COVERAGE` | **RESEARCH HELPER** | MEASUREMENT_PENDING | NOT_INTEGRATED |
| `pitch_range_90_10_semitones` | Dynamic pitch excursion | $P_{90}(s) - P_{10}(s)$ where $s = 12 \log_2(F0 / 50.0)$ | Voiced child speech frames | F0 pitch tracking | Child-Intrinsic | Semitones (90th - 10th percentile) | $\ge 1.0\text{ s}$ and $\ge 30\%$ voiced coverage | $[0.0, 36.0]$ ST | `NaN` + `LOW_VOICED_COVERAGE` | **RESEARCH HELPER** | MEASUREMENT_PENDING | NOT_INTEGRATED |
| `pitch_valid_fraction` | Pitch extraction quality | $\text{Voiced frames count} / \text{Total child speech frames}$ | Child speech segments | F0 voicing confidence | Child-Intrinsic | Proportion | $\ge 1.0\text{ s}$ total child speech | $[0.0, 1.0]$ | $0.0$ + `LOW_VOICED_COVERAGE` | **RESEARCH HELPER** | UNIT_TESTED | NOT_INTEGRATED |
| `pause_duration_ratio` | Within-turn speech planning | $\frac{\sum \text{within-child-turn pauses} \ge 200\text{ms}}{\text{Total detected child speech duration}}$ | VAD boundaries within child turns | VAD silence detector | Child-Intrinsic | Proportion of detected speech time | $\ge 3.0\text{ s}$ detected child speech | $[0.0, 1.0]$ | `NaN` + `INSUFFICIENT_DATA` | **RESEARCH HELPER** | MEASUREMENT_PENDING | NOT_INTEGRATED |
| `overlap_rate` | Dyadic speech collision | $\frac{\text{Total overlap speech duration}}{\text{Total session speech duration}}$ | Multi-speaker diarization | Diarization overlap segments | Dyadic | Proportion | $\ge 10.0\text{ s}$ total speech | $[0.0, 1.0]$ | `NaN` + `DIARIZATION_UNCERTAIN` | **PROPOSED** | MEASUREMENT_PENDING | RESTRICTED |
| `articulation_rate_sps` | Motor speech pace | $\frac{\text{Estimated Syllables}}{\text{Phonated child speech seconds}}$ | Forced alignment / Envelope peak detector | Phone alignment + Audio envelope | Child-Intrinsic | Syllables per second | $\ge 3.0\text{ s}$ phonated speech | $[0.5, 10.0]$ sps | `NaN` + `LOW_ALIGNMENT_COVERAGE` | **PROPOSED** | MEASUREMENT_PENDING | RESTRICTED |

---

## 4. Operational Formulations & Handling Rules

### Response Latency Math
For every eligible adult turn $k$ ending at $t_{\text{adult\_offset}}^{(k)}$ where the immediately subsequent turn is a child turn starting at $t_{\text{child\_onset}}^{(k)}$:
$$\text{latency}_k = t_{\text{child\_onset}}^{(k)} - t_{\text{adult\_offset}}^{(k)}$$
- **Positive Latency ($\text{latency} > 0$):** Silence / conversational gap.
- **Zero Latency ($\text{latency} \approx 0$):** Immediate smooth transition.
- **Negative Latency ($\text{latency} < 0$):** Child began speaking before adult finished (overlap). **Negative values are preserved and NOT truncated to zero.**
- *Boundary Exclusion:* If $t_{\text{child\_onset}}^{(k)} - t_{\text{adult\_offset}}^{(k)} > 10,000\text{ ms}$, the transition is treated as an isolated interaction break rather than a conversational turn response and is excluded from latency calculations.

### Semitone Transformation
Pitch fundamental frequency $F0$ (in Hz) is converted to semitones relative to a standardized $50.0\text{ Hz}$ base reference:
$$s_j = 12 \times \log_2\left(\frac{F0_j}{50.0}\right)$$
This log-scale transformation standardizes pitch intervals across children with varying vocal pitch baselines.

---

## 5. Thai Language Adaptations

1. **Lexical Tone vs Prosodic Variation:** In Thai, pitch trajectories carry lexical phonemic tone distinctions (e.g. Mid, Low, Falling, High, Rising). Pitch variance (`pitch_f0_sd_semitones`) will therefore reflect both lexical tone distributions and affective intonation.
2. **Mandatory Rule:** English-derived pitch variance normative cutoffs shall never be applied to Thai speech samples without Thai language-specific calibration and normative reference validation.
