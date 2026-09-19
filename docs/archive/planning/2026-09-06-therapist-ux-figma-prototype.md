# Therapist UX and Figma Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a research-traceable, clinically safe, accessible Figma prototype that lets a therapist complete LinguaLens's five-step assessment workflow and generates publication-ready UX artifacts before frontend implementation.

**Architecture:** Treat Figma as the executable interaction specification for the primary therapist web experience, not merely a collection of attractive screens. The Figma file is organized from evidence and task flows through low-fidelity frames, reusable components, high-fidelity responsive screens, prototype branches, usability iterations, and developer handoff. Repository documents bind every critical screen to the approved workflow, API contract, safety rule, and research evidence.

**Tech Stack:** Figma and FigJam, WCAG 2.2 AA review, Thai-first clinical content, Noto Sans Thai, desktop/tablet responsive frames, Markdown/CSV/JSON handoff artifacts, synthetic test scenarios.

---

## Plan position

This is **Plan 0** of the developmental-profile redesign. It may run in parallel with [Foundation V2](2026-09-06-assessment-foundation-v2.md), but it must be accepted before Capture or therapist-web implementation begins.

Plan 0 does not create production frontend code. `TDD_REQUIRED: no` because this slice produces design and research artifacts only. Its equivalent quality gates are scenario walkthroughs, component-state coverage, accessibility inspection, clinical-safety comprehension checks, and formative usability evidence.

## Relationship to the senior project

`/Users/porschecaa/Downloads/Term2.pdf` uses this project sequence:

```text
Conceptualization
  -> Designing UX/UI and features
  -> Application development
  -> Application testing
  -> Deployment
```

The relevant examples are PDF pages 21, 24–26, and 33–37: method overview, hand sketch, Figma layout, exported UX/UI design, application architecture, frontend/backend flowchart, storyboard, application showcase, and feature-comparison table.

LinguaLens will retain those useful deliverables and strengthen them with:

- explicit therapist task analysis rather than screens derived only from a feature list;
- evidence traceability to the approved paper shortlist;
- alternative/error states, not only the happy path;
- concern, trend, and diagnosis semantic separation;
- a no-numeric-ASD-probability safety rule;
- keyboard, contrast, text-scaling, and non-color accessibility checks;
- a moderated formative usability protocol with synthetic child data;
- an exact Figma-to-FastAPI handoff map.

## Acceptance boundary

Plan 0 is accepted only when:

1. the Figma file contains all nine required pages and the named frame inventory below;
2. a clickable prototype covers the main therapist workflow and all ten safety/error branches;
3. every computed result displays evidence, limitation, and next action;
4. measured feature, developmental domain, attention cue, trend, and clinician-authored diagnosis are visually and semantically distinct;
5. no screen shows an automated diagnosis or numeric ASD probability;
6. all clinical screens work at desktop and tablet sizes, while critical capture/recovery actions remain usable at mobile size;
7. keyboard, focus, contrast, zoom, and non-color meaning checks pass;
8. at least one formative usability round is completed under the approved ethics/advisor boundary, or the prototype is explicitly marked `not usability validated` if recruitment is not authorized;
9. every critical screen maps to an API state, response, or error code without inventing local clinical data;
10. exported figures are synthetic, de-identified, reproducible, and suitable for the research report.

## Figma file structure

Create one Figma design file named `LinguaLens — Therapist Assessment Workflow v0.1` with these pages in this order:

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

Use these frame prefixes consistently:

```text
R = research artifact
F = user/task flow
L = low-fidelity wireframe
C = component or component state
H = high-fidelity screen
P = prototype starting point
U = usability evidence or revision
D = developer handoff
```

## Repository artifact map

Create only documentation artifacts in this slice:

```text
docs/ux/therapist-workflow/
├── README.md
├── evidence-matrix.md
├── task-model.md
├── content-and-safety-language.md
├── frame-inventory.csv
├── prototype-scenarios.md
├── usability-protocol.md
├── usability-observation-sheet.csv
├── findings-and-iterations.md
├── figma-delivery-manifest.md
├── api-screen-contract-map.md
└── design-tokens.draft.json
```

The repository stores no Figma access token, participant identity, raw interview recording, child identifier, transcript, or audio.

### Task 1: Build the evidence and requirement traceability pack

**Files:**

