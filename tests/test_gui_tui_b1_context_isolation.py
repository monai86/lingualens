"""Focused tests for D1 Finding B1: GUI/TUI V2–legacy context isolation.

Covers:
1. GUI entering V2 mode explicitly clears legacy context (active_case_id, active_session_id,
   active_transcript, active_report, active_audio_path) and transitions current_mode to "v2".
2. Direct invocation of legacy callbacks in V2 mode (including when active_assessment_id is None,
   e.g. child-only context, loading, empty, or assessment load error) is strictly guarded and blocked.
3. Legacy audio playback, continuous playback, seek, and space shortcut are blocked in V2 mode,
   and any active playback is terminated when entering V2 mode.
4. Legacy clipboard / report export is blocked in V2 mode and does not leak stale legacy data.
5. In-flight legacy worker started before mode switch has its completion safely discarded upon
   switching to V2 (does not overwrite active_transcript, does not switch tabs, does not show success).
6. Explicit user return to Legacy mode restores legacy capabilities, clears V2 context,
   and re-enables downstream legacy tabs without context cross-contamination.
7. TUI workflow runner maintains strict context isolation between V2 (children/assessments)
   and Legacy (cases/sessions), clearing opposite context upon mode transitions and rejecting
   mixed-context execution.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from typing import Any, Callable
import unittest.mock as mock

import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import (
    ClientSession,
    LinguaLensApiError,
    LinguaLensClient,
)
from packages.tui.workflow import WorkflowRunner


# ---------------------------------------------------------------------------
# Fixtures & Fakes
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


class FakeB1ApiClient:
    """Deterministic fake client for B1 context isolation tests."""

    def __init__(self) -> None:
        self.mock_mode = True
        self._session = ClientSession(access_token="test-token", generation=1)

        # Legacy data
        self.cases = [
            {"case_id": "CASE-01", "child_id": "C-LEGACY-1", "birth_ym": "2021-05", "notes": "Legacy Case 1"},
            {"case_id": "CASE-02", "child_id": "C-LEGACY-2", "birth_ym": "2020-02", "notes": "Legacy Case 2"},
        ]
        self.sessions: dict[str, list[dict[str, Any]]] = {
            "CASE-01": [{"session_id": "SESS-01", "case_id": "CASE-01", "session_date": "2026-01-10", "notes": "S1"}],
        }
        self.transcripts: dict[str, dict[str, Any]] = {
            "SESS-01": {"session_id": "SESS-01", "utterances": [{"speaker": "CHI", "text": "hello"}]},
        }
        self.findings: dict[str, dict[str, Any]] = {
            "SESS-01": {"session_id": "SESS-01", "metrics": {"mlu": 2.5}},
        }
        self.reports: dict[str, dict[str, Any]] = {
            "SESS-01": {"session_id": "SESS-01", "content": "Legacy Report Content"},
        }

        # V2 data
        self.children = [
            {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6, "language_context": {"primary": "th", "additional": []}},
            {"id": "child-v2-02", "display_code": "CV2-02", "birth_year": 2020, "birth_month": 3, "language_context": {"primary": "en", "additional": []}},
        ]
        self.consents: dict[str, list[dict[str, Any]]] = {
            "child-v2-01": [{"id": "consent-1", "child_id": "child-v2-01", "purpose": "clinical_assessment", "status": "active", "version": 1}],
        }
        self.assessments: dict[str, list[dict[str, Any]]] = {
            "child-v2-01": [{"id": "asmt-v2-01", "child_id": "child-v2-01", "purpose": "initial", "state": "draft", "age_months": 57}],
        }

        self.list_cases_call_count = 0
        self.list_children_call_count = 0

    def check_health(self) -> bool:
        return True

    def get_session(self) -> ClientSession:
        return self._session

    def list_cases(self) -> list[dict[str, Any]]:
        self.list_cases_call_count += 1
        return list(self.cases)

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        return list(self.sessions.get(case_id, []))

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        return self.transcripts.get(session_id)

    def get_findings(self, session_id: str) -> dict[str, Any]:
        return self.findings.get(session_id, {})

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        return self.reports.get(session_id)

    def list_children(self) -> list[dict[str, Any]]:
        self.list_children_call_count += 1
        return list(self.children)

    def get_child(self, child_id: str) -> dict[str, Any]:
        for c in self.children:
            if c["id"] == child_id:
                return dict(c)
        raise LinguaLensApiError(f"Child {child_id} not found", status_code=404)

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        return list(self.consents.get(child_id, []))

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        return list(self.assessments.get(child_id, []))

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        for asmts in self.assessments.values():
            for a in asmts:
                if a["id"] == assessment_id:
                    return dict(a)
        raise LinguaLensApiError(f"Assessment {assessment_id} not found", status_code=404)


# ---------------------------------------------------------------------------
# Tests: GUI V2-Legacy Isolation
# ---------------------------------------------------------------------------

def test_gui_entering_v2_clears_legacy_context_and_sets_mode(tk_root: tk.Tk) -> None:
    """Entering V2 mode in GUI must set current_mode='v2', clear all legacy context, and stop playback."""
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # Establish legacy active context
    app.current_mode = "legacy"
    app.active_case_id = "CASE-01"
    app.active_session_id = "SESS-01"
    app.active_transcript = {"session_id": "SESS-01", "utterances": [{"text": "legacy"}]}
    app.active_report = {"session_id": "SESS-01", "content": "legacy report"}
    app.active_audio_path = "/path/to/legacy_audio.wav"
    app._is_continuous_playing = True

    # Action: User enters V2 by selecting a child
    child_data = {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6}
    app._current_child_request_id = "req-01"
    app._on_async_child_selected("req-01", child_data, app._get_current_session_generation())

    # Assertions
    assert app.current_mode == "v2"
    assert app.active_child_id == "child-v2-01"
    assert app.active_assessment_id is None  # Initially loading

    # Legacy context must be completely flushed
    assert app.active_case_id is None
    assert app.active_session_id is None
    assert app.active_transcript is None
    assert app.active_report is None
    assert app.active_audio_path is None
    assert app._is_continuous_playing is False


def test_gui_v2_child_only_context_blocks_direct_legacy_callbacks(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In V2 mode with active_child_id but active_assessment_id=None, all legacy actions must be blocked."""
    warnings_shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "tkinter.messagebox.showwarning",
        lambda title, msg, **kw: warnings_shown.append((title, msg)),
    )
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda *a, **kw: "")
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda *a, **kw: "")

    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # Put in V2 child-only mode (assessment is None / loading / empty)
    app.current_mode = "v2"
    app.active_child_id = "child-v2-01"
    app.active_child = {"id": "child-v2-01", "display_code": "CV2-01"}
    app.active_assessment_id = None
    app.active_assessment = None

    assert app._is_v2_mode() is True

    # 1. Ingestion actions (calling actual production methods)
    assert app._browse_audio_file() is None
    assert app._process_audio_file() is None
    assert app._batch_ingest_audio_files() is None
    assert app._load_demo_dialogue() is None
    assert app._browse_text_file() is None
    assert app._ingest_typed_text() is None

    # 2. Review actions
    assert app._save_utterance_edit() is None
    assert app._auto_refine_speakers() is None
    assert app._swap_speakers() is None
    assert app._attest_transcript() is None

    # 3. Report actions (calling actual production methods)
    assert app._generate_report_draft() is None
    assert app._sign_off_report() is None
    assert app._export_report() is None

    # 4. Playback and clipboard
    assert app._play_selected_utterance() is None
    assert app._play_word_segment(0.0, 1.0, "word") is None
    assert app._toggle_continuous_playback() is None
    assert app._seek_to_position(5.0) is None
    assert app._copy_chat_text() is None

    # 5. Dialogs and refresh
    assert app._show_create_session_dialog() is None
    assert app._refresh_sessions_for_active_case() is None
    assert app._refresh_transcript_and_findings() is False

    # Guard must have triggered warnings for blocked operations
    assert len(warnings_shown) >= 10
    for title, msg in warnings_shown:
        assert "V2" in title or "V2" in msg or "Assessment V2" in title or "Assessment V2" in msg

    # Active V2 context must remain uncontaminated
    assert app.active_child_id == "child-v2-01"
    assert app.active_case_id is None
    assert app.active_session_id is None


