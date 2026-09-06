# Development Workflow

Read these files before changing the project:

1. `AGENTS.md`
2. `docs/PROJECT_SOURCE_OF_TRUTH.md`
3. `README.md`
4. the relevant component documentation

## Branch and workspace discipline

- `main` is the integration branch.
- Use a feature branch for multi-session or high-risk work.
- Before editing, run `git status --short` and confirm the active branch.
- Worktrees and subagent branches are temporary. Merge verified work into
  `main`, then delete obsolete local branches/worktrees.
- Never use generated files as the source of truth.

## Canonical paths

- Product frontend: `apps/lingualens-app`
- Product API: `apps/api`
- Research ML/audio: `packages`, `src`, `scripts`
- Legacy compatibility only: `src/therapist_backend`,
  `src/clinical_workflow`

Changing these boundaries requires an ADR and updates to
`docs/PROJECT_SOURCE_OF_TRUTH.md`, `README.md`, and `AGENTS.md`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r apps/api/requirements.txt
```

Frontend dependencies are installed independently:

```bash
cd apps/lingualens-app && npm ci
```

## Run

```bash
# Terminal 1
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 2
cd apps/lingualens-app
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev
```

## Verification

Use the maintained full-project check:

```bash
bash scripts/check_project.sh
```

Assessment v2 checks are additive to the current `/api/v1` product:

```bash
PYTHONPATH=apps/api:src pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
docker compose up -d postgres
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_postgres.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_compose.py
PYTHONPATH=apps/api:src python -m app.assessment_v2.worker_runtime
```

The v2 database and Alembic history are separate from `LINGUALENS_DATABASE_URL`
and the v1 history. A fresh v2 database is intentionally empty; no existing
v1 records or storage objects are imported. Supabase Auth establishes identity,
FastAPI owns policy, and PostgreSQL RLS is defense in depth. Clients continue
to use `/api/v1` until a later migration plan. Rollback means unmounting `/api/v2`
and leaving v2 startup migrations disabled; v1 data is not changed.

The Capture V2 worker polls durable `processing_runs`, verifies upload bytes with
a server-computed SHA-256, and then runs bounded `ffprobe`/`ffmpeg` quality
checks. It never stores raw media in the database and never creates transcripts,
features, diagnoses, or numeric ASD risk. Compose builds the capture-worker from
the root `Dockerfile`, which includes `ffprobe` and `ffmpeg`; the service health
check verifies both binaries. Configure private Supabase Storage and a durable
Redis queue before any nonmock deployment. A missing media tool is reported as
quality `unavailable`, while retryable processing failures are capped at three
attempts.

Targeted checks:

```bash
PYTHONPATH=apps/api:src pytest tests/test_name.py -q
cd apps/api && PYTHONPATH=. pytest tests/test_workflow.py -q
cd apps/lingualens-app && npm test
cd apps/lingualens-app && npm run typecheck && npm run build
cd apps/lingualens-app && npx playwright install chromium && npm run e2e:smoke
cd apps/lingualens-app && PLAYWRIGHT_BACKEND_PORT=8001 PLAYWRIGHT_FRONTEND_PORT=3101 npm run e2e:smoke
```

## Generated and local-only files

Do not commit:

- `.next/`
- `dist/`
- `.local/`
- `node_modules/`
- `*.tsbuildinfo`
- caches, logs, uploaded media, credentials, or private corpus mirrors

Runtime JSON repositories must use anonymized demo records only.

## Documentation and versioning

- Update `README.md` when entry points, setup, architecture, or behavior changes.
- Update `PROJECT_STATUS.md` for maintained status changes.
- Update `CHANGELOG.md` for behavior, dependency, deployment, or meaningful
  maintenance changes.
- Component and schema version tags must be updated when maintained runtime contracts change.
- Use semantic project versions (`v1.6.x`) and Git tags for releases.
- Historical phase/spec/plan documents remain immutable context unless a
  factual correction is required.

## Commit format

Use Conventional Commits:

```text
type(scope): imperative summary
```

AI-authored commits include the required `Co-Authored-By` footer from
`AGENTS.md`.

## Clinical and privacy constraints

- Use anonymized case codes only.
- Do not log transcript/audio content, identifiers, secrets, or storage keys.
- Preserve consent, role, audit, attestation, and report-finalization gates.
- Software verification and Gate 1 results are not clinical validation.
- Thai or mixed-language evidence must fail closed when unsupported.