- Create: `docs/ux/therapist-workflow/README.md`
- Create: `docs/ux/therapist-workflow/evidence-matrix.md`
- Create: `docs/ux/therapist-workflow/task-model.md`
- Reference: `docs/superpowers/specs/2026-09-06-developmental-profile-workflow-redesign.md`
- Reference: `/Users/porschecaa/Downloads/Term2.pdf`

- [ ] **Step 1: Create the workspace README with the fixed design question.**

Use this question verbatim:

> How might LinguaLens help a therapist collect sufficient developmental evidence, understand what requires attention, compare compatible prior assessments, and record a clinician-owned next action without presenting automated diagnosis?

Record the primary user as therapist/clinician, secondary users as clinical supervisor and authorized researcher, and explicitly exclude caregiver self-diagnosis and automated diagnostic use.

- [ ] **Step 2: Create the evidence matrix.**

Use columns:

```text
requirement_id | source | evidence_or_constraint | design_implication | figma_frames | validation_method
```

Include at minimum:

| ID | Source | Required implication |
|---|---|---|
| `REQ-01` | Approved spec §5 | Five-step therapist workflow |
| `REQ-02` | Approved spec §6 | Feature → domain → clinical attention hierarchy |
| `REQ-03` | Approved spec §7 | Concern, trend, and diagnosis remain separate |
| `REQ-04` | Approved spec §8 | Compare only compatible prior assessments |
| `REQ-05` | Approved spec §12 | Explicit offline, insufficient, stale, and partial states |
| `REQ-06` | Approved spec §13 | Consent and role boundaries remain visible |
| `REQ-07` | `XSIL8EJU` | Screening requires follow-up and Thai-context interpretation |
| `REQ-08` | `2M5MN383` | Indeterminate/abstention and referral path are first-class |
| `REQ-09` | `KMH2LMXK` | Task/language generalization limits must be visible |
| `REQ-10` | `H7DB7I5I` | Prosody is one evidence channel, never a standalone diagnosis |
| `REQ-11` | `IZZE6KCS` | Consent, privacy, fairness, human accountability, and limits |
| `REQ-12` | `ZGS6NEZB` | Resource-aware next actions and referral |
| `REQ-13` | Term2 PDF pages 24–26 | Sketch, Figma layout, and complete screen overview |
| `REQ-14` | Term2 PDF pages 33–37 | Architecture, flowchart, storyboard, showcase, comparison |

- [ ] **Step 3: Define the therapist task model.**

Document this hierarchy:

```text
Goal: complete one defensible developmental assessment
  1. Select the correct child and verify context
  2. Choose assessment purpose and confirm consent
  3. Follow a guided protocol and capture usable evidence
  4. Resolve uncertain data and inspect the developmental profile
  5. Record disposition and prepare a clinician-owned report
```

For each task specify trigger, information needed, primary action, completion evidence, recoverable errors, unrecoverable stop, and data that must not appear in logs.

- [ ] **Step 4: Validate traceability before opening Figma.**

Expected result: all 14 requirement IDs have a design implication and validation method; no implication contains automated diagnosis or numeric ASD probability.

- [ ] **Step 5: Commit Task 1 artifacts.**

```bash
git add docs/ux/therapist-workflow/README.md docs/ux/therapist-workflow/evidence-matrix.md docs/ux/therapist-workflow/task-model.md
git commit -m "docs(ux): define therapist workflow requirements" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 2: Define information architecture and complete workflow branches

**Files:**

- Create: `docs/ux/therapist-workflow/prototype-scenarios.md`
- Create: `docs/ux/therapist-workflow/frame-inventory.csv`
- Modify: Figma page `02_Information_Architecture_and_Flows`

- [ ] **Step 1: Create the top-level information architecture.**

Use four primary destinations only:

```text
Today
Children
Assessments
Reports
```

Keep Organization and Account settings secondary. Processing jobs, provider names, feature schema versions, audit records, and research exports are not primary therapist navigation.

- [ ] **Step 2: Draw the main FigJam flow.**

Create `F01_Main_Therapist_Workflow`:

```text
Today
  -> Select child
  -> Child workspace
  -> Start assessment
  -> Purpose + consent
  -> Protocol review
  -> Guided capture
  -> Quality decision
  -> Processing status
  -> Transcript uncertainty review
  -> Evidence sufficiency
  -> Developmental profile
  -> Attention cue review
  -> Clinical disposition
  -> Report preparation
  -> Clinician sign-off