def test_gui_v2_assessment_error_keeps_legacy_actions_guarded(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When V2 assessment loading fails, active_assessment_id remains None but legacy actions remain blocked."""
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **kw: None)
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # Child selected, assessments fail to load
    child_data = {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6}
    app._current_child_request_id = "req-01"
    app._on_async_child_selected("req-01", child_data, app._get_current_session_generation())
    req_asmt_id = "req-asmt-01"
    app._assessment_list_request_id = req_asmt_id
    app._on_assessments_refresh_error(
        child_id="child-v2-01",
        error=LinguaLensApiError("Network timeout", status_code=503),
        request_id=req_asmt_id,
        session_gen=app._get_current_session_generation(),
        child_sel_gen=app._child_selection_generation,
    )

    assert app.active_child_id == "child-v2-01"
    assert app.active_assessment_id is None
    assert app._is_v2_mode() is True

    # Guard still blocks legacy action
    blocked = app._guard_v2_mode("Audio processing")
    assert blocked is True


def test_gui_legacy_worker_started_before_v2_switch_is_discarded(tk_root: tk.Tk) -> None:
    """An async legacy task started before switching to V2 must be safely discarded when it finishes."""
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # Establish legacy mode
    app.current_mode = "legacy"
    app.active_case_id = "CASE-01"
    app.active_session_id = "SESS-01"

    worker_result = {"session_id": "SESS-01", "utterances": [{"speaker": "CHI", "text": "stale legacy result"}]}
    success_called = []

    def mock_on_success(res: Any) -> None:
        success_called.append(res)
        app.active_transcript = res

    # Start legacy async task
    worker_gate = threading.Event()

    def background_target() -> Any:
        worker_gate.wait(timeout=2.0)
        return worker_result

    t = app._run_async_task(
        target=background_target,
        on_success=mock_on_success,
        busy_msg="Processing legacy...",
    )

    # While worker is running, user switches to V2 mode
    child_data = {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6}
    app._current_child_request_id = "req-02"
    app._on_async_child_selected("req-02", child_data, app._get_current_session_generation())

    assert app.current_mode == "v2"
    assert app.active_child_id == "child-v2-01"
    assert app.active_transcript is None

    # Now let background worker finish
    worker_gate.set()
    t.join(timeout=2.0)

    # Process all pending callbacks in _async_queue
    while not app._async_queue.empty():
        cb, exc = app._async_queue.get_nowait()
        cb()

    # Success callback must NOT have mutated state or written into active_transcript!
    assert len(success_called) == 0
    assert app.active_transcript is None
    assert app.active_child_id == "child-v2-01"
    assert app.current_mode == "v2"


def test_gui_stale_legacy_worker_does_not_mutate_ui_or_busy_owner(tk_root: tk.Tk) -> None:
    """Late legacy worker completion must NOT clear busy state or change status text owned by a newer V2 task."""
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # 1. Start legacy worker A
    app.current_mode = "legacy"
    app.active_case_id = "CASE-01"
    worker_a_gate = threading.Event()
    worker_a_called = []

    t_a = app._run_async_task(
        target=lambda: (worker_a_gate.wait(timeout=2.0), {"legacy": "data"})[1],
        on_success=lambda res: worker_a_called.append(res),
        busy_msg="Processing Legacy Task A...",
        request_id="req-worker-A",
    )

    assert app.is_busy is True
    assert app.lbl_status.cget("text") == "Processing Legacy Task A..."

    # 2. Switch to V2 mode and start V2 task B with its own busy state
    child_data = {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6}
    app._current_child_request_id = "req-02"
    app._on_async_child_selected("req-02", child_data, app._get_current_session_generation())

    app._set_busy_state(True, "Loading V2 Task B...", request_id="req-worker-B")
    assert app.is_busy is True
    assert app.lbl_status.cget("text") == "Loading V2 Task B..."

    # 3. Worker A finishes late
    worker_a_gate.set()
    t_a.join(timeout=2.0)

    while not app._async_queue.empty():
        cb, exc = app._async_queue.get_nowait()
        cb()

    # Assertions: Stale worker A must NOT clear busy state or alter status text of Task B
    assert len(worker_a_called) == 0
    assert app.is_busy is True
    assert app.lbl_status.cget("text") == "Loading V2 Task B..."
    assert getattr(app, "_current_busy_request_id", None) == "req-worker-B"

    # Clean up Task B
    app._set_busy_state(False, "Ready", request_id="req-worker-B")
    assert app.is_busy is False
    assert app.lbl_status.cget("text") == "Ready"


def test_gui_v2_mode_blocks_actual_export_callbacks_with_residual_data(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In V2 mode, actual bound export and playback callbacks must fail-closed even if residual legacy data exists."""
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # Enter V2 mode
    app.current_mode = "v2"
    app.active_child_id = "child-v2-01"

    # Artificially inject residual legacy data into fields to prove guard does not rely solely on active_transcript=None
    app.active_transcript = {"session_id": "SESS-RESIDUAL", "utterances": [{"speaker": "CHI", "text": "residual"}]}
    app.active_session_id = "SESS-RESIDUAL"
    app.active_case_id = "CASE-RESIDUAL"
    app.active_audio_path = "/path/to/residual_audio.wav"

    # Trap any external side effects
    file_dialog_calls: list[str] = []
    file_write_calls: list[str] = []
    get_findings_calls: list[str] = []
    popen_calls: list[Any] = []

    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kw: file_dialog_calls.append("asksaveasfilename") or "")
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **kw: None)
    monkeypatch.setattr("builtins.open", lambda *a, **kw: file_write_calls.append("open"))
    monkeypatch.setattr(fake_client, "get_findings", lambda sid: get_findings_calls.append(sid) or {})
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: popen_calls.append("Popen"))

    # Test actual export buttons / callbacks
    app._export_cha_file()
    app._export_csv_biomarkers()
    app._export_html_report()
    app._export_report()
    app._copy_chat_text()

    # Test actual playback callbacks
    app._play_selected_utterance()
    app._play_word_segment(0.0, 1.0, "word")
    app._play_audio_range(0.0, 1.0)
    app._toggle_continuous_playback()
    app._seek_to_position(1.0)
    app._seek_and_play(1.0)

    # Must be ZERO side effects
    assert len(file_dialog_calls) == 0, f"Expected 0 file dialog calls, got {file_dialog_calls}"
    assert len(file_write_calls) == 0, f"Expected 0 file writes, got {file_write_calls}"
    assert len(get_findings_calls) == 0, f"Expected 0 get_findings calls, got {get_findings_calls}"
    assert len(popen_calls) == 0, f"Expected 0 audio Popen calls, got {popen_calls}"


