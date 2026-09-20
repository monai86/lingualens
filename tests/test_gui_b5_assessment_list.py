"""Focused tests for D1 Finding B5: assessment-list failure must not appear as empty success.

Covers:
1. 200 with [] is genuine empty success.
2. 401 routes through existing auth boundary, not showing empty success.
3. 403/network/5xx is explicit failure, does not fallback to [].
4. malformed response is a contract error, not empty success.
5. failure after existing data must not allow stale data from child A to be used under child B.
6. stale response after switching child/session must not overwrite current state.
7. creation succeeds but list refresh fails: preserves creation fact, reports refresh failure separately, no auto-retry POST.
8. retry GET after failure recovers cleanly.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from typing import Any
import unittest.mock as mock

import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import (
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensClient,
    LinguaLensPermissionError,
    LinguaLensServerError,
)


class FakeB5ApiClient:
    """Deterministic fake client for B5 assessment-list tests."""

    def __init__(self) -> None:
        self.mock_mode = False
        self.children_to_return: list[dict[str, Any]] = [
            {"id": "child-01", "display_code": "C01", "birth_year": 2021, "birth_month": 6},
            {"id": "child-02", "display_code": "C02", "birth_year": 2020, "birth_month": 3},
        ]
        self.child_data_map: dict[str, dict[str, Any]] = {
            "child-01": {"id": "child-01", "display_code": "C01", "birth_year": 2021, "birth_month": 6},
            "child-02": {"id": "child-02", "display_code": "C02", "birth_year": 2020, "birth_month": 3},
        }
        self.assessments_map: dict[str, list[dict[str, Any]]] = {}
        self.list_assessments_side_effect: Exception | None = None
        self.list_assessments_gate: threading.Event | None = None
        self.list_assessments_call_count = 0

        self.cases_to_return: list[dict[str, Any]] = []
        self.sessions_map: dict[str, list[dict[str, Any]]] = {}
        self.transcripts_map: dict[str, dict[str, Any]] = {}
        self.findings_map: dict[str, dict[str, Any]] = {}
        self.consents_map: dict[str, list[dict[str, Any]]] = {}

        self.create_assessment_call_count = 0
        self.create_assessment_return_value: dict[str, Any] | None = None
        self.get_assessment_calls: list[str] = []

    def check_health(self) -> bool:
        return True

    def list_cases(self) -> list[dict[str, Any]]:
        return self.cases_to_return

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        return self.sessions_map.get(case_id, [])

    def get_session_transcript(self, session_id: str) -> dict[str, Any]:
        return self.transcripts_map.get(session_id, {"utterances": []})

    def get_findings(self, session_id: str) -> dict[str, Any]:
        return self.findings_map.get(session_id, {"has_data": False, "metrics": {}})

    def list_children(self) -> list[dict[str, Any]]:
        return self.children_to_return

    def get_child(self, child_id: str) -> dict[str, Any]:
        return self.child_data_map.get(child_id, {"id": child_id})

    def get_consents(self, child_id: str) -> list[dict[str, Any]]:
        return self.consents_map.get(child_id, [])

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        self.list_assessments_call_count += 1
        if self.list_assessments_gate:
            self.list_assessments_gate.wait(timeout=2.0)
        if self.list_assessments_side_effect:
            raise self.list_assessments_side_effect
        return list(self.assessments_map.get(child_id, []))

    def create_assessment(self, child_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.create_assessment_call_count += 1
        if self.create_assessment_return_value:
            return self.create_assessment_return_value
        asmt_id = f"asmt-{child_id}-{self.create_assessment_call_count}"
        new_asmt = {
            "id": asmt_id,
            "child_id": child_id,
            "purpose": payload.get("purpose", "clinical_assessment"),
            "state": "draft",
            "assigned_clinician_id": payload.get("assigned_clinician_id", "clinician-01"),
            "version": 1,
        }
        if child_id not in self.assessments_map:
            self.assessments_map[child_id] = []
        self.assessments_map[child_id].append(new_asmt)
        return new_asmt

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        if not hasattr(self, "get_assessment_calls"):
            self.get_assessment_calls = []
        self.get_assessment_calls.append(assessment_id)
        for child_asmts in self.assessments_map.values():
            for a in child_asmts:
                if a.get("id") == assessment_id:
                    return a
        raise LinguaLensApiError(f"Assessment '{assessment_id}' not found.")


@pytest.fixture
def tk_root() -> tk.Tk:
    """Create a headless, withdrawn Tk root."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not available or headless environment without DISPLAY")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def _drain_async_queue(app: LinguaLensGUIApp) -> None:
    """Synchronously drain all pending tasks from the async queue onto the main thread."""
    while True:
        try:
            callback, _ = app._async_queue.get_nowait()
            callback()
        except queue.Empty:
            break