```

- [ ] **Step 3: Draw ten explicit alternate branches.**

Create `F02_Safety_and_Recovery_Branches` with these IDs:

| ID | Trigger | Required recovery |
|---|---|---|
| `E01` | API unreachable | show offline state; retry; create no server/local clinical record |
| `E02` | permission denied | explain role/care-team restriction; return to child list |
| `E03` | consent absent/withdrawn | stop capture; show consent action |
| `E04` | insufficient audio | explain quality issue; record additional sample |
| `E05` | reference unavailable | show descriptive evidence only |
| `E06` | conflicting evidence | show indeterminate cue and next evidence action |
| `E07` | dependent result stale | exclude from report; reprocess or review changed input |
| `E08` | prior assessment incompatible | explain why no trend is produced |
| `E09` | partial processing failure | preserve successful channels and label unavailable channel |
| `E10` | session timeout/unsaved note | preserve visible draft state; reauthenticate before submit |

- [ ] **Step 4: Populate the frame inventory.**

Use CSV columns:

```text
frame_id,page,name,viewport,user_goal,entry_condition,primary_action,success_exit,error_branches,requirements,notes
```

Inventory the 20 high-fidelity screens `H01`–`H20` defined in Task 5 and ten error/state variants `E01`–`E10`. Every frame must map to at least one `REQ` ID.

- [ ] **Step 5: Validate flow completeness.**

Walk the flow once from `Today` to `Finalized report`, once through `E03`, once through `E04`, once through `E07`, and once through `E08`. Expected: every branch has a visible next action and rejoins or safely exits the workflow.

- [ ] **Step 6: Commit Task 2 repository artifacts.**

```bash
git add docs/ux/therapist-workflow/prototype-scenarios.md docs/ux/therapist-workflow/frame-inventory.csv
git commit -m "docs(ux): map therapist assessment flows" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 3: Produce low-fidelity wireframes before visual styling

**Files:**

- Modify: Figma page `03_Low_Fidelity_Wireframes`
- Modify: `docs/ux/therapist-workflow/frame-inventory.csv`

- [ ] **Step 1: Create desktop and tablet layout shells.**

Use:

```text
Desktop: 1440 × 900, 12-column grid, 80px side margins, 24px gutters
Tablet portrait: 1024 × 1366, 8-column grid, 32px margins, 20px gutters
Mobile recovery/capture: 390 × 844, 4-column grid, 16px margins, 16px gutters
```

The desktop shell uses a persistent left navigation and contextual header. The tablet capture shell gives the activity prompt and record controls the largest visual area. Mobile is a compatibility view, not the preferred report-review surface.

- [ ] **Step 2: Wireframe the critical path.**

Create grayscale `L01`–`L20` frames corresponding one-to-one with `H01`–`H20`. Use real Thai interface labels and synthetic codes such as `LL-0007`; do not use lorem ipsum, a real name, or a real transcript.

- [ ] **Step 3: Enforce one primary action per screen.**

Examples:

```text
Child workspace          -> เริ่มการประเมิน
Purpose and consent      -> ยืนยันและเลือกกิจกรรม
Guided capture           -> เริ่มบันทึกเสียง
Audio quality            -> บันทึกตัวอย่างเพิ่มเติม
Transcript review        -> ยืนยันข้อความที่ตรวจแล้ว
Developmental profile    -> บันทึกการพิจารณาของนักบำบัด
Clinical disposition     -> เตรียมรายงาน
Report review            -> ลงนามรับรอง
```

- [ ] **Step 4: Run a paper-prototype walkthrough.**

Give a reviewer only this scenario: “Open child `LL-0007`, begin a developmental follow-up, discover that consent has been withdrawn, and recover safely.” Expected: the reviewer identifies the correct sequence without explanation and cannot reach recording.

- [ ] **Step 5: Revise wireframes until the walkthrough passes.**

Record each changed frame and reason in the frame inventory `notes` column. Do not begin colors or typography before the path passes.

### Task 4: Build the clinical design system and component states

**Files:**

- Create: `docs/ux/therapist-workflow/design-tokens.draft.json`
- Create: `docs/ux/therapist-workflow/content-and-safety-language.md`
- Modify: Figma page `04_Design_System_and_Components`

- [ ] **Step 1: Create Figma variables and repository tokens.**

Use these initial light-theme semantic tokens:

