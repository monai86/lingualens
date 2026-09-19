# ADR-001: Isolated assessment v2 foundation

- Status: Accepted for the foundation slice
- Date: 2026-09-06
- Scope: `apps/api` assessment workflow foundation

## Context

LinguaLens already serves the maintained therapist product through `/api/v1`
and an existing database/migration history. The redesign needs an
assessment-centric workflow with explicit child, consent, tenant, care-team,
audit, and optimistic-concurrency boundaries. Rewriting the v1 migration chain
or importing old records would couple the new research workflow to legacy data
and make rollback difficult to reason about.

The project is a research and education prototype. It must not imply automated
ASD diagnosis, expose an ASD probability, or silently treat old demo data as
clinical evidence.

## Decision

Build the foundation as an additive bounded package under `apps/api/app/assessment_v2`.

- Keep `/api/v1` and all existing clients unchanged.
- Expose only the foundation routes under `/api/v2` for now: child, consent,
  and assessment lifecycle operations.
- Use `LINGUALENS_ASSESSMENT_DATABASE_URL` with its own Alembic history and a
  fresh database. Do not import, rewrite, or delete v1 records or storage.
- Let Supabase Auth establish identity, FastAPI enforce organization, role,
  care-team, consent, and workflow policy, and PostgreSQL RLS provide defense
  in depth.
- Keep mutation audit events in the same transaction as their mutation, require
  composite tenant foreign keys for child-linked records, and use optimistic
  assessment versions for transitions.
- Serialize consent changes and consent-gated assessment creation on the child
  row. Local Compose uses a dedicated `NOSUPERUSER`/`NOBYPASSRLS` assessment
  role and enables v2 migration startup so the declared runtime is usable.
- Fail closed before Capture and feature-analysis slices are implemented.

## Consequences

Positive consequences:

- The v1 therapist app can continue operating while the new workflow is built.
- The new schema can model developmental assessments without legacy table
  compatibility constraints.
- Tenant and consent gates are testable independently at service, repository,
  and PostgreSQL RLS layers.
- Rollback is bounded: stop mounting `/api/v2` and keep
  `LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP=false`; v1 data is untouched.

Trade-offs:

- Local development has two database URLs and two migration commands.
- No historical v1 records are available in v2 until a separately approved
  migration/export design exists.
- The v2 foundation is not yet a therapist-ready end-to-end workflow. Capture,
  audio/evidence processing, feature extraction, longitudinal interpretation,
  and usability validation remain later slices.

## Verification boundary

The foundation is verified with SQLite migration smoke tests, focused service
and route tests, v1 regression tests, a PostgreSQL integration test using a
`NOSUPERUSER NOBYPASSRLS` role, and a disposable Compose/API runtime check.
These are software safety checks, not clinical validation and not evidence that
the system can diagnose ASD or developmental delay.
