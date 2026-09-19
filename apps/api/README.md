# lingualens API

FastAPI boundary for the case-centered lingualens workflow.

Local development defaults to a durable JSON repository at
`.local/lingualens-app-repository.json`. Set
`LINGUALENS_REPOSITORY_MODE=memory` for isolated test/demo runs, or
`LINGUALENS_REPOSITORY_MODE=sql` with
`LINGUALENS_DATABASE_URL` for the SQLAlchemy-backed repository.

Legacy v2 env names remain supported temporarily for backward compatibility.

- `json`: default local usable-prototype persistence; survives API restarts.
- `memory`: isolated tests and intentional demo resets only.
- `sql`: PostgreSQL-ready SQLAlchemy scaffold; not pilot-hardened yet.

The frontend treats backend records as the clinical workflow source of truth.
`sessionStorage` is only a UI cache/local fallback. Audio bytes remain in memory
unless the therapist explicitly uploads them.
Case creation validates bounded de-identified fields server-side and defaults
new records to pending consent. Session workflows remain consent-gated.

Transcript and report creation are retry-safe. If a session already has an
active transcript or editable report draft, creation returns that record.
Intentional transcript replacement requires `replace_existing: true`.

Run locally:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src uvicorn app.main:app --reload --port 8000
```

Run tests:

```bash
cd apps/api
PYTHONPATH=.:../..:../../src pytest -q
```

Repository-root invocation is also supported:

```bash
PYTHONPATH=apps/api:src pytest apps/api/tests -q
```

`LINGUALENS_DEBUG_FEATURE_OVERRIDE=false` is the default and keeps failed-QA
or unattested transcripts blocked from feature extraction. Engineering-only runs
may set it to `true` when they also provide an explicit override reason.

## Assessment V2 durable processing

The additive `/api/v2` assessment boundary uses a separate PostgreSQL database
and Alembic history. Migration `0007_durable_evidence_jobs` extends
`processing_runs` with assessment/transcript targets, leases, retry/cancel
state, and evidence result linkage. After a therapist attests the current
transcript, `POST /api/v2/assessments/{assessment_id}/evidence-runs` returns
`202` and the durable run; clients poll the current-run/detail endpoints and
read the profile from `GET /api/v2/assessments/{assessment_id}/evidence` only
after the worker persists it.

Capture and evidence stages share the native worker:

```bash
PYTHONPATH=apps/api:src python -m app.assessment_v2.worker_runtime
```

The worker uses PostgreSQL `processing_runs` as its queue and requires an
explicit `LINGUALENS_CAPTURE_WORKER_ORGANIZATION_IDS` allowlist for RLS-safe
tenant polling. Redis/Celery are not required for this path. Docker Compose is
optional packaging verification; the primary acceptance gate is
`scripts/check_assessment_v2_native.py`. The workflow is research/education
decision support only and does not diagnose ASD or expose numeric risk.
