# Assessment Foundation V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first independently usable slice of the approved redesign: a fresh assessment-centric database boundary, tenant and care-team authorization, consent-gated assessment creation, auditable state transitions, optimistic concurrency, and a stable `/api/v2` error contract.

**Architecture:** Add an isolated `app.assessment_v2` bounded package and a separate Alembic history backed by `LINGUALENS_ASSESSMENT_DATABASE_URL`. Mount `/api/v2` beside the existing `/api/v1`; do not migrate old records or change v1 behavior. Reuse the existing Supabase bearer verification to establish identity, then enforce organization, role, care-team, and consent policy in a v2 service and again through PostgreSQL RLS. Web, GUI, and TUI migration is deliberately deferred to later slices.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL/Supabase, psycopg 3, PyJWT, pytest, Docker Compose.

---

## Plan position and acceptance boundary

This is implementation plan **1 of 7** for [the approved developmental-profile workflow redesign](../specs/2026-09-06-developmental-profile-workflow-redesign.md). A separate [Plan 0 therapist UX and Figma prototype](2026-09-06-therapist-ux-figma-prototype.md) may run in parallel but must be accepted before Capture or therapist-web implementation begins. The later implementation plans are Capture, Evidence, Clinical Review, Longitudinal, Thin Clients, and Pilot Validation. Write each later plan only after the preceding slice has a stable, verified contract.

Foundation V2 is accepted only when all of the following are true:

- a fresh, empty assessment database upgrades to the v2 foundation schema through its own Alembic history;
- existing `/api/v1` routes, persistence, and migration history remain operational and unchanged in behavior;
- authenticated users can create and view children only inside their selected active organization;
- only a principal whose verified identity has an active persisted organization membership can use v2;
- a therapist is automatically assigned to the care team of a child they create;
- assessment creation requires active `clinical_assessment` consent and care-team access;
- every protected mutation creates a sanitized audit event in the same transaction;
- assessment transitions reject stale versions and illegal state changes;
- PostgreSQL RLS independently prevents cross-organization reads and writes;
- all v2 failures use the documented error envelope and correlation ID;
- no endpoint returns diagnosis, ASD probability, transcript analysis, developmental profile, or fabricated/mock clinical results.

## Explicit non-goals

- Do not delete or migrate the existing database, storage bucket, fixtures, or local research artifacts.
- Do not add protocols, recordings, transcripts, feature extraction, attention cues, reports, or longitudinal comparison yet.
- Do not alter `src/therapist_backend/` or `src/clinical_workflow/`.
- Do not move the web, desktop GUI, or TUI to `/api/v2` in this slice.
- Do not let a browser client mutate Supabase clinical tables directly.
- Do not add names, transcript text, filenames, storage keys, or audio bytes to audit records, logs, or fixtures.

## Execution controls

Before implementation, the executing agent must:

- [ ] Read `AGENTS.md`, `docs/PROJECT_SOURCE_OF_TRUTH.md`, the approved spec, and this complete plan.
- [ ] Load `test-driven-development/SKILL.md`, then read its referenced `writing-good-tests.md` before writing production code.
- [ ] Record `TDD_REQUIRED: yes`, the observable seam, and RED/GREEN/REFACTOR evidence for every behavior task below.
- [ ] Load `using-git-worktrees/SKILL.md` and create an isolated worktree from the approved-spec commit. The current checkout is heavily dirty and its unrelated changes must not be copied, staged, overwritten, or committed.
- [ ] Use branch `codex/assessment-foundation-v2` unless it already exists; if it exists, inspect rather than overwrite it.
- [ ] Build one verification profile from `AGENTS.md`, package scripts, CI, and Compose before changing code.
- [ ] Use final-strict assurance because this slice changes authentication, tenant isolation, migrations, data integrity, and a public API. Use `ASSURANCE_UNIT_ID: lingualens-assessment-foundation-v2`, `TARGET_REVIEW_CALLS: 1`, `REVIEW_BUDGET_MODE: default`, and `MAX_REVIEW_CALLS: 3`.

Run focused tests during Tasks 1–8. Run the repository-wide and final-strict gates only after the complete Foundation candidate is frozen in Task 9.

## Target file map

Create this isolated package:

```text
apps/api/app/assessment_v2/
├── __init__.py
├── dependencies.py
├── errors.py
├── routes.py
├── schemas.py
├── services.py
├── domain/
│   ├── __init__.py
│   ├── models.py
│   └── transitions.py
└── db/
    ├── __init__.py
    ├── base.py
    ├── models.py
    ├── repositories.py
    ├── session.py
    ├── migrations_runner.py
    └── migrations/
        ├── env.py
        ├── script.py.mako
        └── versions/
            └── 0001_assessment_foundation.py
```

Create a separate `apps/api/alembic-assessment.ini`. The old `apps/api/alembic.ini` and `apps/api/app/db/migrations/` remain the v1 history.

The initial v2 tables are exactly:

