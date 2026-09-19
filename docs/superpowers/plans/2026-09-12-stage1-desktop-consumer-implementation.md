# Assessment V2 Stage 1 Desktop Consumer Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect desktop consumer UI surfaces (`packages/gui/app.py` Tkinter Desktop GUI and `packages/tui/workflow.py` Terminal TUI) to verified Assessment V2 Stage 1 client methods (`create_child`, `list_children`, `get_active_consent`, `record_consent`, `create_assessment`, `get_assessment`), establishing safe typed V2 context transition, explicit consent verification, and downstream tab isolation without touching legacy v1 APIs or mutating local mock state.

**Architecture:** A thin-client consumer integration that sits atop the verified `LinguaLensClient` transport layer. The GUI and TUI present V2 Child intake, query backend-authoritative consent status badges with explicit consent-recording dialogs, enforce active consent gates before assessment creation, and store `active_assessment_id` strictly isolated from legacy `active_session_id`. Downstream legacy tabs (audio ingestion, utterance QA, findings, reports) are placed in a protected V2 mode with legacy action buttons disabled until subsequent V2 stages are implemented.

**Tech Stack:** Python 3.12 (`.venv/bin/python`), Tkinter / ttk (Desktop GUI), Rich (Terminal TUI), `pytest` test suite, FastAPI `TestClient` bridge.

---

## Scope & Critical Constraints

1. **Strict Stage 1 Boundary:**
   - ZERO audio capture, upload intents, or presigned storage operations (reserved for Stage 2).
   - ZERO new backend routes or clinical policy changes in `apps/api/`.
2. **Context Isolation (No ID Pollution):**
   - `self.active_assessment_id` must NEVER be assigned to `self.active_session_id` or passed to legacy v1 endpoints without compatibility checks.
   - Downstream tabs (Tabs 2–5) must inspect V2 context state and disable legacy action buttons (`Select Audio File`, `Ingest Demo Audio`, `Auto Refine`, etc.) with informative banners.
3. **Consent Gating Rules:**
   - Missing or withdrawn consent must NEVER be auto-granted upon assessment creation or child selection.
   - Opening an assessment does NOT grant consent; an explicit authorized action (`record_consent`) is required.
   - The backend is the authoritative consent gate (`HTTP 409 active_consent_required`); client-side UI prechecks do not replace server-side conflict handling during concurrent withdrawal races.
4. **Auth & State Lifecycle Rules:**
   - `HTTP 401` (`LinguaLensAuthError`): Invalidate session and wipe clinical context (`active_child=None`, `active_child_id=None`, `active_consent=None`, `active_assessment=None`, `active_assessment_id=None`, clear tables).
   - `HTTP 403` (`LinguaLensPermissionError`): Display permission denial dialog without clearing session or forcing logout.
   - Child switch, logout, or cancelled mutations must immediately purge active child context; late async worker responses from previous children must be silently discarded.
   - Live mode (`mock_mode=False`) must NEVER fall back to mock data or mutate local state upon failure.
   - Explicit UI mode badge must clearly distinguish `[LOCAL RESEARCH MOCK]` from `[CLINICAL LIVE - FASTAPI]`.

---

## File Structure & Responsibilities

| File Path | Surface | Responsibility |
| :--- | :--- | :--- |
| `packages/gui/app.py` | Tkinter GUI | V2 Child selector & intake modal, consent status badge & record dialog, assessment intake modal, context isolation, downstream tab protection, async response race guarding, mode badging |
| `packages/tui/workflow.py` | Terminal TUI | Interactive V2 Child intake menu, consent status display & grant wizard, assessment creation wizard, error loop recovery |
| `tests/test_gui.py` | GUI Tests | Verification of GUI Child intake, consent gating, withdrawal race 409 handling, V2 context isolation, 401 wiping, 403 preservation, late response discarding |
| `tests/test_tui.py` | TUI Tests | Verification of TUI Child menu, consent gating, assessment creation, and error recovery |

---

## Task A: Child Selection / Creation & Typed V2 Context

### Goal
Provide desktop users (GUI and TUI) with child intake and selection flows communicating via canonical `create_child` and `list_children` methods, maintaining a typed `active_child` model while isolating previous child state.

**Files:**
- Modify: `packages/gui/app.py`
- Modify: `packages/tui/workflow.py`
- Test: `tests/test_gui.py`
- Test: `tests/test_tui.py`

