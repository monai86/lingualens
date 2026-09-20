"""Unit tests for LinguaLens Desktop GUI Application."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
import tkinter as tk
import pytest

from packages.tui.client import LinguaLensClient
from packages.gui.app import LinguaLensGUIApp


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


def test_gui_app_initialization():
    """Verify GUI widgets initialize cleanly without pre-populated mock cases."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()  # Don't show actual window during test
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Starts clean and empty
    assert app.active_case_id is None
    assert len(app.tree_cases.get_children()) == 0
    assert len(app.notebook.tabs()) == 5

    # Test tab switching
    app.notebook.select(1)
    assert app.notebook.index("current") == 1

    # Create new case
    new_c = client.create_case("C-001", "2021-06", "th", "Referral")
    app._refresh_cases()
    assert app.active_case_id == new_c["case_id"]
    assert len(app.tree_cases.get_children()) == 1

    root.destroy()


def test_empty_state_without_fake_metrics():
    """Verify that sessions without transcripts do NOT show synthetic metrics or fake radar polygons."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Create case and empty session
    new_c = client.create_case("C-EMPTY", "2021-06", "th")
    new_s = client.create_session(new_c["case_id"], "2026-08-22")
    app.active_case_id = new_c["case_id"]
    app.active_session_id = new_s["session_id"]
    app._refresh_transcript_and_findings()

    # Findings should be clean empty state
    findings = client.get_findings(new_s["session_id"])
    assert findings["has_data"] is False
    assert findings["metrics"] == {}

    # Tab 4 feature table should show "No Data" notice, not fake numbers
    rows = [app.tree_metrics.item(i)["values"] for i in app.tree_metrics.get_children()]
    assert any("No Data" in str(r) for r in rows)

    # Report draft on empty session should not generate fake text
    app._generate_report_draft()
    assert app.txt_narrative.get("1.0", tk.END).strip() == ""

    root.destroy()


def _pump_events(root: tk.Tk) -> None:
    """Pump Tkinter event queue safely without blocking on withdrawn windows."""
    try:
        import _tkinter
        for _ in range(20):
            if not root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
                break
    except Exception:
        root.update_idletasks()


def test_async_task_execution():
    """Verify background task execution updates UI asynchronously via root.after."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    result_holder = []

    def background_work():
        return {"status": "ok", "value": 42}

    def on_complete(result):
        result_holder.append(result)

    thread = app._run_async_task(
        target=background_work,
        on_success=on_complete,
        on_error=lambda err: None,
        busy_msg="Processing test...",
    )

    if thread:
        thread.join(timeout=2.0)

    # Drain async queue on main thread
    app._poll_async_queue()

    assert len(result_holder) == 1
    assert result_holder[0]["value"] == 42
    root.destroy()


def test_audio_segment_playback_command():
    """Verify audio snippet command generation for given start and end seconds."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    cmd, _ = app._build_audio_segment_command("sample.wav", 1.5, 4.2)
    assert cmd is not None
    assert any("afplay" in str(arg) or "play" in str(arg) or "sound" in str(arg).lower() for arg in cmd)
    root.destroy()


def test_utterance_edit_marks_stale():
    """Editing an utterance must mark findings and reports as stale until recalculated."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest demo dialogue synchronously via worker
    thread = app._load_demo_dialogue()
    if thread:
        thread.join(timeout=2.0)
    app._poll_async_queue()

    assert not app.is_findings_stale
    assert app.tree_utterances.get_children()

    # Select first utterance and edit
    first_u = app.tree_utterances.get_children()[0]
    app.tree_utterances.selection_set(first_u)
    app._on_utterance_selected(None)
    app.entry_u_text.delete(0, tk.END)
    app.entry_u_text.insert(0, "เล่น รถ สี แดง เร็ว")
    app._save_utterance_edit()

    assert app.is_findings_stale is True

    # Recalculate findings
    app._recalculate_findings()
    assert app.is_findings_stale is False
    root.destroy()


def test_spider_diagram_drawing_and_resize():
    """Verify radar chart draws correctly and recalculates on resize."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    thread = app._load_demo_dialogue()
    if thread:
        thread.join(timeout=2.0)
    app._poll_async_queue()

    assert len(app.canvas_radar.find_all()) > 0

    # Trigger resize event handler
    app._on_canvas_radar_resize(None)
    app._do_redraw_radar()
    assert len(app.canvas_radar.find_all()) > 0
    root.destroy()


def test_dialog_creation():
    """Verify create case and session dialogs instantiate with dynamic column weights."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    dialog_case = app._build_create_case_window()
    assert dialog_case.winfo_exists()
    dialog_case.destroy()

    dialog_session = app._build_create_session_window()
    assert dialog_session.winfo_exists()
    dialog_session.destroy()

    root.destroy()


def test_word_segment_ui_and_playback():
    """Verify word timing chips render and invoke segment audio playback."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Mock an active transcript with sub-word alignments
    app.active_transcript = {
        "transcript_id": "tr-test-words",
        "session_id": "S-001",
        "status": "pending_review",
        "utterances": [
            {
                "id": "u-1",
                "speaker": "CHI",
                "text": "เล่น รถ แดง",
                "start_time": 1.0,
                "end_time": 3.5,
                "words": [
                    {"text": "เล่น", "start_time": 1.0, "end_time": 1.5},
                    {"text": "รถ", "start_time": 1.6, "end_time": 2.2},
                    {"text": "แดง", "start_time": 2.3, "end_time": 3.5},
                ],
            }
        ],
    }
    app.active_audio_path = "mock_session.wav"
    app.tree_utterances.insert("", tk.END, iid="u-1", values=("1", "CHI", "1.00 - 3.50", "เล่น รถ แดง", ""))
    app.tree_utterances.selection_set("u-1")
    app._on_utterance_selected(None)

    # Verify that word chips were rendered
    chips = app.container_word_buttons.winfo_children()
    assert len(chips) == 3
    assert "เล่น" in chips[0].cget("text")
    assert "รถ" in chips[1].cget("text")
    assert "แดง" in chips[2].cget("text")

    # Verify build audio segment command for word
    cmd, _ = app._build_audio_segment_command("mock_session.wav", 1.6, 2.2)
    assert cmd is not None
    assert any("afplay" in str(arg) or "play" in str(arg) or "sound" in str(arg).lower() for arg in cmd)

    # Test utterance highlighting method
    app._highlight_utterance("u-1")
    assert "playing" in app.tree_utterances.item("u-1", "tags")

    # Test stop playback clears highlighting tags
    app._stop_playback()
    assert "playing" not in app.tree_utterances.item("u-1", "tags")

    root.destroy()


def test_continuous_playback_toolbar_and_follow():
    """Verify audio player toolbar and live follow state controls."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    assert hasattr(app, "btn_play_continuous")
    assert hasattr(app, "btn_stop_audio")
    assert hasattr(app, "lbl_playback_status")

    # Test stop when idle is safe
    app._stop_playback()
    assert not app._is_continuous_playing
    assert "Stopped" in app.lbl_playback_status.cget("text")

    root.destroy()


def test_audio_ingest_progress_dialog_and_stage_updates():
    """Verify audio ingestion progress modal creation, live updates, and graceful teardown."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Trigger progress dialog
    app._show_ingest_progress_dialog("test_sample.wav")
    assert app._progress_dialog is not None
    assert app._progress_dialog.winfo_exists()
    assert app._dlg_bar_progress is not None

    # Test real-time progress update
    app._update_ingest_progress(0.45, "Running Whisper ASR: transcribing 00:04.2s - 00:08.5s...")
    assert app._dlg_bar_progress["value"] == 45
    assert "45%" in app._dlg_lbl_pct.cget("text")
    assert "Whisper ASR" in app._dlg_lbl_stage.cget("text")
    assert "45%" in app.lbl_status.cget("text")

    # Test dismiss and cleanup
    app._close_ingest_progress_dialog()
    assert app._progress_dialog is None

    root.destroy()


def test_audio_ingestion_and_findings_determinism(tmp_path, monkeypatch):
    """Verify that ingesting the same audio produces deterministic transcript and feature metrics."""
    import soundfile as sf
    import numpy as np
    from src.audio_pipeline.pipeline import PipelineResult
    from src.audio_pipeline.whisper_transcribe import UtteranceSegment, WordSegment
    from src.audio_pipeline.acoustic_profile import AcousticProfile

    sr = 16000
    t = np.linspace(0, 1.0, int(sr * 1.0))
    wav_data = (0.4 * np.sin(2 * np.pi * 320 * t)).astype(np.float32)
    wav_file = tmp_path / "deterministic_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    def mock_audio_to_cha(audio_path, **kwargs):
        u1 = UtteranceSegment(start=0.0, end=1.0, text="เล่น รถ", speaker="CHI", words=[WordSegment("เล่น", 0.0, 0.4, 0.95), WordSegment("รถ", 0.5, 1.0, 0.95)])
        prof = AcousticProfile(duration_sec=1.0, f0_median_hz=315.0, f0_iqr_hz=18.0, voiced_ratio=0.8, pause_ratio=0.2, child_speech_rate_wps=2.0)
        chat = "@UTF8\n@Begin\n@Languages:\ttha\n@Participants:\tCHI Child\n*CHI:\tเล่น รถ .\n%mor:\tv|เล่น n|รถ .\n@End\n"
        return PipelineResult(
            chat_text=chat,
            chat_path=None,
            utterances=[u1],
            n_child_utterances=1,
            n_adult_utterances=0,
            total_duration_sec=1.0,
            acoustic_profile=prof,
        )

    import src.audio_pipeline.pipeline
    monkeypatch.setattr(src.audio_pipeline.pipeline, "audio_to_cha", mock_audio_to_cha)

    client1 = LinguaLensClient(mock_mode=True)
    c1 = client1.create_case("C-DET-01", "2021-05", "th")
    s1 = client1.create_session(c1["case_id"], "2026-08-23")
    tr1 = client1.ingest_audio_file(s1["session_id"], str(wav_file))
    f1 = client1.get_findings(s1["session_id"])

    client2 = LinguaLensClient(mock_mode=True)
    c2 = client2.create_case("C-DET-02", "2021-05", "th")
    s2 = client2.create_session(c2["case_id"], "2026-08-23")
    tr2 = client2.ingest_audio_file(s2["session_id"], str(wav_file))
    f2 = client2.get_findings(s2["session_id"])

    assert len(tr1["utterances"]) == len(tr2["utterances"]) == 1
    assert tr1.get("raw_cha") == tr2.get("raw_cha")
    assert f1["metrics"].get("f0_median_hz") == f2["metrics"].get("f0_median_hz") == 315.0
    assert f1["metrics"].get("mlu_words") == f2["metrics"].get("mlu_words") == 2.0
    assert f1["metrics"].get("ttr") == f2["metrics"].get("ttr") == 1.0


def test_waveform_and_speed_control(tmp_path):
    """Verify waveform peak calculation, canvas rendering, and speed rate command options."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    import soundfile as sf
    import numpy as np

    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5))
    wav_data = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    wav_file = tmp_path / "waveform_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    peaks = app._compute_waveform_peaks(str(wav_file), num_peaks=50)
    assert len(peaks) > 0
    assert max(peaks) <= 1.0

    app.active_audio_path = str(wav_file)
    app._audio_waveform_peaks = peaks
    app._redraw_waveform()

    # Test Speed change
    app.combo_speed.set("0.75x")
    app._on_speed_changed(None)
    assert app.playback_speed == 0.75

    cmd, _ = app._build_audio_segment_command(str(wav_file), 0.0, 1.0)
    assert cmd is not None
    if sys.platform == "darwin":
        assert "-r" in cmd
        assert "0.75" in cmd

    root.destroy()