```json
{
  "color": {
    "primary": "#0E7490",
    "onPrimary": "#FFFFFF",
    "accent": "#047857",
    "onAccent": "#FFFFFF",
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "foreground": "#164E63",
    "mutedSurface": "#E8F1F6",
    "mutedForeground": "#475569",
    "border": "#64748B",
    "attention": "#B45309",
    "destructive": "#DC2626",
    "focus": "#0369A1"
  },
  "font": {
    "family": "Noto Sans Thai",
    "sizes": [12, 14, 16, 18, 24, 32],
    "lineHeightBody": 1.6
  },
  "space": [4, 8, 12, 16, 24, 32, 48],
  "radius": [4, 8, 12],
  "touchTargetMinimum": 44
}
```

The darker cyan and green replace the lighter search recommendations because white text on `#0891B2` and `#059669` did not reach 4.5:1; `#0E7490` and `#047857` do. The darker muted foreground and border also keep text and interactive boundaries distinguishable on both white and muted surfaces.

- [ ] **Step 2: Create text styles.**

Use Noto Sans Thai for headings and body so Thai glyph rhythm stays consistent. Create `Display/32`, `Heading/24`, `Title/18`, `Body/16`, `BodyStrong/16`, `Label/14`, and `Caption/12`. Body line height is at least 1.5 and long clinical text is limited to 75 characters per line.

- [ ] **Step 3: Create component sets with named states.**

Create:

```text
C01 Button: primary / secondary / tertiary / destructive × default / hover / focus / pressed / loading / disabled
C02 Text field: default / focus / filled / error / disabled / read-only
C03 Select and combobox: closed / open / selected / error / disabled
C04 Step indicator: current / complete / blocked / optional
C05 Assessment status: draft / capture / processing / review / ready / finalized / cancelled
C06 Evidence status: sufficient / attention / insufficient / unavailable / stale / not-assessed
C07 Attention cue card: unreviewed / acknowledged / disagreed / more-evidence-requested
C08 Quality issue card: blocking / non-blocking / resolved
C09 Recording control: idle / permission-request / recording / paused / saving / upload-pending / failed
C10 Transcript segment: certain / uncertain / edited / attested
C11 Trend row: improved / stable / attention / indeterminate / not-comparable
C12 Dialog: confirmation / destructive / consent-block / session-expired
C13 Banner: info / attention / error / offline / stale
C14 Skeleton and progress: loading / partial-complete / retryable-failure
C15 Table and chart fallback: visual / accessible-data-table
```

Every status uses icon, text, and shape in addition to color. Every interactive state has a visible 3px focus ring and at least a 44×44px target.

- [ ] **Step 4: Lock clinical-safety language.**

Use these Thai labels exactly in the first prototype:

```text
Clinical attention profile -> ประเด็นที่ควรพิจารณาเพิ่มเติม
Insufficient evidence      -> ข้อมูลยังไม่เพียงพอ
Reference unavailable      -> ไม่มีข้อมูลอ้างอิงที่เหมาะสม
Not comparable             -> ไม่สามารถเปรียบเทียบกับครั้งก่อนได้
Clinician diagnosis        -> ข้อสรุปที่บันทึกโดยผู้เชี่ยวชาญ
Safety boundary            -> ระบบช่วยจัดระเบียบหลักฐาน การวินิจฉัยเป็นหน้าที่ของผู้เชี่ยวชาญ
```

Prohibit `ตรวจพบออทิสติก`, `ไม่เป็นออทิสติก`, `ความน่าจะเป็น ASD`, `ASD score`, and any percentage next to an ASD-related cue.

- [ ] **Step 5: Validate tokens and components.**

Expected: normal text contrast is at least 4.5:1, non-text state contrast is at least 3:1, every component has keyboard focus, loading controls are disabled against duplicate submission, and no status relies on red/green alone.

- [ ] **Step 6: Commit design-system documents.**