- [ ] **Step A.1: Write failing GUI tests for Child intake validation and child-switch context flushing**

In `tests/test_gui.py`, add:
```python
def test_gui_child_intake_empty_code_rejected_client_side(monkeypatch):
    """Empty display_code must be rejected client-side without calling client.create_child."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from unittest.mock import MagicMock

    root = tk.Tk()
    root.withdraw()
    client = MagicMock()
    app = LinguaLensGUIApp(root, client)

    # Call child intake modal validation directly or simulate empty submission
    validation_error = app._validate_child_intake("", 2021, 5)
    assert validation_error == "Child Identifier / Display Code is required."
    client.create_child.assert_not_called()
    root.destroy()


def test_gui_child_switch_flushes_previous_clinical_context(monkeypatch):
    """Switching active child must flush consent, assessment ID, and previous child views."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from unittest.mock import MagicMock

    root = tk.Tk()
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [
        {"id": "c1", "display_code": "C-001", "birth_year": 2020, "birth_month": 1},
        {"id": "c2", "display_code": "C-002", "birth_year": 2021, "birth_month": 6},
    ]
    client.get_active_consent.return_value = None
    client.list_assessments.return_value = []

    app = LinguaLensGUIApp(root, client)
    # Set existing clinical context for child 1
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-001"}
    app.active_consent = {"id": "consent-1", "status": "active"}
    app.active_assessment_id = "asmt-001"
    app.active_assessment = {"id": "asmt-001"}

    # Switch to child 2
    app._set_active_child("c2")

    assert app.active_child_id == "c2"
    assert app.active_consent is None
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()
```

- [x] **Step A.1: Write failing GUI test for Child intake validation & switch context flush**
- [x] **Step A.2: Run test to verify it fails (observed RED)**
- [x] **Step A.3: Write failing TUI test for Child intake menu**
- [x] **Step A.4: Run TUI test to verify it fails (observed RED)**
- [x] **Step A.5: Implement Child state & intake in `packages/gui/app.py` and `packages/tui/workflow.py`**
- [x] **Step A.6: Run tests to verify they pass (observed GREEN: 29/29 GUI tests, 73/73 TUI/transport/canonical tests pass)**

---

## Task B: Consent Status Display & Explicit Recording Interaction

### Goal
Provide visible consent verification status badges indicating the latest loaded state with explicit refresh (not real-time polling), distinguish states (`not-loaded`, `loading`, `active`, `withdrawn`, `no-record`, `error`) using `list_consents` and canonical latest-version-per-purpose semantics, enforce explicit authorized recording (NO auto-grant on child selection), provide an explicit `Record / Update Consent` interaction modal/wizard for active/withdrawn states, and handle conflict errors (`HTTP 409`) and lifecycle races.

> [!WARNING]
> **Canonical Schema & Endpoint Binding Reminder for Task B:**
> `record_consent` must strictly use the canonical backend schema and path:
> - Route: `POST /api/v2/children/{child_id}/consents`
> - Payload fields: `purpose`, `scope_version`, `status` ONLY (`evidence_ref` does NOT exist in canonical schema).
> - `child_id` is passed via URL path, NOT the request body.
> - DO NOT add `organization_id` or `granted_by_relation` to client payloads or schemas from narrative reports without explicit backend contract support.
> - Assessment creation is strictly Task C; do not add assessment endpoints or fake assessment test paths in Task B.

**Files:**
- Modify: `packages/gui/app.py`
- Modify: `packages/tui/workflow.py`
- Modify: `packages/tui/ui.py` (if needed for rendering)
- Test: `tests/test_gui.py`
- Test: `tests/test_tui.py`

- [x] **Step B.1: Write failing GUI tests for consent status badges, explicit recording, and lifecycle/race handling** (observed RED)
- [x] **Step B.2: Write failing TUI tests for consent workspace display and explicit wizard** (observed RED)
- [x] **Step B.3: Run tests to verify they fail (RED)**
- [x] **Step B.4: Implement Consent UI, Badge, and Action Handlers in `packages/gui/app.py`, `packages/tui/workflow.py`, and `packages/tui/ui.py`**
- [x] **Step B.5: Run tests to verify they pass (GREEN: 55/55 GUI passed, 46/46 TUI passed, 138/138 combined client suite passed)**

