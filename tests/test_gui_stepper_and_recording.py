"""Unit tests for Therapist 5-Step Guided Workflow, Live Recording, and Thai LSA in GUI."""

from __future__ import annotations

import os
import sys
import time
import tkinter as tk
import pytest

from packages.gui.app import LinguaLensGUIApp
from packages.tui.client import LinguaLensClient


@pytest.fixture(autouse=True)
def mock_msgbox(monkeypatch):
    """Prevent blocking modal dialogs during automated tests."""
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda *a, **k: "")
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda *a, **k: "")
    yield
    import gc
    gc.collect()


def test_gui_stepper_bar_and_next_action_ribbon():
    """Verify 5-step stepper bar and contextual Next Action ribbon initialization and state transitions."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # 1. Initially without any cases, step 1 is active
    assert hasattr(app, "frame_stepper")
    assert len(app.step_frames) == 5
    assert hasattr(app, "frame_next_action")
    assert hasattr(app, "btn_next_action")
    assert "Open Case" in app.btn_next_action.cget("text")

    # 2. Add case -> transitions to step 2 (Add Session)
    new_c = client.create_case("C-STEP-1", "2021-08", "th", "Stepper test case")
    app.active_case_id = new_c["case_id"]
    app._update_stepper_state()
    assert "Add Session" in app.btn_next_action.cget("text")

    # 3. Add session -> transitions to step 3 (Ingest Material)
    new_s = client.create_session(new_c["case_id"], "2026-09-20", "Therapy session")
    app.active_session_id = new_s["session_id"]
    app._update_stepper_state()
    assert "Ingest Material" in app.btn_next_action.cget("text")

    # 4. Ingest demo dialogue -> transcript exists -> transitions to step 4 (Review Transcript)
    t = app._load_demo_dialogue()
    if t:
        t.join(timeout=2.0)
    app._poll_async_queue()

    assert app.active_transcript is not None
    app._update_stepper_state()
    assert "Review Transcript" in app.btn_next_action.cget("text")

    # 5. Attest transcript -> transitions to step 5 (Progress Report)
    app._attest_transcript()
    app._update_stepper_state()
    assert "Progress Report" in app.btn_next_action.cget("text")

    # Verify clicking step 3 navigates to Tab 1 (index 1)
    app._nav_to_step(3, 1)
    assert app.notebook.index("current") == 1

    root.destroy()


def test_gui_live_mic_recording_controls():
    """Verify Live Microphone Recording card widgets and start/stop flow."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Check live recording UI widgets
    assert hasattr(app, "btn_start_record")
    assert hasattr(app, "btn_stop_record")
    assert hasattr(app, "lbl_rec_timer")
    assert hasattr(app, "canvas_vu_meter")

    # Start live recording
    app._start_live_recording()
    assert app.audio_recorder.is_recording is True
    assert "disabled" in str(app.btn_start_record.cget("state"))
    assert "normal" in str(app.btn_stop_record.cget("state"))

    # Timer update iteration
    app._update_live_recording_ui()

    # Stop live recording
    app._stop_live_recording()
    assert app.audio_recorder.is_recording is False
    assert "normal" in str(app.btn_start_record.cget("state"))
    assert "disabled" in str(app.btn_stop_record.cget("state"))
    assert app.entry_audio_path.get().endswith(".wav")

    root.destroy()


def test_gui_technical_disclosure_toggle():
    """Verify collapsible disclosure controls for technical diagnostic details."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    assert hasattr(app, "btn_toggle_tech_details")
    assert hasattr(app, "frame_tech_details_content")
    assert app._is_tech_details_visible is False

    # Expand
    app._toggle_tech_details()
    assert app._is_tech_details_visible is True
    assert "Hide" in app.btn_toggle_tech_details.cget("text")

    # Collapse
    app._toggle_tech_details()
    assert app._is_tech_details_visible is False
    assert "Advanced" in app.btn_toggle_tech_details.cget("text")

    root.destroy()


def test_gui_thai_lsa_findings_integration():
    """Verify that Thai Clinical LSA metrics appear under Domain 5 in tree_metrics."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Create case and session
    c = client.create_case("C-THAI-LSA", "2021-05", "th", "Thai LSA Test")
    app.active_case_id = c["case_id"]
    s = client.create_session(c["case_id"], "2026-09-20", "LSA session")
    app.active_session_id = s["session_id"]

    # Load demo dialogue containing Thai speech
    t = app._load_demo_dialogue()
    if t:
        t.join(timeout=2.0)
    app._poll_async_queue()

    # Search for Domain 5 in tree_metrics items
    metric_categories = [
        app.tree_metrics.item(item)["values"][0]
        for item in app.tree_metrics.get_children()
    ]
    assert any("5. Thai Language (LSA)" in str(cat) for cat in metric_categories)

    root.destroy()