| Table | Required content |
|---|---|
| `organizations` | scoped organization ID, display label, active flag, timestamps |
| `user_profiles` | auth user ID, non-clinical display label, timestamps |
| `organization_memberships` | organization, user, role, active flag, timestamps |
| `children` | scoped child ID, organization, non-identifying display code, birth month/year, language context, version, timestamps |
| `care_team_assignments` | organization, child, user, role, active flag, timestamps |
| `consent_records` | organization, child, purpose, scope version, status, granted/withdrawn timestamps, actor, version |
| `assessments` | organization, child, purpose, state, age in months, language context, assigned clinician, version, timestamps |
| `audit_events` | organization, actor, action, target type/ID, outcome, correlation ID, target version, timestamp, metadata JSON |

Use opaque string IDs generated with `uuid4().hex`; do not store child names. Use timezone-aware UTC datetimes. Every tenant-owned table has a non-null `organization_id` and indexed tenant foreign keys.

### Task 1: Establish the pure assessment domain and transition contract

**Files:**

- Create: `apps/api/app/assessment_v2/__init__.py`
- Create: `apps/api/app/assessment_v2/domain/__init__.py`
- Create: `apps/api/app/assessment_v2/domain/models.py`
- Create: `apps/api/app/assessment_v2/domain/transitions.py`
- Create: `apps/api/tests/assessment_v2/__init__.py`
- Create: `apps/api/tests/assessment_v2/test_state_machine.py`

- [ ] **Step 1: Write failing state-machine tests.**

```python
from dataclasses import replace

import pytest

from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentSnapshot, AssessmentState
from app.assessment_v2.domain.transitions import InvalidAssessmentTransition, transition_assessment


def assessment(state: AssessmentState = AssessmentState.DRAFT, version: int = 1) -> AssessmentSnapshot:
    return AssessmentSnapshot(
        id="assessment_01",
        organization_id="org_alpha",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=state,
        assigned_clinician_id="therapist_01",
        version=version,
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (AssessmentState.DRAFT, AssessmentState.READY_FOR_CAPTURE),
        (AssessmentState.READY_FOR_CAPTURE, AssessmentState.CAPTURING),
        (AssessmentState.CAPTURING, AssessmentState.PROCESSING),
        (AssessmentState.PROCESSING, AssessmentState.REVIEW_REQUIRED),
        (AssessmentState.REVIEW_REQUIRED, AssessmentState.READY_FOR_CLINICIAN),
        (AssessmentState.READY_FOR_CLINICIAN, AssessmentState.FINALIZED),
    ],
)
def test_allows_forward_workflow(source: AssessmentState, target: AssessmentState) -> None:
    updated = transition_assessment(assessment(source, version=4), target, expected_version=4)
    assert updated.state is target
    assert updated.version == 5


def test_allows_cancellation_before_finalization() -> None:
    updated = transition_assessment(assessment(AssessmentState.PROCESSING), AssessmentState.CANCELLED, 1)
    assert updated.state is AssessmentState.CANCELLED


@pytest.mark.parametrize("terminal", [AssessmentState.FINALIZED, AssessmentState.CANCELLED])
def test_rejects_transition_from_terminal_state(terminal: AssessmentState) -> None:
    with pytest.raises(InvalidAssessmentTransition):
        transition_assessment(assessment(terminal), AssessmentState.REVIEW_REQUIRED, 1)


def test_rejects_skipped_state() -> None:
    with pytest.raises(InvalidAssessmentTransition):
        transition_assessment(assessment(), AssessmentState.PROCESSING, 1)


def test_rejects_stale_version() -> None:
    with pytest.raises(InvalidAssessmentTransition, match="stale_assessment_version"):
        transition_assessment(replace(assessment(), version=3), AssessmentState.READY_FOR_CAPTURE, 2)
```

- [ ] **Step 2: Run RED and preserve the failure.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_state_machine.py -q`

Expected: collection fails because `app.assessment_v2.domain` does not exist.

- [ ] **Step 3: Implement the minimum pure domain.**

`domain/models.py` must define string enums for four purposes and eight states, plus this immutable snapshot:

```python
from dataclasses import dataclass
from enum import StrEnum


class AssessmentPurpose(StrEnum):
    INITIAL = "initial"
    DEVELOPMENTAL_FOLLOW_UP = "developmental_follow_up"
    POST_INTERVENTION_FOLLOW_UP = "post_intervention_follow_up"
    ADDITIONAL_EVIDENCE = "additional_evidence"


class AssessmentState(StrEnum):
    DRAFT = "draft"
    READY_FOR_CAPTURE = "ready_for_capture"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    READY_FOR_CLINICIAN = "ready_for_clinician"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class AssessmentSnapshot:
    id: str
    organization_id: str
    child_id: str
    purpose: AssessmentPurpose
    state: AssessmentState
    assigned_clinician_id: str
    version: int
```

`domain/transitions.py` must hold one explicit adjacency map. `transition_assessment` compares `expected_version`, rejects terminal/skipped/backward transitions, and returns `dataclasses.replace(current, state=target, version=current.version + 1)`. Its exception exposes a stable machine code of `stale_assessment_version` or `invalid_assessment_transition`.

- [ ] **Step 4: Run GREEN and refactor only with the test green.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_state_machine.py -q`