def test_multiformat_export_center(tmp_path, monkeypatch):
    """Verify TalkBank .cha, CSV, and HTML report export flows."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest mock transcript
    c = client.create_case("C-EXP-01", "2021-05", "th")
    s = client.create_session(c["case_id"], "2026-08-23")
    app.active_case_id = c["case_id"]
    app.active_session_id = s["session_id"]
    client.ingest_transcript_text(s["session_id"], "CHI: เล่น รถ สนุก\nINV: เก่ง มาก ครับ")
    app._refresh_transcript_and_findings()

    # 1. Test CHA Export
    cha_out = tmp_path / "test_export.cha"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(cha_out))
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    app._export_cha_file()
    assert cha_out.exists()
    assert "@Begin" in cha_out.read_text(encoding="utf-8")

    # 2. Test CSV Export
    csv_out = tmp_path / "test_export.csv"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(csv_out))
    app._export_csv_biomarkers()
    assert csv_out.exists()
    csv_content = csv_out.read_text(encoding="utf-8")
    assert "mlu_words" in csv_content or "metric_name" in csv_content

    # 3. Test HTML Report Export
    html_out = tmp_path / "test_export.html"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: str(html_out))
    app._export_html_report()
    assert html_out.exists()
    html_content = html_out.read_text(encoding="utf-8")
    assert "LinguaLens" in html_content
    assert "<!DOCTYPE html>" in html_content

    # 4. Test Edit Box Buttons & Speaker Update
    assert app.btn_play_snippet.cget("text") == "🔊 Play Snippet"
    assert app.btn_save_u_edit.cget("text") == "💾 Save Utterance Edit"

    # Select u-1, change speaker to MOT and save
    app.tree_utterances.selection_set("u-1")
    app._on_utterance_selected(None)
    assert app.combo_spk.get() == "CHI"
    app.combo_spk.set("MOT")
    app._save_utterance_edit()
    assert app.is_findings_stale is True

    updated_tr = client.get_session_transcript(s["session_id"])
    assert updated_tr["utterances"][0]["speaker"] == "MOT"

    root.destroy()


def test_audio_scrubber_and_seeking(tmp_path):
    """Verify audio scrubber slider, waveform seeking, playhead needle, and utterance auto-highlighting."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    import soundfile as sf
    import numpy as np

    sr = 16000
    t = np.linspace(0, 3.0, int(sr * 3.0))
    wav_data = (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    wav_file = tmp_path / "scrubber_test.wav"
    sf.write(str(wav_file), wav_data, sr)

    app.active_audio_path = str(wav_file)
    app._audio_waveform_duration = 3.0
    app.active_transcript = {
        "transcript_id": "tr-scrub-01",
        "utterances": [
            {"id": "u-1", "speaker": "INV", "text": "สวัสดีครับ", "start_time": 0.0, "end_time": 1.0},
            {"id": "u-2", "speaker": "CHI", "text": "เล่น รถ", "start_time": 1.2, "end_time": 2.5},
        ]
    }
    app.tree_utterances.insert("", tk.END, iid="u-1", values=("1", "INV", "0.0 - 1.0", "สวัสดีครับ", "Clean"))
    app.tree_utterances.insert("", tk.END, iid="u-2", values=("2", "CHI", "1.2 - 2.5", "เล่น รถ", "Clean"))

    # Test time formatting
    assert app._format_time(65.4) == "01:05.4"
    assert app._format_time(0.0) == "00:00.0"

    # Test seek to 1.5s (should highlight u-2)
    app._seek_and_play(1.5, auto_play=False)
    assert app._playhead_time_sec == 1.5
    assert app.lbl_time_current.cget("text") == "00:01.5"
    assert "playing" in app.tree_utterances.item("u-2", "tags")
    assert "playing" not in app.tree_utterances.item("u-1", "tags")

    # Test scrubber drag
    app._on_scrubber_press(None)
    assert app._is_user_scrubbing is True
    app._on_scrubber_slide("0.5")
    assert "playing" in app.tree_utterances.item("u-1", "tags")
    app._on_scrubber_release(None)
    assert app._is_user_scrubbing is False

    # Test stop playback
    app._stop_playback()
    assert app._is_continuous_playing is False

    # Test snippet playback via _play_selected_utterance
    app.tree_utterances.selection_set("u-2")
    app._play_selected_utterance()
    assert app._is_continuous_playing is True
    assert app._playback_end_limit_sec == 2.5
    assert app._current_playback_offset_sec == 1.2

    # Verify widget destruction safety (no TclError)
    app._on_utterance_selected(None)
    app._stop_playback()
    root.destroy()


def test_speaker_refinement_and_hotkeys(tmp_path, monkeypatch):
    """Verify Auto-Refine Speakers, Swap Speakers, and C/I/M keyboard tagging."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Ingest session with inverted speakers
    c = client.create_case("C-SPK-01", "2021-05", "th")
    s = client.create_session(c["case_id"], "2026-08-23")
    app.active_case_id = c["case_id"]
    app.active_session_id = s["session_id"]

    tr_data = {
        "transcript_id": "tr-spk-01",
        "session_id": s["session_id"],
        "utterances": [
            {"id": "u-1", "speaker": "CHI", "text": "Can you do this? Try again.", "start_time": 0.0, "end_time": 2.0},
            {"id": "u-2", "speaker": "INV", "text": "car", "start_time": 2.2, "end_time": 3.0},
            {"id": "u-3", "speaker": "CHI", "text": "Good job. Now touch your nose.", "start_time": 3.2, "end_time": 5.0},
        ],
        "qa_summary": {"total_utterances": 3, "unresolved_flags": 0, "child_utterance_count": 2},
    }
    client._mock_data["transcripts"]["tr-spk-01"] = tr_data
    app.active_transcript = tr_data
    app._refresh_transcript_and_findings()

    # 1. Test Auto-Refine Speakers
    app._auto_refine_speakers()
    utts = app.active_transcript["utterances"]
    assert utts[0]["speaker"] == "INV"  # Adult prompt corrected
    assert utts[1]["speaker"] == "CHI"  # Child response
    assert utts[2]["speaker"] == "INV"  # Adult prompt corrected

    # 2. Test Swap CHI <-> Adult
    app._swap_speakers()
    assert utts[0]["speaker"] == "CHI"
    assert utts[1]["speaker"] == "INV"
    assert utts[2]["speaker"] == "CHI"

    # 3. Test Keyboard Quick Tagging (Press C/I/M)
    app.tree_utterances.selection_set("u-1")

    class FakeEvent:
        def __init__(self, char, keysym=""):
            self.char = char
            self.keysym = keysym

    # Press 'I' on u-1
    res = app._on_tree_key_press(FakeEvent("i", "i"))
    assert res == "break"
    assert app.active_transcript["utterances"][0]["speaker"] == "INV"

    # Press 'C' on next row (u-2)
    res = app._on_tree_key_press(FakeEvent("c", "c"))
    assert res == "break"
    assert app.active_transcript["utterances"][1]["speaker"] == "CHI"

    root.destroy()


def test_f0_pitch_overlay_and_longitudinal_trajectory(tmp_path, monkeypatch):
    """Verify F0 pitch curve overlay toggling and Longitudinal trajectory tracking across sessions."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # 1. Test F0 Pitch Overlay Toggle
    assert app._show_pitch_overlay is True
    app._toggle_pitch_overlay()
    assert app._show_pitch_overlay is False
    assert "OFF" in app.btn_toggle_pitch.cget("text")
    app._toggle_pitch_overlay()
    assert app._show_pitch_overlay is True
    assert "ON" in app.btn_toggle_pitch.cget("text")

    # 2. Test Longitudinal Cross-Session Trajectory Tracking
    c = client.create_case("C-LONG-01", "2021-05", "th")
    s1 = client.create_session(c["case_id"], "2026-08-01", "Session 1 Baseline")
    s2 = client.create_session(c["case_id"], "2026-08-15", "Session 2 Follow-up")
    s3 = client.create_session(c["case_id"], "2026-08-23", "Session 3 Progress")

    client.ingest_transcript_text(s1["session_id"], "CHI: รถ\nINV: รถสีอะไร")
    client.ingest_transcript_text(s2["session_id"], "CHI: รถ แดง\nINV: รถสีแดงสวยมาก")
    client.ingest_transcript_text(s3["session_id"], "CHI: รถ สี แดง วิ่ง เร็ว\nINV: เก่งมากเลยครับ")

    app.active_case_id = c["case_id"]
    app.active_session_id = s3["session_id"]
    app._refresh_transcript_and_findings()

    items = app.tree_longitudinal.get_children()
    assert len(items) == 3
    assert s1["session_id"] in items
    assert s2["session_id"] in items
    assert s3["session_id"] in items

    # Verify summary banner
    summary_text = app.lbl_longitudinal_summary.cget("text")
    assert "3 sessions recorded" in summary_text

    # 3. Test Bilingual Clinical Report Export
    out_report = tmp_path / "clinical_bilingual_report.html"
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kw: str(out_report))
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    app._export_html_report()
    assert out_report.exists()
    content = out_report.read_text(encoding="utf-8")
    assert "LinguaLens Clinical LSA Report" in content
    assert "Longitudinal Assessment Trajectory" in content
    root.destroy()


def test_gui_failure_presentation_on_api_error(monkeypatch):
    """Verify that GUI displays sanitized error without crash or fabricated state on API failure."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    from packages.tui.client import LinguaLensServerError

    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Simulate an API error during task completion
    app._on_task_done(None, None, LinguaLensServerError("Server error: HTTP 500 Internal server failure."))

    assert len(errors_shown) == 1
    title, msg = errors_shown[0]
    assert title == "Operation Failed"
    assert "Server error: HTTP 500" in msg
    # Verify no raw clinical identifiers or internal URLs in user-facing message
    assert "http://" not in msg
    assert "token" not in msg.lower()
    assert app.lbl_status.cget("text") == "Ready"

    root.destroy()


def test_gui_create_case_api_error_presentation(monkeypatch):
    """Verify that synchronous modal actions (e.g. create_case) catch API errors and show error dialog without false success."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from tkinter import ttk
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = LinguaLensClient(mock_mode=True)
    def failing_create(*args, **kwargs):
        raise LinguaLensApiError("API service unavailable")
    monkeypatch.setattr(client, "create_case", failing_create)

    app = LinguaLensGUIApp(root, client=client)
    win = app._build_create_case_window()

    # Find the Create Case button inside btn_row
    btn_create = None
    for child in win.winfo_children():
        for sub in child.winfo_children():
            if isinstance(sub, ttk.Frame):
                for b in sub.winfo_children():
                    if isinstance(b, ttk.Button) and b.cget("text") == "Create Case":
                        btn_create = b
                        break

    assert btn_create is not None
    # Invoking button should catch the LinguaLensApiError and show errorbox
    btn_create.invoke()

    assert len(errors_shown) == 1
    assert "API service unavailable" in errors_shown[0][1]
    # Window should remain open so user does not lose input
    assert win.winfo_exists()
    win.destroy()
    root.destroy()


