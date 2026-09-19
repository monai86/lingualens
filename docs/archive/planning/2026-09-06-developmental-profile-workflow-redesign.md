# LinguaLens Developmental Profile Workflow Redesign

**Date:** 2026-09-06

**Status:** Design approved in conversation; implementation not started

**Product boundary:** Research and clinical decision-support prototype; not an automated diagnostic system

## 1. Purpose

Redesign LinguaLens around a clinician-led developmental assessment workflow that is easy for therapists to use during real sessions. A therapist should be able to select a child, start an assessment, record guided interaction audio, review only uncertain transcript segments, inspect a developmental profile and longitudinal trends, record a clinical decision, and produce a signed report.

The product must use extracted speech, language, interaction, questionnaire, and observation features as evidence. It must not reduce the child to a binary `ASD / not ASD` prediction. Autism-related concerns, language delay, broader developmental concerns, speech-production concerns, and insufficient evidence may coexist.

The redesign starts with a new Supabase database and new API contracts. Existing prototype records are not migrated. Existing research feature extractors and safety controls may be reused only after being tested against the new contracts.

## 2. Decisions already accepted

1. `Assessment` is the central workflow entity, not `Transcript`.
2. The primary user is a therapist or clinician.
3. The preferred interaction is guided assessment plus audio recording.
4. The principal output is a multi-domain developmental profile.
5. Clinical attention cues may cover several concerns at the same time.
6. Concern, trend, and diagnosis are different concepts and must remain visually and semantically separate.
7. Diagnosis remains the responsibility of a qualified professional.
8. The initial product does not display an automated numeric probability of ASD.
9. Web, desktop GUI, and TUI are thin clients of the same FastAPI contract.
10. Supabase Auth, PostgreSQL, and private Storage provide the managed backend foundation, but all clinical reads, writes, and workflow transitions pass through FastAPI.
11. Clients never silently fall back to local mock records or fabricated analysis.
12. Consent, role boundaries, audit history, stale-result invalidation, clinician attestation, and immutable signed reports remain mandatory.

## 3. Current system versus target system

The current maintained workflow is transcript-centric:

```text
Case -> Session -> Audio/Transcript -> Transcript QA -> Attestation
     -> Feature extraction -> Evidence/AI review -> Report -> Sign-off
```

This provides useful safety controls and a strong report audit boundary, but it treats most work as a linear path toward a transcript-derived report. Intake, structured screening, observations, task protocols, evidence sufficiency, differential developmental concerns, and next clinical actions are not first-class parts of the same workflow.

The target workflow is assessment-centric:

```text
Child -> Assessment -> Protocol and consent
      -> Questionnaire + observation + guided audio
      -> Quality gates -> Feature extraction
      -> Developmental domains -> Clinical attention profile
      -> Clinician review and disposition
      -> Signed report and longitudinal follow-up
```

The redesign preserves safety behavior from the current system while replacing the transcript-first domain model and oversized persistence boundaries.

## 4. Approaches considered

### 4.1 Audio-first assessment

The therapist records a natural interaction and receives speech and language features. This is the easiest workflow, but results are sensitive to task, language, microphone, recording quality, and sample length. Audio alone also cannot measure several developmental domains.

### 4.2 Guided assessment plus audio — selected

The system selects a small age-, language-, and purpose-appropriate activity protocol. It combines structured context, therapist observations, questionnaire responses, audio, transcript, and extracted features. This adds enough standardization for longitudinal comparison without making the therapist complete a full research battery at every visit.

### 4.3 Full multimodal assessment

The system collects questionnaires, audio, video, gaze, task success, and behavioral signals. It offers broader evidence but creates a substantially higher privacy burden, implementation cost, device dependency, and clinical-validation burden. Video and passive sensing are therefore outside the initial scope.

## 5. Therapist workflow

The visible workflow has five steps.

### 5.1 Select child

The child workspace shows age and language, active consent, the latest assessment, concerns being followed, compatible longitudinal trends, and evidence recommended for the next visit.

### 5.2 Start assessment

