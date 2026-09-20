"""Focused TDD tests for B3b GUI live-mode startup, search, and manual refresh error containment.

Verifies that live API failures (network drops, 500 server errors, 401 auth expiration,
403 permission errors) at GUI boundaries:
1. Do not escape constructors or crash the GUI lifecycle.
2. Do not fabricate active cases or sessions.
3. Do not wipe existing UI state before a successful fetch.
4. Do not misinterpret search API failures as "no matching cases" or change active selection.
5. Invalidate dependent session/transcript context when switching cases/sessions and fetch fails.
6. Do not mask unexpected programming errors as network failures.
7. Do not report success on manual refresh while async operations are pending or when any component fails.
8. Support clean recovery on retry once healthy.
"""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Any
import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import (
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensClient,
    LinguaLensPermissionError,
    LinguaLensServerError,
)


class FakeApiClient(LinguaLensClient):
    """Deterministic synthetic test client preventing accidental real HTTP calls."""

    def __init__(self) -> None:
        super().__init__(base_url="http://127.0.0.1:9", mock_mode=False)
        self.cases_to_return: list[dict[str, Any]] = []
        self.sessions_map: dict[str, list[dict[str, Any]]] = {}
        self.children_to_return: list[dict[str, Any]] = []
        self.transcripts_map: dict[str, dict[str, Any]] = {}
        self.consents_map: dict[str, list[dict[str, Any]]] = {}
        self.assessments_map: dict[str, list[dict[str, Any]]] = {}

        self.list_cases_side_effect: Exception | None = None
        self.list_sessions_side_effect: Exception | None = None
        self.list_children_side_effect: Exception | None = None
        self.get_transcript_side_effect: Exception | None = None

        self.list_children_event: threading.Event | None = None

    def list_cases(self) -> list[dict[str, Any]]:
        if self.list_cases_side_effect:
            raise self.list_cases_side_effect
        return list(self.cases_to_return)

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        if self.list_sessions_side_effect:
            raise self.list_sessions_side_effect
        return list(self.sessions_map.get(case_id, []))

    def list_children(self) -> list[dict[str, Any]]:
        if self.list_children_event:
            self.list_children_event.wait(timeout=3.0)
        if self.list_children_side_effect:
            raise self.list_children_side_effect
        return list(self.children_to_return)

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        if self.get_transcript_side_effect:
            raise self.get_transcript_side_effect
        return self.transcripts_map.get(session_id)

    def get_findings(self, session_id: str) -> dict[str, Any]:
        return {"has_data": False, "metrics": {}}

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        return list(self.consents_map.get(child_id, []))

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        return list(self.assessments_map.get(child_id, []))


@pytest.fixture(autouse=True)
def mock_msgbox(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[str, str]]]:
    """Capture messageboxes without blocking tests."""
    calls: dict[str, list[tuple[str, str]]] = {
        "showinfo": [],
        "showwarning": [],
        "showerror": [],
    }

    def _info(title: str, msg: str, *args: Any, **kwargs: Any) -> None:
        calls["showinfo"].append((title, msg))

    def _warn(title: str, msg: str, *args: Any, **kwargs: Any) -> None:
        calls["showwarning"].append((title, msg))

    def _err(title: str, msg: str, *args: Any, **kwargs: Any) -> None:
        calls["showerror"].append((title, msg))

    monkeypatch.setattr("tkinter.messagebox.showinfo", _info)
    monkeypatch.setattr("tkinter.messagebox.showwarning", _warn)
    monkeypatch.setattr("tkinter.messagebox.showerror", _err)
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    return calls


@pytest.fixture
def tk_root() -> tk.Tk:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def _drain_async_queue(app: LinguaLensGUIApp) -> None:
    """Drain all pending callbacks on app._async_queue on the main thread."""
    while not app._async_queue.empty():
        try:
            callback, err = app._async_queue.get_nowait()
            if callback:
                callback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Core Boundary Tests
# ---------------------------------------------------------------------------

def test_startup_list_cases_failure_does_not_crash_app_constructor(tk_root: tk.Tk) -> None:
    """When list_cases fails during GUI startup, the constructor must not raise an unhandled error."""
    client = FakeApiClient()
    client.list_cases_side_effect = LinguaLensServerError("Server error 500: Database unavailable.")

    app = LinguaLensGUIApp(tk_root, client=client)

    assert app.active_case_id is None
    assert app.active_session_id is None
    assert len(app.tree_cases.get_children()) == 0
    status_text = app.lbl_status.cget("text")
    assert "⚠️" in status_text or "Failed" in status_text or "Server error" in status_text