def test_gui_batch_audio_ingest_reports_failure_no_false_success(monkeypatch, tmp_path):
    """Verify that batch audio ingestion does not claim 100% success when an item fails."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    info_messages = []
    warning_messages = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg: info_messages.append((title, msg)))
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: warning_messages.append((title, msg)))

    from packages.tui.client import LinguaLensApiError
    client = LinguaLensClient(mock_mode=True)
    # Fail ingest_audio_file
    def failing_ingest(*args, **kwargs):
        raise LinguaLensApiError("Audio ingestion failed on backend")
    monkeypatch.setattr(client, "ingest_audio_file", failing_ingest)

    app = LinguaLensGUIApp(root, client=client)
    app.active_case_id = "case_demo_001"

    fake_f1 = tmp_path / "audio1.wav"
    fake_f1.write_bytes(b"RIFFdummyWAVEfmt ")
    monkeypatch.setattr("tkinter.filedialog.askopenfilenames", lambda **kw: [str(fake_f1)])

    # We patch threading.Thread so worker runs synchronously in test
    import threading
    class SyncThread:
        def __init__(self, target, daemon=True):
            self.target = target
        def start(self):
            self.target()
    monkeypatch.setattr(threading, "Thread", SyncThread)
    app._batch_ingest_audio_files()

    # Process Tk idle events
    root.update_idletasks()

    # Must show warning for failures, not false success info
    assert len(warning_messages) == 1
    assert "failure" in warning_messages[0][1].lower() or "error" in warning_messages[0][1].lower() or "failed" in warning_messages[0][1].lower()
    assert not any("All" in msg and "successfully" in msg for _, msg in info_messages)

    for w in list(root.winfo_children()):
        if isinstance(w, tk.Toplevel):
            try:
                w.grab_release()
            except Exception:
                pass
            w.destroy()
    root.destroy()


def test_gui_handles_auth_error_with_reauth_state(monkeypatch):
    """Verify GUI sets authentication required state when LinguaLensAuthError is received."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from packages.tui.client import LinguaLensAuthError
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    auth_err = LinguaLensAuthError("Authentication failed: HTTP 401 Session expired or invalid token.")
    app._on_task_done(None, None, auth_err)

    assert len(errors_shown) == 1
    assert "Sign-in" in errors_shown[0][0] or "Authentication" in errors_shown[0][0] or "Operation Failed" in errors_shown[0][0]
    status_text = app.lbl_status.cget("text").lower()
    assert "auth" in status_text or "session expired" in status_text or "sign in" in status_text or "login" in status_text
    root.destroy()


def test_gui_stale_clinical_state_cleared_on_auth_failure(monkeypatch):
    """Verify that when an auth failure occurs, active clinical state is cleared to prevent data leakage."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from packages.tui.client import LinguaLensAuthError
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *args: None)

    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Set up active clinical state
    app.active_case_id = "case_sensitive_001"
    app.active_session_id = "session_sensitive_001"
    app.active_transcript = {"transcript_id": "tr-sens-01", "utterances": [{"speaker": "CHI", "text": "secret"}]}

    auth_err = LinguaLensAuthError("Authentication failed: HTTP 401 Session expired or invalid token.")
    app._on_task_done(None, None, auth_err)

    # All active clinical state must be cleared
    assert app.active_case_id is None
    assert app.active_session_id is None
    assert app.active_transcript is None
    root.destroy()


def test_gui_child_intake_empty_code_rejected_client_side():
    """Empty display_code must be rejected client-side without calling client.create_child."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    app = LinguaLensGUIApp(root, client=client)

    validation_error = app._validate_child_intake("", 2021, 5)
    assert validation_error == "Child Identifier / Display Code is required."

    invalid_year_error = app._validate_child_intake("C-01", 1850, 5)
    assert "year" in invalid_year_error.lower()

    invalid_month_error = app._validate_child_intake("C-01", 2021, 13)
    assert "month" in invalid_month_error.lower()

    valid_error = app._validate_child_intake("C-01", 2021, 5)
    assert valid_error is None

    client.create_child.assert_not_called()
    root.destroy()


def test_gui_child_switch_flushes_previous_clinical_context():
    """Switching active child must flush consent, assessment ID, and previous child views."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [
        {"id": "c1", "display_code": "C-001", "birth_year": 2020, "birth_month": 1},
        {"id": "c2", "display_code": "C-002", "birth_year": 2021, "birth_month": 6},
    ]
    client.get_child.side_effect = lambda cid: {"id": cid, "display_code": f"C-{cid}"}
    client.get_active_consent.return_value = None
    client.list_assessments.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    # Set existing clinical context for child 1
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-001"}
    app.active_consent = {"id": "consent-1", "status": "active"}
    app.active_assessment_id = "asmt-001"
    app.active_assessment = {"id": "asmt-001"}

    # Switch to child 2
    app._set_active_child("c2")
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id == "c2"
    assert app.active_child["display_code"] == "C-c2"
    assert app.active_consent is None
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_set_active_child_api_error_never_fabricates_child():
    """When get_child fails (404/transport), GUI must not fabricate a child dict or set active_child_id."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    client = MagicMock()
    client.get_child.side_effect = LinguaLensApiError("Child 'nonexistent' not found.")

    app = LinguaLensGUIApp(root, client=client)
    app._set_active_child("nonexistent")
    time.sleep(0.05)
    app._poll_async_queue()

    # MUST NOT be fabricated!
    assert app.active_child_id is None
    assert app.active_child is None
    root.destroy()


def test_gui_set_active_child_401_clears_auth_and_clinical_context():
    """When get_child returns 401, session is cleared and clinical context is wiped."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError, ClientSession
    root.withdraw()
    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok", organization_id="org1")
    client.get_child.side_effect = LinguaLensAuthError("HTTP 401 Unauthorized")

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c-prev"
    app.active_child = {"id": "c-prev"}

    app._set_active_child("c1")
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id is None
    assert app.active_child is None
    client.clear_session.assert_called()
    root.destroy()


def test_gui_set_active_child_403_shows_permission_denied_preserves_session(monkeypatch):
    """When get_child returns 403, permission error is displayed but session is NOT cleared."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensPermissionError, ClientSession
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = MagicMock()
    session = ClientSession(access_token="tok", organization_id="org1")
    client.get_session.return_value = session
    client.get_child.side_effect = LinguaLensPermissionError("HTTP 403 Access Denied to child")

    app = LinguaLensGUIApp(root, client=client)
    app._set_active_child("c-forbidden")
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id is None
    assert app.active_child is None
    # Session must be preserved!
    client.clear_session.assert_not_called()
    assert len(errors_shown) == 1
    assert "Permission" in errors_shown[0][0] or "Denied" in errors_shown[0][0] or "Failed" in errors_shown[0][0]
    root.destroy()


def test_gui_late_async_child_response_discarded_after_switch():
    """Late background worker response for a previous child request must be discarded if active child changed."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    app = LinguaLensGUIApp(root, client=client)

    # Active child is now C-NEW with generation 2
    app.active_child_id = "child-NEW"
    app.active_child = {"id": "child-NEW", "display_code": "NEW"}

    # Late response from child-OLD with generation 1
    app._on_async_child_selected(request_id="req-old-gen1", child_data={"id": "child-OLD", "display_code": "OLD"})

    # Must NOT have overwritten active_child
    assert app.active_child_id == "child-NEW"
    assert app.active_child["display_code"] == "NEW"
    root.destroy()


def test_gui_child_intake_modal_submission_calls_create_child_and_refreshes():
    """Actual child creation dialog submission invokes create_child with typed payload and updates active context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    created_child = {
        "id": "child-created-999",
        "display_code": "C-SUBMIT-01",
        "birth_year": 2021,
        "birth_month": 4,
        "language_context": {"primary": "th", "additional": []},
    }
    client.create_child.return_value = created_child
    client.list_children.return_value = [created_child]
    client.get_child.return_value = created_child

    app = LinguaLensGUIApp(root, client=client)

    # Open child creation dialog
    win = app._show_create_child_dialog()
    assert win is not None
    assert isinstance(win, tk.Toplevel)

    # Submit with valid fields
    app._submit_create_child(
        win=win,
        display_code="C-SUBMIT-01",
        birth_year=2021,
        birth_month=4,
        language="th",
    )
    time.sleep(0.05)
    app._poll_async_queue()
    time.sleep(0.05)
    app._poll_async_queue()

    client.create_child.assert_called_once_with(
        "C-SUBMIT-01",
        2021,
        4,
        {"primary": "th", "additional": []},
    )
    assert app.active_child_id == "child-created-999"
    assert app.active_child["display_code"] == "C-SUBMIT-01"
    # Legacy case ID must not be touched
    assert app.active_case_id is None
    root.destroy()


def test_gui_child_list_selection_and_mode_badge():
    """Selecting a child from tree_children updates active_child_id, and mode badge reflects client mode."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    root.withdraw()
    client = LinguaLensClient(mock_mode=True)
    c1 = client.create_child("C-LIST-01", 2020, 2)
    c2 = client.create_child("C-LIST-02", 2021, 7)

    app = LinguaLensGUIApp(root, client=client)
    app._refresh_children()
    time.sleep(0.05)
    app._poll_async_queue()

    # Verify mode badge exists and displays mock mode
    assert hasattr(app, "lbl_mode")
    assert "MOCK" in app.lbl_mode.cget("text")

    # Select child 2 from tree_children
    children_items = app.tree_children.get_children()
    assert len(children_items) >= 2

    # Select c2 item
    for item_id in children_items:
        vals = app.tree_children.item(item_id)["values"]
        if vals and vals[0] == c2["id"]:
            app.tree_children.selection_set(item_id)
            app._on_child_selected(None)
            break

    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id == c2["id"]
    assert app.active_child["display_code"] == "C-LIST-02"
    root.destroy()


def test_gui_set_active_child_returns_immediately_while_in_flight():
    """_set_active_child dispatches network fetch to background thread and returns immediately."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    fetch_started = threading.Event()
    allow_finish = threading.Event()

    def slow_get_child(cid):
        fetch_started.set()
        allow_finish.wait(timeout=5.0)
        return {"id": cid, "display_code": f"C-{cid}"}

    client.get_child.side_effect = slow_get_child
    app = LinguaLensGUIApp(root, client=client)

    # Call _set_active_child: must return immediately without waiting for slow_get_child!
    app._set_active_child("c-async-1")
    assert fetch_started.wait(timeout=2.0), "Background fetch should have started"
    # Main thread returned while fetch is still blocked!
    assert app.active_child is None, "active_child must not be set before completion"

    # Now unblock background worker
    allow_finish.set()
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id == "c-async-1"
    assert app.active_child["display_code"] == "C-c-async-1"
    root.destroy()


def test_gui_pending_child_response_then_logout_never_restores_child():
    """If child fetch completes after user logged out / 401, completion must not restore child."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    fetch_started = threading.Event()
    allow_finish = threading.Event()

    def slow_get_child(cid):
        fetch_started.set()
        allow_finish.wait(timeout=5.0)
        return {"id": cid, "display_code": f"C-{cid}"}

    client.get_child.side_effect = slow_get_child
    app = LinguaLensGUIApp(root, client=client)

    app._set_active_child("c-async-logout")
    assert fetch_started.wait(timeout=2.0)

    # User logs out / 401 occurs while request is in-flight!
    app._handle_auth_error(Exception("401 Unauthorized"))

    # Unblock background worker
    allow_finish.set()
    time.sleep(0.05)
    app._poll_async_queue()

    # Context must remain None, never restored by late response!
    assert app.active_child_id is None
    assert app.active_child is None
    root.destroy()


def test_gui_child_request_racing_later_selection_never_overwrites():
    """If request for Child A completes after Child B is selected, Child B must not be overwritten."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    a_started = threading.Event()
    allow_a_finish = threading.Event()

    def mock_get_child(cid):
        if cid == "child-A":
            a_started.set()
            allow_a_finish.wait(timeout=5.0)
            return {"id": "child-A", "display_code": "CHILD-A"}
        return {"id": "child-B", "display_code": "CHILD-B"}

    client.get_child.side_effect = mock_get_child
    app = LinguaLensGUIApp(root, client=client)

    # 1. Start selection of Child A
    app._set_active_child("child-A")
    assert a_started.wait(timeout=2.0)

    # 2. Quickly select Child B while Child A is still in-flight
    app._set_active_child("child-B")
    time.sleep(0.05)
    app._poll_async_queue()
    assert app.active_child_id == "child-B"
    assert app.active_child["display_code"] == "CHILD-B"

    # 3. Now let Child A complete
    allow_a_finish.set()
    time.sleep(0.05)
    app._poll_async_queue()

    # Active child MUST still be Child B!
    assert app.active_child_id == "child-B"
    assert app.active_child["display_code"] == "CHILD-B"
    root.destroy()


