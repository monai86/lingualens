# API–Screen Contract Map

This map binds the prototype to the FastAPI boundary without inventing runtime
endpoints. Names such as `Capture slice` and `Evidence slice` are approved
workstream boundaries from the redesign spec; concrete routes are added only
when their slice is implemented and tested.

All rows use the local-data rule: **UI cache only; no fabricated clinical record
or result**. Supabase Auth may establish identity, but clinical reads, writes,
uploads, and workflow transitions pass through FastAPI.

| frame | user intent | API operation | required role | success state | empty state | error code/state | retry behavior | local-data rule |
|---|---|---|---|---|---|---|---|---|
| H01 | Sign in | Identity/auth session | Authenticated therapist | Authenticated | No clinical data | E01/E02 | Retry auth; no clinical payload | No local clinical record |
| H02 | See assigned work | Today slice: read assigned work | Therapist | Work list | No work requiring attention | E01 | Retry read | No fabricated work item |
| H03 | Find scoped child | Foundation: list accessible children | Therapist/care-team member | Scoped child list | No matching child | E01/E02 | Retry; safe return | No cached identifier promoted to record |
| H04 | Verify child context | Foundation: read child workspace | Therapist/care-team member | Context and latest assessment | No prior assessment | E02/E03 | Retry or return | No local child creation |
| H05 | Choose purpose | Foundation: create assessment draft | Therapist | Draft with purpose | No purpose selected | E01/E02 | Retry idempotently; do not duplicate | No draft without server ID |
| H06 | Confirm consent | Foundation: read/confirm consent | Therapist with valid role | Consent gate passed | Consent unavailable | E02/E03/E10 | Re-read consent; no capture | No local consent record |
| H07 | Review protocol | Protocol slice: propose/validate protocol | Therapist | Protocol ready | No compatible protocol | E01/E05 | Retry or choose supported action | No fabricated protocol |
| H08 | Capture activity | Capture slice: create recording intent/upload | Therapist with consent | Recording accepted | No sample | E03/E04/E10 | Retry upload or add sample | No local audio record |
| H09 | Resolve quality | Capture slice: evaluate recording quality | Therapist | Quality decision | Quality not available | E04/E09 | Add sample or retry quality | No fabricated quality result |
| H10 | Follow processing | `POST /assessments/{id}/evidence-runs`; `GET /assessments/{id}/evidence-processing-run`; `GET /processing-runs/{id}`; explicit retry/cancel | Therapist | Queued/running/succeeded/partial/cancelled state from FastAPI | Not started | E01/E07/E09 | Retry only when `can_retry=true`; cancel only when `can_cancel=true` | No fabricated completion or local job state |
| H11 | Attest transcript | Transcript slice: read uncertainty/attest; attestation unlocks the evidence enqueue endpoint | Therapist | Transcript dependency attested | No usable transcript | E07/E09/E10 | Reprocess current revision or save limitation | No local transcript source or evidence computation |
| H12 | Inspect sufficiency | Evidence slice: read sufficiency | Therapist | Sufficiency state | Insufficient/unavailable | E05/E06/E07/E09 | Request evidence or reprocess | No local evidence result |
| H13 | Review profile | Evidence slice: read developmental profile | Therapist | Domain list | Not assessed | E05/E07 | Retry or continue with limitation | No locally computed profile |
| H14 | Inspect domain evidence | Evidence slice: read feature/domain provenance | Therapist | Evidence detail | No compatible evidence | E05/E06/E07 | Retry; preserve limitation | No local feature payload |
| H15 | Compare prior data | Longitudinal slice: compatibility/read comparison | Therapist | Compatible dated values | Not comparable | E05/E08 | Request compatible evidence | No forced local trend |
| H16 | Review attention cues | Clinical review slice: read/record response | Therapist | Cue responses recorded | No cue/insufficient | E05/E06/E07 | Request more evidence | No local cue generation |
| H17 | Record disposition | Clinical review slice: save clinician disposition | Assigned therapist | Disposition saved | No disposition selected | E06/E07/E10 | Save draft; reauth if needed | No local sign-off state |
| H18 | Prepare report | Reporting slice: draft from current evidence | Assigned therapist | Editable draft | No report-ready evidence | E07/E10 | Resolve stale/blocking gate | No local report finalization |
| H19 | Sign off | Reporting slice: sign immutable snapshot | Assigned therapist | Signed snapshot/version | Readiness gate incomplete | E07/E10 | Resolve gates; no bypass | No local signature |
| H20 | Review finalized result | Reporting slice: read signed snapshot/amendment path | Authorized therapist/supervisor | Immutable signed view | No finalized assessment | E01/E10 | Retry read; amendment creates draft | No local mutation of signed result |
| E01 | Recover from API outage | Any applicable operation | Existing authorized role | Previous safe screen | No server record | `api_unreachable` | Retry only | Never create local clinical record |
| E02 | Recover from access denial | Foundation authorization check | Authorized role only | Scoped child list | Restricted record hidden | `permission_denied` | Return to list | Never cache restricted detail |
| E03 | Stop on consent failure | Consent gate | Therapist | Capture blocked | Consent action unavailable | `consent_blocked` | Review/return | Never emulate consent locally |
| E04 | Recover from poor sample | Capture quality operation | Therapist | Additional sample | No usable sample | `insufficient_audio` | Record additional sample | Never label sample usable locally |
| E05 | Review without reference | Evidence read | Therapist | Descriptive-only evidence | No reference | `reference_unavailable` | Continue with limitation | Never invent reference band |
| E06 | Resolve conflict | Clinical review read/write | Therapist | Evidence request/disposition | Conflict unresolved | `conflicting_evidence` | Request targeted evidence | Never collapse conflict locally |
| E07 | Rebuild stale result | Processing/evidence operation; current-run lookup returns only the current revision/contract | Therapist | Current dependency | Stale result excluded | `stale_result` / system-cancelled processing run | Enqueue current input; old run cannot be revived | Never report stale result or locally mutate run state |
| E08 | Explain incompatible trend | Longitudinal compatibility | Therapist | Not-comparable state | No trend | `incompatible_prior_assessment` | Request compatible evidence | Never draw forced trend |
| E09 | Continue partial result | Processing operation; read run state and evidence result separately | Therapist | Successful channels preserved | Failed channel unavailable | `partial_processing_failure` | Retry only from backend-provided action state | Never fill missing channel or synthesize completion |
| E10 | Reauthenticate draft | Auth/session operation | Therapist | Draft restored and confirmed | No recoverable draft | `session_expired` | Reauthenticate before submit | Never sign or submit offline |

