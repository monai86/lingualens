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

## A1 durable processing-state delta

The local contract now specifies the H10/H11/E07/E09 states for queued,
running, retry-scheduled, failed, user-cancelled, system-cancelled/stale, and
succeeded evidence processing, including backend-provided `can_retry` and
`can_cancel` actions. The Figma file still requires an authenticated edit,
Presentation-mode walkthrough, accessibility inspection, synthetic export and
freeze evidence before those states can be marked accepted. This manifest
therefore remains `working skeleton`; local documentation must not be treated
as proof that the Figma nodes were updated.