def test_gui_explicit_return_to_legacy_restores_legacy_capabilities(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicitly selecting a Legacy Case transitions back to legacy mode, clearing V2 context and re-enabling tabs."""
    fake_client = FakeB1ApiClient()
    app = LinguaLensGUIApp(tk_root, client=fake_client)  # type: ignore[arg-type]

    # 1. Start in V2 mode
    child_data = {"id": "child-v2-01", "display_code": "CV2-01", "birth_year": 2021, "birth_month": 6}
    app._current_child_request_id = "req-01"
    app._on_async_child_selected("req-01", child_data, app._get_current_session_generation())
    app.active_assessment_id = "asmt-01"
    assert app.current_mode == "v2"
    assert app._is_v2_mode() is True

    # 2. User explicitly selects a Legacy Case in tree_cases
    if "CASE-01" not in app.tree_cases.get_children():
        app.tree_cases.insert("", "end", iid="CASE-01", values=("CASE-01", "C-01", "2021-05", "1"))
    app.tree_cases.selection_set("CASE-01")
    app._on_case_selected(None)

    # 3. Assertions: Transition to legacy mode
    assert app.current_mode == "legacy"
    assert app.active_case_id == "CASE-01"
    assert app._is_v2_mode() is False

    # V2 context must be cleared
    assert app.active_child_id is None
    assert app.active_child is None
    assert app.active_consent is None
    assert app.active_assessment_id is None
    assert app.active_assessment is None

    # Downstream buttons re-enabled for legacy
    assert str(app.btn_select_audio["state"]) == "normal"
    assert str(app.btn_process_audio["state"]) == "normal"

    # 4. Verify valid legacy exports work without V2 guard blocking
    app.active_session_id = "SESS-01"
    app.active_transcript = {"session_id": "SESS-01", "utterances": [{"speaker": "CHI", "text": "hello"}]}
    dialog_opened = []
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kw: dialog_opened.append("opened") or "")
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **kw: None)

    app._export_cha_file()
    assert len(dialog_opened) == 1, "Legacy export should reach file dialog when in legacy mode"


# ---------------------------------------------------------------------------
# Tests: TUI V2-Legacy Isolation
# ---------------------------------------------------------------------------

def test_tui_entering_v2_clears_legacy_context() -> None:
    """TUI setting an active child profile must flush any previous legacy case/session context."""
    fake_client = FakeB1ApiClient()
    runner = WorkflowRunner(fake_client)  # type: ignore[arg-type]

    # Set legacy context
    runner.active_case_id = "CASE-01"
    runner.active_session_id = "SESS-01"
    runner.active_transcript = {"session_id": "SESS-01"}

    # Action: Set active child
    runner._set_active_child("child-v2-01")

    # Assertions
    assert runner.active_child_id == "child-v2-01"
    assert runner.active_case_id is None
    assert runner.active_session_id is None
    assert runner.active_transcript is None


def test_tui_entering_legacy_clears_v2_context() -> None:
    """TUI setting an active case must flush any previous V2 child/assessment context."""
    fake_client = FakeB1ApiClient()
    runner = WorkflowRunner(fake_client)  # type: ignore[arg-type]

    # Set V2 context
    runner.active_child_id = "child-v2-01"
    runner.active_child = {"id": "child-v2-01"}
    runner.active_assessment_id = "asmt-01"
    runner.active_assessment = {"id": "asmt-01"}

    # Action: Set active case
    runner._set_active_case("CASE-01")

    # Assertions
    assert runner.active_case_id == "CASE-01"
    assert runner.active_child_id is None
    assert runner.active_child is None
    assert runner.active_assessment_id is None
    assert runner.active_assessment is None


def test_tui_legacy_subflows_fail_closed_if_v2_active() -> None:
    """TUI legacy session subflows must reject execution when in V2 context or when legacy context is missing."""
    fake_client = FakeB1ApiClient()
    runner = WorkflowRunner(fake_client)  # type: ignore[arg-type]

    # Active V2 context
    runner._set_active_child("child-v2-01")
    runner.active_assessment_id = "asmt-01"

    # Direct calls to legacy subflows must fail closed / return early without mutation
    with mock.patch("packages.tui.workflow.Prompt.ask", return_value=""):
        runner._ingest_transcript_flow()
        runner._review_transcript_flow()
        runner._report_flow()
        runner._export_flow()

    # V2 state remains uncontaminated
    assert runner.active_child_id == "child-v2-01"
    assert runner.active_assessment_id == "asmt-01"
    assert runner.active_case_id is None
    assert runner.active_session_id is None