def test_startup_session_fetch_failure_does_not_crash_app(tk_root: tk.Tk) -> None:
    """When initial case exists but list_sessions fails, startup survives without fabricated session."""
    client = FakeApiClient()
    client.cases_to_return = [{
        "case_id": "case-b3b-001",
        "child_id": "CH-001",
        "age_months": 42,
        "primary_language": "th",
        "session_count": 1,
        "clinical_notes": "Initial intake",
    }]
    client.list_sessions_side_effect = LinguaLensServerError("Server error 500: Session service timeout.")

    app = LinguaLensGUIApp(tk_root, client=client)

    assert app.active_case_id == "case-b3b-001"
    assert app.active_session_id is None
    assert len(app.tree_sessions.get_children()) == 0
    status_text = app.lbl_status.cget("text")
    assert "⚠️" in status_text or "Failed" in status_text or "timeout" in status_text


def test_startup_401_triggers_auth_boundary(tk_root: tk.Tk, mock_msgbox: dict[str, list[tuple[str, str]]]) -> None:
    """When startup encounters HTTP 401, it routes to _handle_auth_error without crashing."""
    client = FakeApiClient()
    client.list_cases_side_effect = LinguaLensAuthError("Authentication failed: HTTP 401 Session expired.")

    app = LinguaLensGUIApp(tk_root, client=client)

    assert app.active_case_id is None
    assert app.active_session_id is None
    assert len(mock_msgbox["showerror"]) >= 1
    assert any("Sign-in" in call[0] or "Session expired" in call[1] for call in mock_msgbox["showerror"])


def test_case_search_typing_failure_does_not_claim_no_matching_cases_and_does_not_switch_selection(
    tk_root: tk.Tk,
) -> None:
    """When search typing triggers an API failure, it must NOT claim 'No matching cases' or switch selection."""
    client = FakeApiClient()
    client.cases_to_return = [
        {"case_id": "case-001", "child_id": "Alice", "clinical_notes": "First child"},
        {"case_id": "case-002", "child_id": "Bob", "clinical_notes": "Second child"},
    ]

    app = LinguaLensGUIApp(tk_root, client=client)
    app.active_case_id = "case-001"

    # Simulate network outage during search typing
    client.list_cases_side_effect = LinguaLensApiError("API request failed: Connection reset.")

    app.entry_case_search.delete(0, tk.END)
    app.entry_case_search.insert(0, "searching")
    app._on_case_search_typing(None)

    combo_vals = list(app.combo_global_case["values"])
    assert "(No matching cases)" not in combo_vals
    assert app.active_case_id == "case-001"
    assert "⚠️" in app.lbl_status.cget("text") or "Search failed" in app.lbl_status.cget("text")


def test_refresh_cases_preserves_existing_rows_on_fetch_failure(tk_root: tk.Tk) -> None:
    """_refresh_cases must not wipe existing treeview rows if the new fetch fails."""
    client = FakeApiClient()
    client.cases_to_return = [
        {"case_id": "case-keep-1", "child_id": "Child-1", "age_months": 36, "primary_language": "th"},
        {"case_id": "case-keep-2", "child_id": "Child-2", "age_months": 48, "primary_language": "th"},
    ]

    app = LinguaLensGUIApp(tk_root, client=client)
    assert len(app.tree_cases.get_children()) == 2

    # Break list_cases
    client.list_cases_side_effect = LinguaLensServerError("HTTP 502 Bad Gateway")

    result = app._refresh_cases()
    assert result is False
    assert len(app.tree_cases.get_children()) == 2
    assert "case-keep-1" in app.tree_cases.get_children()
    assert "case-keep-2" in app.tree_cases.get_children()


def test_refresh_cases_distinguishes_empty_list_from_failure(tk_root: tk.Tk) -> None:
    """Genuine empty list [] is a clean success with '(No Cases)', distinct from an error."""
    client = FakeApiClient()
    client.cases_to_return = []

    app = LinguaLensGUIApp(tk_root, client=client)
    res = app._refresh_cases()

    assert res is True
    assert app.active_case_id is None
    assert app.combo_global_case.get().startswith("(No Cases")
    assert "⚠️" not in app.lbl_status.cget("text")


