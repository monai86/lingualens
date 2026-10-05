# Changelog

## [v1.7.0] - 2026-10-04

### Added
- **TUI Desktop Audio Integration** (`packages/tui/`):
  Extended `ClinicalDataPort` protocol with `get_waveform_peaks` and
  `get_playback_grant`; implemented HTTP adapter byte transport, synthetic
  waveform generation in memory adapter (signed 8-bit, clamped [-100, 80]),
  and canonical integration test coverage (112 TUI tests passing).
- **Clinical Pilot & Ethics Documentation**:
  Updated `docs/PILOT_DEPLOYMENT.md` with Audio Review Workbench dual canvas,
  hotkeys, TUI CLI, and multi-tier consent.
  Updated `reports/clinical/THAI_PILOT_VARIANCE_ANALYSIS_PLAN.md` with feature
  battery alignment, Rule 9 invalidation, and clinician ground-truth labeling.
  Enhanced `reports/human_actions/THAI_CLINICAL_PILOT_ETHICS_CHECKLIST.md` with
  multi-tier consent, 15-minute signed playback grants, and non-diagnostic
  disclosures.

### Fixed
- **`findings_stale` / `report_stale` persistence** (`apps/api/`):
  Added mapped boolean columns to `SessionRecord` and hydration in
  `SqlAlchemyRepository` so downstream staleness marking survives round-trips.
- **Next.js CVE remediation**: Upgraded `next` from `16.3.5` to `^16.3.8`
  (GHSA-vcvr-r3jv-pc5j, RCE in `next/og` ImageResponse).
- **CI security scan scope**: Scoped `npm audit` to `--omit=dev` to avoid
  non-actionable `braces` devDependency advisory from `tailwindcss 3.x`.
- **ReportLab PDF threshold**: Lowered export engine PDF size assertion from
  `> 5000` to `> 2000` for headless Linux runner font compatibility.
- **ESLint `react-hooks/purity`**: Silenced false-positive on `Date.now()` in
  assistant page event handler.

### Changed
- Complete visual redesign across all web application surfaces (`apps/lingualens-app/`) adhering to the official PasaScope flat 2D geometric visual brand identity (Pasa Teal `#265347`, Scope Coral `#F45B69`, clean neutral pine canvas `#F7FAF8`, and crisp hairline styling).
- Redesigned and aligned Login page, Workspace Shell, Practice Dashboard, Work Queue (Today workbench), Cases Workspace (Case list & Case detail), Session Assessment workflows (Intake, Stepper, Radar Chart, Reports), Settings administration, Supabase Access Gate, and MFA panels.
- Extracted and integrated high-resolution PasaScope brand assets and logo components (`<PasaScopeLogo>`, `<PasaScopeLogoMark>`, `pasascope-logo.png`, `pasascope-mark-transparent.png`, `clinical-workflow.svg`).
- Rebranded application surfaces and documentation from LinguaLens to **PasaScope (ภาษา-สโคป)**.
- Added backward-compatible `PASASCOPE_` environment variable alias resolution in backend settings.
- Updated Next.js application package name to `pasascope` and layout metadata branding.
- Project version bumped to `v1.7.0`.
- `PROJECT_SOURCE_OF_TRUTH.md` updated with current Next.js version and project
  version.

## [v1.6.3] - 2026-09-21

### Added
- **Thai Clinical Pragmatics & Syntax Engine Expansion** (`src/clinical_speech/thai_lsa.py`, `packages/reports/clinical_report_template.py`, `packages/gui/app.py`):
  Differentiates immediate verbatim repetition (≥80% overlap) from mitigated echolalia (40–79% overlap), filters valid communicative affirmative responses (`ใช่`, `ไม่เอา`, `ชอบ`), and detects Thai pronoun reversal (`เธอ`/`คุณ` self-referencing with desire/state predicates). Surfaced in GUI metrics tree and clinical PDF/HTML report alerts.
- **Clinician Assistant Live API Bridge & Push to Draft** (`apps/lingualens-app/src/app/assistant/page.tsx`):
  Connected web clinician assistant directly to `listBackendCases()` with de-identified child code labels, dynamic clinical prompt templates, and 1-click "คัดลอกลง Report Draft" mutation storing into session draft storage.
