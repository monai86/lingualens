# LinguaLens Examiner Variance & Tripartite Feature Framework
**Document Date:** 2026-08-24  
**Status:** Methodological Framework Specification  
**Applies To:** Feature Schemas v1, v2, v3a, v3b  

---

## 1. The Examiner Confounding Problem

In conversational language sampling, speech is co-constructed by the child and the adult conversation partner. If an examiner asks rapid, closed-ended questions, the child will produce shorter utterances, lower lexical diversity, and faster turn transitions—regardless of clinical phenotype.

To avoid misattributing examiner interaction styles to child pathology, LinguaLens establishes a **Tripartite Feature Classification Framework**:

```text
                     COMMUNICATIVE EVENT
                              │
     ┌────────────────────────┼────────────────────────┐
     ▼                        ▼                        ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  CHILD-INTRINSIC │  │ EXAMINER-CONTEXT │  │ DYADIC INTERACT. │
│     FEATURES     │  │     FEATURES     │  │     FEATURES     │
│                  │  │                  │  │                  │
│ Individual traits│  │ Adult elicitation│  │ Bidirectional    │
│ of child speech  │  │ style & behavior │  │ emergent dynamics│
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 2. The Three Feature Families

### Family 1: Child-Intrinsic Features
Features that reflect internal linguistic, articulatory, or vocal production mechanisms of the child. These metrics are normalized against child speaking duration or child token counts.

- **Examples (Language/Text):** `ttr`, `vocabulary_diversity`, `subordinate_clause_ratio`, `verb_ratio`, `noun_ratio`, `mlu_morphemes`.
- **Examples (Acoustic/Prosodic v3a):** `pitch_f0_sd_semitones`, `pitch_range_90_10_semitones`, `child_pause_duration_ratio`, `articulation_rate_sps`.
- **Construct Boundary:** Measured strictly within the boundaries of child speech segments. Unaffected by adult pauses.

### Family 2: Examiner-Context Features (Environmental Controls)
Features that characterize the adult clinician's prompt style, questioning intensity, and verbal dominance during the interaction.

- **Examples:**
  - `adult_question_rate`: Proportion of adult utterances ending in questions or interrogative markers.
  - `adult_prompt_level_distribution`: Proportion of Level 0 vs Level 4 prompts.
  - `adult_speaking_time_ratio`: Total adult phonated duration / total session phonated duration.
  - `adult_mlu_words`: Mean length of utterance of the examiner.
  - `adult_intervention_rate`: Number of adult turns per minute.
- **Construct Boundary:** Used exclusively as environmental covariates, confounding audit metrics, and quality checks. **Never used as child diagnostic markers.**

### Family 3: Dyadic Interaction Features (Bidirectional Emergent Metrics)
Features that emerge strictly from the temporal or conversational coupling between the child and the examiner.

- **Examples (Conversational v2):** `speaker_balance_ratio`, `turn_alternation_rate`, `child_response_rate`, `adult_response_rate`, `partner_repetition_exact_ratio`, `partner_repetition_overlap_mean`.
- **Examples (Acoustic v3a/v3b):** `response_latency_median_ms`, `response_latency_iqr_ms`, `overlap_duration_ratio`, `prosodic_entrainment`.
- **Construct Boundary:** **Must NEVER be described as pure child traits.** A child's response latency is mathematically coupled to the examiner's preceding pause length and prompt complexity.

---

## 3. Feature Family Mapping Matrix

| Feature Identifier | Schema | Conceptual Family | Construct | Potential Examiner Sensitivity |
| :--- | :---: | :--- | :--- | :--- |
| `mlu_words` | v1 | Child-Intrinsic | Syntactic complexity | Moderate (suppressed by rapid closed questions) |
| `ttr` | v1 | Child-Intrinsic | Lexical diversity | Low-Moderate |
| `pitch_f0_sd_semitones` | v3a | Child-Intrinsic | Intonational pitch variation | Low |
| `pause_duration_ratio` | v3a | Child-Intrinsic | Within-turn speech planning | Low |
| `speaker_balance_ratio` | v2 | Dyadic Interaction | Conversational contribution | **High** (driven by adult verbal dominance) |
| `turn_alternation_rate` | v2 | Dyadic Interaction | Interactive back-and-forth | **High** (driven by adult pacing) |
| `child_response_rate` | v2 | Dyadic Interaction | Conversational responsiveness | **High** (driven by adult question salience) |
| `partner_repetition_exact_ratio` | v2 | Dyadic Interaction / Repetition | Immediate echoing | Moderate |
| `response_latency_median_ms` | v3a | Dyadic Interaction | Response timing / processing | **High** (driven by adult prompt duration) |

---

## 4. Methodological Guidelines for Analysis & Reporting

1. **Covariate Adjustment in Prospective Trials:**  
   When testing dyadic features (e.g. `response_latency_median_ms`), models must include examiner covariates (e.g. `adult_question_rate`, `adult_mlu_words`) or utilize mixed-effects models with random intercepts for clinician (`(1 | clinician_uid)`).
2. **Future product-design hypothesis:**  
   If dyadic features ever pass prospective measurement and clinical-safety gates, a separately reviewed product change would need examiner-context information. Current therapist-product display is prohibited.