---

## Task C: Assessment Creation & Safe Desktop Context Transition

### Goal
Implement Assessment V2 creation, store `active_assessment_id` strictly isolated from legacy `active_session_id`, protect downstream tabs by disabling incompatible legacy actions, implement 401/403 lifecycle handling, discard late async worker responses, and badge mock vs live mode.

**Files:**
- Modify: `packages/gui/app.py`
- Modify: `packages/tui/workflow.py`
- Test: `tests/test_gui.py`
- Test: `tests/test_tui.py`

- [ ] **Step C.1: Write failing GUI tests for context isolation, downstream tab disabling, and auth/permission lifecycle**

In `tests/test_gui.py`, add:
```python
def test_gui_assessment_creation_sets_v2_context_without_legacy_pollution():
    """Assessment V2 creation sets active_assessment_id and leaves active_session_id None."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from packages.tui.client import LinguaLensClient

    root = tk.Tk()
    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    child = client.create_child("C-ASMT-01", 2020, 10)
    client.record_consent(child["id"], purpose="clinical_assessment", status="active")

    app = LinguaLensGUIApp(root, client)
    app._set_active_child(child["id"])

    # Create assessment
    app._create_assessment_action(purpose="initial")

    assert app.active_assessment_id is not None
    assert app.active_assessment_id.startswith("asmt-")
    # CRITICAL INVARIANT: active_session_id must NOT be polluted with assessment_id
    assert app.active_session_id is None
    root.destroy()


def test_gui_downstream_tabs_disabled_in_v2_mode():
    """In V2 assessment mode, downstream legacy actions in Ingestion and Review tabs are disabled."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from unittest.mock import MagicMock

    root = tk.Tk()
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = []
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.get_active_consent.return_value = {"id": "con-1", "status": "active"}
    client.create_assessment.return_value = {"id": "asmt-999", "purpose": "initial"}
    client.list_assessments.return_value = [{"id": "asmt-999", "purpose": "initial"}]

    app = LinguaLensGUIApp(root, client)
    app._set_active_child("c1")
    app._create_assessment_action(purpose="initial")

    assert app.active_assessment_id == "asmt-999"
    # Ingestion tab legacy actions must be disabled in V2 mode
    assert app.btn_select_audio.cget("state") == "disabled"
    assert app.btn_ingest_demo.cget("state") == "disabled"
    root.destroy()


def test_gui_auth_401_clears_v2_clinical_context():
    """HTTP 401 must clear active_child, active_consent, and active_assessment."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from packages.tui.client import LinguaLensClient, LinguaLensAuthError

    root = tk.Tk()
    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client)
    app.active_child_id = "c-1"
    app.active_child = {"id": "c-1"}
    app.active_consent = {"id": "con-1"}
    app.active_assessment_id = "asmt-1"
    app.active_assessment = {"id": "asmt-1"}

    # Trigger auth error handling
    app._handle_auth_error(LinguaLensAuthError("Session expired."))

    assert app.active_child_id is None
    assert app.active_child is None
    assert app.active_consent is None
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_permission_403_preserves_session():
    """HTTP 403 displays permission denial dialog without clearing active session credentials."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensClient, LinguaLensPermissionError, ClientSession

    root = tk.Tk()
    root.withdraw()
    client = LinguaLensClient(mock_mode=False)
    client.set_session(ClientSession(access_token="valid-token", organization_id="org-1"))
    app = LinguaLensGUIApp(root, client)

    dialog_shown = []
    monkeypatch = None
    import tkinter.messagebox
    original_showerror = tkinter.messagebox.showerror
    tkinter.messagebox.showerror = lambda title, msg: dialog_shown.append((title, msg))

    try:
        app._handle_permission_error(LinguaLensPermissionError("Permission denied for child."))
        assert client.get_session() is not None
        assert client.get_session().access_token == "valid-token"
        assert len(dialog_shown) == 1
        assert "Permission Denied" in dialog_shown[0][0]
    finally:
        tkinter.messagebox.showerror = original_showerror
        root.destroy()


def test_gui_late_async_response_discarded_on_child_switch():
    """Late background worker response for a previous child must not overwrite state of newly selected child."""
    from packages.gui.app import LinguaLensGUIApp
    import tkinter as tk
    from packages.tui.client import LinguaLensClient

    root = tk.Tk()
    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client)

    app.active_child_id = "child-CURRENT"
    # Late callback arrives from child-OLD
    app._on_async_child_assessments_loaded("child-OLD", [{"id": "asmt-old"}])

    # Must be discarded because child-OLD != active_child_id
    assert app.active_assessment_id is None
    assert len(app.tree_assessments.get_children()) == 0
    root.destroy()
```