- **Age-Cohort Normative Benchmarks & Typical Development Growth Corridor** (`packages/gui/radar_renderer.py`, `packages/gui/app.py`):
  Introduced 3 age-stratified developmental cohorts (24–35m, 36–47m, 48–60m) for 5-domain radar charts and rendered a shaded Typical Development (TD) milestone growth corridor (`#eef2ff`, dashed `#c7d2fe`) in the multi-session longitudinal trajectory chart.
- **24-Segment Discrete LED Level Meter & Voice Activity Detection (VAD)** (`packages/gui/audio_controller.py`, `packages/gui/app.py`):
  Integrated studio-grade 24-segment discrete LED VU meter (green/amber/red) with energy-based real-time `● VOICE ACTIVE` badge and headroom clipping alerts (`⚠️ CLIPPING DETECTED`) during live speech capture.
- **Turnkey Pilot Deployment Orchestration** (`scripts/launch_pilot.sh`, `docs/PILOT_DEPLOYMENT.md`):
  Provided one-command automated startup with environment preflight validation (Python 3.11+, Node.js 20+, port availability), dual FastAPI + Next.js service management, health probing, and graceful shutdown handling.
- Integrated Thai Clinical LSA Engine into Desktop Memory Adapter & API Feature Provider (`packages/tui/adapters/memory_adapter.py`, `apps/api/app/services/providers/basic_provider.py`):
  calculates authentic Thai word segmentation (`tokenize_thai_words`), MLU-w, TTR, and linguistic markers for child language sample analysis, eliminating whitespace-splitting artifacts on Thai script.
- Built Reusable Longitudinal Trend Trajectory Card (`apps/lingualens-app/src/features/reports/components/longitudinal-trend-card.tsx`):
  provides multi-session trajectory analysis tracking changes in MLU-w, TTR, conversational turn-taking, and echolalia across consecutive sessions with directional indicator badges and clinical caution disclaimers.
- Enhanced Clinical PDF & Bilingual HTML Export Engine (`packages/gui/export_engine.py`, `packages/reports/clinical_report_template.py`):
  standalone pure vector SVG 5-Domain Spider Diagram (`RadarChartRenderer.render_svg`), quantitative Thai LSA grid card, multi-session longitudinal trajectory table, and 1-click "Print to PDF" with `@media print` layout formatting.
- Created Comprehensive Thai Advisor & Academic Summary (`docs/PROJECT_SUMMARY_TH.md`):
  detailing the 5-Domain clinical framework, Thai LSA engine architecture, live microphone recording pipeline, and non-diagnostic clinical safety boundaries.
- Implemented Therapist Simple 5-Step Guided Workflow UI in Desktop GUI (`packages/gui/app.py`):
  interactive 5-step stepper bar with progress badges (`Open Case` -> `Add Session` -> `Ingest Material` -> `Review Transcript` -> `Progress Report`), dynamic contextual Next Action Ribbon providing single-click workflow guidance, and collapsible disclosures (`View Details` / `Advanced`) for technical acoustic and model parameters.
- Added Live Microphone Recording in Desktop GUI (`packages/gui/audio_controller.py`, `packages/gui/app.py`):
  thread-safe direct speech capture using `sounddevice` with headless fallback, real-time audio volume VU meter feedback, duration tracking, auto-saving to 16kHz mono WAV, and immediate handoff to the acoustic/transcript analysis pipeline.
- Implemented Deep Thai Clinical Language Sample Analyzer (LSA Engine in `src/clinical_speech/thai_lsa.py`):
  quantitative morphological analysis using `pythainlp` tokenization for Thai child speech samples, evaluating Mean Length of Utterance in words (MLU-w), Type-Token Ratio (TTR), question particle detection, negation usage, pronouns, polite particles, and immediate repetition/echolalia markers.
- Modernized Web App Clinical PDF Report (`apps/lingualens-app/src/features/reports/components/clinical-pdf-report.tsx`):
  high-fidelity A4 clinical print stylesheet, structured grid presentation for quantitative Thai LSA indicators, and enhanced verification testing.
- Added an explicit v2 research transcript contract with 8 conversational
  fields. Benchmarks use 21 non-age inputs (13 v1 + 8 v2); synchronized local
  exports contain 22 numeric fields when `age_months` is included and are bound
  by a SHA-256 artifact manifest.
