# LinguaLens Dataset & Participant Integrity Audit
**Generated Date:** 2026-08-23  
**Registry File:** `data/ml/participant_registry.csv`  
**Status:** Complete, Reconciled, and Programmatically Verified  

---

## 1. Executive Summary & Core Sample Counts

| Metric | Full Scanned Manifest | Analysis-Ready QC-Pass Cohort |
| :--- | :---: | :---: |
| **Total Transcript Rows (Sessions)** | 2960 | **1961** |
| **Total Unique Independent Participants** | 1756 | **1144** |
| **Cross-Sectional Participants (Single Session)** | - | **886** |
| **Longitudinal Participants (>1 Session)** | - | **258** |

> [!IMPORTANT]
> **Clinical Terminology Guardrail:** In speech-language pathology research, transcript files represent *interaction sessions*, not independent clinical subjects. The true clinical sample size is **1144 unique independent children**, representing **1961 longitudinal sessions**.

---

## 2. Definitive Reconciliation of ASD Sample Counts

### 2.1 The Exact Analysis-Ready ASD Breakdown

Across the entire audited repository, exactly **136 ASD sessions** and **62 unique independent ASD children** meet all QC criteria:

```text
     corpus  sessions  unique_children  mean_sessions  max_sessions
     Eigsti        16               16           1.00             1
   Flusberg        64                6          10.67            13
NYU-Emerson        26               26           1.00             1
      Nadig         9                9           1.00             1
    Rollins        21                5           4.20             5
```

- Total ASD Sessions: **136** (64 + 26 + 21 + 16 + 9 = 136)
- Total Unique ASD Children: **62** (6 + 26 + 5 + 16 + 9 = 62)

### 2.2 Why QuigleyMcNally is Excluded from the Analysis-Ready Cohort

All 203 transcript files in `data/QuigleyMcNally/` are classified as `analysis_ready = False` in the manifest due to `missing_child_speech_tier`.
- **Reason:** The QuigleyMcNally corpus comprises video recordings of infant-caregiver vocalizations at 6 to 18 months of age. The transcripts encode pre-speech vocal gestures (`0word`, infant nonverbal vocalizations) rather than orthographic child speech utterances (`*CHI:`).
- **Stage of Exclusion:** Manifest curation (`data/manifests/english_child_transcript_manifest.csv`).
- **Conclusion:** QuigleyMcNally contains **0 analysis-ready transcripts**.

### 2.3 Clarification of Historical Documentation Figures

1. **ASD = 136 (`data/ml/participant_registry.csv` & `data/ml/canonical_features.parquet`):**
   - The authoritative count of analysis-ready ASD sessions across 5 corpora (`Flusberg` 64, `NYU-Emerson` 26, `Rollins` 21, `Eigsti` 16, `Nadig` 9).
   - Corresponds to **62 unique independent ASD children**.
2. **ASD = 65 (`data/combined_features.csv`):**
   - A historical cross-sectional extraction that took only **Session 1** per participant (`NYU-Emerson` 30, `Eigsti` 16, `Nadig` 13, `Flusberg` 6) prior to strict manifest harmonization.
3. **ASD = 17 (`data/curated_group_features.csv`):**
   - An early prototype cohort comprising `Eigsti` (16) + `QuigleyMcNally` trial file (1) before incorporating the larger TalkBank clinical collections.

---

## 3. Analysis-Ready Participant & Session Breakdown by Diagnostic Group

All metrics below are computed dynamically with strict programmatic assertions (`min <= mean <= max`, sum of groups equals dataset total):

```text
Diagnostic Group  Analysis-Ready Sessions  Unique Participants  Mean Sessions / Child  Median Sessions  Min Sessions  Max Sessions  Longitudinal Children (>1 session)
             ASD                      136                   62                   2.19                1             1            13                                  11
              DD                       16                   16                   1.00                1             1             1                                   0
              HL                      138                   42                   3.29                3             1             5                                  40
              LT                      408                  197                   2.07                1             1             7                                  54
              NH                      170                   36                   4.72                5             3             5                                  36
             SLI                      113                  113                   1.00                1             1             1                                   0
              TD                      980                  678                   1.45                1             1             7                                 117
```

---

## 4. Corpus-Level Participant and Diagnostic Distribution