def test_retry_after_failure_recovers_cleanly(tk_root: tk.Tk) -> None:
    """After an initial failure, subsequent refresh when healthy restores normal GUI state."""
    client = FakeApiClient()
    client.list_cases_side_effect = LinguaLensServerError("Transient failure")

    app = LinguaLensGUIApp(tk_root, client=client)
    assert app.active_case_id is None

    # Recover health
    client.list_cases_side_effect = None
    client.cases_to_return = [
        {"case_id": "case-rec-001", "child_id": "Recovered", "age_months": 50, "primary_language": "th"}
    ]

    res = app._refresh_cases()
    assert res is True
    assert len(app.tree_cases.get_children()) == 1
    assert "case-rec-001" in app.tree_cases.get_children()


# ---------------------------------------------------------------------------
# Corrective Gap Tests (B3b Gap Closure)
# ---------------------------------------------------------------------------

def test_refresh_all_data_does_not_report_success_while_children_pending(
    tk_root: tk.Tk, mock_msgbox: dict[str, list[tuple[str, str]]]
) -> None:
    """_refresh_all_data must NOT show success messagebox while async children refresh is still pending."""
    client = FakeApiClient()
    client.cases_to_return = [{"case_id": "case-01", "child_id": "C-01"}]
    # Gate children refresh on an event so it stays pending
    gate = threading.Event()
    client.list_children_event = gate

    app = LinguaLensGUIApp(tk_root, client=client)
    mock_msgbox["showinfo"].clear()

    # Initiate refresh all
    app._refresh_all_data()

    # While children refresh worker is in-flight, success must NOT be reported
    assert len(mock_msgbox["showinfo"]) == 0, "Showed success prematurely while children was pending"

    # Now let children worker complete and drain queue on main thread
    gate.set()
    import time
    time.sleep(0.05)
    _drain_async_queue(app)

    # Now overall success should be reported
    assert len(mock_msgbox["showinfo"]) == 1
    assert "Data refreshed successfully" in mock_msgbox["showinfo"][0][1]


def test_refresh_all_data_reports_failure_when_children_fails_even_if_cases_sessions_succeed(
    tk_root: tk.Tk, mock_msgbox: dict[str, list[tuple[str, str]]]
) -> None:
    """When cases/sessions succeed but children fails, overall success must NOT be reported."""
    client = FakeApiClient()
    client.cases_to_return = [{"case_id": "case-01", "child_id": "C-01"}]
    client.list_children_side_effect = LinguaLensServerError("Children database unreachable")

    app = LinguaLensGUIApp(tk_root, client=client)
    mock_msgbox["showinfo"].clear()
    mock_msgbox["showerror"].clear()

    app._refresh_all_data()
    import time
    time.sleep(0.05)
    _drain_async_queue(app)

    # Overall success must NOT be shown
    assert len(mock_msgbox["showinfo"]) == 0
    # Error must be reported
    assert len(mock_msgbox["showerror"]) >= 1
    assert any("Children" in call[1] or "children" in call[1] or "Failed" in call[1] for call in mock_msgbox["showerror"])


def test_refresh_all_data_reports_failure_when_transcript_fetch_fails(
    tk_root: tk.Tk, mock_msgbox: dict[str, list[tuple[str, str]]]
) -> None:
    """When transcript fetch fails for the active session, refresh must report partial failure."""
    client = FakeApiClient()
    client.cases_to_return = [{"case_id": "case-01", "child_id": "C-01"}]
    client.sessions_map["case-01"] = [{
        "session_id": "sess-01",
        "case_id": "case-01",
        "session_date": "2026-09-01",
        "transcript_id": "tr-01",
    }]
    client.get_transcript_side_effect = LinguaLensServerError("Transcript storage 500")

    app = LinguaLensGUIApp(tk_root, client=client)
    mock_msgbox["showinfo"].clear()
    mock_msgbox["showerror"].clear()

    res = app._refresh_all_data()
    import time
    time.sleep(0.05)
    _drain_async_queue(app)

    assert res is False
    assert len(mock_msgbox["showinfo"]) == 0
    assert len(mock_msgbox["showerror"]) >= 1


