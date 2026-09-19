# LinguaLens Prospective Data Collection Confounder Audit Checklist
**Document Date:** 2026-08-24  
**Status:** Canonical Prospective Quality Audit Checklist  
**Target:** Prospective Clinical Trials, Research Cohorts, and Pilot Clinic Sites  

---

## 1. Objective

To prevent reproducing retrospective corpus shortcuts (e.g. where diagnostic group is collinear with child age, examiner identity, or hospital site), all prospective data collection must pass this **Confounder Audit Checklist** before entering research benchmark pipelines.

---

## 2. Prospective Confounder Checklist

### Audit Item 1: Examiner / Clinician Balancing
- [ ] **Condition:** Every participating clinician examines BOTH clinical cases (ASD / DD) and comparison controls (TD).
- [ ] **Red Flag Structure:** Clinician A evaluates 90% ASD children; Clinician B evaluates 90% TD children.
- [ ] **Remedy:** Enforce balanced cross-clinician scheduling at each participating site.

### Audit Item 2: Age Matching & Distribution
- [ ] **Condition:** Mean age and age variance are matched within $\pm 3\text{ months}$ between diagnostic groups.
- [ ] **Red Flag Structure:** ASD cohort is significantly older (e.g. mean 54 months) than TD cohort (mean 38 months).
- [ ] **Remedy:** Stratified age-bin recruitment (e.g. 24–36m, 36–48m, 48–60m, 60–72m).

### Audit Item 3: Recording Hardware & Device Uniformity
- [ ] **Condition:** Identical microphone model, recording gain, and audio channel configuration across all recording rooms.
- [ ] **Red Flag Structure:** Site 1 uses high-end wireless boundary microphones; Site 2 uses laptop built-in mono microphones.
- [ ] **Remedy:** Deploy standardized hardware kits to all clinical partner sites.

### Audit Item 4: Protocol Block Adherence
- [ ] **Condition:** All sessions complete standard Block A (free play), Block B (semi-structured), and Block C (narrative) with recorded block timestamps.
- [ ] **Red Flag Structure:** Sessions vary in length from 5 to 45 minutes with unrecorded activity transitions.
- [ ] **Remedy:** Digital session timer and block logger embedded in clinician UI.

### Audit Item 5: Language & Dialect Homogeneity
- [ ] **Condition:** Primary language and regional dialect logged. Bilingual exposure status recorded.
- [ ] **Red Flag Structure:** ASD group recruited from urban clinic (Standard Thai); TD group recruited from rural community (Regional Dialect).
- [ ] **Remedy:** Geographic and dialect matching across study arms.

---

## 3. Negative Control Audit Protocols

Before running diagnostic ML classifiers on prospective datasets, the following **Negative Control Shortcut Audits** must be executed:

1. **Age-Only Classifier:** Must verify that an age-only model does NOT achieve AUROC $> 0.60$ within diagnostic comparisons.
2. **Clinician Prediction Classifier:** Evaluate whether features can predict `clinician_uid`. If `clinician_uid` is predicted with AUROC $> 0.80$, examine feature sensitivity to clinician prompt styles.
3. **Site Prediction Classifier:** Evaluate whether features predict `site_uid`.
4. **Device Prediction Classifier:** Evaluate whether features predict microphone / device type.