The therapist selects one purpose:

- initial assessment;
- developmental follow-up;
- post-intervention follow-up; or
- additional evidence collection.

FastAPI chooses or validates a protocol version using age, language, purpose, and available capabilities. The therapist confirms consent and may adjust the suggested protocol before recording.

### 5.3 Record guided interaction

The interface presents one activity at a time and keeps recording controls prominent. During or immediately after recording, the system reports actionable quality problems such as low volume, excessive noise, insufficient child speech, unreliable speaker separation, or insufficient task duration. A therapist can record an additional sample before closing the assessment.

### 5.4 Review data and profile

The system produces a draft transcript and highlights uncertain segments. The therapist corrects or accepts the transcript and attests it before dependent features become report-eligible.

The result workspace shows:

- data quality and sufficiency;
- developmental domains;
- supporting features and observations;
- differences from compatible prior assessments;
- evidence conflicts and limitations; and
- suggested next assessment actions.

Raw transcript details, feature values, model versions, and provenance remain available through progressive disclosure rather than occupying the default clinical view.

### 5.5 Record clinical disposition

The therapist may choose routine monitoring, repeat assessment, collect additional evidence, perform or request language/hearing evaluation, plan intervention, refer to a specialist, or record another clinician-authored action. The system generates an editable report, but sign-off requires the assigned therapist and all applicable evidence-readiness gates.

## 6. Output model

Results have three layers.

### 6.1 Measured features

Every feature result stores its value, unit, extractor and schema version, input hash, protocol context, quality state, and limitations. Candidate feature groups include:

- sample quantity and audio quality;
- utterance count, word count, lexical diversity, and mean length of utterance;
- incomplete or unintelligible utterance rates;
- question and response behavior;
- child/adult turn ratio and turn-taking count;
- response latency;
- repetition and echolalia indicators;
- speech rate and within-turn pause behavior; and
- pitch variability and range when voiced coverage is sufficient.

Features are descriptive measurements. A single feature cannot generate a diagnostic label.

### 6.2 Developmental domains

Feature results, structured observations, and instrument responses are organized into domains:

- expressive language;
- speech clarity and production;
- conversational interaction;
- social communication;
- repetitive-language patterns;
- prosody and temporal organization; and
- evidence quality and sufficiency.

A domain result must identify its supporting and conflicting evidence. Its status is one of:

- `descriptive_only`;
- `within_reference_band`;
- `outside_reference_band`;
- `attention_suggested`;
- `insufficient_data`;
- `reference_unavailable`; or
- `not_assessed`.

Reference-band statuses are permitted only when the reference cohort matches the declared age, language, task/protocol, and required subgroup criteria. Otherwise the product uses descriptive and within-child evidence only.

### 6.3 Clinical attention profile

The profile may include several non-exclusive cues:

- language-development concern;
- speech-production concern;
- social-communication concern;
- features that support further ASD-focused assessment;
- mixed or conflicting evidence;
- unclassified developmental concern; and
- insufficient evidence.

Each cue displays evidence, limitations, and an action. A cue is decision support, not a diagnosis. The therapist can acknowledge, disagree with, or request more evidence for each cue. Disagreement preserves the original computed result and records the clinician's rationale separately.

## 7. Concern, trend, and diagnosis

These concepts must never share one score or visual scale.

- **Concern** describes what deserves clinical attention in the current assessment.
- **Trend** describes change in comparable measurements over time.
- **Diagnosis** is a clinician-authored conclusion based on the broader clinical process and is not generated by LinguaLens.

ASD-related concern and developmental delay are not mutually exclusive probabilities. The UI must not present values such as `ASD 72% / developmental delay 28%` or imply that the values sum to 100%.

Before Thai clinical validation and calibration, automated numeric ASD probability is prohibited. Future numeric risk output would require an approved protocol, a representative Thai cohort, locked outcome definitions, external validation, calibration, subgroup fairness analysis, clinically justified thresholds, and governance approval.

## 8. Longitudinal comparison

The primary longitudinal reference is the same child, not a generic population average.