def test_case_switch_invalidates_session_context_when_session_fetch_fails(tk_root: tk.Tk) -> None:
    """Switching from Case A to Case B when list_sessions(B) fails must NOT leave Case A's session context."""
    client = FakeApiClient()
    client.cases_to_return = [
        {"case_id": "case-A", "child_id": "Child-A"},
        {"case_id": "case-B", "child_id": "Child-B"},
    ]
    client.sessions_map["case-A"] = [{
        "session_id": "sess-A1",
        "case_id": "case-A",
        "session_date": "2026-08-01",
        "transcript_id": "tr-A1",
    }]
    client.transcripts_map["sess-A1"] = {"utterances": [{"speaker": "CHI", "text": "Hello from A"}]}

    app = LinguaLensGUIApp(tk_root, client=client)
    assert app.active_case_id == "case-A"
    assert app.active_session_id == "sess-A1"
    assert app.active_transcript is not None

    # Now make list_sessions fail for case-B
    def failing_sessions(case_id: str) -> list[dict[str, Any]]:
        if case_id == "case-B":
            raise LinguaLensServerError("Sessions offline for case-B")
        return client.sessions_map.get(case_id, [])

    client.list_sessions = failing_sessions  # type: ignore[assignment]

    # Select Case B in Treeview and trigger selection callback
    app.tree_cases.selection_set("case-B")
    app._on_case_selected(None)

    assert app.active_case_id == "case-B"
    # Actionable session & transcript of A must NOT remain under B!
    assert app.active_session_id is None, "Active session of A remained active under B"
    assert app.active_transcript is None, "Active transcript of A remained active under B"
    assert "sess-A1" not in app.tree_sessions.get_children()
    assert "sess-A1" not in app.lbl_ingest_ctx.cget("text")


def test_session_switch_invalidates_transcript_when_transcript_fetch_fails(tk_root: tk.Tk) -> None:
    """Switching to a new session whose transcript fetch fails must NOT retain the old transcript."""
    client = FakeApiClient()
    client.cases_to_return = [{"case_id": "case-01", "child_id": "C-01"}]
    client.sessions_map["case-01"] = [
        {"session_id": "sess-01", "case_id": "case-01", "session_date": "2026-08-01", "transcript_id": "tr-01"},
        {"session_id": "sess-02", "case_id": "case-01", "session_date": "2026-08-15", "transcript_id": "tr-02"},
    ]
    client.transcripts_map["sess-01"] = {"utterances": [{"id": "u-01", "speaker": "CHI", "text": "Session 1 text"}]}

    app = LinguaLensGUIApp(tk_root, client=client)
    # Select sess-01
    app.active_session_id = "sess-01"
    app._refresh_transcript_and_findings()
    assert app.active_transcript is not None
    assert app.active_transcript["utterances"][0]["text"] == "Session 1 text"

    # Now fail transcript for sess-02
    client.get_transcript_side_effect = LinguaLensServerError("HTTP 500 transcript failure")

    # Select sess-02
    app.active_session_id = "sess-02"
    app._refresh_transcript_and_findings()

    # Must NOT retain sess-01's transcript
    assert app.active_transcript is None, "Old transcript remained active under new session"
    assert len(app.tree_utterances.get_children()) == 0
    assert "Session 1 text" not in app.txt_chat_view.get("1.0", tk.END)


def test_unexpected_programming_error_is_not_masked_as_network_failure(tk_root: tk.Tk) -> None:
    """Programming errors (TypeError, AttributeError) must raise directly and not be silenced."""
    client = FakeApiClient()

    def bug_in_code() -> list[dict[str, Any]]:
        raise TypeError("Unexpected NoneType encountered in data parsing")

    client.list_cases = bug_in_code  # type: ignore[assignment]

    app = LinguaLensGUIApp(tk_root, client=FakeApiClient())
    app.client = client

    # Calling _refresh_cases with a client raising TypeError must raise TypeError, NOT return False
    with pytest.raises(TypeError, match="Unexpected NoneType"):
        app._refresh_cases()


def test_stale_async_children_refresh_does_not_overwrite_newer_session_generation(tk_root: tk.Tk) -> None:
    """Stale completion from an older session generation is discarded and does not overwrite current state."""
    client = FakeApiClient()
    client.children_to_return = [{"id": "child-old", "display_code": "OLD-01"}]

    app = LinguaLensGUIApp(tk_root, client=client)
    # Clear children tree
    for item in app.tree_children.get_children():
        app.tree_children.delete(item)

    # Start a refresh in generation 1
    old_gen = app._get_current_session_generation()
    t = app._refresh_children()

    # User signs out or session advances to generation 2 before worker returns
    app._current_session_generation = old_gen + 1

    if t:
        t.join(timeout=1.0)
    _drain_async_queue(app)

    # Stale generation 1 children must NOT have been inserted
    assert "child-old" not in app.tree_children.get_children()
