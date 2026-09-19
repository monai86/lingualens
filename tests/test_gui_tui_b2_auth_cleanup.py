"""Focused tests for D1 Finding B2: Current-session 401 clinical-state cleanup.

Covers:
1. Current-session 401 during GUI and TUI operation strictly invalidates credentials
   and sensitive clinical state (cases, sessions, transcripts, reports, children,
   assessments, consents, caches, trees, audio playback).
2. Cancelled operation followed by current-session 401 still triggers full auth cleanup
   (cancellation does not excuse discarding current-session auth invalidation).
3. Switching mode (legacy -> V2) or changing selection (child/assessment) followed by
   current-session 401 still triggers full auth cleanup.
4. Logout/login resulting in a new session generation followed by a late 401 from an
   earlier session generation does NOT clear the new session credentials or context.
5. Late worker success arriving after auth invalidation does NOT restore clinical data
   or show success.
6. Repeated 401 errors are idempotent and do NOT cause dialog storms.
7. 403 (Permission), 409 (Conflict), and network errors are NOT treated as 401 auth errors.
8. Non-auth exceptions with messages containing "auth" or "401" substrings do NOT trigger
   logout or wipe clinical state.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Any, Callable
import unittest.mock as mock

import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import (
    ClientSession,
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensConflictError,
    LinguaLensPermissionError,
)
from packages.tui.workflow import WorkflowRunner


# ---------------------------------------------------------------------------
# Fixtures & Fake Client
# ---------------------------------------------------------------------------

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


class FakeB2ApiClient:
    """Deterministic fake client for B2 auth cleanup tests."""

    def __init__(self, initial_generation: int = 1) -> None:
        self.mock_mode = False
        self._session_generation = initial_generation
        self._session: ClientSession | None = ClientSession(
            access_token="initial-valid-token",
            organization_id="org-123",
            generation=initial_generation,
        )

        # Legacy data store
        self.cases = [
            {"case_id": "CASE-B2-01", "child_id": "C-01", "birth_ym": "2021-05", "notes": "Case 1"},
        ]
        self.sessions: dict[str, list[dict[str, Any]]] = {
            "CASE-B2-01": [{"session_id": "SESS-B2-01", "case_id": "CASE-B2-01", "session_date": "2026-01-10", "notes": "S1"}],
        }
        self.transcripts: dict[str, dict[str, Any]] = {
            "SESS-B2-01": {
                "transcript_id": "tr-b2-01",
                "session_id": "SESS-B2-01",
                "utterances": [{"id": "u1", "speaker": "CHI", "text": "test utterance"}],
            },
        }

        # V2 data store
        self.children = [
            {"id": "child-b2-01", "display_code": "CB2-01", "birth_year": 2021, "birth_month": 6, "language_context": {"primary": "th", "additional": []}},
        ]
        self.consents: dict[str, list[dict[str, Any]]] = {
            "child-b2-01": [{"id": "consent-b2-01", "child_id": "child-b2-01", "purpose": "clinical_assessment", "status": "active", "version": 1}],
        }
        self.assessments: dict[str, list[dict[str, Any]]] = {
            "child-b2-01": [{"id": "asmt-b2-01", "child_id": "child-b2-01", "purpose": "initial", "state": "draft", "age_months": 57}],
        }

        # Configurable call behavior
        self.get_child_error: Exception | None = None
        self.list_consents_error: Exception | None = None
        self.list_assessments_error: Exception | None = None
        self.get_assessment_error: Exception | None = None
        self.create_assessment_error: Exception | None = None
        self.list_cases_error: Exception | None = None

    def get_session(self) -> ClientSession | None:
        return self._session

    def set_session(self, access_token: str, organization_id: str | None = None) -> ClientSession:
        self._session_generation += 1
        self._session = ClientSession(
            access_token=access_token,
            organization_id=organization_id,
            generation=self._session_generation,
        )
        return self._session

    def clear_session(self) -> None:
        self._session = None

    def check_health(self) -> bool:
        return True

    def list_cases(self) -> list[dict[str, Any]]:
        if self.list_cases_error:
            raise self.list_cases_error
        return self.cases

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        return self.sessions.get(case_id, [])

    def get_session_transcript(self, session_id: str) -> dict[str, Any]:
        return self.transcripts.get(session_id, {"session_id": session_id, "utterances": []})

    def get_findings(self, session_id: str) -> dict[str, Any]:
        return {"session_id": session_id, "metrics": {"mlu": 3.0}}

    def get_session_report(self, session_id: str) -> dict[str, Any]:
        return {"session_id": session_id, "content": "Sample report"}

    def list_children(self) -> list[dict[str, Any]]:
        return self.children

    def get_child(self, child_id: str) -> dict[str, Any]:
        if self.get_child_error:
            raise self.get_child_error
        for c in self.children:
            if c["id"] == child_id:
                return c
        return {"id": child_id, "display_code": child_id}

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        if self.list_consents_error:
            raise self.list_consents_error
        return self.consents.get(child_id, [])

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        if self.list_assessments_error:
            raise self.list_assessments_error
        return self.assessments.get(child_id, [])

    def get_assessment(self, asmt_id: str) -> dict[str, Any]:
        if self.get_assessment_error:
            raise self.get_assessment_error
        for clist in self.assessments.values():
            for a in clist:
                if a["id"] == asmt_id:
                    return a
        return {"id": asmt_id, "purpose": "clinical_assessment", "state": "draft"}

    def create_assessment(self, child_id: str, purpose: str = "clinical_assessment", assigned_clinician_id: str | None = None) -> dict[str, Any]:
        if self.create_assessment_error:
            raise self.create_assessment_error
        return {"id": "asmt-new-01", "child_id": child_id, "purpose": purpose, "state": "draft"}


def _drain_tk_queue(app: LinguaLensGUIApp) -> None:
    """Drain Tk async queue deterministically on the main thread."""
    while not app._async_queue.empty():
        item = app._async_queue.get_nowait()
        fn = item[0]
        if callable(fn):
            fn()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_current_session_401_invalidates_gui_and_tui_credentials_and_clinical_state(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1. Current-session 401 must clear credentials and all sensitive clinical context in GUI and TUI."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showinfo", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    # Populate sensitive clinical state in GUI
    app.active_case_id = "CASE-B2-01"
    app.active_session_id = "SESS-B2-01"
    app.active_transcript = {"utterances": [{"text": "secret"}]}
    app.active_report = {"content": "confidential clinical report"}
    app.active_audio_path = "/path/to/child_audio.wav"
    app.active_child_id = "child-b2-01"
    app.active_child = {"id": "child-b2-01", "display_code": "SecretChild"}
    app.active_consent = {"status": "active", "version": 1}
    app.active_assessment_id = "asmt-b2-01"
    app.active_assessment = {"id": "asmt-b2-01"}
    app._cached_assessments = [{"id": "asmt-b2-01"}]

    app.tree_cases.insert("", tk.END, iid="c1", values=("CASE-B2-01", "C-01", "24", "th", "1", "Notes"))
    app.tree_sessions.insert("", tk.END, iid="s1", values=("SESS-B2-01", "2026-01-10", "1", "Reported", "Notes"))
    app.tree_children.insert("", tk.END, iid="ch1", values=("child-b2-01", "SecretChild", "2021-06", "th", "Active (v1)"))
    for it in app.tree_utterances.get_children():
        app.tree_utterances.delete(it)
    app.tree_utterances.insert("", tk.END, iid="b2_u1", values=("0.0", "1.0", "CHI", "sensitive utterance", ""))

    # Verify session is initially valid
    assert fake_client.get_session() is not None
    assert fake_client.get_session().generation == 1

    # Trigger 401 for current session (gen 1)
    auth_err = LinguaLensAuthError("Session expired: HTTP 401", status_code=401)
    app._handle_auth_error(auth_err, session_generation=1)

    # Assert credentials cleared
    assert fake_client.get_session() is None
    assert app._get_current_session_generation() > 1

    # Assert ALL sensitive clinical state wiped
    assert app.active_case_id is None
    assert app.active_session_id is None
    assert app.active_transcript is None
    assert app.active_report is None
    assert app.active_audio_path is None
    assert app.active_child_id is None
    assert app.active_child is None
    assert app.active_consent is None
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    assert app._cached_assessments == []

    # Assert treeviews wiped
    assert app.tree_cases.get_children() == ()
    assert app.tree_sessions.get_children() == ()
    assert app.tree_children.get_children() == ()
    assert app.tree_assessments.get_children() == ()
    assert app.tree_utterances.get_children() == ()

    # Now verify TUI workflow runner invalidates all state on 401
    tui_client = FakeB2ApiClient(initial_generation=1)
    workflow = WorkflowRunner(client=tui_client)
    workflow.active_case_id = "CASE-B2-01"
    workflow.active_session_id = "SESS-B2-01"
    workflow.active_transcript = {"utterances": [{"text": "secret"}]}
    workflow.active_report = {"content": "confidential"}
    workflow.active_child_id = "child-b2-01"
    workflow.active_child = {"id": "child-b2-01"}
    workflow.active_consent = {"status": "active"}
    workflow.active_assessment_id = "asmt-b2-01"
    workflow.active_assessment = {"id": "asmt-b2-01"}

    assert tui_client.get_session() is not None
    workflow._handle_auth_error(auth_err)

    assert tui_client.get_session() is None
    assert workflow.active_case_id is None
    assert workflow.active_session_id is None
    assert workflow.active_transcript is None
    assert workflow.active_report is None
    assert workflow.active_child_id is None
    assert workflow.active_child is None
    assert workflow.active_consent is None
    assert workflow.active_assessment_id is None
    assert workflow.active_assessment is None


def test_cancel_operation_still_triggers_current_session_401_cleanup(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2. Cancellation must NOT excuse skipping auth cleanup when a current-session 401 arrives."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    app.active_child_id = "child-b2-01"
    app.active_assessment_id = "asmt-b2-01"
    app.active_assessment = {"id": "asmt-b2-01"}

    session_gen = app._get_current_session_generation()
    child_sel_gen = app._child_selection_generation

    # Create dummy top level dialog
    dlg = tk.Toplevel(tk_root)
    dlg._dlg_token = "dlg-token-123"
    app._current_asmt_dialog_token = "dlg-token-123"

    cancel_event = threading.Event()
    # User cancels the operation
    cancel_event.set()
    app._current_asmt_dialog_token = "new-or-none-token"

    # Current session 401 returns from the server for this cancelled request
    auth_err = LinguaLensAuthError("HTTP 401 Unauthorized", status_code=401)
    app._on_create_assessment_error(
        win=dlg,
        dlg_token="dlg-token-123",
        request_id="req-123",
        child_id="child-b2-01",
        error=auth_err,
        session_gen=session_gen,
        child_sel_gen=child_sel_gen,
        cancel_event=cancel_event,
    )

    # Auth cleanup MUST have happened despite cancel_event being set!
    assert fake_client.get_session() is None
    assert app.active_child_id is None
    assert app.active_assessment_id is None


def test_mode_switch_and_selection_change_still_triggers_current_session_401_cleanup(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3. Changing mode (legacy -> V2) or selection must NOT ignore current-session 401."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    # Start in legacy mode with active case
    app.current_mode = "legacy"
    app.active_case_id = "CASE-B2-01"
    session_gen = app._get_current_session_generation()
    expected_gen = app._legacy_context_generation

    # User switches to V2 mode while legacy task was in flight
    app.current_mode = "v2"
    app._legacy_context_generation += 1

    # Current-session 401 arrives from the legacy task
    auth_err = LinguaLensAuthError("HTTP 401 Unauthorized", status_code=401)
    app._on_task_done(
        result=None,
        callback=None,
        error=auth_err,
        task_mode="legacy",
        expected_gen=expected_gen,
        request_id="task-legacy-01",
        session_gen=session_gen,
    )

    # Current session 401 MUST clean up session despite mode switch
    assert fake_client.get_session() is None
    assert app.active_case_id is None

    # Test selection change for V2 consent refresh
    fake_client.set_session("new-token-gen2")
    app.active_child_id = "child-b2-02"
    app.current_mode = "v2"
    session_gen2 = app._get_current_session_generation()
    old_child_sel_gen = app._child_selection_generation

    # User changed selection to child 3
    app._child_selection_generation += 1
    app.active_child_id = "child-b2-03"

    # Current-session 401 arrives from previous child's consent refresh
    app._on_consent_refresh_error(
        child_id="child-b2-02",
        error=auth_err,
        request_id="consent-old-req",
        session_gen=session_gen2,
        child_sel_gen=old_child_sel_gen,
    )

    # Current session 401 MUST clean up session despite stale child selection
    assert fake_client.get_session() is None
    assert app.active_child_id is None


def test_stale_401_from_prior_session_does_not_clear_new_session_or_context(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4. Late 401 from prior session generation must NOT wipe new session credentials or context."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    # User re-authenticates to session generation 2
    fake_client.set_session("valid-token-gen2")
    app._current_session_generation = 2

    # Set up clinical context in generation 2
    app.active_child_id = "child-gen2"
    app.active_child = {"id": "child-gen2"}

    # Late 401 arrives from session generation 1
    stale_auth_err = LinguaLensAuthError("Old session expired: HTTP 401", status_code=401)
    app._handle_auth_error(stale_auth_err, session_generation=1)

    # Generation 2 session credentials and context MUST be preserved
    assert fake_client.get_session() is not None
    assert fake_client.get_session().access_token == "valid-token-gen2"
    assert app.active_child_id == "child-gen2"
    assert app.active_child == {"id": "child-gen2"}


def test_late_success_after_auth_invalidation_does_not_restore_clinical_data_or_show_success(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5. In-flight worker completing with success after auth invalidation must be discarded."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showinfo", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    # Invalidation happens (session generation bumped)
    auth_err = LinguaLensAuthError("HTTP 401", status_code=401)
    app._handle_auth_error(auth_err, session_generation=1)

    assert app.active_child_id is None
    assert fake_client.get_session() is None

    # Late success callback from worker dispatched before invalidation (session_gen=1)
    success_mock = mock.MagicMock()
    app._on_async_child_selected(
        request_id="old-child-req",
        child_data={"id": "stale-child-data", "display_code": "LeakedChild"},
        session_generation=1,
    )
    # Clinical state must NOT be populated with stale child data
    assert app.active_child_id is None
    assert app.active_child is None

    # Test late success on async task done
    app._on_task_done(
        result={"transcript": "leaked transcript"},
        callback=success_mock,
        error=None,
        task_mode="legacy",
        expected_gen=0,
        request_id="old-req",
        session_gen=1,
    )
    success_mock.assert_not_called()
    assert app.active_transcript is None


def test_repeated_401_is_idempotent_and_prevents_dialog_storm(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """6. Repeated 401 errors must be idempotent and must not trigger dialog storms."""
    showerror_mock = mock.MagicMock()
    monkeypatch.setattr(tk.messagebox, "showerror", showerror_mock)

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    auth_err = LinguaLensAuthError("HTTP 401 Unauthorized", status_code=401)

    # Dispatch 3 concurrent 401 errors for generation 1
    app._handle_auth_error(auth_err, session_generation=1)
    app._handle_auth_error(auth_err, session_generation=1)
    app._handle_auth_error(auth_err, session_generation=1)

    # Exactly 1 dialog should be presented to the user
    assert showerror_mock.call_count == 1
    assert fake_client.get_session() is None


def test_403_and_409_and_network_failures_are_not_treated_as_401(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """7. HTTP 403, 409, and network errors must NOT clear authenticated session credentials."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)
    app.active_child_id = "child-b2-01"

    perm_err = LinguaLensPermissionError("HTTP 403 Forbidden", status_code=403)
    conflict_err = LinguaLensConflictError("HTTP 409 Conflict", status_code=409)
    net_err = OSError("Connection refused")

    # Handle 403
    app._handle_permission_error(perm_err)
    assert fake_client.get_session() is not None  # Session preserved!

    # Handle 409 in assessment error
    dlg = tk.Toplevel(tk_root)
    dlg._dlg_token = "dlg-409"
    app._current_asmt_dialog_token = "dlg-409"
    app._on_create_assessment_error(
        win=dlg,
        dlg_token="dlg-409",
        request_id="req-409",
        child_id="child-b2-01",
        error=conflict_err,
        session_gen=1,
        child_sel_gen=app._child_selection_generation,
    )
    assert fake_client.get_session() is not None  # Session preserved!

    # Handle network error in task done
    app._on_task_done(
        result=None,
        callback=None,
        error=net_err,
        task_mode="v2",
        expected_gen=app._legacy_context_generation,
        request_id="task-net-01",
        session_gen=1,
    )
    assert fake_client.get_session() is not None  # Session preserved!


