# Figma Delivery Manifest

**Working file:** [LinguaLens — Therapist Assessment Workflow v0.1](https://www.figma.com/design/YOh8m47gDzPuX2EBZsPCcy)  
**File key:** `YOh8m47gDzPuX2EBZsPCcy`  
**Working date:** 2026-09-06  
**Accepted version:** not frozen  
**Manifest status:** working skeleton; export and final acceptance pending

## Account and file constraints

The authenticated account is on the Figma Starter plan, which permits three
pages. The approved nine logical page names are preserved as ordered frames on
three pages rather than silently omitted. The Figma MCP allowance was exhausted
after the skeleton, so additional mutations and export operations remain
pending. No access token is stored here.

## Actual page and section map

| actual page | page node | logical sections | section node IDs |
|---|---|---|---|
| `00_Cover_and_Changelog` | `0:1` | `00_Cover_and_Changelog`, `01_Research_and_Requirements` | `3:4`, `3:5` |
| `02_Information_Architecture_and_Flows` | `2:4` | `02_Information_Architecture_and_Flows`, `03_Low_Fidelity_Wireframes` | `3:2`, `3:3` |
| `04_Design_System_and_Components` | `2:5` | `04_Design_System_and_Components`, `05_High_Fidelity_Screens`, `06_Clickable_Prototype`, `07_Usability_and_Iterations`, `08_Developer_Handoff` | `3:6`, `3:7`, `3:8`, `3:9`, `3:10` |

## Created working nodes

- Cover/research text nodes: `4:2`–`4:8`.
- High-fidelity inventory cards and labels: `5:2`–`5:41`, named `H01`–`H20`.
- Component inventory: `5:42`–`5:56`, named `C01`–`C15`.
- Prototype entry cards and labels: `5:57`–`5:64`, named `P01`–`P04`.
- `P01` has a working same-page navigation reaction to the high-fidelity
  section. Other links are not yet confirmed after the MCP allowance ended.

## Planned export set

The following exports are required by the plan but have not been generated:

| artifact | format | frame/source | status | sha256 |
|---|---|---|---|---|
| method-overview | PDF/SVG/2× PNG | `P04_Research_Storyboard` | not exported | — |
| therapist-task-flow | PDF/SVG/2× PNG | `F01_Main_Therapist_Workflow` | not exported | — |
| low-fidelity-sketch-overview | PDF/SVG/2× PNG | `L01-L20` | not exported | — |
| figma-layout-overview | PDF/SVG/2× PNG | `H01-H20` | not exported | — |
| ux-ui-screen-overview | PDF/SVG/2× PNG | `H01-H20` | not exported | — |
| system-architecture-context | PDF/SVG/2× PNG | `D01` | not exported | — |
| frontend-backend-state-flow | PDF/SVG/2× PNG | `F01-F02` | not exported | — |
| assessment-storyboard | PDF/SVG/2× PNG | `P04` | not exported | — |
| application-showcase | PDF/SVG/2× PNG | `H01-H20` | not exported | — |
| feature-and-safety-comparison | PDF/SVG/2× PNG | `C01-C15`, `E01-E10` | not exported | — |
| usability-iteration-before-after | PDF/SVG/2× PNG | `U01` | not exported | — |

## Freeze gate

This file must not be labeled accepted until the missing prototype links,
Presentation-mode walkthroughs, accessibility inspection, synthetic exports,
hashes, and version freeze are complete. The current state is intentionally
visible as `working skeleton` so downstream frontend work cannot mistake it for
a validated clinical interface specification.

## A2 segment-review handoff delta

The local developer handoff now adds the following logical frames to the
existing `H11` transcript-review family. These are contract frames for the
frontend/API implementation; they are not claims that the remote Figma file was
mutated or exported.

| logical frame | purpose | required visible state | FastAPI binding | local implementation |
|---|---|---|---|---|
| `H11-S` | Full segment timeline | Ordered offsets, speaker role, text, confidence, uncertainty label, revision/version | `GET /assessments/{id}/transcript-segment-set` | `AssessmentSegmentReviewWorkspace` timeline |
| `H11-U` | Uncertain-only focus | Filter count, explicit zero-match state, selected segment remains keyboard reachable | Same GET; client-side filter only | `uncertainOnly` view |
| `H11-E` | Focused edit | Text, speaker, offsets, confidence, uncertainty reason, dirty state, save revision | `POST /assessments/{id}/transcript-segment-sets` | Focused editor and expected revision/version |
| `H11-R` | Replay available/unavailable | Short-lived player or explicit unavailable message | `POST /transcript-segments/{id}/audio-replay-grant` | Signed grant player / non-fatal fallback |
| `H11-A` | Attestation | Explicit checkbox, disabled while dirty, server-confirmed state | `POST /transcript-segment-sets/{id}/attest` | Segment attestation panel |
| `E11` | Revision conflict | No silent merge, reload latest action, preserved server revision | `409 stale_segment_set_version` | Conflict alert + reload |

### Figma mutation and export status

No remote Figma mutation was performed in A2 because the previously recorded
MCP allowance is exhausted. The manifest, frame inventory, and API-screen map
are the source-controlled handoff for the next authenticated Figma session.
The existing `working skeleton` status remains unchanged; no export hash is
invented and no frame is marked accepted without Presentation-mode and
accessibility evidence.

## A1 durable processing-state delta

The local contract now specifies the H10/H11/E07/E09 states for queued,
running, retry-scheduled, failed, user-cancelled, system-cancelled/stale, and
succeeded evidence processing, including backend-provided `can_retry` and
`can_cancel` actions. The Figma file still requires an authenticated edit,
Presentation-mode walkthrough, accessibility inspection, synthetic export and
freeze evidence before those states can be marked accepted. This manifest
therefore remains `working skeleton`; local documentation must not be treated
as proof that the Figma nodes were updated.

## Antigravity U1 Handoff & Remote Delivery Boundary

As of 2026-09-12, the remote Figma environment lacks authenticated credentials
and MCP connectivity in this local execution runtime. In accordance with Section
5 of the master roadmap:
- **Remote delivery status**: `blocked` (authentication/MCP unavailable locally).
- **Local wireframes & specs**: Completed in `docs/ux/therapist-workflow/wireframes-and-screen-specs.md` covering all 5 therapist workflow steps, B/C comparison frames (`H14-NoHistory`, `H14-Incompatible`, `H14-Compatible`), clinician attention cues (`H15`), disposition drafting (`H18`), sign-off guards (`E18`), and immutable signed export (`H19`).
- **Checklist for next authenticated Figma session**:
  1. Authenticate with Figma API / MCP using therapist design account.
  2. Create/update node tree for `H12`–`H19` and `E18` per `wireframes-and-screen-specs.md`.
  3. Wire interactive prototype transitions for Steps 1–5 including error branches.
  4. Perform keyboard navigation & WCAG contrast audit on Thai text elements.
  5. Export 11 planned synthetic figures to `docs/ux/therapist-workflow/exports/`.
  6. Compute SHA-256 hashes of all exports and update the planned export set table in this manifest.
  7. Transition status from `working skeleton` to `accepted`.

