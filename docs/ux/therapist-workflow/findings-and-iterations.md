# Safety, Accessibility, and Heuristic Findings

**Review status:** internal artifact review complete for the repository pack;
Figma prototype review and therapist usability validation are pending.  
**Usability status:** expert review only — not usability validated.

## Clinical-safety review

| check | result | evidence or limitation |
|---|---|---|
| Can the therapist see evidence quality? | Pass in content contract; prototype pending | `content-and-safety-language.md`; H09/H12/H14 are inventoried but not fully reviewed in Presentation mode. |
| Can the therapist see limitations? | Pass in content contract; prototype pending | Required sentence pattern and E05/E07/E08 states are documented. |
| Is the next action visible? | Pass in task model; prototype pending | Every task and safety branch names a recovery/next action. |
| Can multiple concerns coexist? | Pass in content contract; prototype pending | Concern vocabulary is explicitly non-exclusive. |
| Is insufficient evidence distinct from no concern? | Pass | `ข้อมูลยังไม่เพียงพอ` is a dedicated state and zero/normal/negative substitution is prohibited. |
| Is trend distinct from ASD severity? | Pass | Trend is defined as dated compatible change; no severity scale is permitted. |
| Is diagnosis visibly clinician-authored? | Pass | `ข้อสรุปที่บันทึกโดยผู้เชี่ยวชาญ` and sign-off ownership are required. |
| Can computed evidence be preserved after disagreement? | Pass in workflow rule; prototype pending | The task model preserves the computed cue and stores clinician response separately. |

## Accessibility review

| check | result | follow-up |
|---|---|---|
| Normal text contrast ≥ 4.5:1 | Token decision recorded | Verify every rendered Figma component after the MCP allowance returns. |
| Non-text contrast ≥ 3:1 | Token decision recorded | Inspect borders, focus ring, controls, and status shapes. |
| Touch target ≥ 44×44px | Required by token contract | Measure interactive variants in Figma and implementation. |
| Keyboard focus order | Required by flow contract | Traverse each prototype branch with keyboard. |
| 200% zoom/reflow | Required by frame inventory | Validate tablet/mobile variants and long Thai wrapping. |
| Non-color meaning | Pass in content contract; prototype pending | Pair every status with text, icon, and shape. |
| Reduced motion | Not yet verified | Add explicit transition rule before accepted freeze. |
| Error announcement | Required by content contract; prototype pending | Verify aria-live equivalent in the web implementation. |
| Accessible chart table | Pass as design rule | Line charts require a data-table alternative; no radar chart. |

## Ten-heuristic pass

The following is a pre-usability baseline. Severity `3` or `4` blocks formal
testing until resolved.

| finding_id | heuristic | severity | finding | status |
|---|---|---:|---|---|
| `UX-01` | Visibility of system status | 2 | Processing and partial-result states are specified but require a Presentation-mode walkthrough. | Open — Figma validation pending |
| `UX-02` | Match with the real world | 1 | Therapist language, guided activities, and Thai labels match the task model. | Recorded |
| `UX-03` | User control and freedom | 2 | Recovery routes are specified; back-navigation and preserved scroll still need prototype validation. | Open — Figma validation pending |
| `UX-04` | Consistency and standards | 1 | Shared semantic tokens and state names are locked in the draft contract. | Recorded |
| `UX-05` | Error prevention | 1 | Consent, role, stale, and sign-off gates are explicit. | Recorded |
| `UX-06` | Recognition rather than recall | 2 | Evidence/limitation/next-action sentence pattern is specified; visual density needs review. | Open — Figma validation pending |
| `UX-07` | Flexibility and efficiency | 2 | Uncertain transcript segments are prioritized; keyboard path is not yet walked. | Open — Figma validation pending |
| `UX-08` | Aesthetic and minimalist design | 2 | Progressive disclosure is specified; high-fidelity screens are inventory cards pending content fill. | Open — Figma validation pending |
| `UX-09` | Help users recover from errors | 1 | All E01–E10 branches have explicit next actions. | Recorded |
| `UX-10` | Help and documentation | 1 | API mapping, safety copy, and task model are repository-backed. | Recorded |

## External blockers

1. The Figma Starter plan permits only three pages; nine logical workstreams are
   represented as ordered sections instead.
2. The Figma MCP Starter allowance was exhausted during skeleton construction;
   prototype-link completion, Presentation-mode walkthroughs, and exports are
   pending.
3. No participant recruitment is authorized; the protocol must remain marked
   not usability validated.

These are declared limitations, not evidence that the unverified prototype has
passed its acceptance boundary.
