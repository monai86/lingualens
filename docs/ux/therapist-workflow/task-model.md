# Therapist Task Model

## Primary goal

> Complete one defensible developmental assessment while preserving consent,
> evidence quality, clinician accountability, and an auditable next action.

The task model is deliberately outcome-oriented. A screen is successful only
when the therapist can explain what was collected, what is limited, what needs
attention, and what action they own next.

## Task hierarchy

```text
Goal: complete one defensible developmental assessment
  1. Select the correct child and verify context
  2. Choose assessment purpose and confirm consent
  3. Follow a guided protocol and capture usable evidence
  4. Resolve uncertain data and inspect the developmental profile
  5. Record disposition and prepare a clinician-owned report
```

## Task details

| task | trigger | information needed | primary action | completion evidence | recoverable errors | unrecoverable stop | data that must not appear in logs |
|---|---|---|---|---|---|---|---|
| 1. Select child and verify context | Therapist opens Today or Children to begin planned work. | Scoped child code, age at assessment, language context, consent status, assigned care team, latest assessment purpose/state. | Open the intended child workspace and confirm the context is correct. | Child workspace shows the scoped record, active access, consent state, latest assessment, and next evidence suggestion. | Search miss, stale list, wrong filter, API retry, permission denied with safe return. | No authorized access, ambiguous child selection that cannot be resolved, or missing required context. | Child name/code, date of birth, transcript, audio filename/key, raw URL, clinical note, or search text containing an identifier. |
| 2. Choose purpose and confirm consent | Therapist starts an assessment from the child workspace. | One of four purposes, protocol suggestion, consent purpose/scope/version/status, role and care-team boundary. | Choose purpose, review protocol, and explicitly confirm valid consent before capture. | Assessment draft is created by FastAPI only after the purpose and consent gate pass. | Change purpose, inspect consent detail, renew/withdraw consent, return without creating a record, session timeout before submit. | Consent absent/withdrawn, role not permitted, or policy conflict. Recording and clinical write remain blocked. | Consent text, child identifier, exact protocol answers, auth token, or storage key. |
| 3. Capture guided interaction | A valid assessment is ready for capture. | One activity prompt, participant roles, expected duration, recording permission, device state, protocol rationale. | Start/pause/stop the current activity and add another sample when quality is insufficient. | Recording intent and quality result are stored server-side; therapist can see what was preserved and whether processing may continue. | Permission prompt, pause/resume, low volume, noise, insufficient child speech, speaker separation issue, upload retry. | Consent withdrawal, unrecoverable storage/auth failure, or a policy block. No fabricated recording or quality result. | Audio bytes, raw waveform, raw filename, storage key, participant identity, and exact utterances. |
| 4. Resolve data and inspect profile | Processing finishes or returns a partial/limited result. | Processing stage, transcript uncertainty markers, audio replay control, feature provenance, quality, domain evidence, conflicts, compatible prior data. | Review uncertain transcript segments, attest the usable text, inspect features/domains, and request more evidence when needed. | Current evidence is labeled sufficient/insufficient/unavailable/stale; profile exposes supporting/conflicting evidence and limitations. | Retry partial processing, reprocess stale input, mark a transcript segment uncertain, open domain detail, acknowledge/disagree with a cue, record more evidence. | Current input cannot be trusted, signed/attested dependency is missing, or no safe provenance is available. Dependent results remain ineligible. | Transcript text, audio content, child code, model input, storage key, raw feature payload, or clinical interpretation. |
| 5. Record disposition and report | Profile review is complete enough for clinician decision-making. | Evidence sufficiency, attention cues, limitations, comparable trends, clinician identity, disposition options, report readiness gates. | Choose or write a clinician-owned next action, edit the draft report, and sign off only when gates are visible and satisfied. | Report contains reviewed evidence, limitations, author, timestamp, signed snapshot/version, and follow-up action; amendments create a new draft revision. | Return to profile, request more evidence, choose monitoring/repeat/evaluation/intervention/referral, save draft, reauthenticate after timeout. | Blocking evidence/consent/role/signature/audit gate; no sign-off or export occurs. | Report excerpt, diagnosis text, child identifier, clinician name, raw evidence, or storage key in operational logs. |

## State and recovery rules

- The primary action must be visible and singular for each task. Secondary
  actions may preserve or recover work but must not compete with the task goal.
- A recovery action must state whether the server record exists. If an API call
  fails before a server identifier exists, the client must not create a local
  clinical record or claim that work was saved.
- Missing, stale, conflicting, or unavailable evidence is shown as a limitation,
  never as zero, normal, negative, or a hidden omission.
- A therapist's disagreement with a computed attention cue preserves the
  computed cue and stores the clinician response separately.
- A signed report is immutable. A later correction creates a draft revision
  linked to the signed version.

## Observability boundary

Product logs may contain route templates, correlation IDs, operation outcome,
workflow state, sanitized error codes, latency, and version metadata. They must
not contain identifiers, transcript text, audio content, raw filenames, storage
keys, report excerpts, or clinical content. The UI may display scoped clinical
content to an authorized therapist, but that does not permit copying it into
logs, analytics, fixtures, or research artifacts.

## Walkthrough scenario

Use only synthetic child code `LL-0007`:

> Open the child due for developmental follow-up, choose the follow-up purpose,
> discover that consent has been withdrawn, and recover safely.

Pass criteria: the reviewer understands the reason capture is blocked, can find
the consent action or safe return, and cannot reach recording through a hidden,
hover-only, or stale client action.