Expected: all state-machine tests pass.

- [ ] **Step 5: Commit only Task 1 files.**

```bash
git add apps/api/app/assessment_v2 apps/api/tests/assessment_v2
git commit -m "feat(api): define assessment v2 lifecycle" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 2: Add isolated v2 configuration and relational metadata

**Files:**

- Modify: `apps/api/app/core/config.py`
- Create: `apps/api/app/assessment_v2/db/__init__.py`
- Create: `apps/api/app/assessment_v2/db/base.py`
- Create: `apps/api/app/assessment_v2/db/models.py`
- Create: `apps/api/tests/assessment_v2/test_config.py`
- Create: `apps/api/tests/assessment_v2/test_db_models.py`

- [ ] **Step 1: Write failing configuration and schema-contract tests.**

The tests must assert:

```python
EXPECTED_TABLES = {
    "organizations",
    "user_profiles",
    "organization_memberships",
    "children",
    "care_team_assignments",
    "consent_records",
    "assessments",
    "audit_events",
}


def test_assessment_database_uses_dedicated_environment_variable(monkeypatch):
    monkeypatch.setenv("LINGUALENS_ASSESSMENT_DATABASE_URL", "postgresql+psycopg://v2.example/test")
    settings = Settings.from_env()
    assert settings.assessment_database_url == "postgresql+psycopg://v2.example/test"
    assert settings.assessment_api_prefix == "/api/v2"


def test_foundation_metadata_is_complete_and_tenant_scoped():
    assert set(AssessmentBase.metadata.tables) == EXPECTED_TABLES
    for table_name in EXPECTED_TABLES - {"organizations", "user_profiles"}:
        assert "organization_id" in AssessmentBase.metadata.tables[table_name].columns
```

Also assert unique constraints for membership `(organization_id, user_id)`, care team `(organization_id, child_id, user_id)`, and child display code `(organization_id, display_code)`.

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_config.py tests/assessment_v2/test_db_models.py -q`

Expected: imports or assertions fail because v2 settings and metadata do not exist.

- [ ] **Step 3: Add v2-only settings without changing v1 defaults.**

Add:

```python
DEFAULT_ASSESSMENT_DATABASE_URL = (
    "postgresql+psycopg://therapist:therapist@localhost/lingualens_assessment_v2"
)

class Settings(BaseModel):
    assessment_api_prefix: str = "/api/v2"
    assessment_database_url: str = DEFAULT_ASSESSMENT_DATABASE_URL
    run_assessment_migrations_on_startup: bool = False
```

`Settings.from_env()` must map `LINGUALENS_ASSESSMENT_DATABASE_URL` and `LINGUALENS_RUN_ASSESSMENT_MIGRATIONS_ON_STARTUP`. Production validation must reject a localhost/default v2 URL and must require v2 auto-schema creation to remain disabled. Do not repurpose `database_url`.

- [ ] **Step 4: Implement the eight-table SQLAlchemy 2 metadata contract.**

Use typed `Mapped[T]` attributes, `mapped_column`, named foreign keys, named unique/check constraints, and timezone-aware `DateTime(timezone=True)`. Required value constraints are:

- membership role: `therapist`, `clinical_supervisor`, `org_admin`, `researcher`;
- care-team role: `assigned_clinician`, `supervisor`, `observer`;
- consent purpose: `clinical_assessment` or `research_reuse`;
- consent status: `active` or `withdrawn`;
- assessment purpose and state: exactly the domain enum values;
- every mutable aggregate starts at version `1` and has `version >= 1`;
- `birth_month` is 1–12, `birth_year` is 1900–2100, and assessment age is 0–216 months;
- `audit_events.metadata_json` defaults to an empty JSON object and never stores payload bodies.

Keep `user_profiles` independent from Supabase's `auth.users` so SQLite metadata tests and self-hosted PostgreSQL work. The auth user ID remains the logical link.

- [ ] **Step 5: Run GREEN and inspect metadata names.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_config.py tests/assessment_v2/test_db_models.py -q`

Expected: all tests pass and only the eight named tables appear in `AssessmentBase.metadata`.

- [ ] **Step 6: Commit Task 2.**

```bash
git add apps/api/app/core/config.py apps/api/app/assessment_v2/db apps/api/tests/assessment_v2
git commit -m "feat(api): add assessment v2 data model" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 3: Create the fresh Alembic history and empty-database smoke gate

**Files:**

- Create: `apps/api/alembic-assessment.ini`
- Create: `apps/api/app/assessment_v2/db/migrations/env.py`
- Create: `apps/api/app/assessment_v2/db/migrations/script.py.mako`
- Create: `apps/api/app/assessment_v2/db/migrations/versions/0001_assessment_foundation.py`
- Create: `apps/api/app/assessment_v2/db/migrations_runner.py`
- Create: `scripts/check_assessment_v2_migrations.py`
- Create: `apps/api/tests/assessment_v2/test_migrations.py`

- [ ] **Step 1: Write the failing migration smoke test.**