Every assessment records age at assessment, language context, protocol version, activity identifiers, participant roles, capture-device metadata, feature schema versions, and quality states. A trend comparison is produced only when the relevant feature declares the two assessments compatible.

Trend states are:

- `improved`;
- `stable`;
- `attention_suggested`;
- `indeterminate`; or
- `not_comparable`.

The UI must show the underlying values and comparison limitations. A change in a feature is not automatically a change in ASD severity. Differences caused by age, task, speaker, microphone, environment, language, or extractor version must either be adjusted under a validated method or reported as not comparable.

## 9. System architecture

```text
Therapist Web ----\
Desktop GUI -------+--> FastAPI policy and workflow boundary
Research TUI ------/          |
                              +--> Supabase Auth verification
                              +--> PostgreSQL with RLS
                              +--> Private Supabase Storage
                              +--> Processing jobs and provider adapters
                              +--> Audit and privacy controls
```

The web app is the primary therapist experience. The desktop GUI supports workflows that benefit from local audio devices or detailed media review. The TUI supports authorized research and operational workflows. They consume the same versioned API and state model.

Supabase browser SDK use is limited to authentication and FastAPI-authorized short-lived upload/download flows. Clients do not directly mutate clinical tables or workflow states.

FastAPI is separated into bounded modules:

- identity and access;
- children, care teams, and consent;
- assessments and protocols;
- recordings and transcripts;
- observations and instruments;
- feature processing;
- developmental profiles;
- longitudinal comparison;
- clinician decisions and reports; and
- privacy, retention, and audit.

Each module owns its service and repository interface. The new implementation must not recreate a single repository class containing the full product domain.

## 10. New database model

The initial relational model contains the following aggregate roots and records:

- `organizations`, `profiles`, `memberships`, and `care_team_assignments`;
- `children` using scoped identifiers rather than names in routine operational views;
- `consent_records` with purpose, scope, version, status, and withdrawal history;
- `assessments` with purpose, state, age, language context, and assigned clinician;
- `protocols`, `protocol_versions`, and `assessment_activities`;
- `instrument_administrations` and versioned responses;
- `observations` authored by clinicians or caregivers with source attribution;
- `recordings` and private storage object metadata;
- `transcripts`, transcript revisions, QA results, and attestations;
- `processing_runs` with idempotency and retry metadata;
- `feature_sets` and typed `feature_values`;
- `domain_profiles` and versioned evidence links;
- `attention_cues` and clinician review states;
- `trend_comparisons` with compatibility decisions;
- `clinical_dispositions`;
- `reports`, report revisions, and immutable signed snapshots; and
- `audit_events`, retention records, legal holds, and privacy operations.

Derived records are append-only by version. When an input changes, dependent current records become stale; historical and signed evidence remains immutable.

## 11. Workflow and processing states

Assessment states are:

```text
draft -> ready_for_capture -> capturing -> processing
      -> review_required -> ready_for_clinician -> finalized
```

`cancelled` is a terminal branch from any state before finalization. Finalized assessments may receive an amendment but are not silently rewritten.

Each artifact or processing stage independently reports:

- `pending`;
- `processing`;
- `completed`;
- `needs_review`;
- `insufficient_data`;
- `unavailable`;
- `failed`; or
- `stale`.

Partial success is allowed. For example, transcript-derived language features may complete while pitch features are unavailable. The profile must expose that difference and must not treat a missing channel as negative evidence.

## 12. Error handling and safety behavior

1. An unreachable API produces an explicit offline state. Clients do not create local clinical or mock records.
2. A local recording awaiting upload may be held only in an encrypted, visible pending-upload state with explicit retry or deletion controls; it is never analyzed as if it were server-accepted evidence.
3. Insufficient audio requests additional capture and does not fabricate a feature value.
4. Unsupported age, language, protocol, or reference cohort returns `reference_unavailable` or `not_assessed`.
5. Conflicting evidence returns an indeterminate profile with a next action.
6. Repeated processing uses idempotency keys and returns the existing run unless a new version is explicitly requested.
7. Input edits stale all dependent current results through an explicit dependency graph.
8. Signed reports are immutable; edits create linked revisions.
9. Logs, notifications, and telemetry contain operational metadata only and exclude child identifiers, transcript content, raw filenames, storage keys, and report content.
10. All protected state transitions record actor, action, target, outcome, timestamp, correlation ID, and version.