```bash
git add docs/ux/therapist-workflow/design-tokens.draft.json docs/ux/therapist-workflow/content-and-safety-language.md
git commit -m "docs(ux): define clinical interface system" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 5: Design the complete high-fidelity therapist workspace

**Files:**

- Modify: Figma page `05_High_Fidelity_Screens`
- Modify: `docs/ux/therapist-workflow/frame-inventory.csv`

- [ ] **Step 1: Create the 20 canonical high-fidelity screens.**

| ID | Screen | Required content |
|---|---|---|
| `H01` | Sign in | organization-aware authentication; no clinical data |
| `H02` | Today | assigned follow-ups, drafts, processing items, explicit empty state |
| `H03` | Children | search by scoped code, filters, no names in synthetic prototype |
| `H04` | Child workspace | age/language, consent, latest assessment, concerns followed, compatible trends, next evidence |
| `H05` | Assessment purpose | four accepted purposes with concise descriptions |
| `H06` | Consent confirmation | purpose/scope/version/status and blocking consent action |
| `H07` | Protocol review | suggested activities, rationale, duration, therapist adjustment |
| `H08` | Guided capture | one activity, prompt, timer, recording control, participant roles |
| `H09` | Audio quality | volume/noise/child speech/separation/duration with concrete recovery |
| `H10` | Processing | stage list, partial success, retryable failure, safe navigation away |
| `H11` | Transcript review | uncertain segments first, audio replay, edit/accept, attestation |
| `H12` | Evidence sufficiency | available/missing/stale channels and next collection action |
| `H13` | Developmental profile | seven domains, descriptive status, evidence and limitation summaries |
| `H14` | Domain evidence detail | measured features, observations, conflicts, provenance disclosure |
| `H15` | Longitudinal comparison | compatible values, underlying dates/protocols, limitation, table fallback |
| `H16` | Attention cue review | non-exclusive cues, evidence, limitation, action, therapist response |
| `H17` | Clinical disposition | monitoring/evidence/evaluation/intervention/referral/other authored action |
| `H18` | Report preparation | editable clinician narrative and explicitly reviewed evidence |
| `H19` | Sign-off confirmation | assigned therapist, readiness gates, immutable snapshot warning |
| `H20` | Finalized assessment | signed version, audit summary, amendment path, follow-up action |

- [ ] **Step 2: Create responsive variants.**

Create desktop 1440×900 and tablet 1024×1366 variants for `H02`–`H20`. Create mobile 390×844 variants for `H02`, `H04`, `H06`, `H08`, `H09`, `H10`, and `E01`–`E04`. No variant may introduce or remove a clinical action; only information density and progressive disclosure may change.

- [ ] **Step 3: Separate the result concepts visually.**

Apply these fixed treatments:

```text
Measured feature       = neutral value row with unit, quality, and source
Developmental domain   = evidence summary card with descriptive status
Attention cue          = action-oriented review card without score/probability
Trend                   = dated comparable measurements plus line/table view
Diagnosis               = clinician-authored text block with author and timestamp
```

Do not use a radar chart for the developmental profile because it encourages false comparison across unlike domains. Use a vertical domain list. Use a line chart only when at least four compatible points exist; otherwise use dated value rows. Always provide a data table.

- [ ] **Step 4: Add `E01`–`E10` state frames.**

Each state frame must show what happened, what evidence is preserved, what the therapist can do next, and what action is blocked. It must not replace missing results with zero, normal, or negative evidence.

- [ ] **Step 5: Run the semantic safety inspection.**

Search all Figma text for `%`, `probability`, `ASD score`, `diagnosed by system`, `ตรวจพบออทิสติก`, and `ไม่เป็นออทิสติก`. Expected: no prohibited result wording. Percent signs are permitted only for operational quality such as upload progress when the label clearly says upload.

### Task 6: Build the clickable Figma prototype and storyboard

**Files:**

- Modify: Figma page `06_Clickable_Prototype`
- Modify: `docs/ux/therapist-workflow/prototype-scenarios.md`

- [ ] **Step 1: Create three prototype starting points.**

```text
P01_Happy_Path_Desktop
P02_Consent_and_Quality_Recovery_Tablet
P03_Profile_and_Trend_Review_Desktop
```

- [ ] **Step 2: Wire the happy path.**

`P01` must traverse `H02 -> H04 -> H05 -> H06 -> H07 -> H08 -> H09 -> H10 -> H11 -> H12 -> H13 -> H16 -> H17 -> H18 -> H19 -> H20` with predictable back navigation and preserved selections.

- [ ] **Step 3: Wire safety and recovery.**

`P02` first enters `E03` and returns to `H04` without creating an assessment. Its second branch reaches `E04`, records an additional sample, then continues through `H10`. `E01` offers retry only; it never opens fabricated child records.

- [ ] **Step 4: Wire evidence interpretation.**

`P03` opens a domain detail, exposes supporting and conflicting evidence, returns to profile without losing scroll position, opens a longitudinal view, encounters `E08`, and records a request for comparable evidence. It must be possible to disagree with an attention cue while preserving the computed cue.

- [ ] **Step 5: Create a publication-ready storyboard.**

On `06_Clickable_Prototype`, create `P04_Research_Storyboard` with eight numbered frames:

```text
1 Select child
2 Confirm purpose and consent
3 Follow guided activity
4 Resolve recording quality
5 Review uncertain transcript
6 Interpret evidence and compatible trend
7 Record clinical disposition
8 Prepare and sign report
```

This is the LinguaLens counterpart to Term2 PDF page 35, but it must show decision points and recovery, not just navigation arrows.

- [ ] **Step 6: Validate all prototype links.**

Start each prototype from Presentation mode, use mouse and keyboard separately, traverse every documented path, and confirm no dead end, hidden hover-only action, broken back route, or state reset.

### Task 7: Perform clinical-safety, accessibility, and heuristic review

**Files:**

- Create: `docs/ux/therapist-workflow/findings-and-iterations.md`
- Modify: Figma page `07_Usability_and_Iterations`

- [ ] **Step 1: Run the clinical-safety review.**

For every result screen answer yes/no with frame evidence:

```text
Can the therapist see evidence quality?
Can the therapist see limitations?
Is the next action visible?
Can multiple concerns coexist?
Is insufficient evidence distinct from no concern?
Is trend distinct from ASD severity?
Is diagnosis visibly clinician-authored?
Can computed evidence be preserved when the clinician disagrees?
```

Any `no` is a blocker.

- [ ] **Step 2: Run accessibility inspection.**

Inspect all primary frames for 4.5:1 normal-text contrast, 3:1 component contrast, 44×44px targets, visible focus order, 200% zoom reflow, no color-only meaning, Thai text wrapping, reduced-motion behavior, error announcements, and accessible table alternatives to charts.

- [ ] **Step 3: Run a ten-heuristic pass.**

Record findings under visibility, real-world match, user control, consistency, error prevention, recognition, efficiency, minimalist design, recovery, and help. Assign severity `0`–`4`, where `3` and `4` block usability testing.

- [ ] **Step 4: Resolve blocking findings in Figma.**

For every changed frame, place before/after variants on `07_Usability_and_Iterations`, connect the finding ID, and update the changelog on `00_Cover_and_Changelog`.

- [ ] **Step 5: Commit the review record.**

```bash
git add docs/ux/therapist-workflow/findings-and-iterations.md
git commit -m "docs(ux): review prototype safety and accessibility" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 8: Run formative therapist usability evaluation