```text
      Corpus  Total Sessions  Unique Participants  ASD Sessions  ASD Participants  TD Sessions  TD Participants  Other Sessions  Mean Sessions/Child  Max Sessions  Longitudinal Children
     Ambrose             154                   39             0                 0            0                0             154                 3.95             5                     38
        ENNI             361                  361             0                 0          286              286              75                 1.00             1                      0
      Eigsti              48                   48            16                16           16               16              16                 1.00             1                      0
EisenbergGuo              34                   34             0                 0           17               17              17                 1.00             1                      0
EllisWeismer             554                  131             0                 0          288               76             266                 4.23             7                    121
    Flusberg              64                    6            64                 6            0                0               0                10.67            13                      6
      Gillam             122                  122             0                 0          101              101              21                 1.00             1                      0
 NYU-Emerson              26                   26            26                26            0                0               0                 1.00             1                      0
       Nadig              32                   32             9                 9           23               23               0                 1.00             1                      0
  NewEngland             162                   72             0                 0          162               72               0                 2.25             4                     50
    Nicholas             154                   39             0                 0            0                0             154                 3.95             5                     38
    Rescorla             229                  229             0                 0           87               87             142                 1.00             1                      0
     Rollins              21                    5            21                 5            0                0               0                 4.20             5                      5
```

---

## 5. Excluded Transcripts Audit

Total excluded transcript files in manifest: **999**.

```text
        corpus          exclusion_reason  excluded_sessions
       Ambrose          not_english_only                  5
  EllisWeismer missing_child_speech_tier                  1
   NYU-Emerson          not_english_only                  1
    NewEngland missing_child_speech_tier                 96
    NewEngland          not_english_only                  3
      Nicholas          not_english_only                  5
QuigleyMcNally missing_child_speech_tier                201
      Rescorla missing_child_speech_tier                  3
      Rescorla          not_english_only                  1
```

---

## 6. Demographic & Task Distribution (Analysis-Ready Cohort)

### Age in Months by Diagnostic Group:
```text
                  count   mean    std    min    25%    50%     75%     max
diagnostic_group                                                          
ASD               136.0  63.15  22.44  26.00  44.80  58.11   79.32  116.60
DD                 16.0  57.17   9.45  38.83  51.94  58.28   61.27   78.87
HL                138.0  24.66   7.88  13.00  18.00  26.00   27.40   36.00
LT                408.0  55.01  30.90  30.00  36.00  48.00   60.00  156.00
NH                170.0  23.26   8.04  13.00  18.00  22.00   27.00   36.00
SLI               113.0  82.01  25.57  37.00  60.87  87.00  105.40  127.00
TD                979.0  60.34  34.26  13.43  30.00  54.00   89.35  156.00
```

### Sex Distribution by Group:
```text
sex               female  male  unknown   All
diagnostic_group                             
ASD                    7   103       26   136
DD                     2    14        0    16
HL                    86    42       10   138
LT                    89   292       27   408
NH                    98    72        0   170
SLI                   42    69        2   113
TD                   412   522       46   980
All                  736  1114      111  1961
```

### Task Type Distribution by Group:
```text
task_type         narrative  picture_description  toyplay   All
diagnostic_group                                               
ASD                       0                    0      136   136
DD                        0                    0       16    16
HL                        0                    0      138   138
LT                        0                    0      408   408
NH                        0                    0      170   170
SLI                      96                   17        0   113
TD                      387                   17      576   980
All                     483                   34     1444  1961
```

---

## 7. Confounding and Leakage Safeguards

1. **Local-only source identifiers:** The ignored participant registry retains source-linked identifiers for reproducible extraction and participant grouping. Committed reports and fixtures must contain only pseudonymous row-level identifiers, synthetic examples, or aggregates.
2. **Mandatory Participant Grouping:** Repeated longitudinal sessions are never randomly partitioned between train and test. **`GroupKFold(groups=participant_uid)`** is enforced across all ML validation workflows.
3. **Corpus & Task Confounding:** As shown in Section 6, 100% of SLI data originates from structured story-retelling tasks (`ENNI`, `Gillam`), whereas 100% of ASD data originates from naturalistic/play dialogue. Naive cross-task pooling creates severe shortcut learning, necessitating domain-controlled evaluation.