def test_gui_create_child_closing_dialog_in_flight_discards_stale_completion():
    """Closing the intake dialog while creation is in-flight must not auto-activate child on stale completion."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    create_started = threading.Event()
    allow_create_finish = threading.Event()

    def slow_create(code, by, bm, lang):
        create_started.set()
        allow_create_finish.wait(timeout=5.0)
        return {"id": "child-cancelled", "display_code": code, "birth_year": by, "birth_month": bm}

    client.create_child.side_effect = slow_create
    app = LinguaLensGUIApp(root, client=client)

    win = app._show_create_child_dialog()
    app._submit_create_child(win, "C-CANCEL", 2021, 5, "th")
    assert create_started.wait(timeout=2.0)

    # User closes dialog before worker finishes!
    win.destroy()

    # Unblock worker
    allow_create_finish.set()
    time.sleep(0.05)
    app._poll_async_queue()

    # Stale completion must not activate the child
    assert app.active_child_id is None
    assert app.active_child is None
    root.destroy()


def test_gui_stale_401_from_old_session_does_not_clear_new_session():
    """An async error tied to an older session generation must not clear a newly established session."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError, ClientSession
    root.withdraw()
    client = MagicMock()
    # Current session is session 2
    session_2 = ClientSession(access_token="tok2", organization_id="org1")
    client.get_session.return_value = session_2
    app = LinguaLensGUIApp(root, client=client)
    app._current_session_generation = 2

    # Stale 401 callback with session_generation = 1 arrives
    app._handle_auth_error(LinguaLensAuthError("401 Unauthorized"), session_generation=1)

    # Active session 2 must NOT be cleared!
    client.clear_session.assert_not_called()
    root.destroy()


def test_gui_create_child_never_auto_retried_on_failure():
    """POST create_child mutation failure must not be auto-retried."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    client = MagicMock()
    client.create_child.side_effect = LinguaLensApiError("500 Internal Server Error")
    app = LinguaLensGUIApp(root, client=client)

    win = app._show_create_child_dialog()
    app._submit_create_child(win, "C-FAIL", 2021, 5, "th")
    time.sleep(0.05)
    app._poll_async_queue()

    # Must have been called exactly once (NO auto-retry!)
    assert client.create_child.call_count == 1
    win.destroy()
    root.destroy()


def test_gui_list_children_401_clears_context_and_credentials():
    """list_children returning 401 must clear credentials and wipe clinical context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError, ClientSession
    root.withdraw()
    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok1", organization_id="org1")
    client.list_children.side_effect = LinguaLensAuthError("401 Session expired")
    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c-pre-list"

    app._refresh_children()
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id is None
    client.clear_session.assert_called()
    root.destroy()


def test_gui_list_children_403_preserves_credentials(monkeypatch):
    """list_children returning 403 must show permission denial without clearing credentials."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensPermissionError, ClientSession
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok1", organization_id="org1")
    client.list_children.side_effect = LinguaLensPermissionError("403 Forbidden to list children")
    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c-keep"

    app._refresh_children()
    time.sleep(0.05)
    app._poll_async_queue()

    # Session credentials must remain intact!
    client.clear_session.assert_not_called()
    assert len(errors_shown) >= 1
    assert "Permission" in errors_shown[0][0] or "Denied" in errors_shown[0][0]
    root.destroy()


def test_gui_create_child_401_clears_context_and_credentials():
    """create_child returning 401 must clear credentials and wipe clinical context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError, ClientSession
    root.withdraw()
    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok1", organization_id="org1")
    client.create_child.side_effect = LinguaLensAuthError("401 Token invalid")
    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c-pre-create"

    win = app._show_create_child_dialog()
    app._submit_create_child(win, "C-FAIL-401", 2021, 5, "th")
    time.sleep(0.05)
    app._poll_async_queue()

    assert app.active_child_id is None
    client.clear_session.assert_called()
    root.destroy()


def test_gui_create_child_403_preserves_credentials(monkeypatch):
    """create_child returning 403 must show permission denial without clearing credentials."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensPermissionError, ClientSession
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok1", organization_id="org1")
    client.create_child.side_effect = LinguaLensPermissionError("403 Forbidden to create child")
    app = LinguaLensGUIApp(root, client=client)

    win = app._show_create_child_dialog()
    app._submit_create_child(win, "C-FAIL-403", 2021, 5, "th")
    time.sleep(0.05)
    app._poll_async_queue()

    # Session credentials must remain intact!
    client.clear_session.assert_not_called()
    assert len(errors_shown) == 1
    assert "Permission" in errors_shown[0][0] or "Denied" in errors_shown[0][0]
    root.destroy()


def test_gui_child_request_403_after_switch_does_not_clear_newer_child(monkeypatch):
    """Request A returns 403 after user switched to Child B -> Child B and credentials remain intact."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensPermissionError, ClientSession
    root.withdraw()
    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok1", organization_id="org1")

    # get_child will delay for child A, return immediately for child B
    def get_child_side_effect(cid):
        if cid == "child-A":
            time.sleep(0.08)
            raise LinguaLensPermissionError("403 Forbidden for Child A")
        return {"id": "child-B", "display_code": "C-B"}

    client.get_child.side_effect = get_child_side_effect
    app = LinguaLensGUIApp(root, client=client)

    # 1. Dispatch request for Child A
    t_a = app._set_active_child("child-A")
    # 2. Immediately switch to Child B before A finishes
    t_b = app._set_active_child("child-B")
    if t_b:
        t_b.join(timeout=1.0)
    app._poll_async_queue()

    assert app.active_child_id == "child-B"
    assert app.active_child == {"id": "child-B", "display_code": "C-B"}

    # 3. Now let A finish with 403
    if t_a:
        t_a.join(timeout=1.0)
    app._poll_async_queue()

    # Child B and credentials MUST NOT be cleared by stale 403 from Child A!
    assert app.active_child_id == "child-B"
    assert app.active_child == {"id": "child-B", "display_code": "C-B"}
    client.clear_session.assert_not_called()
    root.destroy()


def test_gui_stale_error_from_old_session_does_not_clear_new_session():
    """Old child request returning error after session generation change must not touch new session."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensPermissionError, ClientSession
    root.withdraw()
    client = MagicMock()
    client.get_session.return_value = ClientSession(access_token="tok2", organization_id="org2")

    def slow_get_child(cid):
        time.sleep(0.08)
        raise LinguaLensPermissionError("403 from old session")

    client.get_child.side_effect = slow_get_child
    app = LinguaLensGUIApp(root, client=client)

    # Dispatch request in initial session
    t = app._set_active_child("child-old")

    # Simulate sign-out / new session switch before response arrives
    app._current_session_generation = getattr(app, "_current_session_generation", 0) + 1
    app.active_child_id = "child-new-session"
    app.active_child = {"id": "child-new-session"}

    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # New session state must be completely preserved
    assert app.active_child_id == "child-new-session"
    assert app.active_child == {"id": "child-new-session"}
    client.clear_session.assert_not_called()
    root.destroy()


def test_gui_out_of_order_refresh_preserves_latest_snapshot():
    """When two refreshes complete out-of-order, latest snapshot is preserved without duplicate iid or TclError."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()

    snapshot_old = [{"id": "c_old", "display_code": "C_OLD", "birth_year": 2021, "birth_month": 1}]
    snapshot_new = [{"id": "c_new", "display_code": "C_NEW", "birth_year": 2022, "birth_month": 2}]

    app = LinguaLensGUIApp(root, client=client)
    time.sleep(0.05)
    app._poll_async_queue()

    # Configure side effect for out-of-order completions:
    # First call (t1) will be slow and return snapshot_old with duplicate c1
    # Second call (t2) returns immediately with snapshot_new
    # snapshot_old had c1. snapshot_new has ONLY c2 (c1 was deleted/removed)
    call_count = 0
    def list_children_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            time.sleep(0.08)
            return [{"id": "c1", "display_code": "C1-OLD", "birth_year": 2021, "birth_month": 1}]
        return [{"id": "c2", "display_code": "C2-NEW", "birth_year": 2022, "birth_month": 2}]

    client.list_children.side_effect = list_children_side_effect

    # 1. Dispatch first refresh (slow, contains c1)
    t1 = app._refresh_children()
    # 2. Dispatch second refresh (fast, contains only c2)
    t2 = app._refresh_children()

    if t2:
        t2.join(timeout=1.0)
    app._poll_async_queue()

    # Latest snapshot has only c2
    assert set(app.tree_children.get_children()) == {"c2"}

    # 3. Now t1 completes later with older snapshot containing c1
    if t1:
        t1.join(timeout=1.0)
    app._poll_async_queue()

    # Must preserve the latest snapshot (only c2), NOT resurrect deleted c1!
    final_children = set(app.tree_children.get_children())
    assert "c1" not in final_children
    assert final_children == {"c2"}
    root.destroy()


def test_gui_create_child_racing_child_selection_does_not_auto_activate():
    """When child creation is in-flight and user selects another child, create completion must not overwrite selection."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()

    def slow_create_child(*args, **kwargs):
        time.sleep(0.08)
        return {"id": "c-created-new", "display_code": "C-NEW"}

    client.create_child.side_effect = slow_create_child
    client.list_children.return_value = [{"id": "c-created-new", "display_code": "C-NEW"}]
    client.get_child.return_value = {"id": "c-user-selected", "display_code": "C-SELECTED"}

    app = LinguaLensGUIApp(root, client=client)
    win = app._show_create_child_dialog()

    # 1. Submit child creation
    t_create = app._submit_create_child(win, "C-NEW", 2021, 5, "th")

    # 2. User explicitly selects another child while creation is in flight
    t_select = app._set_active_child("c-user-selected")
    if t_select:
        t_select.join(timeout=1.0)
    app._poll_async_queue()
    assert app.active_child_id == "c-user-selected"

    # 3. Create completes
    if t_create:
        t_create.join(timeout=1.0)
    app._poll_async_queue()

    # Must NOT have auto-activated c-created-new over user selection!
    assert not any("c-created-new" in str(call) for call in client.get_child.call_args_list)
    assert app.active_child_id == "c-user-selected"
    root.destroy()


def test_gui_submit_create_child_while_in_flight_prevents_duplicate_post():
    """Clicking submit multiple times while creation is pending must not dispatch duplicate POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    created_events = []

    def slow_create_child(*args, **kwargs):
        created_events.append(kwargs)
        time.sleep(0.08)
        return {"id": "c-dup-test", "display_code": "C-DUP"}

    client.create_child.side_effect = slow_create_child
    client.list_children.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    win = app._show_create_child_dialog()

    # First click
    t1 = app._submit_create_child(win, "C-DUP", 2021, 5, "th")
    assert t1 is not None

    # Second rapid click while in flight
    t2 = app._submit_create_child(win, "C-DUP", 2021, 5, "th")
    assert t2 is None  # Debounced / guarded!

    if t1:
        t1.join(timeout=1.0)
    app._poll_async_queue()

    assert client.create_child.call_count == 1
    root.destroy()