- Added executable benchmark-gate fixtures for isolated latency noise,
  sustained regression, missing measurements, and scroll-FPS floor breaches.
- Hardened LinguaLens thin clients (`packages/tui`, `packages/gui`) against silent mock fallback:
  in live mode (`mock_mode=False`), all operations communicate via the backend REST API
  or fail closed with structured, sanitized exceptions (`LinguaLensApiError`, `LinguaLensAuthError`,
  `LinguaLensPermissionError`, `LinguaLensConflictError`, `LinguaLensRateLimitError`, `LinguaLensServerError`,
  `LinguaLensUnsupportedOperationError`). Local mock mutations (`_mock_data`) are strictly prohibited in
  live mode, unsupported local-only methods (`ingest_audio_file`, `update_utterance`, `auto_refine_speakers`,
  `swap_speakers`) raise before local mutation, and GUI/TUI direct access to `_mock_data` has been replaced
  with clean client query methods (`get_session_report`, `get_report`) and UI state counts. Added loopback
  transport and parameterized failure test suites.
- Added the first therapist web Capture V2 entry point at `/assessments`:
  consent-gated child selection, protocol activities, browser audio capture,
  SHA-256 upload handoff, quality polling, non-diagnostic quality states, and
  resume for in-progress assessments. Existing `/api/v1` session screens are
  unchanged.
- Added Capture V2 under `/api/v2`: immutable protocol selection, consent-gated
  activity recordings, private Supabase TUS upload intents, durable upload and
  quality processing runs, server-owned checksum verification, bounded
  non-diagnostic media quality checks, tombstone-first cleanup, and a Compose
  capture-worker runtime with `ffprobe`/`ffmpeg`. No ASD diagnosis or numeric
  risk output is produced.
- Hardened Capture V2 upload lifecycle behavior: persisted membership roles are
  authoritative, expired intents queue cleanup, worker transitions are audited,
  accepted evidence invalidates stale quality results and reopens capture, and
  public upload responses contain only short-lived signed URLs and constraints.
- Added an additive assessment v2 foundation under `apps/api` with a fresh,
  separately migrated database boundary, consent-gated assessment lifecycle,
  tenant/care-team policy, atomic consent gating, safe error envelopes, and
  PostgreSQL RLS checks using a non-superuser Compose runtime role.
- Added the reviewed-transcript and evidence boundary under `/api/v2`: append-only
  transcript revisions, therapist attestation, the `/assessments/{id}/transcript`
  review page, an explicit provenance-bound reviewed-transcript extraction worker,
  feature/domain persistence, stale invalidation after transcript changes, and a
  therapist evidence workspace. The read model is descriptive decision support;
  reference-band comparison, ASD/developmental diagnosis, and numeric risk
  output remain out of scope.
- Added durable Assessment V2 evidence processing: `processing_runs` now owns
  assessment/transcript targets, leases, bounded retry, explicit therapist
  cancellation, result linkage, and safe recovery state. The evidence endpoint
  returns `202` after enqueue; the shared native worker processes capture and
  evidence stages, while the therapist web client reloads and polls the server
  run before reading the descriptive profile. No diagnosis or numeric risk is
  produced.
- Added immutable Assessment V2 transcript segment review under `/api/v2` and
  `/assessments/{assessmentId}/transcript`: timestamped segments with controlled
  speaker/uncertainty fields, uncertain-only filtering, focused therapist edits,
  explicit segment attestation, bounded private replay grants, and segment-bound
  evidence provenance. Segment edits create new revisions; transcript changes
  safely stale prior segment evidence. The native PostgreSQL gate now verifies
  migrations through `0009`, RLS/lease behavior, tenant/consent/role denials,
  and this workflow without Docker. No diagnosis or numeric risk is produced.