# ---------------------------------------------------------------------------
# Test Cases for B5
# ---------------------------------------------------------------------------

def test_assessment_list_200_empty_list_is_genuine_empty_success(tk_root: tk.Tk) -> None:
    """1. HTTP 200 with [] is genuine empty success: 0 rows, no error row, no error in status."""
    client = FakeB5ApiClient()
    client.assessments_map["child-01"] = []

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    t = app._refresh_assessments()
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    assert app._cached_assessments == []
    assert len(app.tree_assessments.get_children()) == 0
    assert getattr(app, "_assessment_list_error", None) is None
    assert "Failed to list assessments" not in app.lbl_status.cget("text")


def test_assessment_list_401_routes_to_auth_boundary_not_empty_success(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """2. HTTP 401 routes through existing auth boundary, and does NOT claim empty success."""
    client = FakeB5ApiClient()
    client.list_assessments_side_effect = LinguaLensAuthError("HTTP 401 Session expired")

    auth_calls = []
    monkeypatch.setattr(
        LinguaLensGUIApp,
        "_handle_auth_error",
        lambda self, err, **kw: auth_calls.append(err),
    )

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    t = app._refresh_assessments()
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    assert len(auth_calls) == 1
    assert isinstance(auth_calls[0], LinguaLensAuthError)


def test_assessment_list_403_and_5xx_and_network_error_are_explicit_failures(tk_root: tk.Tk) -> None:
    """3. 403, 5xx, and network errors are explicit failures, not fallback []."""
    client = FakeB5ApiClient()
    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    errors_to_test = [
        LinguaLensPermissionError("HTTP 403 Forbidden: Insufficient role"),
        LinguaLensServerError("HTTP 500 Internal Server Error"),
        LinguaLensApiError("Connection refused by upstream API"),
    ]

    for err in errors_to_test:
        client.list_assessments_side_effect = err
        t = app._refresh_assessments()
        if t:
            t.join(timeout=1.0)
        _drain_async_queue(app)

        # Must record explicit failure
        assert getattr(app, "_assessment_list_error", None) is not None
        assert str(err) in getattr(app, "_assessment_list_error", "")
        # Status bar must show explicit failure
        assert "⚠️ Failed to list assessments" in app.lbl_status.cget("text")
        # Tree must NOT appear as clean empty success (it must show error row)
        items = app.tree_assessments.get_children()
        assert len(items) == 1
        assert items[0] == "_error"
        assert "⚠️ Error" in str(app.tree_assessments.item("_error")["values"])


def test_assessment_list_malformed_response_raises_contract_error_in_client() -> None:
    """4. Malformed non-list response is a contract error in client.py, not empty success."""
    client = LinguaLensClient(mock_mode=False)

    # Mock _http_request returning a dict or string instead of list
    with mock.patch.object(client, "_http_request", return_value={"status": "not_a_list"}):
        with pytest.raises(LinguaLensApiError, match="[Mm]alformed response"):
            client.list_assessments("child-01")

    with mock.patch.object(client, "_http_request", return_value="invalid string"):
        with pytest.raises(LinguaLensApiError, match="[Mm]alformed response"):
            client.list_assessments("child-01")


def test_assessment_list_failure_on_new_child_does_not_use_old_child_assessments(tk_root: tk.Tk) -> None:
    """5. Failure after existing data must not allow stale data from child A to remain under child B."""
    client = FakeB5ApiClient()
    # Child A has assessments
    client.assessments_map["child-01"] = [
        {"id": "asmt-A1", "child_id": "child-01", "purpose": "screening", "state": "draft", "clinician": "c1", "version": 1},
    ]

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    t = app._refresh_assessments()
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    assert "asmt-A1" in app.tree_assessments.get_children()
    assert len(app._cached_assessments) == 1

    # Now switch to Child B, but listing assessments fails
    client.list_assessments_side_effect = LinguaLensServerError("HTTP 502 Bad Gateway")
    app._set_active_child("child-02")
    _drain_async_queue(app)

    # Wait for child B assessment thread
    if getattr(app, "_current_assessment_thread", None):
        app._current_assessment_thread.join(timeout=1.0)
    _drain_async_queue(app)

    # Child A's assessments must NOT be in cache or tree under Child B
    assert "asmt-A1" not in app.tree_assessments.get_children()
    assert not any(a.get("id") == "asmt-A1" for a in app._cached_assessments)
    assert app.active_assessment_id is None
    # Must show error indicator for Child B
    assert getattr(app, "_assessment_list_error", None) is not None


def test_assessment_list_stale_response_discarded_after_child_or_session_switch(tk_root: tk.Tk) -> None:
    """6. Stale response after switching child/session must not overwrite current state."""
    client = FakeB5ApiClient()
    gate = threading.Event()
    client.list_assessments_gate = gate
    client.assessments_map["child-01"] = [
        {"id": "asmt-stale-01", "child_id": "child-01", "purpose": "screening", "state": "draft", "clinician": "c1", "version": 1},
    ]

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    # Start refresh for child-01 (blocked by gate)
    t = app._refresh_assessments()

    # User immediately switches to child-02
    client.list_assessments_gate = None
    app._set_active_child("child-02")
    _drain_async_queue(app)

    # Now let stale worker for child-01 finish
    gate.set()
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    # Stale assessment from child-01 must NOT be inserted into child-02
    assert "asmt-stale-01" not in app.tree_assessments.get_children()
    assert not any(a.get("id") == "asmt-stale-01" for a in app._cached_assessments)


def test_assessment_creation_success_with_list_refresh_failure_preserves_creation_fact_without_retry(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """7. Creation succeeds but list refresh fails: preserves creation fact, reports refresh failure, no auto-retry."""
    client = FakeB5ApiClient()
    created_asmt = {
        "id": "asmt-created-999",
        "child_id": "child-01",
        "purpose": "diagnostic",
        "state": "draft",
        "assigned_clinician_id": "therapist-1",
        "version": 1,
    }
    client.create_assessment_return_value = created_asmt
    client.list_assessments_side_effect = LinguaLensServerError("HTTP 500 downstream refresh failure")

    warnings_shown = []
    monkeypatch.setattr(
        "tkinter.messagebox.showwarning",
        lambda title, msg, **kw: warnings_shown.append((title, msg)),
    )

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    session_gen = app._get_current_session_generation()
    child_sel_gen = getattr(app, "_child_selection_generation", 0)

    # Trigger post-creation refresh
    t = app._refresh_assessments_after_creation(
        child_id="child-01",
        session_gen=session_gen,
        child_sel_gen=child_sel_gen,
        created_asmt=created_asmt,
    )
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    # FACT PRESERVED: created assessment is in the treeview
    assert "asmt-created-999" in app.tree_assessments.get_children()
    # Warning dialog shown specifically for refresh failure
    assert len(warnings_shown) == 1
    assert "Assessment Created (Refresh Failed)" in warnings_shown[0][0]
    # No auto-retry POST was executed
    assert client.create_assessment_call_count == 0  # Only refresh was called here


def test_assessment_list_retry_recovers_after_transient_failure(tk_root: tk.Tk) -> None:
    """8. Retry GET after transient failure recovers cleanly."""
    client = FakeB5ApiClient()
    client.list_assessments_side_effect = LinguaLensServerError("Temporary 503 Service Unavailable")

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    # Initial failed attempt
    t1 = app._refresh_assessments()
    if t1:
        t1.join(timeout=1.0)
    _drain_async_queue(app)

    assert getattr(app, "_assessment_list_error", None) is not None
    assert "_error" in app.tree_assessments.get_children()

    # Recovery
    client.list_assessments_side_effect = None
    client.assessments_map["child-01"] = [
        {"id": "asmt-recovered-1", "child_id": "child-01", "purpose": "progress", "state": "draft", "clinician": "c1", "version": 1},
    ]

    t2 = app._refresh_assessments()
    if t2:
        t2.join(timeout=1.0)
    _drain_async_queue(app)

    # Recovered state
    assert getattr(app, "_assessment_list_error", None) is None
    assert "_error" not in app.tree_assessments.get_children()
    assert "asmt-recovered-1" in app.tree_assessments.get_children()
    assert len(app._cached_assessments) == 1
    assert app.lbl_status.cget("text") == "Ready"


def test_selecting_presentation_error_row_does_not_invoke_detail_api_or_start_selection_worker(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """9. Selecting presentation error row does NOT invoke get_assessment, mutate active context, or start worker."""
    errors_shown = []
    monkeypatch.setattr(
        "tkinter.messagebox.showerror",
        lambda title, msg, **kw: errors_shown.append((title, msg)),
    )

    client = FakeB5ApiClient()
    client.list_assessments_side_effect = LinguaLensServerError("500 Outage")

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    # Refresh fails via real callback path
    t = app._refresh_assessments()
    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    assert "_error" in app.tree_assessments.get_children()
    # Reset thread tracker if any from startup
    app._current_assessment_detail_thread = None

    # User clicks/selects the error row via real event/callback
    app.tree_assessments.selection_set("_error")
    app._on_assessment_selected()
    _drain_async_queue(app)

    # 1. No API call with "_error"
    assert "_error" not in client.get_assessment_calls
    # 2. No active assessment context mutation
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    # 3. No selection worker started
    assert getattr(app, "_current_assessment_detail_thread", None) is None
    # 4. Error row should not remain selected as a domain record
    assert "_error" not in app.tree_assessments.selection()


def test_cache_miss_detail_fetch_preserved_for_genuine_assessment_after_recovery(
    tk_root: tk.Tk,
) -> None:
    """10. After recovery, genuine assessment selection works; cache-miss invokes detail fetch."""
    client = FakeB5ApiClient()
    client.list_assessments_side_effect = LinguaLensServerError("500 Outage")

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_child_id = "child-01"

    # Initial failure
    t1 = app._refresh_assessments()
    if t1:
        t1.join(timeout=1.0)
    _drain_async_queue(app)
    assert "_error" in app.tree_assessments.get_children()

    # Recovery: list succeeds with domain record
    client.list_assessments_side_effect = None
    real_asmt = {
        "id": "asmt-real-1",
        "child_id": "child-01",
        "purpose": "diagnostic",
        "state": "draft",
        "assigned_clinician_id": "clinician-01",
        "version": 1,
    }
    client.assessments_map["child-01"] = [real_asmt]

    t2 = app._refresh_assessments()
    if t2:
        t2.join(timeout=1.0)
    _drain_async_queue(app)

    assert "asmt-real-1" in app.tree_assessments.get_children()
    assert "_error" not in app.tree_assessments.get_children()

    # Clear cache to simulate a cache-miss for genuine assessment
    app._cached_assessments = []

    # Select real assessment row
    app.tree_assessments.selection_set("asmt-real-1")
    app._on_assessment_selected()

    # Worker must be started for cache-miss
    detail_thread = getattr(app, "_current_assessment_detail_thread", None)
    assert detail_thread is not None
    detail_thread.join(timeout=1.0)
    _drain_async_queue(app)

    # API detail was fetched
    assert "asmt-real-1" in client.get_assessment_calls
    # Active assessment is updated
    assert app.active_assessment_id == "asmt-real-1"
    assert app.active_assessment is not None
    assert app.active_assessment.get("id") == "asmt-real-1"

