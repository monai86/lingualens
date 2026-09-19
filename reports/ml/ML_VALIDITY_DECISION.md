# LinguaLens ML Validity & Decision Gate Report
**Generated Date:** 2026-08-23  
**Decision Gate Status:** Outcome B — Canonical Features Capture Within-Domain Phenotype and Developmental Delay Signals, but Fail Cross-Corpus ASD Generalization  

---

## 1. Summary of Scientific Findings

1. **Within-Domain Characterization:** 
   - Within the standardized `Eigsti` cohort (interactive toyplay), canonical linguistic features (`features-basic-v1`) demonstrate moderate exploratory discrimination for ASD vs TD (**Elastic-Net AUROC 0.6234** [95% CI: 0.535–0.712], **Balanced Acc 0.5688**).
   - In distinguishing ASD from non-autistic Developmental Delay (DD) matched on age and protocol, pragmatic features achieve substantial exploratory separation (**Elastic-Net AUROC 0.7730** [95% CI: 0.696–0.842], **Balanced Acc 0.6812**).
   - In distinguishing TD from DD, grammatical complexity and lexical diversity achieve strong separation (**Elastic-Net AUROC 0.8266** [95% CI: 0.757–0.885], **Balanced Acc 0.7563**).

2. **Cross-Corpus Generalization Failure:**
   - Under rigorous bidirectional cross-corpus validation on independent unseen data (`Eigsti ↔ Nadig`), models perform at or below chance (**Eigsti → Nadig AUROC 0.4879**, **Nadig → Eigsti AUROC 0.5586**).
   - The canonical `features-basic-v1` lexical transcript feature set is insufficient for autonomous cross-domain ASD screening.

3. **Confounding & Shortcut Protection:**
   - Metadata-only negative controls achieve an AUROC of **0.9956** on naively pooled data, and age-only controls achieve an AUROC of **0.9855** cross-corpus.
   - Headline accuracy in pooled evaluations was entirely driven by site, task protocol, and age mismatch rather than robust ASD speech-language markers.

4. **Clinical Boundaries:**
   - Current features must not be deployed for automated clinical diagnosis or risk scoring.
   - They remain retrospective research-characterization variables only; no individual clinical use is authorized.

---

## 2. Decision Gate Verdict

**Outcome B is Formally Adopted.**  
The current canonical lexical feature set (`features-basic-v1`) did not generalize in the evaluated corpora. Feature Schema v2 is therefore an offline measurement-research extension, not a clinical or product progression.

---

## 3. Prioritized Roadmap for Feature Development

1. **Feature Schema v2 (Conversational Dynamics):**
   - Speaker balance ratio, turn alternation rate, child/adult response rates, and deterministic lexical repetition overlaps.
2. **Feature Schema v3 (Acoustic & Prosodic Markers — Future Branch):**
   - Fundamental frequency ($F_0$) variability, pause duration distributions, speech rate, and vocal intensity from aligned audio.
3. **Thai Clinical Data Collection:**
   - Prospective, protocol-standardized language sample collection in Thai clinical settings to establish valid local normative benchmarks.
