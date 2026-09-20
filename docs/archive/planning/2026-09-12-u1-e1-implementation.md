# U1 & E1 Implementation Plan: UX Handoff & Evidence Completeness

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide full local UX specifications and exact remote Figma checklists (U1), and implement E1 Evidence Completeness with research matrix, versioned clinician/caregiver observations, and generic instrument administration contracts.

**Architecture:** Extend Assessment V2 with focused domain modules `domain/observations.py` and `domain/instruments.py`, relational models in `db/models.py`, migration `0010_observations_and_instruments.py`, and `db/observations_repository.py`. Link feature definitions to research literature in `docs/research/feature-evidence-matrix.md`.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic, pytest.

---

### Task 1: U1 — Local UX Wireframes & Remote Handoff Checklist
**Files:**
- Create: `docs/ux/therapist-workflow/wireframes-and-screen-specs.md`
- Modify: `docs/ux/therapist-workflow/figma-delivery-manifest.md`

- [ ] **Step 1: Document remote delivery block in figma-delivery-manifest.md**
- [ ] **Step 2: Create comprehensive local wireframe & error states document**
- [ ] **Step 3: Verify documentation formatting and links**

---

### Task 2: E1 — Research Inventory & Feature-Evidence Matrix
**Files:**
- Create: `docs/research/feature-evidence-matrix.md`

- [ ] **Step 1: Map all features against actual PDFs in `/Users/porschecaa/Desktop/Paper-ASD/`**
- [ ] **Step 2: Resolve QJR8K5QS title discrepancy from PDF on disk**
- [ ] **Step 3: Document acoustic/timing boundaries and language transfer limitations**

---

### Task 3: E1 — Observations Domain Model (TDD)
**Files:**
- Create: `apps/api/app/assessment_v2/domain/observations.py`
- Test: `apps/api/tests/assessment_v2/test_observations.py`

- [ ] **Step 1: Write failing domain tests for ObservationRecordValue, amendment immutability, and validation**
- [ ] **Step 2: Run test to verify RED**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_observations.py -v`
- [ ] **Step 3: Implement minimal domain entities in domain/observations.py**
- [ ] **Step 4: Run test to verify GREEN**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_observations.py -v`

---

### Task 4: E1 — Instruments Domain Model (TDD)
**Files:**
- Create: `apps/api/app/assessment_v2/domain/instruments.py`
- Test: `apps/api/tests/assessment_v2/test_instruments.py`

- [ ] **Step 1: Write failing domain tests for InstrumentAdministration and InstrumentItemResponse**
- [ ] **Step 2: Run test to verify RED**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_instruments.py -v`
- [ ] **Step 3: Implement domain entities in domain/instruments.py**
- [ ] **Step 4: Run test to verify GREEN**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_instruments.py -v`

---

### Task 5: E1 — Relational Schema & Migration 0010 (TDD)
**Files:**
- Modify: `apps/api/app/assessment_v2/db/models.py`
- Create: `apps/api/app/assessment_v2/db/migrations/versions/0010_observations_and_instruments.py`
- Test: `apps/api/tests/assessment_v2/test_observation_db_models.py`

- [ ] **Step 1: Write failing model tests for database schema, constraints, and RLS tables**
- [ ] **Step 2: Run test to verify RED**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_observation_db_models.py -v`
- [ ] **Step 3: Add ORM models in db/models.py and write migration 0010**
- [ ] **Step 4: Run migration check**
  `PYTHONPATH=apps/api:src python3 scripts/check_assessment_v2_migrations.py`
- [ ] **Step 5: Run model tests to verify GREEN**
  `PYTHONPATH=apps/api:src python3 -m pytest apps/api/tests/assessment_v2/test_observation_db_models.py -v`

---

### Task 6: E1 — Repository & Integration (TDD)
**Files:**
- Create: `apps/api/app/assessment_v2/db/observations_repository.py`
- Test: `apps/api/tests/assessment_v2/test_observation_repository.py`

- [ ] **Step 1: Write failing repository tests for observation insertion, queries, tenant isolation, and amendments**
- [ ] **Step 2: Run test to verify RED**
- [ ] **Step 3: Implement repository methods**
- [ ] **Step 4: Run test to verify GREEN**
- [ ] **Step 5: Run full assessment v2 test suite and record in ANTIGRAVITY_HANDOFF_PROGRESS.md**
