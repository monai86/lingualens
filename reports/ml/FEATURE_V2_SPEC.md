# LinguaLens Feature Schema v2 Specification (`features-conversation-v2`)
**Specification Date:** 2026-08-23  
**Status:** Canonical & Additive (100% Backward Compatible with `features-basic-v1`)  

---

## 1. Feature Definition & Mathematical Specification Table

| Feature Name | Clinical / Communication Construct | Exact Formula | Required CHAT Input | Expected Range | Known Confounders | Decision |
| :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| `speaker_balance_ratio` | Relative conversational participation | $\frac{\text{CHI utterances}}{\text{CHI utts} + \text{Adult utts}}$ | Speaker codes & utterance counts | $[0.0, 1.0]$ | Examiner chattiness | **IMPLEMENT** |
| `turn_alternation_rate` | Reciprocal conversational switching | $\frac{\text{Speaker transitions}}{\text{Total adjacent utterance pairs } (N - 1)}$ | Chronological utterance sequence | $[0.0, 1.0]$ | Monologue vs dialogue tasks | **IMPLEMENT** |
| `child_run_length_mean` | Tendency for unprompted multi-utterance runs | $\frac{\sum \text{len(contiguous CHI runs)}}{\text{Count of CHI runs}}$ | Chronological speaker sequence | $[1.0, \infty)$ | Non-responsive examiner | **IMPLEMENT** |
| `child_response_rate` | Immediate response to an adult utterance | $\frac{\text{Adult utterances immediately followed by CHI}}{\text{All adult utterances}}$ | Ordered utterance sequence; same-speaker continuation and terminal adult utterance count as non-response | $[0.0, 1.0]$ | Examiner utterance frequency and protocol | **IMPLEMENTED / DESCRIPTIVE ONLY** |
| `adult_response_rate` | Immediate partner response (context control) | $\frac{\text{CHI utterances immediately followed by Adult}}{\text{All CHI utterances}}$ | Ordered utterance sequence; same-speaker continuation and terminal child utterance count as non-response | $[0.0, 1.0]$ | Examiner protocol constraints | **IMPLEMENTED / DESCRIPTIVE ONLY** |
| `partner_repetition_exact_ratio` | Immediate verbatim partner echo | $\frac{\text{CHI responses identical to adult prompt}}{\text{Total CHI responses to adult}}$ | Normalized content tokens on adjacent turns | $[0.0, 1.0]$ | Prompt simplicity (e.g. "say cat") | **IMPLEMENT** |
| `partner_repetition_overlap_mean` | Lexical borrowing / partial partner repetition | $\frac{1}{K} \sum \frac{|\text{Tokens}_{\text{CHI}} \cap \text{Tokens}_{\text{Adult}}|}{|\text{Tokens}_{\text{CHI}} \cup \text{Tokens}_{\text{Adult}}|}$ | Normalized content tokens on adjacent turns | $[0.0, 1.0]$ | Shared toy vocabulary | **IMPLEMENT** |
| `self_repetition_exact_ratio` | Perseverative intra-child self-repetition | $\frac{\text{CHI utts identical to child's previous utt}}{\text{Total adjacent CHI-CHI pairs}}$ | Normalized content tokens on adjacent CHI tiers | $[0.0, 1.0]$ | Single-word play vocatives | **IMPLEMENT** |
| `response_latency_median_sec` | Response latency & conversational hesitation | Median gap in ms between Adult end and CHI start | Precise turn-level millisecond timestamps | $[0.0, 30.0\text{s}]$ | Missing timestamps in older CHAT data | **DEFERRED (v3)** |
| `overlap_interruption_rate` | Overlapping speech & conversational turn collision | $\frac{\text{Overlapping utterances}}{\text{Total utterances}}$ | Standardized `[<]`, `[>]` CHAT overlap tags | $[0.0, 1.0]$ | Inconsistent transcription coding across sites | **DEFERRED** |

---

## 2. Denominator Safeguards & Edge Cases

1. **Single-Speaker Transcript (e.g., child monologue or missing adult tier):**
   - `adult_utterances = 0` $\rightarrow$ `speaker_balance_ratio = 1.0`, `turn_alternation_rate = 0.0`, `child_response_rate = 0.0`, `adult_response_rate = 0.0`, `partner_repetition_exact_ratio = 0.0`, `partner_repetition_overlap_mean = 0.0`.
2. **Missing Child Tier / Zero Child Utterances:**
   - `child_utterances = 0` $\rightarrow$ all ratios return `0.0`, `child_run_length_mean = 0.0`.
3. **Short Transcripts ($< 2$ utterances):**
   - $N < 2 \rightarrow$ `turn_alternation_rate = 0.0`, `child_run_length_mean = float(total_child_utterances)`.
4. **Empty Tokens on Punctuation-Only Utterances:**
   - Handled cleanly by stripping punctuation tokens; empty sets yield Jaccard similarity `0.0`.
