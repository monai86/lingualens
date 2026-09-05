# Evidence and Requirement Matrix

This matrix is the traceability contract for the first therapist workflow
prototype. A source can constrain design without validating the LinguaLens
implementation. `figma_frames` names the planned frame IDs; validation must be
completed before frontend implementation treats a frame as normative.

| requirement_id | source | evidence_or_constraint | design_implication | figma_frames | validation_method |
|---|---|---|---|---|---|
| `REQ-01` | Approved spec §5 | The therapist workflow has five visible steps: select child, start assessment, record guided interaction, review data/profile, and record disposition. | Use a persistent step indicator and one primary action per step; preserve progress and recovery. | `F01`, `L01-L20`, `H02-H20` | Moderated happy-path walkthrough; keyboard path; state-transition review. |
| `REQ-02` | Approved spec §6 | Extracted features support developmental domains and clinical attention, but a feature is not a diagnosis. | Present Feature → Domain → Attention as progressive disclosure with evidence and limitation text. | `H13-H16`, `C06-C07` | Content inspection and clinician comprehension check. |
| `REQ-03` | Approved spec §7 | Concern, trend, and diagnosis are different concepts. | Use distinct components, headings, semantics, and author metadata; never share a probability scale. | `H15-H20`, `C11` | Safety-language search; semantic review of screen copy. |
| `REQ-04` | Approved spec §8 | Longitudinal comparison is allowed only for compatible protocol, language, age/context, feature schema, and quality. | Show compatibility inputs and a visible `not comparable` state instead of forcing a trend. | `H04`, `H15`, `E08` | Compatibility counterexample walkthrough with mismatched protocol. |
| `REQ-05` | Approved spec §12 | Offline, insufficient, stale, partial, and unavailable states are explicit workflow states. | Every failure state explains preserved evidence, blocked action, retry/recovery, and safe exit. | `E01`, `E04`, `E07`, `E09`, `C13-C14` | Branch walkthrough and failure-state checklist. |
| `REQ-06` | Approved spec §13 | Consent and role boundaries gate capture and clinical access. | Show consent purpose, scope, version, status, and role/care-team boundary before recording. | `H05-H06`, `E02-E03`, `C12` | Withdrawn-consent task; permission-denied task; no-recording assertion. |
| `REQ-07` | `XSIL8EJU` | Thai screening evidence supports follow-up and Thai sociocultural interpretation rather than questionnaire-only decisions. | Offer a follow-up purpose and show local/context limitations beside screening-derived evidence. | `H05`, `H12-H17` | Evidence-matrix review; Thai-context content comprehension check. |
| `REQ-08` | `2M5MN383` | Indeterminate/abstention and referral paths are safety controls for complex cases. | Make insufficient, indeterminate, and referral actions first-class; never substitute a negative result. | `H12`, `H16-H17`, `E06` | Indeterminate scenario; verify no diagnosis/probability wording. |
| `REQ-09` | `KMH2LMXK` | Vocal-marker performance can change across tasks, datasets, and languages. | Bind evidence to protocol/language/task metadata and disclose reference-unavailable limitations. | `H07`, `H14-H15`, `E05`, `E08` | Cross-task/language compatibility counterexample. |
| `REQ-10` | `H7DB7I5I` | Natural-speech prosody is heterogeneous evidence and cannot stand alone. | Label prosody as one measured channel with voiced-coverage and task limitations; avoid a standalone cue. | `H14`, `C06-C07` | Feature-to-cue trace review; content inspection. |
| `REQ-11` | `IZZE6KCS` | AI/gadget use requires consent, privacy, fairness, human accountability, and limits on generalization. | Keep consent, provenance, limitations, clinician review, and privacy language visible at the relevant decision. | `H06`, `H14`, `H18-H20`, `C12-C13` | Safety and accessibility review; clinician accountability comprehension question. |
| `REQ-12` | `ZGS6NEZB` | Stepped care, task sharing, local adaptation, and resource-aware referral matter. | Offer practical next actions with resource-aware alternatives and clinician-authored referral/monitoring choices. | `H16-H18` | Disposition scenario; action discoverability walkthrough. |
| `REQ-13` | `Term2.pdf` pp. 24–26 | The senior project communicates early sketches, Figma layouts, and an overall UX/UI showcase. | Produce low-fidelity frames before high-fidelity screens and preserve a publication-ready screen overview. | `L01-L20`, `H01-H20`, `P04` | Paper-prototype walkthrough; frame inventory completeness check. |
| `REQ-14` | `Term2.pdf` pp. 33–37 | The senior project documents architecture, frontend/backend flow, storyboard, showcase, and feature comparison. | Add an explicit architecture/state-flow storyboard and a developer handoff mapping Figma states to FastAPI operations. | `F01-F02`, `P04`, `D01-D04` | API-screen contract review; end-to-end storyboard walkthrough. |

## Traceability rules

1. A frame may support multiple requirements, but every critical requirement must
   have a visible frame and a named validation method.
2. A validation method is not satisfied by a visual inspection alone when the
   requirement concerns comprehension, recovery, or clinical semantics.
3. A reference-band or trend display must expose compatibility and limitation
   information; missing reference data is not equivalent to a normal result.
4. Any copy that implies automated diagnosis, ASD probability, or a definitive
   negative must be treated as a blocker and removed.