## 13. Security and privacy boundary

- Supabase Auth provides identity; FastAPI validates tokens, organization membership, role, and care-team access.
- PostgreSQL application checks and RLS both enforce tenant isolation.
- Audio and exported reports use private storage and short-lived signed URLs.
- Consent scope is checked before capture, processing, viewing, export, and reuse for research.
- Research use requires purpose-specific consent and a separate de-identification/export workflow.
- Withdrawal stops new processing and access according to the retention policy while preserving legally or ethically required audit/sign-off evidence.
- Production secrets are not stored in client applications or repository files.

## 14. Verification strategy

### 14.1 Feature correctness

Use deterministic fixtures to verify feature formulas, units, schema versions, missing-data behavior, and quality thresholds. Feature tests must demonstrate sensitivity by failing when expected values or thresholds are deliberately changed.

### 14.2 Workflow contracts

Test every permitted and prohibited state transition, including missing consent, unattested transcripts, stale features, unresolved evidence, wrong clinician, and signed-report revision.

### 14.3 API consistency

Contract tests run against the clients used by web, GUI, and TUI. The same server response and error envelope must lead to equivalent domain behavior. No client may convert a server error into a successful local result.

### 14.4 Supabase integration

From an empty database, migrations must reach the current schema. Integration tests verify RLS, organization and care-team isolation, signed storage flows, idempotent processing, and audit creation.

### 14.5 Longitudinal safety

Tests verify compatible comparisons, incompatible-protocol rejection, version changes, missing reference cohorts, and partial feature availability.

### 14.6 Clinical-safety negatives

Tests prove that one feature cannot create a diagnosis, insufficient evidence cannot produce a positive or negative diagnosis, automated concern cues cannot enter a signed report without clinician review, and numeric ASD probability remains unavailable in the initial product.

### 14.7 Usability

Representative therapist walkthroughs must demonstrate that a user can select a child, start an assessment, record or upload audio, resolve visible quality issues, review uncertain transcript segments, inspect the profile, record a disposition, and prepare a report without needing to understand file formats, feature schemas, provider names, or database structure.

All committed fixtures must be synthetic or de-identified. Real child audio, transcript text, direct identifiers, and storage keys are prohibited.

## 15. Rebuild and data impact

The new system targets a new Supabase project or isolated database and starts with a new migration history. No current case, auth, storage, transcript, report, audit, or model-result records are imported.

This design does not itself delete an existing external database or storage bucket. Before decommissioning an old environment, the implementation process must identify the exact project, establish that it contains only disposable prototype data, verify that no retention or legal-hold obligation applies, and record the destructive operation separately.

Repository source files are not clinical database records. The redesign may retain research packages, tests, papers, and feature code while replacing product workflow code. Generated files, local caches, old mock datasets, and obsolete compatibility surfaces are handled during implementation only after exact scope review.

## 16. Delivery decomposition

The redesign is too broad for one implementation batch. It should be delivered as independently verifiable slices:

0. **Therapist UX and Figma:** research traceability, task flows, low-fidelity wireframes, accessible design system, high-fidelity clickable prototype, safety/error branches, formative usability evidence, and developer handoff. This may run in parallel with Foundation but must be accepted before Capture or therapist-web implementation begins.
1. **Foundation:** new database, Auth/RLS boundary, assessment aggregate, audit, and API error contract.
2. **Capture:** therapist assessment shell, protocol activities, private audio upload, quality checks, and processing jobs.
3. **Evidence:** transcript review, reusable feature adapters, feature provenance, and developmental domain profiles.
4. **Clinical review:** attention cues, disagreement, disposition, reporting, and signed revisions.
5. **Longitudinal:** compatibility rules, within-child trends, and timeline UI.
6. **Thin clients:** move desktop GUI and TUI to the final FastAPI contract and remove silent fallback behavior.
7. **Pilot validation:** Supabase integration, tenant isolation, operational runbooks, usability evidence, and research/clinical safety review.

