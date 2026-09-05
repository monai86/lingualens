# Prototype Scenarios and Workflow Branches

**Data policy:** all scenarios use synthetic values. The child code `LL-0007`
is a placeholder only; no name, audio, transcript, or participant data is stored
in the repository or Figma file.

## Information architecture

The therapist-facing information architecture has four primary destinations:

```text
Today | Children | Assessments | Reports
```

`Organization` and `Account` are secondary settings. Processing jobs, provider
names, feature schema versions, audit records, and research exports are reached
through contextual detail or authorized settings, not primary therapist
navigation.

The labels map to the existing canonical web routes without creating a second
route family:

| IA label | Canonical runtime entry |
|---|---|
| Today | `/today` |
| Children | `/cases` (scoped child/case list) |
| Assessments | `/cases?intent=start-session`, then `/sessions/{sessionId}?view=...` |
| Reports | `/reports`, opening the Session Workspace editor |
| Organization/Account | `/settings` with role-gated sections |

## Main scenario: `P01_Happy_Path_Desktop`

### Goal

Complete a developmental follow-up for synthetic child `LL-0007`, review the
available evidence, record a clinician-owned next action, and reach a signed
report without an automated diagnosis or numeric ASD probability.

### Path

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
  -> Finalized assessment
```

### Walkthrough assertions

1. The selected purpose remains visible after the protocol is reviewed.
2. A recording is impossible until the consent gate and role boundary pass.
3. Every result has evidence, limitation, and next-action content.
4. Feature values, developmental domains, attention cues, trends, and
   clinician-authored text remain visibly separate.
5. A disagreement changes the clinician response, not the computed evidence.
6. Finalization shows an immutable signed snapshot and an amendment path.

## Recovery scenario: `P02_Consent_and_Quality_Recovery_Tablet`

1. Begin with the child workspace and enter `H05 Assessment purpose`.
2. Select developmental follow-up and open `H06 Consent confirmation`.
3. Set the synthetic consent state to withdrawn and enter `E03`.
4. Confirm that recording controls are absent or disabled and that no
   assessment record is created when the server ID does not exist.
5. Follow the consent action or return safely to the child workspace.
6. Restart with valid synthetic consent, enter guided capture, and route an
   insufficient-child-speech result to `E04`.
7. Select `บันทึกตัวอย่างเพิ่มเติม`, return to capture, and continue to
   processing only after a usable sample is available.

## Evidence scenario: `P03_Profile_and_Trend_Review_Desktop`

1. Open a completed synthetic assessment at the developmental profile.
2. Open a domain detail and inspect measured features, observations, conflicts,
   provenance, and limitations.
3. Return to the profile without losing the prior scroll position.
4. Open longitudinal comparison. Show dated compatible values and a table.
5. Introduce a mismatched protocol and route to `E08`.
6. Record `ขอข้อมูลที่เปรียบเทียบได้เพิ่มเติม`; do not draw a forced trend.
7. Disagree with one attention cue, record a rationale, and verify that the
   original computed cue remains available for audit.

## Safety and recovery branches

| branch_id | trigger | visible state | required recovery or safe exit | rejoins |
|---|---|---|---|---|
| `E01` | API unreachable | Generic offline/error banner with no clinical payload. | Retry; if no server identifier exists, leave without creating a local clinical record. | Prior screen or `H03` |
| `E02` | Permission denied | Role/care-team restriction with generic explanation. | Return to scoped child list; do not reveal the restricted record. | `H03` |
| `E03` | Consent absent or withdrawn | Blocking consent state; recording unavailable. | Review consent action or return; no capture and no assessment transition. | `H04` or `H06` |
| `E04` | Insufficient audio | Quality issue explains child speech/volume/noise problem. | Record an additional sample or stop with limitation. | `H08` or `H10` |
| `E05` | Reference unavailable | Descriptive evidence only; no reference-band status. | Continue with within-child evidence or request compatible reference. | `H12-H16` |
| `E06` | Conflicting evidence | Indeterminate cue with supporting and conflicting evidence. | Request targeted evidence or clinician review. | `H16-H17` |
| `E07` | Dependent result stale | Stale result excluded from current report. | Reprocess changed input or review the current dependency. | `H10-H12` |
| `E08` | Prior assessment incompatible | Not-comparable message with mismatch reason. | Record request for compatible evidence; do not show a trend. | `H15-H17` |
| `E09` | Partial processing failure | Successful channels preserved; failed channel labeled unavailable. | Retry failed channel or continue with limitation. | `H10-H12` |
| `E10` | Session timeout or unsaved note | Visible draft status; submit/sign-off blocked. | Reauthenticate and confirm the preserved draft before submit. | Current screen |

## Validation checklist

- Walk `P01` from Today to finalized assessment with mouse and keyboard.
- Walk `P02` through withdrawn consent and insufficient audio.
- Walk `P03` through conflicting evidence, disagreement, and incompatible
  longitudinal data.
- Confirm every branch states what was preserved, what is blocked, and what to
  do next.
- Search all frame copy for prohibited diagnosis/probability wording.