**Files:**

- Create: `docs/ux/therapist-workflow/usability-protocol.md`
- Create: `docs/ux/therapist-workflow/usability-observation-sheet.csv`
- Modify: `docs/ux/therapist-workflow/findings-and-iterations.md`
- Modify: Figma page `07_Usability_and_Iterations`

- [ ] **Step 1: Establish the ethics and privacy boundary.**

Before recruitment or recording, obtain the advisor/institution's written determination about ethics review and consent. If human-participant work is not yet authorized, perform only an internal expert walkthrough and mark results `expert review only — not usability validated`.

Use synthetic child `LL-0007`, synthetic audio quality indicators, and invented transcript fragments. Do not use patient data or ask a participant to discuss an identifiable case.

- [ ] **Step 2: Write the moderated protocol.**

Use five tasks:

```text
T1 Find the child due for follow-up and start the correct assessment purpose.
T2 Respond safely when consent is withdrawn.
T3 Capture audio and recover from insufficient child speech.
T4 Explain what the profile says, what it does not say, and why one trend is unavailable.
T5 Disagree with one attention cue, record rationale, and prepare a report without changing computed evidence.
```

The moderator does not teach navigation. After each task collect completion, assistance, critical error, time on task, and a 1–7 ease rating. After T4 ask: “Does this screen tell you that the child has ASD?” The desired answer is no, followed by an explanation that it organizes evidence and suggests next assessment actions.

- [ ] **Step 3: Recruit a small formative sample only after authorization.**

Target five representative therapists/clinicians who may use the workflow. Record role category and experience band only; do not store name, workplace, contact detail, patient population, or identifiable free text in the repository.

