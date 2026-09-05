# LinguaLens Therapist Workflow UX Workspace

**Prototype:** LinguaLens — Therapist Assessment Workflow v0.1  
**Status:** evidence/task-model pack and compact Figma skeleton; full prototype not yet accepted
**Audience:** therapist/clinician, clinical supervisor, and authorized researcher

## Fixed design question

> How might LinguaLens help a therapist collect sufficient developmental evidence, understand what requires attention, compare compatible prior assessments, and record a clinician-owned next action without presenting automated diagnosis?

## Product boundary

LinguaLens is a research and clinical decision-support prototype. It organizes
descriptive measurements, observations, questionnaire context, evidence quality,
and compatible within-child trends for professional review. It does not diagnose
ASD, calculate or display numeric ASD probability, replace a developmental
assessment, or make a treatment/referral decision without clinician ownership.

The primary user is a therapist or clinician working with a child. A clinical
supervisor may review the workflow and an authorized researcher may inspect
de-identified, synthetic prototype evidence. Caregiver self-diagnosis,
unsupervised interpretation, and any direct client-to-database clinical write
are out of scope.

## Workflow hypothesis

The prototype treats `Assessment` as the central work item:

```text
Select child -> Purpose and consent -> Guided capture ->
Quality and processing -> Evidence/profile review ->
Clinician disposition -> Report preparation and sign-off
```

The profile is multi-domain. Language-development, speech-production,
social-communication, ASD-focused follow-up, mixed evidence, and insufficient
evidence can coexist. A measured feature, developmental domain, attention cue,
longitudinal trend, and clinician-authored conclusion are separate concepts and
must not be collapsed into one score.

## Evidence pack

| Artifact | Purpose |
|---|---|
| `evidence-matrix.md` | Binds requirements to research/spec sources and validation evidence. |
| `task-model.md` | Defines the therapist's observable work and recovery boundaries. |
| `frame-inventory.csv` | Will bind every Figma frame to a goal, state, and requirement. |
| `prototype-scenarios.md` | Will define happy-path and safety/recovery walkthroughs. |
| `content-and-safety-language.md` | Will lock Thai labels and prohibited wording. |
| `api-screen-contract-map.md` | Will connect approved UI states to the FastAPI boundary. |

This repository stores no Figma access token, participant identity, raw
recording, raw transcript, audio bytes, or clinical storage key. Prototype
walkthroughs use synthetic values and a synthetic child code such as `LL-0007`.

## Research and design lineage

The design retains the useful communication pattern shown in `Term2.pdf`:
conceptualization, UX/UI design, application architecture, storyboard,
showcase, and feature comparison (pages 21, 24–26, and 33–37). It extends that
pattern with task analysis, evidence traceability, safety branches, accessibility
checks, and a FastAPI handoff contract before production frontend work begins.

The research shortlist is used as a design constraint, not as clinical
validation of this product. In particular, it motivates follow-up after
screening, abstention/indeterminate states, protocol and language compatibility,
prosody as one evidence channel, human accountability, and resource-aware
referral.

## Figma workspace status

The working file is [`LinguaLens — Therapist Assessment Workflow v0.1`](https://www.figma.com/design/YOh8m47gDzPuX2EBZsPCcy).
The authenticated Figma Starter plan allows three pages, so the nine logical
workstreams are represented as ordered top-level sections across three pages:

```text
00_Cover_and_Changelog
01_Research_and_Requirements

02_Information_Architecture_and_Flows
03_Low_Fidelity_Wireframes

04_Design_System_and_Components
05_High_Fidelity_Screens
06_Clickable_Prototype
07_Usability_and_Iterations
08_Developer_Handoff
```

This is an external account limitation, not an intentional reduction of the
design scope. The compact skeleton has been created, including the high-fidelity
screen inventory, component inventory, and prototype entry cards. Additional
prototype wiring, export, and accepted-version freeze remain pending until the
Figma MCP allowance is available again or the file plan is upgraded.

## Acceptance notes

The prototype is not usability validated until a documented ethics/advisor
boundary permits formative evaluation. If recruitment is not authorized, the
workspace must explicitly report `expert review only — not usability validated`.