- [x] **Step C.1: Write failing tests for Assessment Intake, Isolation, Tab Protection, and Mode Badges**
  - Observed RED receipt: `.local/verification/antigravity-d1/red_subtask_c_assessment_lifecycle.log` (SHA-256: `c53bb17e747f06278e04ceb15771f1bc7fb0aae77657a4ebe904af50e9c4f45b`, 17 failed, 111 deselected).

- [x] **Step C.2: Run tests to verify they fail**
  - Ran: `PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_gui.py tests/test_tui.py -k "test_gui_create_assessment or test_gui_downstream_handlers_blocked_in_v2_mode or test_gui_legacy_mode_works_when_not_in_v2 or test_tui_create_assessment" -v`
  - Output: Verified RED phase (17 failures).

- [x] **Step C.3: Implement Assessment Intake, Isolation, Tab Protection, and Mode Badges**
  - Implemented in `packages/gui/app.py` and `packages/tui/workflow.py`:
    - Context isolation (`active_assessment_id` distinct from `active_session_id`).
    - Active consent precheck and authoritative backend 409 handling.
    - Modal opening target binding and confirmation drift guards.
    - Downstream isolation (`_guard_v2_mode()` across all legacy buttons, shortcuts, and direct callback entries).
    - Asynchronous creation and list refresh with creation fact preservation.
    - Canonical purpose parity: UI aligned with canonical backend `AssessmentPurpose` enum (`initial`, `developmental_follow_up`, `post_intervention_follow_up`, `additional_evidence`), rejecting invalid values with zero POST.
    - Typed consent preflight: fresh async `list_consents` read before mutation POST, preventing submission on stale cached status.
    - Canonical detail on selection: eliminated fake fallback dicts on selection; asynchronous `get_assessment` detail retrieval with child_id verification.

- [x] **Step C.4: Run all Stage 1 consumer tests to verify they pass**
  - Ran: `PYTHONPATH=. .venv/bin/pytest tests/test_gui.py tests/test_tui.py tests/test_tui_canonical_integration.py tests/test_tui_transport.py -v`
  - Output: **180 passed, 4 warnings in 26.42s** (exit code: 0).
  - Green receipt recorded: `.local/verification/antigravity-d1/subtask_c_preflight_and_canonical_contract_py312_green.log` (SHA-256: `e91da38472360e442cc5b05c73473d60b7ff5c491beee389ddbc368d10c6d8d8`).
  - Scoped source inventory (8 files): `.local/verification/antigravity-d1/source_inventory_subtask_c_preflight_closure.json` (SHA-256: `38def9820318a82978ad49c60ce81337fbcf02260aa7c1fbf3ef8e431f528907`).

---

## Complete Verification & Safety Checklist

1. **Focused Client Suite:**
   ```bash
   PYTHONPATH=.:src .venv/bin/python -m pytest tests/test_gui.py tests/test_tui.py tests/test_tui_transport.py tests/test_tui_canonical_integration.py -v
   ```
2. **Backend Assessment V2 Regression Gate:**
   ```bash
   PYTHONPATH=.:apps/api .venv/bin/pytest apps/api/tests/assessment_v2 -m "not assessment_postgres" -q
   ```
3. **Syntax & Whitespace Checks:**
   ```bash
   .venv/bin/python -m py_compile packages/gui/app.py packages/tui/workflow.py packages/tui/client.py tests/test_gui.py tests/test_tui.py
   git diff --check
   ```
4. **Source Inventory & Behavior Identity:**
   - Record updated inventory in `.local/verification/antigravity-d1/source_inventory_stage1_consumer.json`.
   - Confirm zero secret leakage, zero production database mutation, and zero Git commit/push.

---

## Execution Choice Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-12-stage1-desktop-consumer-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Fresh subagent per task (Task A, then Task B, then Task C), review between tasks, fast iteration.
**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