```python
from pathlib import Path
import subprocess
import sys


def test_fresh_assessment_database_upgrades_and_downgrades() -> None:
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/check_assessment_v2_migrations.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "assessment-v2 migration smoke passed" in result.stdout
```

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_migrations.py -q`

Expected: failure because the smoke script and separate Alembic configuration are absent.

- [ ] **Step 3: Implement the separate migration environment.**

`alembic-assessment.ini` must point `script_location` to `app/assessment_v2/db/migrations`. `env.py` imports all v2 models, sets `target_metadata = AssessmentBase.metadata`, and gets the URL from `LINGUALENS_ASSESSMENT_DATABASE_URL` before falling back to settings. It must enable `compare_type=True` and `transaction_per_migration=True`.

`0001_assessment_foundation.py` must explicitly create all eight tables, constraints, and indexes in dependency order. It must not call `metadata.create_all()`. For PostgreSQL only, it must execute:

```sql
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_memberships_tenant_isolation
ON organization_memberships
USING (organization_id = current_setting('app.current_organization_id', true))
WITH CHECK (organization_id = current_setting('app.current_organization_id', true));
```

Apply the same named policy pattern to `children`, `care_team_assignments`, `consent_records`, `assessments`, and `audit_events`. Do not place RLS on `organizations` or `user_profiles` in this first migration; access to those tables is through explicitly scoped repository queries and will be revisited with Supabase bootstrap policy during Pilot Validation.

The downgrade must drop policies before tables and then drop all eight tables in reverse dependency order.

- [ ] **Step 4: Implement a programmatic migration runner.**

`upgrade_assessment_database(revision="head")` must construct an Alembic `Config` from the absolute `apps/api/alembic-assessment.ini` path, set the runtime URL from settings, and call `alembic.command.upgrade`. It must never fall back to the v1 URL.

- [ ] **Step 5: Implement deterministic SQLite smoke verification.**

The script must create a temporary SQLite file, set only `LINGUALENS_ASSESSMENT_DATABASE_URL`, run upgrade to head, assert the eight tables plus `alembic_version`, run downgrade to base, assert only SQLite internals remain, and delete its temporary directory in `finally`. PostgreSQL-only RLS statements must be dialect-gated in the migration.

- [ ] **Step 6: Run GREEN twice to prove repeatability.**

Run:

```bash
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_migrations.py -q
```

Expected: both smoke runs print `assessment-v2 migration smoke passed`; pytest passes.

- [ ] **Step 7: Commit Task 3.**

```bash
git add apps/api/alembic-assessment.ini apps/api/app/assessment_v2/db scripts/check_assessment_v2_migrations.py apps/api/tests/assessment_v2/test_migrations.py
git commit -m "feat(api): add fresh assessment migration history" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 4: Establish tenant-bound SQL sessions and repository isolation

**Files:**

- Create: `apps/api/app/assessment_v2/db/session.py`
- Create: `apps/api/app/assessment_v2/db/repositories.py`
- Create: `apps/api/tests/assessment_v2/test_repository.py`

- [ ] **Step 1: Write failing repository tests.**

Use an in-memory SQLite engine with `StaticPool` and synthetic IDs. Tests must prove:

- `create_child` assigns the creator as active `assigned_clinician`;
- `synchronize_principal` creates or refreshes only the organization, user profile, and membership represented by the verified current principal;
- an inactive persisted membership is denied even if an object with a matching organization ID is requested;
- organization Alpha cannot fetch organization Beta's child;
- a therapist outside the care team cannot fetch a child even in the same organization;
- an organization admin with active membership can fetch any child in the organization;
- `add_consent` creates an append-only consent record rather than updating a previous one;
- `transition_assessment` uses `WHERE id = :id AND organization_id = :org AND version = :expected_version`;
- each successful write creates one audit event in the same transaction;
- a failed/stale write leaves neither the mutation nor an orphan audit event.

The first test should use this observable seam:

```python
child = repo.create_child(
    organization_id="org_alpha",
    actor_id="therapist_01",
    display_code="LL-0001",
    birth_year=2021,
    birth_month=6,
    language_context={"primary": "th", "additional": []},
    correlation_id="req-create-child",
)
assert repo.get_child("org_alpha", "therapist_01", "therapist", child.id) == child
assert session.scalar(select(func.count()).select_from(CareTeamAssignmentRow)) == 1
assert session.scalar(select(func.count()).select_from(AuditEventRow)) == 1
```

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_repository.py -q`

Expected: failure because session and repository boundaries do not exist.

- [ ] **Step 3: Implement tenant session context.**

Create one cached engine and one `sessionmaker(expire_on_commit=False)`. `assessment_session_for(user)` must open a transaction and, on PostgreSQL, execute:

```python
session.execute(
    text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
    {"organization_id": user.organization_id},
)
session.execute(
    text("SELECT set_config('app.current_user_id', :user_id, true)"),
    {"user_id": user.user_id},
)
```

The dependency yields only after both settings succeed, commits once on normal return, rolls back on any exception, and always closes. Never interpolate IDs into SQL.

- [ ] **Step 4: Implement the focused repository.**

Create `AssessmentRepository` with only these public methods:

```python
class AssessmentRepository(Protocol):
    def synchronize_principal(self, principal: CurrentUser, correlation_id: str) -> None:
        raise NotImplementedError

    def create_child(
        self, scope: AccessScope, command: CreateChild, correlation_id: str
    ) -> ChildSnapshot:
        raise NotImplementedError

    def get_child(self, scope: AccessScope, child_id: str) -> ChildSnapshot | None:
        raise NotImplementedError

    def list_children(self, scope: AccessScope) -> list[ChildSnapshot]:
        raise NotImplementedError

    def add_consent(
        self, scope: AccessScope, child_id: str, command: RecordConsent, correlation_id: str
    ) -> ConsentSnapshot:
        raise NotImplementedError

    def has_active_consent(
        self, scope: AccessScope, child_id: str, purpose: ConsentPurpose
    ) -> bool:
        raise NotImplementedError

    def create_assessment(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        raise NotImplementedError

    def get_assessment(
        self, scope: AccessScope, assessment_id: str
    ) -> AssessmentSnapshot | None:
        raise NotImplementedError

    def list_assessments(
        self, scope: AccessScope, child_id: str
    ) -> list[AssessmentSnapshot]:
        raise NotImplementedError

    def transition_assessment(
        self, scope: AccessScope, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        raise NotImplementedError
```

Implement these signatures with immutable command/snapshot dataclasses in `domain/models.py`: `AccessScope` contains user, organization, and role; `CreateChild` contains display code, birth month/year, and language context; `RecordConsent` contains purpose, scope version, and status; `CreateAssessment` contains child, purpose, age, language context, and assigned clinician; `TransitionAssessment` contains assessment ID, target state, and expected version. Commands never contain an organization supplied by the request body.

Every method receives organization and actor scope explicitly. Keep authorization predicates in private query builders; do not create a product-wide repository. `create_child`, `add_consent`, `create_assessment`, and `transition_assessment` append a sanitized `AuditEventRow` before the surrounding transaction commits. Audit metadata may contain purpose, state, and changed field names but never field values from child, consent, or assessment payloads.

When an optimistic update affects zero rows, re-query by tenant ID only to distinguish `assessment_not_found` from `stale_assessment_version`; return neither another tenant's existence nor current version.

- [ ] **Step 5: Run GREEN and refactor query duplication.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_repository.py -q`

Expected: all repository and atomic-audit tests pass.

- [ ] **Step 6: Commit Task 4.**

```bash
git add apps/api/app/assessment_v2/db apps/api/tests/assessment_v2/test_repository.py
git commit -m "feat(api): enforce tenant-scoped assessment persistence" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 5: Add service policy for child, consent, and assessment operations

**Files:**

- Create: `apps/api/app/assessment_v2/services.py`
- Create: `apps/api/tests/assessment_v2/test_services.py`

- [ ] **Step 1: Write failing service-policy tests with a fake repository.**

Cover these decisions:

| Scenario | Result code |
|---|---|
| inactive organization membership | `inactive_membership` |
| role outside therapist/supervisor/admin | `role_not_permitted` |
| child outside tenant or care team | `child_not_found` |
| missing active `clinical_assessment` consent | `active_consent_required` |
| withdrawn latest clinical consent record | `active_consent_required` |
| assigned clinician differs from actor without supervisor/admin role | `clinician_assignment_not_permitted` |
| unsupported purpose | Pydantic 422 envelope from Task 7 |
| legal creation path | draft assessment version 1 plus audit via repository |

Also prove that consent checking is performed immediately before assessment insertion, not only when a child is loaded.

Add a fail-closed stage test: until Capture is implemented, the service permits `draft -> cancelled` but rejects `draft -> ready_for_capture` with `workflow_stage_unavailable`. The pure state machine remains complete so later slices can add prerequisite gates without changing state names.

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_services.py -q`

Expected: failure because the service does not exist.

- [ ] **Step 3: Implement `AssessmentService`.**

The service accepts a narrow repository protocol and `CurrentUser`. Public methods are:

```python
create_child(command, correlation_id)
get_child(child_id)
list_children()
grant_consent(child_id, command, correlation_id)
create_assessment(child_id, command, correlation_id)
get_assessment(assessment_id)
list_assessments(child_id)
transition_assessment(assessment_id, command, correlation_id)
```

`create_assessment` must calculate age in completed months from birth month/year and the current UTC month, validate 0–216 months, copy the child's language context into the assessment snapshot, and always create state `draft`. Client input cannot choose initial state or organization ID.

Use a `ClinicalPolicyError(code, status_code, safe_message, details=None)` and replace `None` with a fresh empty mapping inside the constructor. Details may include allowed state names but never record existence, names, dates of birth, language payloads, or current versions. Check the persisted active membership before every operation. `synchronize_principal` may insert/update identity rows only from a successfully verified Supabase principal, or from mock identity when `mock_mode=true`; it must never trust a request-body organization or role. A database membership marked inactive wins over a stale token and must not be silently reactivated.

- [ ] **Step 4: Run GREEN.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_services.py -q`

Expected: all service-policy tests pass.

- [ ] **Step 5: Commit Task 5.**

```bash
git add apps/api/app/assessment_v2/services.py apps/api/tests/assessment_v2/test_services.py
git commit -m "feat(api): add consent-gated assessment policy" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 6: Define the versioned API schemas and safe error envelope

**Files:**

- Create: `apps/api/app/assessment_v2/schemas.py`
- Create: `apps/api/app/assessment_v2/errors.py`
- Create: `apps/api/tests/assessment_v2/test_schemas.py`
- Create: `apps/api/tests/assessment_v2/test_errors.py`

- [ ] **Step 1: Write failing schema and error tests.**

The response envelope is exactly:

```json
{
  "error": {
    "code": "active_consent_required",
    "message": "Active clinical-assessment consent is required.",
    "details": {},
    "correlation_id": "req-01"
  }
}
```

Tests must reject unknown input fields, names, exact birth dates, supplied organization IDs, supplied state, negative versions, invalid purpose/state values, and language context without a two-letter primary language code. Response schemas expose `display_code`, birth month/year, language context, and age in months but never a child name.

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_schemas.py tests/assessment_v2/test_errors.py -q`

Expected: imports fail because schemas and handlers do not exist.

- [ ] **Step 3: Implement strict Pydantic models.**

All request models use `ConfigDict(extra="forbid")`. Define:

- `ChildCreateRequest(display_code, birth_year, birth_month, language_context)`;
- `ChildResponse`;
- `ConsentCreateRequest(purpose, scope_version, status)` and `ConsentResponse`; recording `withdrawn` appends a new version and sets its server timestamp rather than editing the active record;
- `AssessmentCreateRequest(purpose, assigned_clinician_id=None)`;
- `AssessmentTransitionRequest(target_state, expected_version)`;
- `AssessmentResponse`;
- `ErrorBody` and `ErrorEnvelope`.

Use constrained strings and integers, not post-validation truncation. Normalize language codes to lowercase but do not infer or translate them.

- [ ] **Step 4: Implement one v2 exception conversion function.**

`assessment_error_response(request, code, status_code, message, details)` reads `request.state.request_id`; if unavailable it generates `uuid4().hex`. It builds a validated `ErrorEnvelope`, passes `payload.model_dump(mode="json")` to `JSONResponse`, copies the correlation ID to `x-request-id`, and must not echo exception strings.

- [ ] **Step 5: Run GREEN.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_schemas.py tests/assessment_v2/test_errors.py -q`

Expected: all schema and envelope tests pass.

- [ ] **Step 6: Commit Task 6.**

```bash
git add apps/api/app/assessment_v2/schemas.py apps/api/app/assessment_v2/errors.py apps/api/tests/assessment_v2
git commit -m "feat(api): define assessment v2 contracts" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 7: Mount the working `/api/v2` vertical slice

**Files:**

- Create: `apps/api/app/assessment_v2/dependencies.py`
- Create: `apps/api/app/assessment_v2/routes.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/logging.py`
- Create: `apps/api/tests/assessment_v2/test_routes.py`
- Modify: `apps/api/tests/test_security_controls.py`

- [ ] **Step 1: Write failing route and logging tests.**

Use `TestClient`, dependency overrides, synthetic users, and a transaction-backed SQLite repository. Verify:

```text
POST /api/v2/children
GET  /api/v2/children
GET  /api/v2/children/{child_id}
POST /api/v2/children/{child_id}/consents
POST /api/v2/children/{child_id}/assessments
GET  /api/v2/children/{child_id}/assessments
GET  /api/v2/assessments/{assessment_id}
POST /api/v2/assessments/{assessment_id}/transitions
```

Acceptance assertions:

- child creation returns `201` and an opaque ID;
- assessment creation without consent returns `409 active_consent_required`;
- consent then assessment creation returns `201` with state `draft` and version `1`;
- cancellation from draft returns state `cancelled` and version `2`;
- advancing from draft to `ready_for_capture` returns `409 workflow_stage_unavailable` until the Capture slice supplies protocol prerequisites;
- repeating it with version `1` returns `409 stale_assessment_version`;
- cross-tenant and out-of-care-team access both return the same `404 child_not_found`;
- malformed input returns the v2 error envelope with code `request_validation_failed`;
- `/api/v1` validation errors retain their existing shape;
- `sanitize_log_path("/api/v2/children/child-secret/assessments")` is `/api/v2/children/[redacted]/assessments`;
- request logs contain the route template, status, duration, and request ID but no child ID.

- [ ] **Step 2: Run RED.**

Run: `cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_routes.py tests/test_security_controls.py -q`

Expected: v2 routes return 404 and logging/error assertions fail.

- [ ] **Step 3: Wire dependencies and routes.**

`get_assessment_service` must compose the current authenticated `CurrentUser`, tenant-bound SQL session, focused repository, and service. It synchronizes only the verified principal's identity boundary, then requires the persisted active membership; it never reactivates an inactive membership. Do not use the old `get_repository()` dependency.

All endpoints return typed response models and declare the standard v2 error response. Mutation endpoints read the middleware correlation ID and pass it through service, repository, and audit event. Router tags are `assessment-v2`.

- [ ] **Step 4: Mount v2 without disturbing v1.**

In `main.py`:

```python
app.include_router(assessment_v2_routes.router, prefix=settings_obj.assessment_api_prefix)
```

Register handlers for `ClinicalPolicyError` and `RequestValidationError`. The validation handler must use the v2 envelope only when `request.url.path.startswith(settings_obj.assessment_api_prefix)` and delegate to FastAPI's existing handler otherwise.

- [ ] **Step 5: Make request correlation and path sanitization work for both versions.**

Set `request.state.request_id = request_id` before `call_next`. Add only static v2 route words to `SAFE_PATH_SEGMENTS`: `v2`, `children`, `consents`, `assessments`, and `transitions`. Replace the single-prefix route-template repair with iteration over `(settings.api_prefix, settings.assessment_api_prefix)`.

- [ ] **Step 6: Run GREEN plus v1 regression tests.**

Run:

```bash
cd apps/api && PYTHONPATH=. pytest tests/assessment_v2/test_routes.py tests/test_security_controls.py -q
cd apps/api && PYTHONPATH=. pytest tests/test_workflow.py tests/test_tenant_isolation_phase1.py -q
```

Expected: v2 route tests pass and selected v1 contracts remain green.

- [ ] **Step 7: Commit Task 7.**

```bash
git add apps/api/app/main.py apps/api/app/core/logging.py apps/api/app/assessment_v2 apps/api/tests
git commit -m "feat(api): expose assessment v2 foundation routes" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 8: Prove PostgreSQL RLS and startup migration separation

**Files:**

- Create: `apps/api/tests/assessment_v2/test_postgres_rls.py`
- Create: `scripts/check_assessment_v2_postgres.py`
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/assessment_v2/test_routes.py`

- [ ] **Step 1: Write the failing PostgreSQL integration test.**

Register marker `assessment_postgres`. The test must use `LINGUALENS_ASSESSMENT_TEST_DATABASE_URL`, migrate as the database owner, create a `NOSUPERUSER NOBYPASSRLS` application role, grant only required schema/table/sequence rights, and connect as that role.

Insert synthetic Alpha and Beta records as owner, then prove as the limited role:

1. with `app.current_organization_id=org_alpha`, Alpha rows are visible and Beta rows are absent;
2. a direct insert with `organization_id=org_beta` fails under Alpha context;
3. without tenant context, tenant tables return zero rows and reject writes;
4. the API repository succeeds because it sets transaction-local tenant context;
5. after transaction completion, a pooled connection does not retain the previous organization context.

- [ ] **Step 2: Run RED against the local PostgreSQL service.**

Use an idempotent helper rather than an unconditional `createdb`:

```bash
docker compose up -d postgres
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_postgres.py
```

Expected: helper or RLS test fails before its implementation is complete.

- [ ] **Step 3: Add an isolated local v2 database.**

Update Compose so the existing PostgreSQL container initializes or can create `lingualens_assessment_v2_test` without changing the v1 database. The API service receives `LINGUALENS_ASSESSMENT_DATABASE_URL`; do not point it at `therapist_app_v2`. Do not embed production Supabase credentials.

`check_assessment_v2_postgres.py` must:

- wait for the existing Compose PostgreSQL healthcheck;
- create the test database only if absent;
- drop and recreate only the explicitly named test schema/database after validating the exact target name;
- run v2 migrations;
- invoke `pytest -m assessment_postgres apps/api/tests/assessment_v2/test_postgres_rls.py -q`;
- never delete or modify the v1 database.

- [ ] **Step 4: Wire separately controlled startup migrations.**

`main.py` must run v1 migrations only under `run_migrations_on_startup` and v2 migrations only under `run_assessment_migrations_on_startup`. A failure in either startup migration must fail application startup and identify only the migration family, never the connection URL.

Add a route test proving both flags default to false and that each runner is called only by its own flag.

- [ ] **Step 5: Run GREEN and the migration pair.**

Run:

```bash
PYTHONPATH=apps/api:src python scripts/check_api_migrations.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_postgres.py
```

Expected: old migration smoke, new migration smoke, and PostgreSQL RLS checks all pass.

- [ ] **Step 6: Commit Task 8.**

```bash
git add apps/api/app/main.py apps/api/tests/assessment_v2 scripts/check_assessment_v2_postgres.py pyproject.toml docker-compose.yml
git commit -m "test(api): prove assessment tenant isolation" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

### Task 9: Integrate documentation, full verification, and final-strict review

**Files:**

- Modify: `scripts/check_project.sh`
- Modify: `README.md`
- Modify: `DEVELOPER_SETUP.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/PROJECT_SOURCE_OF_TRUTH.md`
- Create: `docs/architecture/decisions/ADR-001-assessment-v2-isolated-foundation.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the new focused gates to project verification.**

Place SQLite v2 migration smoke and `pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q` in `scripts/check_project.sh`. Keep the PostgreSQL RLS command as an explicit candidate/release gate because the focused script does not own Compose lifecycle.

- [ ] **Step 2: Document the delivered boundary.**

Documentation must state:

- `/api/v1` remains the current therapist product while `/api/v2` Foundation is built additively;
- the two database URLs and migration histories are intentionally separate;
- the new DB starts empty and no existing records are imported;
- clients still use v1 until their later migration plans;
- v2 currently supports child/consent/assessment foundation only;
- it is research decision support, not diagnosis, and exposes no ASD probability;
- local startup commands and both migration commands;
- Supabase Auth establishes identity, FastAPI owns policy, PostgreSQL RLS is defense in depth;
- the exact rollback is to stop mounting `/api/v2` and stop v2 startup migrations, without touching v1 data.

The ADR records why a separate database URL and migration history were chosen instead of rewriting the existing v1 migration chain.

- [ ] **Step 3: Run focused and complete candidate checks once.**

First run focused checks after documentation integration:

```bash
cd apps/api && PYTHONPATH=. pytest tests/assessment_v2 -m "not assessment_postgres" -q
cd apps/api && PYTHONPATH=. pytest tests/test_workflow.py tests/test_tenant_isolation_phase1.py tests/test_security_controls.py -q
PYTHONPATH=apps/api:src python scripts/check_api_migrations.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_migrations.py
PYTHONPATH=apps/api:src python scripts/check_assessment_v2_postgres.py
git diff --check
```

After focused checks are green, freeze the behavior candidate and run the repository-wide candidate gate once:

```bash
bash scripts/check_project.sh
```

If it fails, fix related failures, rerun focused checks, and then perform one fresh complete pass. Do not repeatedly run the full suite between individual edits.

- [ ] **Step 4: Perform the parent adversarial pass.**

Record counterexamples and observed evidence for:

- forged organization headers with a valid user token;
- inactive membership;
- same-organization user outside the care team;
- consent withdrawal immediately before assessment creation;
- duplicate child display code;
- stale version races;
- direct SQL cross-tenant read/write;
- missing tenant session setting;
- transaction rollback after audit creation;
- v2 exception content reaching logs;
- accidental v1 migration or URL reuse;
- startup with one migration flag enabled and the other disabled;
- malformed client attempts to inject organization, state, diagnosis, or probability.

Prove test sensitivity by deliberately mutating one transition edge, one care-team predicate, and one RLS expectation in the test worktree, observing failures, and reverting only those deliberate mutations before refreezing. Set `PARENT_ADVERSARIAL_READY: yes` only after the clean candidate is green again.

- [ ] **Step 5: Prepare and validate final-strict evidence.**

Follow the repository's final-strict instructions exactly. Bind the exact base commit, candidate commit/tree, staged, unstaged, and untracked in-scope files. Use `scripts/compute_delivery_manifest.py` for runtime-loaded API and migration artifacts. Persist the ledger, attempt journal, reviewer packet, candidate manifest, delivery manifest, and canonical `FINAL_STRICT_READINESS_RECORD`; run `scripts/validate_final_strict_packet.py` and preserve its passing output.

Before reserving the reviewer call, verify:

```text
ASSURANCE_UNIT_ID: lingualens-assessment-foundation-v2
TARGET_REVIEW_CALLS: 1
REVIEW_BUDGET_MODE: default
MAX_REVIEW_CALLS: 3
REVIEW_READY: yes
PARENT_ADVERSARIAL_READY: yes
```

Reserve one unique review attempt under the required exclusive coordination primitive, then request a fresh read-only `solweaver_reviewer` verdict over the complete frozen Foundation candidate. Resolve any blocker through the mandated re-review or parent-recovery flow; never reset or increase the review budget.

- [ ] **Step 6: Commit integration documentation only after behavior is verified.**

```bash
git add scripts/check_project.sh README.md DEVELOPER_SETUP.md docs/DEVELOPMENT.md docs/SECURITY.md docs/PROJECT_SOURCE_OF_TRUTH.md docs/architecture/decisions/ADR-001-assessment-v2-isolated-foundation.md CHANGELOG.md
git commit -m "docs: document assessment v2 foundation" \
  -m "Co-Authored-By: GPT-5 Codex <noreply@openai.com>"
```

- [ ] **Step 7: Report the slice outcome without overstating clinical readiness.**

The handoff must include:

- exact commits and changed files;
- RED/GREEN/REFACTOR evidence per behavior task;
- SQLite migration, PostgreSQL RLS, focused API, v1 regression, and complete verification results;
- final-strict verdict/status and known blockers;
- confirmation that no old data or storage was deleted or migrated;
- confirmation that `/api/v1` still serves existing clients;
- explicit statement that Capture is the next plan and that Foundation alone is not a therapist-ready diagnostic workflow.

## Foundation API contract summary

The delivered v2 contract is intentionally small:

```text
Child
  ├── append ConsentRecord
  └── create Assessment (requires active clinical consent)
        └── transition through an explicit, version-checked lifecycle

Supabase identity
  -> FastAPI organization/role/care-team/consent policy
  -> tenant-bound SQL transaction
  -> PostgreSQL RLS
  -> mutation + sanitized audit event in the same commit
```

All future slices extend the assessment aggregate through new bounded modules. They must not bypass this service, transaction, audit, or error boundary.