- Added Visual Fundamental Pitch Contour Overlay (`self._show_pitch_overlay`) in Desktop GUI with real-time F0 curve rendering, voiced autocorrelation sampling, 250 Hz child pitch threshold guideline, and dynamic toolbar toggle (**📈 F0 Curve: ON/OFF**).
- Added Batch Audio Ingestion Queue & Modal Runner in Desktop GUI (**📦 Batch Ingest Files...**), supporting multi-file automated ingestion into dedicated case sessions with real-time status tracking.
- Added Longitudinal Assessment Trajectory Tracker (`subtab_longitudinal`, `tree_longitudinal`) providing cross-session developmental progress monitoring, MLU-w growth delta, vocabulary TTR trajectory, and historical session comparison.
- Added Bilingual Thai/English Clinical LSA Report Template (`packages/reports/clinical_report_template.py`) supporting professional print/PDF layout, 5-domain Spider Diagram, multi-session longitudinal trajectory tables, and digital clinician sign-off attestation blocks.
- Added TalkBank / CHAT Syntax Studio (`talkbank-chat-viewer.tsx`) with dual-mode editor integration for utterance inspection and standard CHAT syntax review.
- Added Interactive Radar Chart (`interactive-radar-chart.tsx`) for 6-axis developmental comparison against age-matched Typical Development (TD) baseline bands.
- Added modular domain models and type contracts under `apps/lingualens-app/src/lib/workflow/types.ts`.
- Added standalone Desktop GUI (`packages/gui`) and Terminal TUI (`packages/tui`) clinical companion tools with automated test suites (`tests/test_gui.py`, `tests/test_tui.py`).

### Changed
- Changed conversational response rates to count every ordered utterance as an
  immediate-response opportunity, preserving same-speaker continuations and
  terminal utterances as non-responses instead of collapsing speaker runs.
- Restricted backend deployment hooks to successful pushes on `main` after all
  security, backend, frontend, UI-audit, E2E, and benchmark jobs; Redis and the
  dedicated worker are absent from the baseline Compose stack.
- Recorded a local-only audio-pipeline determinism experiment without committing the source audio path, filename, audio bytes, transcript, or direct identifiers; this experiment is not clinical validation.
- Shared cached F0 contour and audio buffer between Diarization and AcousticProfile stages in `src/audio_pipeline/pipeline.py`, eliminating redundant `librosa.yin` computations.
- Redesigned Web App dashboard, topbar, transcript editor studio, and findings views conforming to Impeccable and UI-UX Pro Max design standards with WCAG 2.2 AA contrast and Lucide vector iconography.
- Updated `scripts/check_api_migrations.py` HEAD revision to `0013_session_cues_acknowledgement` with required column validation.
- Upgraded the maintained frontend to Next.js 16.3.1, Vitest 4.1.10, ESLint 9,
  and patched transitive dependencies to clear current npm advisories; aligned
  local, CI, and Vercel runtime guidance on Node.js 22.
- Changed Python and frontend dependency audits from report-only checks into
  blocking CI gates for unresolved high or critical findings.

### Added
- Added a synchronous reviewed-transcript analysis execution seam that builds
  the maintained versioned request, SHA-256 input checksum, profile, provenance,
  and result envelope without adding API, persistence, queue, or UI ownership.
- Added the first analysis-boundary extraction: deterministic semantic CHAT
  subset round trips, synthetic identifier-free fixtures, a versioned
  dependency-free Thai/mixed tokenizer profile, descriptive child-only feature
  definitions, structured QA blockers/limitations, and checksum/version
  provenance through `packages.analysis_contract`.
- Added a therapist-only, de-identified case creation form using React Hook
  Form and Zod; newly created cases start with pending consent and open the
  existing backend-backed consent workflow.
- Persisted downstream findings and editable report drafts as explicitly stale
  after transcript edits, with backward-compatible state parsing, atomic
  backend invalidation, version-aware regeneration, and sign-off/export gates.
- Added backend-generated signed report snapshot metadata for signed-off
  reports, including signer, signed timestamp, report version, SHA-256 report
  hash, and export metadata on report exports.
- Added draft report revision creation when editing a signed-off report, keeping
  the original signed snapshot immutable for audit.
- Added an explicit opt-in gate for non-template AI report drafting providers,
  with provider and input-hash provenance recorded on report drafts.
- Added configurable in-memory API rate limiting with safe generic 429
  responses as a production-hardening foundation.
- Added CI repository consistency, secret scanning, and report-only dependency
  audit steps as security-hardening foundations.
- Hardened structured API request logging to record route templates or sanitized
  paths instead of raw record IDs or sensitive URL segments.
- Added configurable CORS origins with production validation and an Origin guard
  for unsafe browser-origin requests.
