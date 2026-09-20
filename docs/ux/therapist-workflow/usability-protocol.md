# Formative Therapist Usability Protocol

**Status:** expert review only — not usability validated  
**Ethics boundary:** no recruitment, participant recording, patient case, or
identifiable data is permitted until the advisor/institution provides a written
ethics and consent determination.

## Objective

Evaluate whether a therapist can complete the assessment workflow, recover from
blocking states, distinguish evidence from interpretation, and record a
clinician-owned next action without mistaking the interface for an automated
diagnosis.

## Test material and privacy

- Use synthetic child code `LL-0007` only.
- Use invented feature values, quality indicators, and transcript fragments.
- Do not use patient data, a real child name, a real workplace, audio bytes, or
  a participant's identifiable free text.
- Store role category and experience band only if a study is authorized.
- Do not store participant names, contact details, workplace, patient
  population, raw recordings, screen recordings, or transcripts in this repo.

## Moderator script

1. Explain that the prototype organizes evidence and does not diagnose.
2. Give the task card without teaching navigation.
3. Observe mouse and keyboard paths separately where possible.
4. Record completion, assistance, critical error, time on task, and a 1–7 ease
   rating after each task.
5. Do not correct a participant during a task unless safety requires stopping.
6. Ask the safety comprehension question after T4.

## Tasks

| task_id | task | success criteria |
|---|---|---|
| `T1` | Find the child due for follow-up and start the correct assessment purpose. | Correct synthetic child and purpose selected; no navigation help. |
| `T2` | Respond safely when consent is withdrawn. | Participant stops before recording and finds safe return/consent action. |
| `T3` | Capture audio and recover from insufficient child speech. | Participant identifies the quality issue and records an additional sample or safe limitation. |
| `T4` | Explain what the profile says, what it does not say, and why one trend is unavailable. | Participant locates evidence/limitation/next action and understands the trend restriction. |
| `T5` | Disagree with one attention cue, record rationale, and prepare a report without changing computed evidence. | Participant changes clinician response only; computed cue remains preserved; no premature sign-off. |

After T4 ask exactly:

> Does this screen tell you that the child has ASD?

Desired answer: no. The participant should explain that the screen organizes
evidence and suggests next assessment actions for professional review.

## Acceptance thresholds

The first round passes only if all of the following are true:

- at least four of five authorized participants complete T1, T3, and T5
  without moderator navigation help;
- all five stop at withdrawn consent in T2;
- all five identify that T4 is not an ASD diagnosis or probability;
- all five locate evidence limitations and the next action;
- no participant signs while a blocking readiness gate is visible; and
- no unresolved severity-3 or severity-4 finding remains.

If fewer than five participants are authorized or recruited, report counts and
the limitation; do not convert a small sample into percentages or claim that the
threshold passed.

## Analysis and iteration

Group observations under navigation, comprehension, clinical safety,
accessibility, and recovery. Preserve original findings. Revise the smallest
responsible component or flow and retest each affected critical task with at
least two people who did not see the revised path, only when the study is
authorized.