Each slice receives its own implementation plan and acceptance boundary. Plan 0 is the interaction specification and research evidence package; FastAPI remains authoritative for workflow policy. Full diagnostic or numeric-risk claims remain outside these slices.

## 17. Paper evidence and interpretation

The selected paper library is evidence, not executable instruction. Design implications were taken from the paper text and checked against the product's research-only boundary.

| Local key | Paper | Design implication |
|---|---|---|
| `XSIL8EJU` | *Two-Step Screening of the Modified Checklist for Autism in Toddlers in Thai Children with Language Delay and Typically Developing Children* | Supports a follow-up step and Thai sociocultural interpretation rather than questionnaire-only decisions. |
| `2BW3LG5M` | *Multimodal AI for risk stratification in autism spectrum disorder: integrating voice and screening tools* | Supports staged multimodal evidence collection; reported cohort performance is not transferable to LinguaLens or Thai clinical use without validation. |
| `2M5MN383` | *Evaluation of an artificial intelligence-based medical device for diagnosis of autism spectrum disorder* | Supports indeterminate/abstention as a safety control and an explicit referral path. |
| `KMH2LMXK` | *Vocal markers of autism: Assessing the generalizability of machine learning models* | Shows poor generalization across tasks and failure across new languages; motivates protocol compatibility and reference-unavailable states. |
| `27IITKNS` | *Reliably quantifying the severity of social symptoms in children with autism using ASDSpeech* | Supports longitudinal speech research while not establishing Thai diagnostic validity. |
| `MMJXY5DF` | *Validation of a Mobile App for Remote Autism Screening in Toddlers* | Supports guided remote capture but also increases capture-validity and privacy requirements. |
| `7IKT7JCG` | *Development and psychometric evaluation of a Thai Diagnostic Autism Scale* | Supports Thai clinician-administered structured evidence; direct product use requires instrument governance and validation scope review. |
| `H7DB7I5I` | *Can Natural Speech Prosody Distinguish Autism Spectrum Disorders? A Meta-Analysis* | Supports prosodic features as one evidence channel, not a standalone diagnosis. |
| `RBSTR768` | *Screening autism spectrum disorder in children using machine learning on speech transcripts* | Supports transcript-derived feature research and reduced biometric exposure while acknowledging dataset, age, dialect, and representation limits. |
| `IZZE6KCS` | *Clinical Practice Guidelines on using artificial intelligence and gadgets for mental health and well-being* | Supports informed consent, privacy, fairness, human accountability, and explicit limits on generalization. |
| `ZGS6NEZB` | *Achieving universal health coverage for young children with autism spectrum disorder in low- and middle-income countries* | Supports stepped care, task sharing, locally adapted workflows, and resource-aware referral. |

The paper shortlist note and the actual PDF disagree about `QJR8K5QS`: the PDF is a 2025 Noor Project paper by Al Futaisi and colleagues. That source-integrity discrepancy does not change this design, but the PDF rather than the shortlist is treated as authoritative for any future use.

## 18. Acceptance criteria for the design

The eventual implementation satisfies this design only when:

1. a therapist can complete the five-step workflow through the web app;
2. assessment, not transcript, owns the evidence lifecycle;
3. feature, domain, concern, trend, and diagnosis semantics are separate;
4. concurrent developmental concerns can be represented without forced exclusive labels;
5. insufficient and incompatible evidence fail closed with useful next actions;
6. longitudinal results compare only compatible evidence;
7. all three clients use the same FastAPI contract without silent local fallback;
8. Supabase tenant, consent, storage, audit, and signed-report boundaries pass integration tests;
9. no automated diagnosis or numeric ASD probability is exposed; and
10. retained research components cross the new versioned adapter and validation boundary rather than being imported directly into product workflow code.