## A2 segment-review delta (implemented contract)

The segment review screen is now a backend-owned refinement of `H11`. It never
creates timestamps, audio availability, clinical evidence, or a new revision in
the browser. The client keeps only an unsaved visual draft until FastAPI
accepts a new immutable segment-set revision.

| screen state | user intent | FastAPI operation | success state | safe empty/error state | client rule |
|---|---|---|---|---|---|
| `H11-S` full timeline | See every ordered segment and its uncertainty reason | `GET /api/v2/assessments/{assessment_id}/transcript-segment-set` | Current segment set, checksum, revision, speaker role, offsets | `segment_set_not_found` shows that the current transcript has no reviewable segment set; no placeholder timestamps are created | Render only the response returned by FastAPI |
| `H11-U` uncertain-only view | Focus on segments needing therapist attention | Same GET response; local filter only | All segments with `uncertainty_reason != none` remain available for focused review | Zero matches is an explicit empty state, not a normal/negative result | Filtering never changes server state |
| `H11-E` focused editor | Correct text, speaker role, offsets, confidence, or uncertainty reason | Local draft, then `POST /api/v2/assessments/{assessment_id}/transcript-segment-sets` | New immutable revision with server-computed checksum | `stale_segment_set_version` preserves the unsaved edit and asks for reload | Submit `expected_revision` and `expected_version`; never overwrite in place |
| `H11-R` replay | Listen to the selected time-bounded segment | `POST /api/v2/transcript-segments/{segment_id}/audio-replay-grant` | Short-lived signed URL plus bounded offsets and expiry | `available=false` states that audio is unavailable while text review remains usable | Never expose a storage key or permanent credential |
| `H11-A` segment attestation | Confirm the reviewed segment set is ready for evidence processing | `POST /api/v2/transcript-segment-sets/{id}/attest` | `review_state=attested`, actor/time/version captured by FastAPI | Stale version, transcript mismatch, consent, or role denial blocks attestation | Explicit checkbox and server response are both required |
| `E11` revision conflict | Recover when another revision wins | Reload current transcript + segment set | New current revision replaces the visible draft | Unsaved client edits are not silently merged or discarded | Show a safe reload action and preserve server state |
| `E12` replay unavailable | Continue without audio | Replay grant returns `available=false` | Therapist can still edit/attest text subject to normal gates | No fake waveform, no inferred audio quality, no blocked text review | Availability is shown with text and state, never color alone |

### Implementation references

- Client contract: `apps/lingualens-app/src/services/assessment-v2-client.ts`.
- Screen controller: `apps/lingualens-app/src/features/assessment-v2/components/assessment-segment-review-workspace.tsx`.
- Browser interaction coverage: `apps/lingualens-app/src/__tests__/assessment-segment-review-workspace.test.tsx` and `apps/lingualens-app/e2e/assessment-v2-transcript.smoke.spec.ts`.