def test_gui_closed_dialog_discards_create_error_presentation(monkeypatch):
    """Closed/cancelled dialog must discard stale create error presentation without popping error dialog."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))

    client = MagicMock()
    def slow_failing_create(*args, **kwargs):
        time.sleep(0.08)
        raise LinguaLensApiError("Late creation error")

    client.create_child.side_effect = slow_failing_create
    app = LinguaLensGUIApp(root, client=client)

    win = app._show_create_child_dialog()
    t = app._submit_create_child(win, "C-ERR-CLOSED", 2021, 5, "th")

    # User closes dialog before response arrives
    win.destroy()

    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Error dialog must NOT be presented for cancelled/closed dialog!
    assert len(errors_shown) == 0
    root.destroy()


def test_gui_create_child_token_mismatch_discards_completion():
    """If dialog token has changed (re-initialized/rotated), old completion must be discarded."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    app = LinguaLensGUIApp(root, client=client)

    win = app._show_create_child_dialog()
    old_token = win._dlg_token
    # Rotate token to simulate dialog reset/re-init
    win._dlg_token = "new-token-123"

    # Invoke _on_create_child_success with old token
    app._on_create_child_success(
        win=win,
        dlg_token=old_token,
        new_child={"id": "child-stale"},
        session_generation=app._get_current_session_generation(),
    )

    # Dialog must NOT have been destroyed by stale token completion!
    assert win.winfo_exists()
    win.destroy()
    root.destroy()


# =============================================================================
# Subtask B: Consent Status Display & Explicit Recording Interaction Tests
# =============================================================================

def test_gui_consent_status_badge_states():
    """GUI displays consent badge reflecting not-loaded, loading, active, and has explicit refresh button."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]

    app = LinguaLensGUIApp(root, client=client)

    # Check that consent UI elements exist in context bar
    assert hasattr(app, "lbl_consent_status")
    assert hasattr(app, "lbl_consent_loaded_at")
    assert hasattr(app, "btn_refresh_consent")
    assert hasattr(app, "btn_record_consent")

    # Select child and refresh consent
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    # Badge should reflect active consent with version and loaded timestamp
    badge_text = app.lbl_consent_status.cget("text")
    assert "Active" in badge_text
    assert "v1" in badge_text or "2026.1" in badge_text
    assert app.lbl_consent_loaded_at.cget("text") != ""
    root.destroy()


def test_gui_consent_status_uses_list_consents_latest_version_per_purpose():
    """GUI distinguishes withdrawn from no-record using latest version per purpose from list_consents."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    # Historical records: v1 active, v2 withdrawn
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1},
        {"id": "con-2", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "withdrawn", "version": 2},
    ]

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    # Must show Withdrawn (not No Record!)
    badge_text = app.lbl_consent_status.cget("text")
    assert "Withdrawn" in badge_text or "ถอน" in badge_text

    # Next case: no records at all
    client.list_consents.return_value = []
    t_ref1 = app._refresh_consent()
    if t_ref1:
        t_ref1.join(timeout=1.0)
    app._poll_async_queue()
    badge_empty = app.lbl_consent_status.cget("text")
    assert "No Record" in badge_empty or "ไม่มี" in badge_empty

    # Next case: records exist only for different purpose
    client.list_consents.return_value = [
        {"id": "con-3", "child_id": "c1", "purpose": "research_only", "scope_version": "2026.1", "status": "active", "version": 1}
    ]
    t_ref2 = app._refresh_consent()
    if t_ref2:
        t_ref2.join(timeout=1.0)
    app._poll_async_queue()
    badge_mixed = app.lbl_consent_status.cget("text")
    assert "No Record" in badge_mixed or "ไม่มี" in badge_mixed
    root.destroy()


def test_gui_consent_api_failure_shows_error_not_no_consent():
    """When list_consents fails, badge shows error loading, NOT 'no consent'."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.list_consents.side_effect = LinguaLensApiError("503 Service Unavailable")

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    badge_text = app.lbl_consent_status.cget("text")
    assert "Error" in badge_text or "ข้อผิดพลาด" in badge_text
    assert "No Record" not in badge_text
    root.destroy()


def test_gui_record_consent_requires_explicit_confirmation(monkeypatch):
    """Record consent dialog requires explicit confirmation; canceling sends no mutation."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.list_consents.return_value = []
    client.record_consent.return_value = {
        "id": "con-new", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Open dialog
    win = app._show_record_consent_dialog()
    assert win is not None
    assert win.winfo_exists()

    # Check that cancel closes without calling record_consent
    win.btn_cancel.invoke()
    assert not win.winfo_exists()
    client.record_consent.assert_not_called()

    # Re-open and submit with confirmation
    win2 = app._show_record_consent_dialog()
    # Mock confirmation messagebox
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)
    t = app._submit_record_consent(win2, purpose="clinical_assessment", scope_version="2026.1", status="active")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    client.record_consent.assert_called_once_with("c1", "clinical_assessment", "2026.1", "active")
    root.destroy()


def test_gui_record_consent_double_submit_prevented(monkeypatch):
    """Submitting record consent while previous is in-flight does not send double POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import time
    root.withdraw()
    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.list_consents.return_value = []

    def slow_record(*args, **kwargs):
        time.sleep(0.1)
        return {"id": "con-slow", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}

    client.record_consent.side_effect = slow_record
    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)
    win = app._show_record_consent_dialog()

    t1 = app._submit_record_consent(win, purpose="clinical_assessment", scope_version="2026.1", status="active")
    # Immediate second click
    t2 = app._submit_record_consent(win, purpose="clinical_assessment", scope_version="2026.1", status="active")

    assert t2 is None  # Debounced!
    if t1:
        t1.join(timeout=1.0)
    app._poll_async_queue()

    assert client.record_consent.call_count == 1
    root.destroy()


def test_gui_record_consent_401_clears_clinical_context_and_403_preserves_session(monkeypatch):
    """Consent recording handles 401 (invalidates session/wipes context) and 403 (preserves session)."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError
    root.withdraw()

    # Part 1: 401
    client_401 = MagicMock()
    client_401.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client_401.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client_401.list_consents.return_value = []
    client_401.record_consent.side_effect = LinguaLensAuthError("401 Unauthorized")

    app_401 = LinguaLensGUIApp(root, client=client_401)
    t_ch1 = app_401._set_active_child("c1")
    if t_ch1:
        t_ch1.join(timeout=1.0)
    app_401._poll_async_queue()

    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)
    win1 = app_401._show_record_consent_dialog()
    t1 = app_401._submit_record_consent(win1, "clinical_assessment", "2026.1", "active")
    if t1:
        t1.join(timeout=1.0)
    app_401._poll_async_queue()

    # 401 must wipe active child
    assert app_401.active_child_id is None
    assert app_401.active_child is None
    client_401.clear_session.assert_called_once()

    # Part 2: 403
    client_403 = MagicMock()
    client_403.list_children.return_value = [{"id": "c2", "display_code": "C-02"}]
    client_403.get_child.return_value = {"id": "c2", "display_code": "C-02"}
    client_403.list_consents.return_value = []
    client_403.record_consent.side_effect = LinguaLensPermissionError("403 Forbidden")

    app_403 = LinguaLensGUIApp(root, client=client_403)
    t_ch2 = app_403._set_active_child("c2")
    if t_ch2:
        t_ch2.join(timeout=1.0)
    app_403._poll_async_queue()

    win2 = app_403._show_record_consent_dialog()
    t2 = app_403._submit_record_consent(win2, "clinical_assessment", "2026.1", "active")
    if t2:
        t2.join(timeout=1.0)
    app_403._poll_async_queue()

    # 403 must preserve active child and credentials
    assert app_403.active_child_id == "c2"
    client_403.clear_session.assert_not_called()
    root.destroy()


def test_gui_record_consent_409_displays_conflict_and_refreshes_authoritative_state(monkeypatch):
    """409 Conflict displays warning, refreshes authoritative state, and does not retry POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensConflictError
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: errors_shown.append((title, msg)))
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)

    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.list_consents.return_value = []
    client.record_consent.side_effect = LinguaLensConflictError("409 Consent conflict on scope version")

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()
    t = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Error shown
    assert len(errors_shown) == 1
    assert "Conflict" in errors_shown[0][0] or "409" in errors_shown[0][1] or "conflict" in errors_shown[0][1].lower()
    # Refresh list_consents triggered
    assert client.list_consents.call_count >= 2
    # No auto-retry of POST
    assert client.record_consent.call_count == 1
    root.destroy()


def test_gui_record_consent_success_refresh_failure_reported_distinctly(monkeypatch):
    """When mutation succeeds but refresh fails, UI reports record succeeded but refresh failed."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    warnings_shown = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg: warnings_shown.append((title, msg)))
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)

    client = MagicMock()
    client.list_children.return_value = [{"id": "c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "c1", "display_code": "C-01"}
    client.record_consent.return_value = {
        "id": "con-ok", "child_id": "c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }
    # Initial load returns empty, refresh after mutation fails
    client.list_consents.side_effect = [
        [],
        LinguaLensApiError("Network timeout on refresh"),
    ]

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("c1")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()
    t = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Must show warning about refresh, NOT mutation failure
    assert len(warnings_shown) == 1
    assert "refresh" in warnings_shown[0][1].lower() or "โหลดสถานะ" in warnings_shown[0][1]
    root.destroy()


def test_gui_record_consent_racing_child_switch_discards_stale_completion(monkeypatch):
    """If active child changes while consent recording is in-flight, completion does not overwrite new child."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import time
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda title, msg: True)

    client = MagicMock()
    client.list_children.return_value = [
        {"id": "child-A", "display_code": "C-A"},
        {"id": "child-B", "display_code": "C-B"},
    ]
    client.get_child.side_effect = lambda cid: {"id": cid, "display_code": f"C-{cid}"}
    client.list_consents.return_value = []

    def slow_record(child_id, *args, **kwargs):
        time.sleep(0.08)
        return {"id": f"con-{child_id}", "child_id": child_id, "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}

    client.record_consent.side_effect = slow_record

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()
    t = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")

    # User switches active child to child-B before response returns
    app.active_child_id = "child-B"
    app.active_child = {"id": "child-B", "display_code": "C-B"}
    app._child_selection_generation += 1

    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Active child must remain child-B
    assert app.active_child_id == "child-B"
    root.destroy()


def test_gui_record_consent_dialog_bound_to_target_child_switch_prevents_dispatch(monkeypatch):
    """Opening dialog for child-A and switching active child to child-B prevents consent mutation dispatch."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}, {"id": "child-B", "display_code": "C-B"}]
    client.get_child.side_effect = lambda cid: {"id": cid, "display_code": f"C-{cid}"}
    client.list_consents.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    # Open dialog bound to child-A
    win = app._show_record_consent_dialog()
    assert getattr(win, "_target_child_id", None) == "child-A"

    # Clinician switches child in background before confirming
    t2 = app._set_active_child("child-B")
    if t2:
        t2.join(timeout=1.0)
    app._poll_async_queue()

    # Attempt to submit dialog opened for child-A
    res = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    assert res is None
    client.record_consent.assert_not_called()
    root.destroy()


def test_gui_record_consent_context_switch_during_confirmation_cancels_dispatch(monkeypatch):
    """If clinical context changes while the confirmation modal is being answered, submission is aborted."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}]
    client.get_child.return_value = {"id": "child-A", "display_code": "C-A"}
    client.list_consents.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()

    def confirm_and_switch_context(*args, **kwargs):
        # Simulate active child being cleared/switched while confirmation prompt is open
        app.active_child_id = "child-B"
        app._child_selection_generation += 1
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", confirm_and_switch_context)

    res = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    assert res is None
    client.record_consent.assert_not_called()
    root.destroy()


def test_gui_record_consent_blank_or_invalid_scope_version_rejected_client_side(monkeypatch):
    """Empty, whitespace, or excessively long (>64 chars) scope_version is rejected without sending POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}]
    client.get_child.return_value = {"id": "child-A", "display_code": "C-A"}
    client.list_consents.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()

    # Case 1: Empty scope version
    res1 = app._submit_record_consent(win, "clinical_assessment", "", "active")
    assert res1 is None
    client.record_consent.assert_not_called()
    assert any("scope" in msg.lower() for _, msg in errors_shown)

    # Case 2: Overlong scope version (>64 characters)
    errors_shown.clear()
    res2 = app._submit_record_consent(win, "clinical_assessment", "x" * 65, "active")
    assert res2 is None
    client.record_consent.assert_not_called()
    assert any("64" in msg or "scope" in msg.lower() for _, msg in errors_shown)
    root.destroy()


def test_gui_record_consent_mutation_success_refresh_is_asynchronous(monkeypatch):
    """Post-mutation consent refresh is dispatched asynchronously and does not block the UI thread."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import threading
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kw: None)

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}]
    client.get_child.return_value = {"id": "child-A", "display_code": "C-A"}
    client.record_consent.return_value = {
        "id": "con-1", "child_id": "child-A", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }

    refresh_threads = []
    def list_consents_spy(cid):
        refresh_threads.append(threading.current_thread().name)
        return [{"id": "con-1", "child_id": "child-A", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}]

    client.list_consents.side_effect = list_consents_spy

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    refresh_threads.clear()

    win = app._show_record_consent_dialog()
    t_record = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    if t_record:
        t_record.join(timeout=1.0)
    app._poll_async_queue()

    # The post-mutation refresh must have run on a background thread, not MainThread
    assert len(refresh_threads) >= 1
    assert all(tname != "MainThread" for tname in refresh_threads)
    root.destroy()


def test_gui_record_consent_success_refresh_401_triggers_session_invalidation(monkeypatch):
    """When mutation succeeds but subsequent refresh returns 401, session is cleared and clinical context wiped without claiming mutation failed."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensAuthError
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}]
    client.get_child.return_value = {"id": "child-A", "display_code": "C-A"}
    client.record_consent.return_value = {
        "id": "con-1", "child_id": "child-A", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1
    }
    # Initial load returns empty, refresh after mutation raises 401
    client.list_consents.side_effect = [
        [],
        LinguaLensAuthError("401 Token Expired"),
    ]

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()
    t_record = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")
    if t_record:
        t_record.join(timeout=1.0)
    app._poll_async_queue()

    # Wait for async post-mutation refresh thread if any
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    # 401 must clear clinical context
    assert app.active_child_id is None
    # Must NOT report "Consent Recording Failed"
    assert not any("recording failed" in title.lower() for title, _ in errors_shown)
    root.destroy()