def test_error_messages_containing_auth_or_401_substrings_do_not_trigger_logout(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """8. Exceptions with messages containing 'auth' or '401' substrings must not cause logout."""
    showerror_mock = mock.MagicMock()
    monkeypatch.setattr(tk.messagebox, "showerror", showerror_mock)

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)
    app.active_case_id = "CASE-B2-01"

    # Errors that contain "auth" or "401" as substrings but are NOT LinguaLensAuthError
    err1 = RuntimeError("Author name cannot be empty")
    err2 = LinguaLensApiError("Internal error code 4010: record unavailable")
    err3 = ValueError("Invalid authentication header format")

    for err in (err1, err2, err3):
        app._on_task_done(
            result=None,
            callback=None,
            error=err,
            task_mode="legacy",
            expected_gen=app._legacy_context_generation,
            request_id="task-dummy",
            session_gen=1,
        )
        # Session and clinical state MUST NOT be wiped!
        assert fake_client.get_session() is not None
        assert app.active_case_id == "CASE-B2-01"


def test_gui_current_session_401_wipes_all_residual_clinical_displays_and_dialogs(
    tk_root: tk.Tk,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """9. Prove that current-session 401 cleans all visible clinical text, metrics, plots, dropdown options, and open dialogs."""
    monkeypatch.setattr(tk.messagebox, "showerror", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showwarning", mock.MagicMock())
    monkeypatch.setattr(tk.messagebox, "showinfo", mock.MagicMock())

    fake_client = FakeB2ApiClient(initial_generation=1)
    app = LinguaLensGUIApp(tk_root, client=fake_client)

    # 1. Populate text widgets with synthetic sentinel clinical content
    app.txt_chat_view.config(state=tk.NORMAL)
    app.txt_chat_view.delete("1.0", tk.END)
    app.txt_chat_view.insert("1.0", "*CHI:\tSENTINEL_CHILD_TRANSCRIPT_SECRET\n")
    app.txt_chat_view.config(state=tk.DISABLED)  # Test disabled widget cleanup!

    app.txt_narrative.delete("1.0", tk.END)
    app.txt_narrative.insert("1.0", "SENTINEL_CLINICAL_NARRATIVE_SECRET")

    app.txt_recommendations.delete("1.0", tk.END)
    app.txt_recommendations.insert("1.0", "SENTINEL_CLINICAL_RECOMMENDATIONS_SECRET")

    app.txt_manual.delete("1.0", tk.END)
    app.txt_manual.insert("1.0", "SENTINEL_MANUAL_INGEST_SECRET")

    app.txt_radar_summary.delete("1.0", tk.END)
    app.txt_radar_summary.insert("1.0", "SENTINEL_RADAR_SUMMARY_SECRET")

    # 2. Populate treeview metrics and longitudinal tables
    app.tree_metrics.insert("", tk.END, iid="m_sentinel", values=("Domain", "MLU", "3.5", "SENTINEL_METRIC_SECRET"))
    app.tree_guidelines.insert("", tk.END, iid="g_sentinel", values=("Domain", "Norm", "SENTINEL_GUIDELINE_SECRET"))
    app.tree_longitudinal.insert("", tk.END, iid="l_sentinel", values=("SESS-01", "2026-01-01", "5", "SENTINEL_LONGITUDINAL_SECRET"))

    # 3. Populate canvases
    app.canvas_waveform.create_text(10, 10, text="SENTINEL_WAVEFORM_SECRET", tags="waveform_sentinel")
    app.canvas_radar.create_text(10, 10, text="SENTINEL_RADAR_SECRET", tags="radar_sentinel")

    # 4. Populate combobox values and selection
    app.combo_global_case["values"] = ["CASE-SENTINEL-01", "CASE-SENTINEL-02"]
    app.combo_global_case.set("CASE-SENTINEL-01")
    app.combo_global_session["values"] = ["SESS-SENTINEL-01", "SESS-SENTINEL-02"]
    app.combo_global_session.set("SESS-SENTINEL-01")
    app.combo_global_child["values"] = ["CHILD-SENTINEL-01"]
    app.combo_global_child.set("CHILD-SENTINEL-01")

    # 5. Populate entries
    app.entry_audio_path.delete(0, tk.END)
    app.entry_audio_path.insert(0, "/path/to/SENTINEL_AUDIO_SECRET.wav")
    app.entry_u_text.delete(0, tk.END)
    app.entry_u_text.insert(0, "SENTINEL_EDIT_UTTERANCE_SECRET")
    app.entry_case_search.delete(0, tk.END)
    app.entry_case_search.insert(0, "SENTINEL_SEARCH_QUERY")

    # 6. Populate context labels
    app.lbl_ingest_ctx.config(text="Active Context: Case CASE-SENTINEL-01 > Session SESS-SENTINEL-01")
    app.lbl_longitudinal_summary.config(text="📊 SENTINEL_LONGITUDINAL_SUMMARY_SECRET")

    # 7. Open a clinical intake/assessment dialog
    dialog_win = tk.Toplevel(app.root)
    dlg_entry = tk.Entry(dialog_win)
    dlg_entry.insert(0, "SENTINEL_DIALOG_SECRET")

    # Dispatch current-session 401 through the actual production async queue path
    auth_err = LinguaLensAuthError("HTTP 401 Unauthorized", status_code=401)
    app._async_queue.put((
        lambda e=auth_err: app._on_task_done(
            None, None, e, task_mode="legacy", expected_gen=app._legacy_context_generation, request_id="task-auth-01", session_gen=1
        ),
        auth_err,
    ))
    _drain_tk_queue(app)

    # ASSERT ALL RESIDUAL DISPLAYS ARE COMPLETELY WIPED:
    # Text widgets
    chat_txt = app.txt_chat_view.get("1.0", tk.END)
    assert "SENTINEL" not in chat_txt
    assert app.txt_chat_view.cget("state") == tk.DISABLED  # State cleanly preserved!
    assert "SENTINEL" not in app.txt_narrative.get("1.0", tk.END)
    assert "SENTINEL" not in app.txt_recommendations.get("1.0", tk.END)
    assert "SENTINEL" not in app.txt_manual.get("1.0", tk.END)
    assert "SENTINEL" not in app.txt_radar_summary.get("1.0", tk.END)

    # Treeviews
    assert "m_sentinel" not in app.tree_metrics.get_children()
    assert "g_sentinel" not in app.tree_guidelines.get_children()
    assert "l_sentinel" not in app.tree_longitudinal.get_children()

    # Canvases
    assert app.canvas_waveform.find_withtag("waveform_sentinel") == ()
    assert app.canvas_radar.find_withtag("radar_sentinel") == ()

    # Comboboxes (options wiped, cannot re-select old session/case!)
    assert "CASE-SENTINEL-01" not in app.combo_global_case["values"]
    assert app.combo_global_case.get() == ""
    assert "SESS-SENTINEL-01" not in app.combo_global_session["values"]
    assert app.combo_global_session.get() == ""
    assert "CHILD-SENTINEL-01" not in app.combo_global_child["values"]

    # Entry fields
    assert "SENTINEL" not in app.entry_audio_path.get()
    assert "SENTINEL" not in app.entry_u_text.get()
    assert "SENTINEL" not in app.entry_case_search.get()

    # Context labels
    assert "SENTINEL" not in app.lbl_ingest_ctx.cget("text")
    assert "SENTINEL" not in app.lbl_longitudinal_summary.cget("text")

    # Open clinical dialogs destroyed
    assert not dialog_win.winfo_exists()

