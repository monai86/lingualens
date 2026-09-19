# LinguaLens Audio Quality Control (QC) & Provenance Specification
**Document Date:** 2026-08-24  
**Status:** Canonical Audio Measurement Specification  
**Applies To:** `src/audio_pipeline/`, `packages/features/acoustic_features.py`, `apps/api/`

---

## 1. Architectural Principles

```text
ORIGINAL AUDIO RECORDING (Immutable Source Asset)
   │
   ├─ Recorded Metadata: audio_sha256, format, channels, sr, bit_depth
   │
   ▼
AUDIO INTAKE & CONTINUOUS QC
   │
   ├───────────────────────────────┬───────────────────────────────┐
   ▼                               ▼                               ▼
TIMING / SPEAKER LAYER       LEXICAL ALIGNMENT LAYER       ACOUSTIC SIGNAL LAYER
- VAD Speech Boundaries      - Forced Alignment Offsets    - F0 Pitch Contour
- Diarization Segments       - Word / Phone Timings        - Intensity & Energy
- Overlap Detection          - Lexical Word Tokens         - Pause Duration
   │                               │                               │
   └───────────────────────────────┼───────────────────────────────┘
                                   ▼
                      FEATURE AGGREGATION (v3a)
                                   ▼
                       MEASUREMENT QUALITY GATE
                                   ▼
                        `features-acoustic-v3a`
```

1. **Non-Destructive Storage:** The original audio asset is never overwritten or destructively converted. It is stored as an immutable master record with SHA-256 integrity verification.
2. **Analysis Derivatives:** When 16 kHz mono conversion is required by downstream tools (e.g. VAD or forced aligners), an explicit derivative file is generated while preserving original multichannel / high-resolution source audio.
3. **Continuous QC Metrics:** Rather than imposing arbitrary hard exclusions (e.g. dropping audio if SNR < 15 dB), all QC indicators are measured continuously to enable empirical noise-tolerance studies.

---

## 2. Continuous Audio QC Metric Suite

Every processed audio file produces an auditable `AudioQCRecord` containing the following continuous metrics:

| Metric Name | Type | Formula / Operational Definition | Valid Range |
| :--- | :---: | :--- | :---: |
| `duration_seconds` | Float | Total audio recording duration | $> 0.0$ |
| `sample_rate_hz` | Int | Sampling frequency of the audio asset | $\ge 16000$ |
| `channel_count` | Int | Number of audio channels (1 = mono, 2 = stereo) | $\ge 1$ |
| `clipping_fraction` | Float | Fraction of audio samples where amplitude $\ge 0.999 \times \text{max\_val}$ | $[0.0, 1.0]$ |
| `silence_fraction` | Float | Fraction of time with RMS amplitude below noise floor threshold | $[0.0, 1.0]$ |
| `speech_fraction` | Float | Total detected speech time (VAD) / `duration_seconds` | $[0.0, 1.0]$ |
| `estimated_snr_db` | Float | $10 \log_{10}(\text{RMS}_{\text{speech}}^2 / \text{RMS}_{\text{noise}}^2)$ | $[-10.0, 60.0]$ |
| `valid_child_speech_sec` | Float | Total phonated speech duration assigned to Child | $\ge 0.0$ |
| `valid_adult_speech_sec` | Float | Total phonated speech duration assigned to Adult | $\ge 0.0$ |
| `overlap_fraction` | Float | Duration of concurrent multi-speaker speech / `duration_seconds` | $[0.0, 1.0]$ |

---

## 3. Audio Provenance & Metadata Record

For every audio processing run, a JSON provenance record is committed alongside extracted features:

```json
{
  "audio_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "original_asset": {
    "format": "WAV",
    "codec": "pcm_s24le",
    "sample_rate_hz": 48000,
    "channels": 2,
    "bit_depth": 24,
    "duration_seconds": 1245.32
  },
  "analysis_derivative": {
    "format": "WAV",
    "sample_rate_hz": 16000,
    "channels": 1,
    "conversion_version": "resample_soxr_v1"
  },
  "qc_metrics": {
    "clipping_fraction": 0.00002,
    "silence_fraction": 0.284,
    "speech_fraction": 0.716,
    "estimated_snr_db": 22.4,
    "valid_child_speech_sec": 312.4,
    "valid_adult_speech_sec": 482.1,
    "overlap_fraction": 0.042
  },
  "qc_status": "VALID",
  "consent_gate_verified": true
}
```

---

## 4. Privacy, Consent & Storage Boundaries

1. **Consent Verification:** Audio files are processed only if `consent_status == "ACTIVE"`. If consent is revoked, all raw and intermediate audio derivatives are purged immediately from storage.
2. **Local Browser Isolation:** Raw audio bytes are never permanently cached in client browser storage (`localStorage` / `IndexedDB`).
3. **De-Identification:** Audio derivative filenames use random UUIDs (`audio_uuid.wav`) and do not embed child names, hospital IDs, or clinical dates.