def test_gui_record_consent_closed_dialog_discards_presentation_does_not_clear_newer_busy_state(monkeypatch):
    """When dialog is closed while mutation is in-flight, completion does not clear newer request busy state."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import time
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-A", "display_code": "C-A"}]
    client.get_child.return_value = {"id": "child-A", "display_code": "C-A"}
    client.list_consents.return_value = []

    def slow_record(*args, **kwargs):
        time.sleep(0.08)
        return {"id": "con-1", "child_id": "child-A", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}

    client.record_consent.side_effect = slow_record

    app = LinguaLensGUIApp(root, client=client)
    t = app._set_active_child("child-A")
    if t:
        t.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_record_consent_dialog()
    t_record = app._submit_record_consent(win, "clinical_assessment", "2026.1", "active")

    # Close dialog while mutation is in flight
    win.destroy()

    # A newer request starts and sets busy state with a new token
    app._set_busy_state(True, "New In-Flight Job", request_id="new-job-123")

    if t_record:
        t_record.join(timeout=1.0)
    app._poll_async_queue()

    # The busy state of the newer job must NOT be cleared by the old consent recording completion
    assert app.is_busy is True
    root.destroy()


# ============================================================================
# Subtask C: Assessment Creation & Safe Desktop Context Transition (GUI)
# ============================================================================

def test_gui_create_assessment_requires_active_child(monkeypatch):
    """Attempting to open create assessment dialog without an active child shows warning and returns None."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    warnings_shown = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg, **kw: warnings_shown.append((title, msg)))

    client = MagicMock()
    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = None

    win = app._show_create_assessment_dialog()
    assert win is None
    assert len(warnings_shown) == 1
    assert "no child" in warnings_shown[0][0].lower()
    client.create_assessment.assert_not_called()
    root.destroy()


@pytest.mark.parametrize("bad_status", ["not-loaded", "loading", "no-record", "withdrawn", "error"])
def test_gui_create_assessment_blocked_when_consent_not_active(monkeypatch, bad_status):
    """When consent is not active (not-loaded, loading, no-record, withdrawn, error), UI precheck blocks assessment creation."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "child-c1"
    app.active_child = {"id": "child-c1", "display_code": "C-01"}
    app._update_consent_badge(bad_status, None if bad_status != "withdrawn" else {"status": "withdrawn", "version": 1})
    app.active_consent = None if bad_status != "active" else {"status": "active", "version": 1}

    # Attempt opening or dispatching creation
    win = app._show_create_assessment_dialog()
    assert win is None
    assert len(errors_shown) >= 1
    assert any("consent" in msg.lower() for _, msg in errors_shown)
    client.create_assessment.assert_not_called()
    root.destroy()


def test_gui_create_assessment_canonical_payload_and_context_isolation(monkeypatch):
    """Successful assessment creation uses canonical payload, sets active_assessment_id, and keeps active_session_id None."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    info_shown = []
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda title, msg, **kw: info_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]
    created_asmt = {
        "id": "asmt-2026-0001",
        "child_id": "child-c1",
        "purpose": "initial",
        "state": "draft",
        "age_months": 42,
        "language_context": {"primary": "th", "additional": []},
        "assigned_clinician_id": "clinician-007",
        "version": 1,
    }
    client.create_assessment.return_value = created_asmt
    client.list_assessments.return_value = [created_asmt]

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    # Consent is active
    assert app.active_consent is not None
    assert app.active_consent.get("status") == "active"

    # Open create assessment dialog
    win = app._show_create_assessment_dialog()
    assert win is not None
    assert win.winfo_exists()

    # Submit assessment creation
    t_submit = app._submit_create_assessment(win, purpose="initial", clinician_id="clinician-007")
    if t_submit:
        t_submit.join(timeout=1.0)
    app._poll_async_queue()

    # Wait for post-creation refresh thread if any
    if getattr(app, "_current_assessment_thread", None):
        app._current_assessment_thread.join(timeout=1.0)
    app._poll_async_queue()

    # Canonical payload verified: only purpose and assigned_clinician_id
    client.create_assessment.assert_called_once_with(
        "child-c1",
        purpose="initial",
        assigned_clinician_id="clinician-007",
    )

    # Verification of context isolation
    assert app.active_assessment_id == "asmt-2026-0001"
    assert app.active_assessment == created_asmt
    # CRITICAL: active_session_id must NOT be polluted
    assert app.active_session_id is None
    root.destroy()


def test_gui_create_assessment_double_submit_protection(monkeypatch):
    """Submitting assessment creation twice quickly only dispatches a single worker and single POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import time
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]

    def slow_create(*args, **kwargs):
        time.sleep(0.08)
        return {
            "id": "asmt-single",
            "child_id": "child-c1",
            "purpose": "initial",
            "state": "draft",
            "age_months": 36,
            "language_context": {"primary": "th", "additional": []},
            "assigned_clinician_id": "default-clinician",
            "version": 1,
        }

    client.create_assessment.side_effect = slow_create
    client.list_assessments.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_create_assessment_dialog()
    t1 = app._submit_create_assessment(win, purpose="initial", clinician_id=None)
    t2 = app._submit_create_assessment(win, purpose="initial", clinician_id=None)

    assert t1 is not None
    assert t2 is None  # Second submission debounced

    if t1:
        t1.join(timeout=1.0)
    app._poll_async_queue()

    assert client.create_assessment.call_count == 1
    root.destroy()


def test_gui_create_assessment_context_drift_aborts_zero_post(monkeypatch):
    """If active child drifts before confirmation modal returns, submission aborts with zero POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [
        {"id": "child-c1", "display_code": "C-01"},
        {"id": "child-c2", "display_code": "C-02"},
    ]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_create_assessment_dialog()

    # User switches child to child-c2 while dialog is open
    app.active_child_id = "child-c2"
    app.active_child = {"id": "child-c2", "display_code": "C-02"}

    # Now confirm submission for dialog bound to child-c1
    t_submit = app._submit_create_assessment(win, purpose="initial", clinician_id=None)
    assert t_submit is None
    client.create_assessment.assert_not_called()
    assert any("context changed" in title.lower() for title, _ in errors_shown)
    root.destroy()


