# Release Checklist

Use this checklist before the first controlled lingualens clinic launch. It is
not for a public self-serve SaaS release.

## Preflight

- `npm test`, `npm run typecheck`, and `npm run build` pass in `apps/lingualens-app/`.
- `/` redirects to `/today`; `/today`, `/cases`, `/sessions/{sessionId}?view=intake|transcript|findings|report`, `/reports`, and `/settings` render.
- The CI candidate is green for repository/secret and dependency audits, every
  Python 3.11–3.13 backend matrix run, therapist frontend verification, the UI
  design audit, the full therapist and demo Playwright suites, and the
  transcript benchmark gate. `bash scripts/check_project.sh` is a focused
  local check and is not a substitute for these candidate gates.
- Browser audio bytes are not persisted in web storage.
- The selected `LINGUALENS_REPOSITORY_MODE` is tested with anonymized-only child codes.
- Supabase RLS policies are applied and tested for organization isolation,
  assignment-safe metadata boundaries, anonymous denial, and no direct browser
  access to `audit_logs`.
- Supabase Storage uses private buckets only, with opaque generated object keys
  and no human-readable identifiers in object paths.
- `PYTHONPATH=apps/api:src pytest -m "not audio"` passes at the repository root.
- `git ls-files` contains no `.next`, `.local`, `dist`, `node_modules`, or
  `*.tsbuildinfo` paths.
- Mock/sample banner is visible in non-production modes.
- Production auth is invitation-only email/password with required TOTP MFA.
- Public signup is disabled.
- `aal2` is required before app access; `aal1` reaches MFA screens only.
- Multi-org membership requires explicit active-organization selection.
- Therapist users can access assigned cases only.
- Clinical supervisor users can access all cases in the active organization.
- Org admin users remain assignment-safe by default and cannot read clinical
  case content unless explicitly granted through care-team assignment.
- Platform operator access is break-glass only, one case scoped, one hour
  maximum, and fails closed on the next request after expiry.
- Report sign-off is restricted to the primary assigned therapist only.
- Primary therapist removal blocks sign-off until a new primary is assigned.
- Therapist-reviewed transcript remains the only report-eligible transcript
  authority.
- AI review is org-level opt-in and default off, with explicit unavailable
  states when disabled.
- Provider fallbacks return explicit unavailable states and never mocked or
  fabricated clinical outputs.
- Privacy export, consent withdrawal, and deletion requests create audit events.
- The staging tenant-safety evidence package is complete using
  [docs/STAGING_TENANT_SAFETY_VERIFICATION.md](/Users/porschecaa/lingualens/docs/STAGING_TENANT_SAFETY_VERIFICATION.md).

## Production Gate

- `AUTH_MODE`, `DATA_MODE`, `PROCESSING_MODE`, and `FILE_STORAGE_MODE` are set to production values.
- HTTPS is enforced.
- Production mock mode is disabled.
- Supabase staging and production projects exist in `ap-southeast-1`.
- The launch tenant remains one clinic organization first.
- Country allowlist is Thailand only.
- Database backups and restore test are complete.
- Private storage bucket encryption and retention rules are configured.
- Signed upload intent expiry is 15 minutes, upload completion verification is
  enforced server-side, and failed uploads require a new upload intent.
- Admin bootstrap uses a service role or trusted backend path; the browser must
  not be able to self-assign `org_admin`, `clinical_supervisor`, or
  `platform_operator`.
- A durable API-to-worker lifecycle has been implemented, rehearsed, and shown
  to preserve one active job per audio artifact. The current baseline does not
  satisfy this production gate; local Compose intentionally has no Redis or
  dedicated worker.
- Transcript edits immediately stale downstream AI/review/report outputs.
- Monitoring alerts are configured for auth, storage, processing latency or
  failures, API errors, and privacy-operation backlog. Add queue-age alerts if
  asynchronous processing is enabled.
- Audit events keep actor, action, target, outcome, timestamp, and
  correlation ID only, without raw clinical identifiers or content.
- Telemetry and notifications contain operational metadata only.
- No unresolved high/critical security findings remain.
- Go-live approval is explicitly signed off by engineering/product and
  legal/privacy.
- Incident contact and rollback owner are named.
- Supabase org/project setup record is complete using
  [docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md](/Users/porschecaa/lingualens/docs/SUPABASE_PROJECT_SETUP_RUNBOOK.md).
- Supabase setup evidence package exists under
  `docs/release_artifacts/project_setup/`.

## Rollback

1. Revert the Pages/API deployment to the previous known-good artifact.
2. Disable the affected processing path; pause a worker or queue only when one
   is actually enabled.
3. Keep database migrations reversible or apply a documented forward fix.
4. Preserve audit logs and privacy operation records.
5. Confirm login, case ownership, upload blocking, and report export behavior after rollback.
