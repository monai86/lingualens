# LinguaLens Speech Boundary & Forced Alignment Validation Protocol
**Protocol Date:** 2026-08-24  
**Status:** Methodological Validation Standard  
**Applies To:** WhisperX, Montreal Forced Aligner (MFA), PyAnnote Diarization, Silero VAD  

---

## 1. Empirical Timing Measurement Mandate

In child speech analysis, academic literature often quotes forced-alignment accuracy of "±20 ms". However, in naturalistic pediatric interactions (characterized by disfluencies, whispering, overlapping turns, and high vocal tract fundamental frequencies), automated alignment error can exceed 150–300 ms.

**Mandatory Rule:**  
*LinguaLens shall NEVER state or assume a fixed alignment accuracy (e.g. "±20 ms") without empirical measurement on human-annotated pediatric gold benchmarks.*

---

## 2. Alignment Paths Architecture

```text
               AUDIO INPUT (+ Optional Transcript)
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
   [PATH A]                [PATH B]                [PATH C]
Gold Transcript         Audio-Only Session      Timing-Only
+ Audio                 (No Gold Script)        (Response Latency)
       │                       │                       │
Montreal Forced         WhisperX ASR            Silero VAD /
Aligner (MFA)           + Word Alignment        PyAnnote Diarization
       │                       │                       │
       ▼                       ▼                       ▼
Phone/Word Timings      ASR + Timings           Speaker Turn Boundaries
(Max Acoustic Precision)(Exploratory Elicitation)(Lexical-Independent)
```

1. **Path A (Gold Transcript + Audio):** Uses text-constrained forced alignment (e.g. MFA or Wav2Vec2 alignment). Ideal for standardized narrative or picture tasks where lexical ground truth is known.
2. **Path B (Audio Without Transcript):** Uses ASR (WhisperX) followed by phoneme-level CTC alignment. Subject to WER and hallucination risks.
3. **Path C (Timing-Only Independent Path):** Computes turn transitions and response latencies directly from validated VAD and diarization acoustic boundaries **without requiring correct lexical ASR transcription**. This prevents speech recognition errors from corrupting conversational timing measurements.

---

## 3. Human Gold Annotation Benchmarks

To establish ground-truth timing accuracy, LinguaLens uses a standardized manual annotation protocol on a representative subset of pediatric audio samples spanning:
- High SNR (> 25 dB) vs Low SNR (< 12 dB)
- Overlapping speech segments
- Child whisper / vocal play
- Rapid turn transitions (< 200 ms latency) vs Long pauses (> 2000 ms latency)

### Gold Annotation Template Structure:
Stored at `data/ml/validation/audio_alignment_gold_template.csv`.

| Field Name | Type | Description |
| :--- | :---: | :--- |
| `audio_id` | String | Unique hash/ID of the audio asset |
| `segment_id` | String | Sequential segment identifier within recording |
| `speaker_role` | String | Ground-truth speaker (`CHILD`, `ADULT`, `OTHER`, `OVERLAP`) |
| `manual_onset_ms` | Float | Millisecond speech onset marked by human phoneticians |
| `manual_offset_ms` | Float | Millisecond speech offset marked by human phoneticians |
| `automatic_onset_ms` | Float | Millisecond onset predicted by automated pipeline |
| `automatic_offset_ms` | Float | Millisecond offset predicted by automated pipeline |
| `boundary_type` | String | `TURN_TRANSITION`, `WITHIN_TURN_PAUSE`, `ISOLATED_UTTERANCE` |
| `overlap` | Boolean | True if multiple speakers active concurrently |
| `annotator_id` | String | De-identified phonetic annotator ID |
| `notes` | String | Clinical phonetic notes (e.g. "whisper", "toy noise") |

---

## 4. Evaluation Metrics for Boundary & Diarization Precision

When gold annotations are compared against automated pipeline outputs, the following validation metrics are computed:

1. **Onset Absolute Error:** $\Delta_{\text{onset}} = |\text{automatic\_onset\_ms} - \text{manual\_onset\_ms}|$
2. **Offset Absolute Error:** $\Delta_{\text{offset}} = |\text{automatic\_offset\_ms} - \text{manual\_offset\_ms}|$
3. **Median Absolute Error (MAE):** Robust central tendency of boundary deviation.
4. **95th Percentile Error:** Captures catastrophic alignment failures.
5. **Catastrophic Failure Rate:** Percentage of boundaries with error $> 250\text{ ms}$.
6. **Diarization Error Rate (DER):** Standardized NIST DER evaluating Speaker Confusion, Missed Speech, and False Alarm Speech.
7. **Response Latency Error:** Absolute error of the adult-offset $\rightarrow$ child-onset interval ($|\text{Latency}_{\text{auto}} - \text{Latency}_{\text{manual}}|$).

**Quality Threshold Rule:**  
If the 95th percentile response latency measurement error exceeds the clinical effect size under study (e.g. median error $> 200\text{ ms}$), the corresponding acoustic timing features must be marked as `UNRELIABLE_MEASUREMENT` and withheld from predictive modeling.