- Added production runtime validation that rejects demo/default database or
  Redis URLs, local repositories, local storage, and in-memory queues.
- Added an API migration smoke check and backup/restore runbook with RPO/RTO
  restore drill expectations.
- Added an incident-response runbook with stop-rollout criteria for
  cross-tenant exposure, consent bypass, audit loss, and fabricated ASR output.
- Added notification/email safety validation for generic operational messages
  without clinical content or direct identifiers.
- Added audit event shape validation with actor, outcome, correlation ID, and
  clinical-content blocking before persistence.
- Added production observability validation requiring an approved provider,
  critical alert route, and privacy-safe telemetry metadata.
- Added privacy operation retention/legal-hold metadata and deletion-review
  completion safeguards that preserve audit/sign-off evidence.
- Added production secret-store and credential-rotation runtime validation plus
  a secret rotation runbook.
- Added one-day production-like pilot scope/runbook, local/SQL tenant
  scaffolding, backend organization/care-team guards for core clinical records,
  local-private upload intents, and a production auth-mode fail-closed guard.
- Added Phase 1 tenant isolation foundation with organization settings,
  membership/care-team assignment, identity, retention, consent, notification,
  job-attempt SQL tables, organization-scoped clinical child records, broader
  backend tenant guards, PostgreSQL RLS migration SQL, and tests for clinician,
  supervisor, org admin, platform operator, production auth fail-close, and RLS
  coverage.
- Added a backend Supabase Auth scaffold with HS256 bearer-token verification,
  production JWT secret/issuer runtime guards, mock-header bypass protection,
  invitation/MFA/membership checks, break-glass claim validation, and a frozen
  local auth contract in `docs/SUPABASE_AUTH_CONTRACT.md`.
- Added backend organization-admin membership and case care-team assignment
  endpoints with org-admin-only guards, cross-tenant denial, audit tagging, and
  tests proving newly assigned clinicians can access assigned cases.
- Added transactional SQL persistence for organization memberships and case
  care-team assignments, including same-transaction audit writes and case
  care-team updates.
- Added backend-only Phase 2 auth lifecycle workflow endpoints for
  organization invitations, invitation acceptance into active membership,
  membership revocation, scoped audited break-glass case access, and production
  Supabase MFA/invitation fail-closed runtime guards.
- Added a lingualens Settings/Admin Pilot Access Lifecycle console for
  backend-backed invitation creation, membership review, and membership
  revocation, with production-path guardrails visible in the frontend.
- Extended the Settings/Admin Pilot Access Lifecycle console with local
  invitation acceptance into active membership and invited `aal1` session
  preparation so the MFA gate can be exercised in the maintained frontend.
- Added an explicit active-organization session switcher in the maintained
  shell for multi-org mock users, keeping one active organization per session.
- Added a runtime-aware login surface that keeps mock access simulation for
  local auth mode and uses a real browser-side Supabase email/password sign-in
  plus recovery-email path in `supabase` auth mode when browser config is
  present.
- Added frontend Supabase workspace gating so signed-out, `aal1`, and explicit
  org-selection-required states block app routes instead of reusing the mock
  workspace path.
- Added a frontend browser-auth bridge that can normalize a Supabase-like
  session payload into the invitation/MFA/org access-state scaffold used by the
  maintained shell, including initial session restore and auth-state syncing
  from `@supabase/supabase-js`.
- Added frontend persistence for explicit active-organization selection and
  switch-back flow so multi-org Supabase sessions keep one active organization
  per session across refreshes.
- Added a browser-side Supabase TOTP MFA panel for `aal1` workspace gates so
  users can enroll a TOTP factor, verify the authenticator code, and elevate
  the current session to `aal2` without falling back to mock controls.
- Added frontend API auth-header switching so `supabase` runtime requests use
  the current bearer token and active organization context instead of default
  demo headers.
- Added authenticated audio blob loading for protected backend media playback in
  `supabase` runtime, avoiding raw file URLs that cannot carry bearer auth.
- Added authenticated backend upload handling for relative audio-upload routes in
  `supabase` runtime while leaving absolute signed upload URLs free of app auth
  headers.
- Added configurable Playwright smoke-test ports so the maintained therapist
  workflow browser smoke can run on alternate localhost ports when `8000` or
  `3100` are already occupied.
