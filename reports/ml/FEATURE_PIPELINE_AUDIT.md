# LinguaLens Feature Pipeline Audit
**Report Date:** 2026-08-23  
**Status:** Research extraction audit; product integration not established  
**Audit Scope:** Feature Extractors, Parsers, Providers, Schemas, API Endpoints, and Parity Verification

---

## 1. Canonical Feature Extraction Path

The repository has established a canonical research extraction interface. Deterministic parity is tested across supported research inputs; parity with the active therapist product is not claimed:

1. **Canonical Interface:** `packages/features/transcript_features.py`
   - Function: `extract_transcript_features(transcript, age_months=None)`
   - Schema Version: `features-basic-v1`
   - Canonical Schema: `src/feature_schema.py` (`FEATURES` list: 14 numerical features + `age_months`)
2. **File-Based Research Extractor:** `src/chat_feature_extractor.py`
   - Function: `extract_chat_features(cha_path: Path) -> dict`
   - Parses `.cha` files directly using `pylangacq` / `rustling` CHAT parser.
   - Extracts CHAT `@ID` child metadata (`participant_id`, `group_header`, `sex`, `age_months`) and calculates tokenized linguistic metrics.
3. **In-Memory Clinical Extractor:** `src/clinical_speech/feature_extractor.py`
   - Function: `extract_clinical_features(lines: Sequence[NormalizedTranscriptLine], age_months=None)`
   - Computes features from parsed utterance arrays without requiring local disk access.
4. **Therapist product boundary:** [`apps/api/`](../../apps/api) and [`apps/lingualens-app/`](../../apps/lingualens-app)
   - These canonical product surfaces do not currently expose or consume the v2 research vector.
   - Legacy Tkinter/TUI utilities do not establish product integration or parity.

---

## 2. Feature Parity & Extractor Inventory

| Extractor File | Primary Role | Inputs | Schema Alignment | Active Status |
| :--- | :--- | :--- | :--- | :--- |
| `packages/features/transcript_features.py` | Unified Canonical Interface | `.cha` path / `ParsedChaTranscript` / lines | `features-basic-v1` | **Canonical Target** |
| `src/chat_feature_extractor.py` | Research & Batch Dataset Extraction | `.cha` file path | `features-basic-v1` | **Canonical Research** |
| `src/clinical_speech/feature_extractor.py` | Memory-based Parser Engine | Sequence of `NormalizedTranscriptLine` | `features-basic-v1` | **Active Component** |
| `apps/api/` and `apps/lingualens-app/` | Canonical therapist product | Product-specific contracts | No v2 integration | **Separate Boundary** |
| `src/therapist_backend/` & `src/clinical_workflow/` | Legacy Research Compatibility | Various | Deprecated | **Legacy (Do not use)** |

### Parity Verification:
- **Test Files:** [`tests/test_reference_feature_parity.py`](../../tests/test_reference_feature_parity.py) for the legacy v1 seam and [`tests/ml/test_features_v2.py`](../../tests/ml/test_features_v2.py) for v2 research paths and synchronized exports.
- **Status:** PASS for their declared research/compatibility seams. These tests do not prove therapist-product v2 integration.

---

## 3. Current Canonical Feature Definitions

All canonical features defined in `src/feature_schema.py`:

| Feature Name | Category | Formula / Definition | Direction / Expected Pattern |
| :--- | :--- | :--- | :--- |
| `age_months` | Demographics | CHAT `@ID` age converted to decimal months | Covariate |
| `total_utterances` | Productivity | Count of child (`*CHI:`) utterances | Lower in severe nonverbal/shy |
| `mlu` | Complexity | Mean morphemes per child utterance | Lower in delay / language impairment |
| `mluw` | Complexity | Mean words per child utterance | Lower in delay / language impairment |
| `ttr` | Diversity | Type-Token Ratio ($\text{unique words} / \text{total words}$) | Measure of lexical variety |
| `total_words` | Productivity | Total spoken word tokens by child | Correlated with session length/task |
| `unintelligible_count` | Clarity | Count of unintelligible tokens (`xxx`, `xx`) | Higher in phonological/speech delay |
| `unintelligible_ratio` | Clarity | $\text{unintelligible\_count} / \text{total\_words}$ | Rate of unintelligibility |
| `zero_vocalization_count` | Engagement | Child turns with 0 vocalizations (gestures/actions only) | Communication engagement marker |
| `nonverbal_vocalization_count` | Vocal Behavior | Laughing, crying, screeching, vegetative sounds | Non-speech vocal marker |
| `question_ratio` | Pragmatics | Proportion of child utterances ending with `?` | Pragmatic / conversational marker |
| `echolalia_count` | Pragmatics | Count of immediate/delayed repetition of partner's tokens | Typical ASD behavioral marker |
| `echolalia_ratio` | Pragmatics | $\text{echolalia\_count} / \text{total\_utterances}$ | Ratio of echolalic utterances |
| `pronoun_reversal_count` | Pragmatics | Regex count of "you for I", "me for you" confusions | Classic ASD pragmatic marker |

---

## 4. Metadata Availability, QC Behavior & Known Gaps

1. **Quality Control (QC) Gate:**
   - `src/transcript_reviewer.py` and `data/manifests/english_child_transcript_manifest.csv` enforce QC rules:
     - `missing_child_speech_tier`: Files with no child speech are excluded from `analysis_ready`.
     - `not_english_only`: Multilingual / non-English files excluded.
     - `min_utterance_threshold`: Transcripts with $< 3$ child utterances flagged as `insufficient_data`.
2. **Known Metadata Gaps:**
   - One local registry row has unresolved age and must remain `NaN`; its source filename is intentionally omitted from committed reports.
   - Some corpora lack granular sex metadata (recorded as `unknown` or omitted in header; default fallback `'unknown'`).
3. **Identified Risks Prior to ML Training:**
   - **Corpus-Task Confounding:** ENNI and Gillam are structured story retelling (`narrative`), resulting in higher MLU and lower question ratios compared to free toy play (`toyplay`) in Eigsti or Rollins.
   - **Longitudinal Session Inflation:** Rollins and Flusberg contain multiple sessions per child (up to 33 sessions for one child). Using raw rows without participant grouping would cause catastrophic data leakage.

---

## 5. Audit Decision & Canonical Extraction Rule

> [!IMPORTANT]
> **Canonical research path:** Downstream research dataset generation must invoke the versioned functions in `packages.features.transcript_features` or the compatible CHAT extractor. This approval does not authorize product deployment or clinical interpretation.
