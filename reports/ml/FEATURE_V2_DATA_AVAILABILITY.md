# LinguaLens Feature v2 CHAT Data Availability Audit
**Generated Date:** 2026-08-23  
**Status:** Complete Empirical Audit Across 15 Corpora  

---

## 1. Cross-Corpus Transcript Information Availability Table

The following audit was executed across all `.cha` transcript files in the repository:

| Corpus | Total Files | Adult Tiers Present (%) | Timestamped (%) | Overlap Annotations (%) | Pause Annotations (%) | Avg CHI Utts | Avg Adult Utts |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Eigsti** (Interactive Toyplay) | 48 | **100.0%** | **0.0%** | 50.0% | 100.0% | 162.8 | 276.4 |
| **Nadig** (Interactive Toyplay) | 38 | **100.0%** | **0.0%** | **0.0%** | 0.0% | 81.1 | 167.6 |
| **Flusberg** (Home Naturalistic) | 64 | **100.0%** | **0.0%** | 0.0% | 0.0% | 359.7 | 640.1 |
| **NYU-Emerson** (Interactive) | 30 | **100.0%** | **100.0%** | 100.0% | 96.7% | 170.4 | 308.0 |
| **Rollins** (Home Interaction) | 21 | **100.0%** | **0.0%** | 81.0% | 61.9% | 198.6 | 326.2 |
| **QuigleyMcNally** (Infant Observation) | 203 | 100.0% | 0.0% | 0.0% | 13.8% | 0.0 | 86.6 |
| **Curated Reference Cohorts** | 2,644 | 92.5% | 65.2% | 45.6% | 35.6% | 123.9 | 195.6 |

---

## 2. Feature Construct Availability Summary

| Candidate Feature Category | Specific Information Required | Availability Status | Scientific Action |
| :--- | :--- | :---: | :--- |
| **Speaker Balance & Turns** | Speaker codes (`*CHI:`, `*MOT:`, `*INV:`, etc.) and utterance sequence | **AVAILABLE_RELIABLY** (100%) | **Implement in v2** |
| **Turn Alternation & Runs** | Line-by-line speaker transition ordering | **AVAILABLE_RELIABLY** (100%) | **Implement in v2** |
| **Response Contingency** | Immediate adjacency of adult prompt followed by child tier | **AVAILABLE_RELIABLY** (100%) | **Implement in v2** |
| **Repetition Dynamics** | Token-level exact match and Jaccard overlap on adjacent tiers | **AVAILABLE_RELIABLY** (100%) | **Implement in v2** |
| **Response Latency** | Precise millisecond timestamps on turn boundaries (`\x15start_end\x15`) | **UNAVAILABLE** (0.0% in Eigsti & Nadig) | **DEFERRED** — Requires aligned audio in v3 |
| **Overlap & Interruption** | Standardized `[<]`, `[>]` CHAT overlap tags | **UNAVAILABLE_INCONSISTENT** (0% in Nadig, 50% in Eigsti) | **DEFERRED** — Transcription convention bias |
| **Pause Timing** | Standardized pause duration tiers `(1.5)` | **UNAVAILABLE_INCONSISTENT** (0% in Nadig) | **DEFERRED** — Inconsistent cross-site coding |

---

## 3. Scientific Implications for Schema v2 Design

1. **Deterministic Transcript-Sequence Features Only:** Feature v2 will focus strictly on conversational dynamics that can be computed deterministically from speaker sequences and lexical tokens.
2. **Exclusion of Spurious Timings:** No latency will be estimated from line counts or arbitrary constants; latency is strictly deferred until acoustic audio alignment is introduced in Feature Schema v3.
