# LinguaLens Feature v2 Quality & Distribution Report
**Generated Date:** 2026-08-26  
**Feature Schema:** `features-conversation-v2`  
**Dataset:** `data/ml/canonical_features_v2.parquet` (1,961 analysis-ready transcripts)  
**Scope:** Internal retrospective measurement audit; not clinical or Thai validation  

---

## 1. Conversational Feature Distribution & Summary Statistics

| Feature Name | Missing (%) | Mean | Std | Min | Median | Max | Corr Total Utts | Corr Total Words | Corr Age |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `speaker_balance_ratio` | 0.0% | 0.5281 | 0.2473 | 0.0401 | 0.4406 | 1.0 | -0.2676 | 0.2127 | 0.6849 |
| `turn_alternation_rate` | 0.0% | 0.445 | 0.2256 | 0.0 | 0.5175 | 0.9333 | 0.2743 | -0.2105 | -0.556 |
| `child_run_length_mean` | 0.0% | 7.7747 | 20.8327 | 1.0 | 1.4676 | 295.0 | -0.1093 | 0.0922 | 0.2777 |
| `child_response_rate` | 0.0% | 0.5362 | 0.2355 | 0.0 | 0.5385 | 1.0 | -0.1351 | 0.0516 | 0.3127 |
| `adult_response_rate` | 0.0% | 0.5559 | 0.3226 | 0.0 | 0.6804 | 1.0 | 0.2279 | -0.3283 | -0.6781 |
| `partner_repetition_exact_ratio` | 0.0% | 0.0127 | 0.0333 | 0.0 | 0.0 | 1.0 | 0.1951 | 0.055 | -0.0359 |
| `partner_repetition_overlap_mean` | 0.0% | 0.0435 | 0.0479 | 0.0 | 0.0349 | 1.0 | 0.2934 | 0.2046 | -0.0213 |
| `self_repetition_exact_ratio` | 0.0% | 0.0924 | 0.1981 | 0.0 | 0.0085 | 1.0 | 0.0378 | -0.2827 | -0.3934 |

---

## 2. Quality Audit Boundaries

1. **Extraction completeness and ranges:**
   - Zero missing values across all 8 conversational features across 1,961 analysis-ready transcripts (100% extraction completeness).
   - Ratios (`speaker_balance_ratio`, `turn_alternation_rate`, `child_response_rate`, `adult_response_rate`, `partner_repetition_exact_ratio`, `self_repetition_exact_ratio`) strictly respect the bounded interval $[0.0, 1.0]$.
2. **Correlations are descriptive, not independence claims:**
   - The table reports observed correlations with transcript size and age. These corpus-specific diagnostics do not establish construct validity, causal independence, or generalization.
3. **Clinical boundary:**
   - These deterministic transcript measurements require independent human/reference validation before clinical interpretation. They are not diagnostic scores and have not been validated for Thai clinical use.