- Added Clinical Speech Artifact Package quality reports that compare ASR draft
  CHAT against reviewed CHAT using WER, CER, speaker-label accuracy, and
  line edit burden, and canonical feature drift without invoking ML decision
  support.
- Added a Clinical Speech Artifact benchmark reporter for multi-session
  ASR-draft-versus-reviewed-CHAT evaluation, producing JSON and CSV summaries
  for WER, CER, speaker-label accuracy, line edit rate, and feature drift.
- Added a diarization runtime readiness check that reports whether pyannote,
  speechbrain embedding diarization, pitch fallback, or no backend is available
  before running audio jobs.

### Changed
- Split the maintained Cases and Settings workspaces into feature-owned views,
  hooks, and access services while retaining thin compatibility entry points.
- Defined fail-closed Settings sections for therapists and organization admins;
  admin data effects are not mounted for unauthorized roles.
- Consolidated persisted report editing under the canonical Session Workspace,
  with validated view dispatch and a safe Cases fallback for unlinked reports.
- Consolidated desktop and mobile navigation around Today, Cases, Session,
  Reports, and Settings; `/` redirects to `/today`, and identifier-less Session
  entry falls back to `/cases?intent=start-session`.
- Refined Today into the approved focused workbench with one Start session
  action, one backend-derived prioritized queue, explicit remote states, and a
  quiet contextual rail.
- Gated presentation-only `/demo` routes behind exact
  `NEXT_PUBLIC_DEMO_MODE=true`, retained a persistent sample-data notice, and
  replaced Thai age-norm/threshold claims with descriptive non-diagnostic copy.
- Reworked the therapist frontend around calm transcript-oriented surfaces,
  responsive rails, the unified Noto Sans Thai / Noto Sans stack, direct
  transcript editing, and role-gated organization administration in Settings.
- Added route bundle budgets, 100/500/1,000-line transcript benchmarks,
  accessibility acceptance checks, and exact responsive screenshot evidence.
- Kept report-draft generation available after therapist transcript attestation
  and feature extraction even when ML readiness/evidence review is unavailable,
  preserving AI/reference outputs as non-essential launch paths.
- Moved transcript review actions into save-before-QA order and added an inline
  reason when `Run QA` is blocked by unsaved or failed transcript draft state.
- Added Supabase workspace logout actions and a visible desktop role label so
  staging users can switch away from non-clinical accounts such as org admin.

### Fixed
- Preserved the legacy v1 `features` mapping while exposing v2 through explicit
  versioned mappings, including numeric parity for file, parsed, and in-memory
  transcript inputs.
- Replaced an outlier-sensitive p95 benchmark decision with a raw-sample
  sustained-regression rule while keeping fail-closed measurement and FPS gates.
- Removed report claims that contradicted negative v1-to-v2 deltas and corrected
  the frozen v1 model configuration plus complete artifact checksums.
- Restored UI audit compliance for dashboard heading hierarchy, chart text
  sizing, transcript-mode touch targets, and valid escaped print selectors.
- Accepted Supabase JWKS-backed `ES256` access tokens in addition to `RS256`
  while preserving a fail-closed algorithm allowlist and signing-key match
  check.
- Added the missing report-runtime Alembic fields so SQL-backed `/cases` and
  `/reports` no longer fail while loading persisted report records.

## [v1.6.3] - 2026-06-21

### Changed
- Replaced therapist Cases pages with backend-backed case and timeline views,
  while keeping seeded fallback content only for offline/demo continuity.
- Replaced the placeholder Reports page with a persisted report index that opens
  draft or finalized reports from the active API workspace.
- Aligned maintained therapist-product metadata across the therapist app,
  shared package, API OpenAPI version, and report audit provenance.
- Removed obsolete demo surfaces, legacy benchmark pipelines, stale benchmark
  artifacts, and outdated summary documents from the working tree so the
  repository points only to the current therapist workflow and current
  reference-evidence ML path.
- Refreshed maintained documentation and repository checks to describe only the
  current runtime, current ML workflow, and current verification path.

### Fixed
- Accepted the therapist frontend `X-User-Id` header in the active API security
  dependency to remove auth-contract drift between the canonical frontend and
  backend.