- [ ] **Step 4: Apply the predefined acceptance thresholds.**

The prototype passes the first round when:

- at least four of five participants complete T1, T3, and T5 without moderator navigation help;
- all five stop at withdrawn consent in T2;
- all five identify that T4 is not an ASD diagnosis or probability;
- all five can locate evidence limitations and the next action;
- no participant signs a report while a blocking readiness gate is visible;
- no unresolved severity-3 or severity-4 finding remains.

If fewer than five participants are authorized or recruited, report counts rather than percentages and do not claim the thresholds passed.

- [ ] **Step 5: Iterate and retest affected tasks.**

Group failures by navigation, comprehension, clinical safety, accessibility, and recovery. Revise the smallest responsible component/flow, create before/after evidence, and retest each affected critical task with at least two people who did not see that revised path. Preserve the original findings.

- [ ] **Step 6: Commit de-identified research artifacts.**

```bash
git add docs/ux/therapist-workflow/usability-protocol.md docs/ux/therapist-workflow/usability-observation-sheet.csv docs/ux/therapist-workflow/findings-and-iterations.md
git commit -m "docs(ux): add therapist prototype evaluation" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 9: Create developer handoff and research-report figures

**Files:**

- Create: `docs/ux/therapist-workflow/api-screen-contract-map.md`
- Create: `docs/ux/therapist-workflow/figma-delivery-manifest.md`
- Modify: Figma page `08_Developer_Handoff`
- Modify: `docs/ux/therapist-workflow/README.md`

- [ ] **Step 1: Map screens to the FastAPI boundary.**

For each `H` and `E` frame record:

```text
frame | user intent | API operation | required role | success state | empty state | error code | retry behavior | local-data rule
```

Foundation endpoints map to `H03`–`H06`. Capture, Evidence, Clinical Review, and Longitudinal operations remain marked by their approved slice name rather than an invented endpoint. Every API failure maps to a visible error state; `local-data rule` is `no fabricated clinical record` for all screens.

- [ ] **Step 2: Build the Figma handoff page.**

Include annotated spacing, responsive behavior, component names, variable names, focus order, reading order, truncation/wrapping rules, loading behavior, empty/error states, and content ownership. Developers must be able to identify the Figma component and API state for every interactive element.

- [ ] **Step 3: Export the research artifact set.**

Export synthetic, de-identified figures as both PDF/SVG and 2× PNG:

```text
method-overview
therapist-task-flow
low-fidelity-sketch-overview
figma-layout-overview
ux-ui-screen-overview
system-architecture-context
frontend-backend-state-flow
assessment-storyboard
application-showcase
feature-and-safety-comparison
usability-iteration-before-after
```

These correspond to the useful reporting pattern in Term2 while adding evidence and validation artifacts. Store export paths, Figma file URL, file version label, export date, frame IDs, and SHA-256 values in `figma-delivery-manifest.md`. Do not store a private access token.

- [ ] **Step 4: Freeze the accepted prototype.**

Duplicate the accepted Figma version as `LinguaLens — Therapist Assessment Workflow v0.1 — Accepted`, make it view-only for the development handoff, and continue future edits in a new working version. Record the accepted URL and exact version label in the manifest.

- [ ] **Step 5: Run final Plan 0 verification.**

Verify:

```text
9 Figma pages present in order
20 canonical high-fidelity screens present
10 safety/error states present
3 prototype starting points and 1 storyboard present
14 requirements trace to frames and validation
all critical screens have desktop/tablet coverage
all capture/recovery screens have mobile coverage
no prohibited diagnosis/probability wording
no real child or participant data
all manifest exports exist and hashes match
all accepted usability blockers resolved or validation limitation declared
```

- [ ] **Step 6: Commit the handoff package.**

```bash
git add docs/ux/therapist-workflow
git commit -m "docs(ux): deliver therapist Figma handoff" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

## Resulting development order

```text
Plan 0: Evidence -> flow -> sketch -> Figma -> usability -> handoff
                         |
Plan 1: Foundation V2 --+--> Capture implementation
                              -> Evidence
                              -> Clinical Review
                              -> Longitudinal
                              -> Thin Clients
                              -> Pilot Validation
```

The Figma prototype constrains user experience and content; the FastAPI state machine remains the authority for workflow transitions. A clickable transition in Figma does not authorize a client to bypass consent, role, evidence-readiness, or audit policy.