def test_gui_create_assessment_late_success_after_child_switch_or_cancel_discarded(monkeypatch):
    """If child changes or dialog is cancelled while create_assessment is in-flight, late response does not set context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import time
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]

    def slow_create(*args, **kwargs):
        time.sleep(0.08)
        return {
            "id": "asmt-late",
            "child_id": "child-c1",
            "purpose": "initial",
            "state": "draft",
            "age_months": 36,
            "language_context": {"primary": "th", "additional": []},
            "assigned_clinician_id": "default-clinician",
            "version": 1,
        }

    client.create_assessment.side_effect = slow_create
    client.list_assessments.return_value = []

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_create_assessment_dialog()
    t_submit = app._submit_create_assessment(win, purpose="initial", clinician_id=None)

    # User switches active child to None or another child before response returns
    app.active_child_id = "child-c2"
    app.active_child = {"id": "child-c2", "display_code": "C-02"}
    app._child_selection_generation += 1

    if t_submit:
        t_submit.join(timeout=1.0)
    app._poll_async_queue()

    # Late response for child-c1 must NOT set active_assessment_id on child-c2
    assert app.active_assessment_id is None
    root.destroy()


def test_gui_create_assessment_409_conflict_refreshes_consent_no_active_assessment(monkeypatch):
    """When server returns 409 active_consent_required, authoritative consent is refreshed, no active assessment, zero auto-retry."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensConflictError
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    # Precheck had active consent, preflight still sees active, but server-side withdrawal race occurred on POST
    client.list_consents.side_effect = [
        [{"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}],
        [{"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}],
        [{"id": "con-2", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "withdrawn", "version": 2}],
    ]
    client.create_assessment.side_effect = LinguaLensConflictError("Active clinical-assessment consent is required.")

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_create_assessment_dialog()
    t_submit = app._submit_create_assessment(win, purpose="initial", clinician_id=None)
    if t_submit:
        t_submit.join(timeout=1.0)
    app._poll_async_queue()

    # Wait for async 409 refresh thread
    if getattr(app, "_current_consent_thread", None):
        app._current_consent_thread.join(timeout=1.0)
    app._poll_async_queue()

    # Zero auto-retry: create_assessment was called exactly once
    assert client.create_assessment.call_count == 1
    assert app.active_assessment_id is None
    assert any("conflict" in title.lower() or "409" in title for title, _ in errors_shown)
    # Consent badge updated to withdrawn
    assert app.active_consent is None
    root.destroy()


def test_gui_create_assessment_mutation_success_refresh_failure_preserves_fact(monkeypatch):
    """When server creates assessment but subsequent list refresh fails, the creation fact is preserved."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    from packages.tui.client import LinguaLensApiError
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    warnings_shown = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg, **kw: warnings_shown.append((title, msg)))
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    client.list_children.return_value = [{"id": "child-c1", "display_code": "C-01"}]
    client.get_child.return_value = {"id": "child-c1", "display_code": "C-01"}
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "child-c1", "purpose": "clinical_assessment", "scope_version": "2026.1", "status": "active", "version": 1}
    ]
    created_asmt = {
        "id": "asmt-ok-2026",
        "child_id": "child-c1",
        "purpose": "initial",
        "state": "draft",
        "age_months": 40,
        "language_context": {"primary": "th", "additional": []},
        "assigned_clinician_id": "therapist-1",
        "version": 1,
    }
    client.create_assessment.return_value = created_asmt
    client.list_assessments.side_effect = LinguaLensApiError("500 Server error refreshing assessment list")

    app = LinguaLensGUIApp(root, client=client)
    t_child = app._set_active_child("child-c1")
    if t_child:
        t_child.join(timeout=1.0)
    app._poll_async_queue()

    win = app._show_create_assessment_dialog()
    t_submit = app._submit_create_assessment(win, purpose="initial", clinician_id="therapist-1")
    if t_submit:
        t_submit.join(timeout=1.0)
    app._poll_async_queue()

    # Wait for post-mutation refresh
    if getattr(app, "_current_assessment_thread", None):
        app._current_assessment_thread.join(timeout=1.0)
    app._poll_async_queue()

    # FACT PRESERVED: assessment was created on server
    assert app.active_assessment_id == "asmt-ok-2026"
    assert app.active_assessment == created_asmt
    # Must NOT report "Creation Failed"
    assert not any("creation failed" in title.lower() for title, _ in errors_shown)
    # Zero duplicate retry
    assert client.create_assessment.call_count == 1
    root.destroy()


def test_gui_downstream_handlers_blocked_in_v2_mode(monkeypatch):
    """When active_assessment_id is set, downstream legacy handlers and keyboard shortcuts are strictly blocked."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    warnings_shown = []
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda title, msg, **kw: warnings_shown.append((title, msg)))

    client = MagicMock()
    app = LinguaLensGUIApp(root, client=client)
    app.active_assessment_id = "asmt-v2-active"
    app.active_assessment = {"id": "asmt-v2-active", "child_id": "c1"}
    app._update_downstream_tabs_mode()

    # Attempt calling legacy callbacks directly
    app._process_audio_file()
    app._browse_audio_file()
    app._batch_ingest_audio_files()
    app._load_demo_dialogue()
    app._browse_text_file()
    app._ingest_typed_text()
    app._attest_transcript()
    app._save_utterance_edit()
    app._auto_refine_speakers()
    app._swap_speakers()
    app._export_report()
    app._handle_ctrl_s()

    # None of the client legacy methods should have been called
    assert client.ingest_audio_file.call_count == 0
    assert client.create_session.call_count == 0
    assert client.save_transcript.call_count == 0
    assert client.attest_transcript.call_count == 0
    assert client.export_report.call_count == 0
    assert client.auto_refine_speakers.call_count == 0
    assert client.swap_speakers.call_count == 0

    assert len(warnings_shown) > 0
    assert all("v2" in title.lower() or "assessment" in title.lower() for title, _ in warnings_shown)
    root.destroy()


def test_gui_legacy_mode_works_when_not_in_v2(monkeypatch):
    """When active_assessment_id is None and active_session_id is set, legacy operations proceed according to contract."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *args, **kw: None)
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kw: None)

    client = MagicMock()
    client.auto_refine_speakers.return_value = {"utterances": []}
    client.get_findings.return_value = {"metrics": {}}
    app = LinguaLensGUIApp(root, client=client)
    app.active_assessment_id = None
    app.active_session_id = "sess-legacy-123"
    app.active_transcript = {"id": "tr-123", "session_id": "sess-legacy-123", "utterances": []}
    app._update_downstream_tabs_mode()

    # In legacy mode, auto_refine_speakers calls client
    app._auto_refine_speakers()
    client.auto_refine_speakers.assert_called_once_with("tr-123")
    root.destroy()


def test_assessment_purposes_canonical_schema_parity():
    """All purposes offered in UI must validate against canonical AssessmentCreateRequest, while progress/discharge are rejected."""
    import sys
    from pathlib import Path
    api_dir = str(Path(__file__).resolve().parent.parent / "apps" / "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)

    from app.assessment_v2.schemas import AssessmentCreateRequest
    from app.assessment_v2.domain.models import AssessmentPurpose
    import pydantic

    canonical_purposes = [p.value for p in AssessmentPurpose]
    assert canonical_purposes == [
        "initial",
        "developmental_follow_up",
        "post_intervention_follow_up",
        "additional_evidence",
    ]

    for p in canonical_purposes:
        req = AssessmentCreateRequest(purpose=p)
        assert req.purpose.value == p

    for invalid_p in ["progress", "discharge", "followup", "other"]:
        with pytest.raises(pydantic.ValidationError):
            AssessmentCreateRequest(purpose=invalid_p)


def test_gui_create_assessment_rejects_invalid_purpose_zero_post(monkeypatch):
    """If purpose is not a canonical AssessmentPurpose (e.g. progress, discharge, invalid), show validation error and zero POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = tk.Toplevel(root)
    win._bound_child_id = "c1"
    win._bound_session_gen = app._get_current_session_generation()
    win._bound_child_sel_gen = getattr(app, "_child_selection_generation", 0)
    win._dlg_token = "dlg-token-1"

    # Try "progress" and "discharge"
    for bad_purpose in ["progress", "discharge", "unknown_purpose"]:
        res = app._submit_create_assessment(win, purpose=bad_purpose)
        assert res is None
        assert client.create_assessment.call_count == 0

    assert len(errors_shown) >= 3
    assert any("purpose" in msg.lower() for _, msg in errors_shown)
    root.destroy()


@pytest.mark.parametrize("valid_purpose", [
    "initial",
    "developmental_follow_up",
    "post_intervention_follow_up",
    "additional_evidence",
])
def test_gui_create_assessment_all_canonical_purposes_accepted(monkeypatch, valid_purpose):
    """All 4 canonical AssessmentPurpose values are accepted and dispatched to client."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kw: None)

    client = MagicMock()
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}
    ]
    created = {
        "id": f"asmt-{valid_purpose}",
        "child_id": "c1",
        "purpose": valid_purpose,
        "state": "draft",
        "version": 1,
    }
    client.create_assessment.return_value = created

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = tk.Toplevel(root)
    win._bound_child_id = "c1"
    win._bound_session_gen = app._get_current_session_generation()
    win._bound_child_sel_gen = getattr(app, "_child_selection_generation", 0)
    win._dlg_token = "dlg-token-1"

    t = app._submit_create_assessment(win, purpose=valid_purpose)
    assert t is not None
    t.join(timeout=3.0)
    app._poll_async_queue()

    client.create_assessment.assert_called_once_with(
        "c1",
        purpose=valid_purpose,
        assigned_clinician_id=None,
    )
    assert app.active_assessment_id == f"asmt-{valid_purpose}"
    root.destroy()


def test_gui_create_assessment_preflight_fresh_withdrawn_consent_zero_post(monkeypatch):
    """Cached consent was active, but fresh async read during preflight reveals consent was withdrawn -> ZERO POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    # Fresh read returns withdrawn consent
    client.list_consents.return_value = [
        {"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "withdrawn", "version": 2}
    ]

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    # Cache was active initially
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = tk.Toplevel(root)
    win._bound_child_id = "c1"
    win._bound_session_gen = app._get_current_session_generation()
    win._bound_child_sel_gen = getattr(app, "_child_selection_generation", 0)
    win._dlg_token = "dlg-token-1"

    t = app._submit_create_assessment(win, purpose="initial")
    assert t is not None
    t.join(timeout=3.0)
    app._poll_async_queue()

    # Zero POST to create_assessment
    client.create_assessment.assert_not_called()
    assert app.active_assessment_id is None
    assert len(errors_shown) >= 1
    assert any("consent" in msg.lower() for _, msg in errors_shown)
    root.destroy()


def test_gui_create_assessment_preflight_context_drift_zero_post(monkeypatch):
    """Context changes while preflight list_consents is in-flight -> ZERO POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    import threading
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    preflight_started = threading.Event()
    continue_preflight = threading.Event()

    def slow_list_consents(child_id):
        preflight_started.set()
        continue_preflight.wait(timeout=3.0)
        return [{"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}]

    client = MagicMock()
    client.list_consents.side_effect = slow_list_consents

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = tk.Toplevel(root)
    win._bound_child_id = "c1"
    win._bound_session_gen = app._get_current_session_generation()
    win._bound_child_sel_gen = getattr(app, "_child_selection_generation", 0)
    win._dlg_token = "dlg-token-1"

    t = app._submit_create_assessment(win, purpose="initial")
    assert t is not None
    preflight_started.wait(timeout=2.0)

    # Child switches while preflight was in flight
    app.active_child_id = "child-other"
    app._child_selection_generation += 1

    continue_preflight.set()
    t.join(timeout=3.0)
    app._poll_async_queue()

    # Context drifted -> ZERO POST
    client.create_assessment.assert_not_called()
    assert app.active_assessment_id is None
    root.destroy()


def test_gui_on_assessment_selected_cache_miss_fetches_canonical_detail(monkeypatch):
    """Selecting an assessment not in cache asynchronously fetches canonical get_assessment, preventing fabricated assessment."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()

    client = MagicMock()
    canonical_detail = {
        "id": "asmt-999",
        "child_id": "c1",
        "purpose": "initial",
        "state": "draft",
        "age_months": 36,
        "language_context": {"primary": "th"},
        "assigned_clinician_id": "clinician-007",
        "version": 1,
    }
    client.get_assessment.return_value = canonical_detail

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = []  # Cache miss

    app.tree_assessments.insert("", tk.END, iid="asmt-999", values=("asmt-999", "c1", "initial", "draft", "clinician-007", 1))
    app.tree_assessments.selection_set("asmt-999")

    app._on_assessment_selected()
    # If async fetch is launched
    if hasattr(app, "_current_assessment_detail_thread") and app._current_assessment_detail_thread:
        app._current_assessment_detail_thread.join(timeout=3.0)
    app._poll_async_queue()

    client.get_assessment.assert_called_once_with("asmt-999")
    assert app.active_assessment_id == "asmt-999"
    assert app.active_assessment == canonical_detail
    # Must NOT be fabricated {"id": asmt_id, "child_id": active_child_id}
    assert "age_months" in app.active_assessment
    assert "assigned_clinician_id" in app.active_assessment
    root.destroy()


def test_gui_on_assessment_selected_mismatched_child_does_not_activate_context(monkeypatch):
    """If get_assessment returns an assessment belonging to a different child, it must NOT activate context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    errors_shown = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg, **kw: errors_shown.append((title, msg)))

    client = MagicMock()
    # Detail belongs to child-c2, while active child is c1
    client.get_assessment.return_value = {
        "id": "asmt-stale",
        "child_id": "child-c2",
        "purpose": "initial",
        "state": "draft",
        "version": 1,
    }

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = []

    app.tree_assessments.insert("", tk.END, iid="asmt-stale", values=("asmt-stale", "child-c2", "initial", "draft", "", 1))
    app.tree_assessments.selection_set("asmt-stale")

    app._on_assessment_selected()
    if hasattr(app, "_current_assessment_detail_thread") and app._current_assessment_detail_thread:
        app._current_assessment_detail_thread.join(timeout=3.0)
    app._poll_async_queue()

    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_create_assessment_dialog_close_during_preflight_cancels_with_zero_post(monkeypatch):
    """Closing/destroying dialog while consent preflight is pending cancels worker and prevents POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    preflight_started = threading.Event()
    continue_preflight = threading.Event()

    def slow_list_consents(child_id):
        preflight_started.set()
        continue_preflight.wait(timeout=3.0)
        return [{"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}]

    client = MagicMock()
    client.list_consents.side_effect = slow_list_consents

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = app._show_create_assessment_dialog()
    assert win is not None

    t = app._submit_create_assessment(win, purpose="initial")
    assert t is not None
    preflight_started.wait(timeout=2.0)
    assert app.is_busy is True

    # User closes dialog while preflight is running
    win.destroy()

    # Now let preflight finish
    continue_preflight.set()
    t.join(timeout=3.0)
    app._poll_async_queue()

    # Must be ZERO POST
    client.create_assessment.assert_not_called()
    assert app.active_assessment_id is None
    # Busy state must be released
    assert app.is_busy is False
    root.destroy()


def test_gui_create_assessment_dialog_token_change_during_preflight_cancels_with_zero_post(monkeypatch):
    """If dialog token changes (e.g. dialog replaced) during preflight, previous worker aborts with zero POST."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    preflight_started = threading.Event()
    continue_preflight = threading.Event()

    def slow_list_consents(child_id):
        preflight_started.set()
        continue_preflight.wait(timeout=3.0)
        return [{"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}]

    client = MagicMock()
    client.list_consents.side_effect = slow_list_consents

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = app._show_create_assessment_dialog()
    t = app._submit_create_assessment(win, purpose="initial")
    assert t is not None
    preflight_started.wait(timeout=2.0)

    # Invalidate token by setting a new one (e.g. dialog replacement)
    app._current_asmt_dialog_token = "dlg-asmt-replaced-token"

    continue_preflight.set()
    t.join(timeout=3.0)
    app._poll_async_queue()

    client.create_assessment.assert_not_called()
    assert app.active_assessment_id is None
    assert app.is_busy is False
    root.destroy()


def test_gui_create_assessment_cancel_after_post_dispatched_does_not_activate_stale_ui(monkeypatch):
    """Cancellation after POST is in-flight does not activate stale UI context, does not auto-retry, and clears busy state."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kw: True)

    post_started = threading.Event()
    continue_post = threading.Event()

    def slow_create_assessment(child_id, purpose, assigned_clinician_id=None):
        post_started.set()
        continue_post.wait(timeout=3.0)
        return {"id": "asmt-created-after-cancel", "child_id": child_id, "purpose": purpose, "state": "draft"}

    client = MagicMock()
    client.list_consents.return_value = [{"id": "con-1", "child_id": "c1", "purpose": "clinical_assessment", "status": "active", "version": 1}]
    client.create_assessment.side_effect = slow_create_assessment

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._current_consent_status = "active"
    app.active_consent = {"status": "active", "version": 1}

    win = app._show_create_assessment_dialog()
    t = app._submit_create_assessment(win, purpose="initial")
    assert t is not None
    post_started.wait(timeout=2.0)

    # Cancel dialog while POST is in-flight
    win.destroy()

    continue_post.set()
    t.join(timeout=3.0)
    app._poll_async_queue()

    # POST was already sent, but stale UI completion must NOT activate active_assessment_id
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    # Must release busy state
    assert app.is_busy is False
    # No auto-retry
    assert client.create_assessment.call_count == 1
    root.destroy()


def test_gui_assessment_selection_latest_detail_wins_over_slow_earlier_detail(monkeypatch):
    """When selecting A (slow) then B (fast), B must win and late A must NOT overwrite B."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()

    a_started = threading.Event()
    continue_a = threading.Event()

    detail_a = {"id": "asmt-A", "child_id": "c1", "purpose": "initial", "state": "draft", "version": 1}
    detail_b = {"id": "asmt-B", "child_id": "c1", "purpose": "developmental_follow_up", "state": "draft", "version": 1}

    def mock_get_assessment(asmt_id):
        if asmt_id == "asmt-A":
            a_started.set()
            continue_a.wait(timeout=3.0)
            return detail_a
        return detail_b

    client = MagicMock()
    client.get_assessment.side_effect = mock_get_assessment

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = []

    # 1. Select A (cache miss, launches slow fetch)
    app.tree_assessments.insert("", tk.END, iid="asmt-A", values=("asmt-A", "c1", "initial", "draft", "", 1))
    app.tree_assessments.insert("", tk.END, iid="asmt-B", values=("asmt-B", "c1", "developmental_follow_up", "draft", "", 1))

    app.tree_assessments.selection_set("asmt-A")
    app._on_assessment_selected()
    a_started.wait(timeout=2.0)
    t_a = app._current_assessment_detail_thread

    # 2. Select B while A is still pending
    app.tree_assessments.selection_set("asmt-B")
    app._on_assessment_selected()
    t_b = app._current_assessment_detail_thread
    if t_b:
        t_b.join(timeout=3.0)
    app._poll_async_queue()

    # B must be active now
    assert app.active_assessment_id == "asmt-B"
    assert app.active_assessment == detail_b

    # 3. Now let A complete late
    continue_a.set()
    if t_a:
        t_a.join(timeout=3.0)
    app._poll_async_queue()

    # B must STILL be active; late A must NOT overwrite B!
    assert app.active_assessment_id == "asmt-B"
    assert app.active_assessment == detail_b
    root.destroy()


def test_gui_assessment_selection_cache_hit_wins_over_pending_slow_detail(monkeypatch):
    """When selecting A (slow miss) then B (cache hit), B becomes active and late A does not overwrite."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()

    a_started = threading.Event()
    continue_a = threading.Event()

    detail_a = {"id": "asmt-A", "child_id": "c1", "purpose": "initial", "state": "draft", "version": 1}
    cached_b = {"id": "asmt-B", "child_id": "c1", "purpose": "developmental_follow_up", "state": "draft", "version": 1}

    def mock_get_assessment(asmt_id):
        if asmt_id == "asmt-A":
            a_started.set()
            continue_a.wait(timeout=3.0)
            return detail_a
        return {}

    client = MagicMock()
    client.get_assessment.side_effect = mock_get_assessment

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = [cached_b]

    app.tree_assessments.insert("", tk.END, iid="asmt-A", values=("asmt-A", "c1", "initial", "draft", "", 1))
    app.tree_assessments.insert("", tk.END, iid="asmt-B", values=("asmt-B", "c1", "developmental_follow_up", "draft", "", 1))

    # 1. Select A (cache miss)
    app.tree_assessments.selection_set("asmt-A")
    app._on_assessment_selected()
    a_started.wait(timeout=2.0)
    t_a = app._current_assessment_detail_thread

    # 2. Select B (cache hit)
    app.tree_assessments.selection_set("asmt-B")
    app._on_assessment_selected()
    assert app.active_assessment_id == "asmt-B"
    assert app.active_assessment == cached_b

    # 3. A completes late
    continue_a.set()
    if t_a:
        t_a.join(timeout=3.0)
    app._poll_async_queue()

    # B remains active!
    assert app.active_assessment_id == "asmt-B"
    assert app.active_assessment == cached_b
    root.destroy()


def test_gui_assessment_detail_loaded_rejects_mismatched_assessment_id(monkeypatch):
    """If get_assessment returns a detail with an assessment ID different from requested, reject and do not activate."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *args, **kw: None)

    client = MagicMock()
    # Requested asmt-A, but server returned asmt-CORRUPTED
    client.get_assessment.return_value = {
        "id": "asmt-CORRUPTED",
        "child_id": "c1",
        "purpose": "initial",
        "state": "draft",
        "version": 1,
    }

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = []

    app.tree_assessments.insert("", tk.END, iid="asmt-A", values=("asmt-A", "c1", "initial", "draft", "", 1))
    app.tree_assessments.selection_set("asmt-A")

    app._on_assessment_selected()
    if hasattr(app, "_current_assessment_detail_thread") and app._current_assessment_detail_thread:
        app._current_assessment_detail_thread.join(timeout=3.0)
    app._poll_async_queue()

    # Mismatched ID must NOT activate
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_assessment_selection_cancelled_on_child_switch_or_logout(monkeypatch):
    """If child changes or logout happens while assessment detail is fetching, late response must not restore context."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    import threading
    from unittest.mock import MagicMock
    root.withdraw()

    fetch_started = threading.Event()
    continue_fetch = threading.Event()

    def slow_get_assessment(asmt_id):
        fetch_started.set()
        continue_fetch.wait(timeout=3.0)
        return {"id": asmt_id, "child_id": "c1", "purpose": "initial", "state": "draft", "version": 1}

    client = MagicMock()
    client.get_assessment.side_effect = slow_get_assessment

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    app._cached_assessments = []

    app.tree_assessments.insert("", tk.END, iid="asmt-1", values=("asmt-1", "c1", "initial", "draft", "", 1))
    app.tree_assessments.selection_set("asmt-1")

    app._on_assessment_selected()
    fetch_started.wait(timeout=2.0)
    t = app._current_assessment_detail_thread

    # Switch child
    app.active_child_id = "c-OTHER"
    app._child_selection_generation += 1

    continue_fetch.set()
    if t:
        t.join(timeout=3.0)
    app._poll_async_queue()

    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_assessment_selection_failure_clears_context_and_does_not_show_old_assessment(monkeypatch):
    """When switching selection from old assessment to new assessment and new fetch fails, context is cleared (old assessment not retained)."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *args, **kw: None)

    client = MagicMock()
    client.get_assessment.side_effect = RuntimeError("404 Not Found")

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    # Old assessment was active
    app.active_assessment_id = "asmt-OLD"
    app.active_assessment = {"id": "asmt-OLD", "child_id": "c1", "purpose": "initial", "state": "draft"}
    app._cached_assessments = []

    app.tree_assessments.insert("", tk.END, iid="asmt-NEW", values=("asmt-NEW", "c1", "developmental_follow_up", "draft", "", 1))
    app.tree_assessments.selection_set("asmt-NEW")

    app._on_assessment_selected()
    if hasattr(app, "_current_assessment_detail_thread") and app._current_assessment_detail_thread:
        app._current_assessment_detail_thread.join(timeout=3.0)
    app._poll_async_queue()

    # Must be cleared, not showing old assessment
    assert app.active_assessment_id is None
    assert app.active_assessment is None
    root.destroy()


def test_gui_cached_assessment_requires_canonical_fields_not_just_age_and_clinician(monkeypatch):
    """A cached record missing canonical fields (e.g. purpose or state) is NOT treated as complete, triggering get_assessment."""
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Headless environment without display server")

    from unittest.mock import MagicMock
    root.withdraw()

    client = MagicMock()
    canonical_detail = {
        "id": "asmt-incomplete",
        "child_id": "c1",
        "purpose": "initial",
        "state": "draft",
        "age_months": 24,
        "assigned_clinician_id": "clinician-1",
        "version": 1,
    }
    client.get_assessment.return_value = canonical_detail

    app = LinguaLensGUIApp(root, client=client)
    app.active_child_id = "c1"
    app.active_child = {"id": "c1", "display_code": "C-01"}
    # Has age_months and assigned_clinician_id, but missing 'purpose' and 'state'
    incomplete_cached = {
        "id": "asmt-incomplete",
        "child_id": "c1",
        "age_months": 24,
        "assigned_clinician_id": "clinician-1",
    }
    app._cached_assessments = [incomplete_cached]

    app.tree_assessments.insert("", tk.END, iid="asmt-incomplete", values=("asmt-incomplete", "c1", "", "", "clinician-1", 1))
    app.tree_assessments.selection_set("asmt-incomplete")

    app._on_assessment_selected()
    if hasattr(app, "_current_assessment_detail_thread") and app._current_assessment_detail_thread:
        app._current_assessment_detail_thread.join(timeout=3.0)
    app._poll_async_queue()

    # Must have triggered get_assessment to complete canonical contract
    client.get_assessment.assert_called_once_with("asmt-incomplete")
    assert app.active_assessment_id == "asmt-incomplete"
    assert app.active_assessment == canonical_detail
    root.destroy()

