# LinguaLens Acoustic Timing & Alignment Provider Comparison
**Document Date:** 2026-08-24  
**Status:** Methodological Provider Benchmark Specification  
**Applies To:** WhisperX, Montreal Forced Aligner (MFA), Silero VAD + PyAnnote  

---

## 1. Provider Candidates & Architectural Roles

Rather than forcing a single automated engine to handle all speech processing tasks, LinguaLens evaluates three specialized acoustic timing pipelines against human gold annotations:

```text
┌───────────────────────────┬───────────────────────────┬───────────────────────────┐
│        PROVIDER A         │        PROVIDER B         │        PROVIDER C         │
│     VAD + Diarization     │      WhisperX CTC ASR     │      MFA Forced Aligner   │
│  (Silero + PyAnnote 3.1)  │ (Whisper + Phoneme Align) │  (Acoustic HMM/DNN-GOP)   │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ Primary Role:             │ Primary Role:             │ Primary Role:             │
│ Turn-taking boundaries &  │ Automated transcription & │ Precise phonetic & vowel  │
│ response latency timing   │ exploratory word alignment│ boundary alignment        │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ Key Advantage:            │ Key Advantage:            │ Key Advantage:            │
│ Independent of ASR WER;   │ End-to-end transcript +   │ Maximum phonetic boundary │
│ works on non-lexical turns│ word-level timestamps     │ precision on gold text    │
├───────────────────────────┼───────────────────────────┼───────────────────────────┤
│ Limitation:               │ Limitation:               │ Limitation:               │
│ No word/phone boundaries  │ ASR hallucination risks;  │ Requires pre-existing gold│
│                           │ high GPU memory demand    │ transcript & dictionary   │
└───────────────────────────┴───────────────────────────┴───────────────────────────┘
```

---

## 2. Evaluation Matrix for Gold Benchmark Testing

When human gold annotations are available, all three candidate pipelines will be evaluated on the identical locked benchmark:

| Evaluation Metric | Provider A (VAD + Diarization) | Provider B (WhisperX) | Provider C (MFA Aligner) | Target Empirical Threshold |
| :--- | :---: | :---: | :---: | :---: |
| **Onset Boundary MAE (ms)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $< 60\text{ ms}$ |
| **Offset Boundary MAE (ms)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $< 80\text{ ms}$ |
| **Response Latency MAE (ms)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $< 100\text{ ms}$ |
| **95th Percentile Error (ms)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $< 250\text{ ms}$ |
| **Catastrophic Failure Rate ($> 250\text{ ms}$)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $< 5.0\%$ |
| **Boundary Coverage (% valid)** | *Pending Gold Evaluation* | *Pending Gold Evaluation* | *Pending Gold Evaluation* | $> 95.0\%$ |
| **Hardware Requirement** | CPU Friendly (~1.5 GB RAM) | GPU Preferred (4–8 GB VRAM) | CPU / RAM Moderate | Operational Feasibility |

---

## 3. Provider Selection & Functional Modularization Policy

**Policy Principle:**  
*Empirical evidence shall dictate provider assignment. If no single tool dominates across all domains, LinguaLens shall adopt a multi-provider functional division:*

1. **Turn-Taking & Conversational Latency:** Computed via **Provider A (VAD + Diarization)** to prevent speech recognition errors from corrupting timing measurements.
2. **Research transcript candidate:** Evaluate **Provider B (WhisperX)** offline. No provider is assigned to the therapist-product transcript path by this research document.
3. **Phonetic & Tone Trajectory Extraction (Block T):** Handled via **Provider C (Language-specific Forced Alignment)** when scripted gold lexical tokens are available.
