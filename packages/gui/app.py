"""LinguaLens Desktop GUI Application (Tkinter / TTK).

Provides an interactive graphical desktop interface for clinicians replicating
the 5-step LinguaLens decision-support workflow with local audio/video file selection,
acoustic prosody feature extraction, transcript QA review, and report sign-off.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable
import urllib.error
import uuid

from packages.tui.client import (
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensClient,
    LinguaLensPermissionError,
    LinguaLensServerError,
)


class LinguaLensGUIApp:
    """Main Desktop GUI Application window."""

    def __init__(self, root: tk.Tk, client: LinguaLensClient | None = None):
        self.root = root
        self.root.title("LinguaLens — Speech-Language Decision Support Desktop")
        self.root.geometry("1050x740")
        self.root.minsize(900, 600)

        self.client = client or LinguaLensClient()
        self.active_case_id: str | None = None
        self.active_session_id: str | None = None
        self.active_transcript: dict[str, Any] | None = None
        self.active_report: dict[str, Any] | None = None
        self.active_audio_path: str | None = None
        # Assessment V2 context state
        self.active_child_id: str | None = None
        self.active_child: dict[str, Any] | None = None
        self.active_consent: dict[str, Any] | None = None
        self.active_assessment_id: str | None = None
        self.active_assessment: dict[str, Any] | None = None
        self._current_mode: str = "legacy"
        self._legacy_context_generation: int = 0
        self._current_child_request_id: str = ""
        self.is_busy: bool = False
        self.is_findings_stale: bool = False
        self._resize_job: str | None = None
        self._async_queue: queue.Queue[tuple[Callable[[], None], Exception | None]] = queue.Queue()
        self._current_play_process: subprocess.Popen | None = None
        self._is_continuous_playing: bool = False
        self._playback_start_wall_time: float = 0.0
        self._word_highlight_timer_ids: list[str] = []
        self._word_button_widgets: list[tuple[ttk.Button, str, float, float]] = []
        self._progress_dialog: tk.Toplevel | None = None
        self._dlg_bar_progress: ttk.Progressbar | None = None
        self._dlg_lbl_stage: tk.Label | None = None
        self._dlg_lbl_pct: tk.Label | None = None
        self.playback_speed: float = 1.0
        self._audio_waveform_peaks: list[float] | None = None
        self._audio_waveform_duration: float = 0.0
        self._current_playback_offset_sec: float = 0.0
        self._playback_end_limit_sec: float | None = None
        self._playhead_time_sec: float = 0.0
        self._is_user_scrubbing: bool = False
        self._current_temp_slice: str | None = None
        self._show_pitch_overlay: bool = True
        self._audio_f0_contour: list[tuple[float, float]] = []
        self._poll_job: str | None = None
        self._resize_job: str | None = None
        self._current_session_generation: int = 1
        self._current_child_request_id: str | None = None
        self._child_selection_generation: int = 0
        self._current_refresh_request_id: str | None = None
        self._consent_request_id: str | None = None
        self._consent_loaded_at: str | None = None

        self.root.bind("<Destroy>", lambda e: self._cleanup_timers() if e.widget == self.root else None, add="+")

        self._configure_styles()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()
        self._bind_shortcuts()
        self._poll_async_queue()
        self._load_initial_data()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Clinical Teal System Colors & Fonts (Aligned with PRODUCT.md & tokens.css)
        self.bg_color = "#f8fafc"
        self.primary_color = "#0f766e"
        self.primary_strong = "#115e59"
        self.accent_soft = "#f0fdfa"
        self.border_color = "#cbd5e1"
        self.text_color = "#0f172a"
        self.root.configure(bg=self.bg_color)

        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", padding=[14, 7], font=("Helvetica", 10, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.accent_soft), ("active", "#e2e8f0")],
            foreground=[("selected", self.primary_color), ("!selected", "#475569")],
        )
        style.configure("Treeview", rowheight=28, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), background="#e2e8f0", foreground=self.text_color)
        style.configure("Primary.TButton", font=("Helvetica", 10, "bold"), padding=[10, 5])
        style.configure("Success.TButton", font=("Helvetica", 10, "bold"), padding=[10, 5])

    # --- UI Layout Builders ---
    def _build_header(self) -> None:
        # Classic Desktop App Title Header
        header_frame = tk.Frame(self.root, bg="#f8fafc", padx=16, pady=8, highlightthickness=1, highlightbackground="#e2e8f0")
        header_frame.pack(fill=tk.X)

        title_frame = tk.Frame(header_frame, bg="#f8fafc")
        title_frame.pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text="🖥️ LinguaLens v1.6.3",
            font=("Helvetica", 14, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
        ).pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text=" — Clinical Speech-Language Decision Support System",
            font=("Helvetica", 11),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(side=tk.LEFT)

        # Connection Badge
        is_online = self.client.check_health()
        status_text = "● Connected (API)" if is_online else "○ Offline Mode"
        status_bg = "#dcfce7" if is_online else "#fef9c3"
        status_fg = "#166534" if is_online else "#854d0e"

        status_lbl = tk.Label(
            header_frame,
            text=status_text,
            font=("Helvetica", 9, "bold"),
            fg=status_fg,
            bg=status_bg,
            padx=8,
            pady=3,
        )
        status_lbl.pack(side=tk.RIGHT)

        # Mode indicator badge (MOCK vs LIVE)
        mode_text = "[LOCAL RESEARCH MOCK]" if self.client.mock_mode else "[CLINICAL LIVE - FASTAPI]"
        mode_fg = "#0f766e" if self.client.mock_mode else "#0284c7"
        self.lbl_mode = tk.Label(header_frame, text=mode_text, font=("Helvetica", 9, "bold"), fg=mode_fg, bg="#ffffff")
        self.lbl_mode.pack(side=tk.RIGHT, padx=(0, 8))

        # Subtle safety note
        safety_banner = tk.Frame(self.root, bg="#fffbeb", padx=14, pady=3, highlightthickness=1, highlightbackground="#fef3c7")
        safety_banner.pack(fill=tk.X)
        safety_lbl = tk.Label(
            safety_banner,
            text="⚠️ Research/Education Prototype Only. Non-diagnostic. Human-in-the-loop clinician verification required.",
            font=("Helvetica", 9, "italic"),
            fg="#b45309",
            bg="#fffbeb",
        )
        safety_lbl.pack(anchor=tk.W)

        # Persistent Global Context Bar (Searchable Case, Session, Refresh, Actions)
        ctx_bar = tk.Frame(self.root, bg="#f1f5f9", padx=12, pady=6, highlightthickness=1, highlightbackground="#cbd5e1")
        ctx_bar.pack(fill=tk.X, padx=12, pady=(6, 2))

        # Case Search & Selector
        tk.Label(ctx_bar, text="🔍 Find Case:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#334155").pack(side=tk.LEFT, padx=(0, 2))
        self.entry_case_search = ttk.Entry(ctx_bar, width=12, font=("Helvetica", 9))
        self.entry_case_search.pack(side=tk.LEFT, padx=(0, 6))
        self.entry_case_search.bind("<KeyRelease>", self._on_case_search_typing)

        tk.Label(ctx_bar, text="👤 Case:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#0f172a").pack(side=tk.LEFT, padx=(0, 2))
        self.combo_global_case = ttk.Combobox(ctx_bar, state="readonly", width=24, font=("Helvetica", 9))
        self.combo_global_case.pack(side=tk.LEFT, padx=(0, 6))
        self.combo_global_case.bind("<<ComboboxSelected>>", self._on_global_case_changed)

        # Session Selector
        tk.Label(ctx_bar, text="🗓️ Session:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#0f172a").pack(side=tk.LEFT, padx=(0, 2))
        self.combo_global_session = ttk.Combobox(ctx_bar, state="readonly", width=20, font=("Helvetica", 9))
        self.combo_global_session.pack(side=tk.LEFT, padx=(0, 6))
        self.combo_global_session.bind("<<ComboboxSelected>>", self._on_global_session_changed)

        # Child Selector (Assessment V2)
        tk.Label(ctx_bar, text="👶 Child:", font=("Helvetica", 9, "bold"), bg="#f1f5f9", fg="#0f172a").pack(side=tk.LEFT, padx=(4, 2))
        self.combo_global_child = ttk.Combobox(ctx_bar, state="readonly", width=20, font=("Helvetica", 9))
        self.combo_global_child.pack(side=tk.LEFT, padx=(0, 6))
        self.combo_global_child.bind("<<ComboboxSelected>>", self._on_global_child_changed)

        # Consent Status Badge & Actions (Subtask B)
        self.lbl_consent_status = tk.Label(
            ctx_bar,
            text="[Consent Not Loaded]",
            font=("Helvetica", 8, "bold"),
            bg="#f1f5f9",
            fg="#64748b",
            padx=4,
            pady=1,
            relief=tk.GROOVE,
        )
        self.lbl_consent_status.pack(side=tk.LEFT, padx=(2, 2))

        self.lbl_consent_loaded_at = tk.Label(
            ctx_bar,
            text="",
            font=("Helvetica", 8),
            bg="#f1f5f9",
            fg="#94a3b8",
        )
        self.lbl_consent_loaded_at.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_refresh_consent = ttk.Button(
            ctx_bar,
            text="🔄",
            width=3,
            command=self._refresh_consent,
        )
        self.btn_refresh_consent.pack(side=tk.LEFT, padx=(0, 2))

        self.btn_record_consent = ttk.Button(
            ctx_bar,
            text="📋 Record Consent",
            command=self._show_record_consent_dialog,
        )
        self.btn_record_consent.pack(side=tk.LEFT, padx=(2, 4))

        self.lbl_assessment_ctx = tk.Label(
            ctx_bar,
            text="",
            font=("Helvetica", 8, "bold"),
            bg="#f1f5f9",
            fg="#7e22ce",
            padx=4,
            pady=1,
            relief=tk.GROOVE,
        )
        self.lbl_assessment_ctx.pack(side=tk.LEFT, padx=(2, 2))

        self.btn_create_assessment = ttk.Button(
            ctx_bar,
            text="➕ New Assessment",
            command=self._show_create_assessment_dialog,
        )
        self.btn_create_assessment.pack(side=tk.LEFT, padx=(2, 6))

        # Quick Buttons & Refresh
        ttk.Button(ctx_bar, text="🔄 Refresh", command=self._refresh_all_data).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(ctx_bar, text="➕ New Case", command=self._show_create_case_dialog).pack(side=tk.RIGHT, padx=(3, 0))
        ttk.Button(ctx_bar, text="➕ New Session", command=self._show_create_session_dialog).pack(side=tk.RIGHT, padx=(3, 0))
        ttk.Button(ctx_bar, text="➕ New Child", command=self._show_create_child_dialog).pack(side=tk.RIGHT, padx=(3, 0))


    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Cases & Sessions
        self.tab_cases = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_cases, text="1. 📋 Cases & Sessions")
        self._build_tab_cases()

        # Tab 2: Ingestion (Audio / CHA / Text)
        self.tab_ingestion = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ingestion, text="2. 🎙️ Ingest Audio & Transcript")
        self._build_tab_ingestion()

        # Tab 3: Transcript QA Review
        self.tab_review = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_review, text="3. 🗣️ Transcript QA & Review")
        self._build_tab_review()

        # Tab 4: Findings & Guideline Mapping
        self.tab_findings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_findings, text="4. 📊 Findings & Acoustics")
        self._build_tab_findings()

        # Tab 5: Progress Report & Export
        self.tab_report = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_report, text="5. 📝 Report & Sign-off")
        self._build_tab_report()

    def _build_statusbar(self) -> None:
        """Bottom status bar with operational status and indeterminate progress indicator."""
        self.statusbar_frame = tk.Frame(self.root, bg="#e2e8f0", padx=12, pady=4)
        self.statusbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = tk.Label(
            self.statusbar_frame,
            text="Ready",
            font=("Helvetica", 9),
            fg="#334155",
            bg="#e2e8f0",
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.prog_bar = ttk.Progressbar(self.statusbar_frame, mode="indeterminate", length=140)
        # Hidden by default

    def _bind_shortcuts(self) -> None:
        """Register global desktop keyboard shortcuts."""
        self.root.bind("<Control-s>", lambda e: self._handle_ctrl_s())
        self.root.bind("<Command-s>", lambda e: self._handle_ctrl_s())
        self.root.bind("<Control-r>", lambda e: self._refresh_all_data())
        self.root.bind("<Command-r>", lambda e: self._refresh_all_data())
        self.root.bind("<Control-e>", lambda e: self._export_report())
        self.root.bind("<Command-e>", lambda e: self._export_report())
        self.root.bind("<space>", lambda e: self._handle_space_shortcut(e))

    @property
    def current_mode(self) -> str:
        return getattr(self, "_current_mode", "legacy")

    @current_mode.setter
    def current_mode(self, mode: str) -> None:
        prev_mode = getattr(self, "_current_mode", "legacy")
        self._current_mode = mode
        if mode == "v2":
            self.active_case_id = None
            self.active_session_id = None
            self.active_transcript = None
            self.active_report = None
            self.active_audio_path = None
            if getattr(self, "_is_continuous_playing", False):
                self._stop_playback()
            if getattr(self, "_current_busy_mode", None) == "legacy":
                self._set_busy_state(False, "Ready")
        elif mode == "legacy":
            self.active_child_id = None
            self.active_child = None
            self.active_consent = None
            self.active_assessment_id = None
            self.active_assessment = None
            self._cached_assessments = []
            if getattr(self, "_current_busy_mode", None) == "v2":
                self._set_busy_state(False, "Ready")

    def _is_v2_mode(self) -> bool:
        """Return True if the active GUI context is in Assessment V2 mode."""
        return (
            getattr(self, "current_mode", "legacy") == "v2"
            or getattr(self, "active_child_id", None) is not None
            or getattr(self, "active_assessment_id", None) is not None
        )

    def _guard_v2_mode(self, action_name: str = "This action") -> bool:
        """Return True and show warning if in V2 mode, blocking legacy operations."""
        if self._is_v2_mode():
            messagebox.showwarning(
                "Assessment V2 Mode Active",
                f"{action_name} is not applicable in Assessment V2 mode. Downstream V2 capture/review will be available in subsequent stages.",
            )
            return True
        return False

    def _handle_space_shortcut(self, event: Any) -> None:
        """Toggle playback when space is pressed outside text entry inputs."""
        if self._is_v2_mode():
            return
        focus_w = self.root.focus_get()
        # Don't trigger playback toggle if user is editing inside a Text or Entry widget
        if isinstance(focus_w, (tk.Text, tk.Entry, ttk.Entry)):
            return

        if getattr(self, "_is_continuous_playing", False):
            self._stop_playback()
        else:
            if hasattr(self, "_toggle_continuous_playback"):
                self._toggle_continuous_playback()
            else:
                self._toggle_continuous_playback()

    def _handle_ctrl_s(self) -> None:
        """Handle quick save depending on current tab."""
        if self._guard_v2_mode("Save"):
            return
        current_tab = self.notebook.index("current")
        if current_tab == 2:  # Review tab
            self._save_utterance_edit()
        elif current_tab == 4:  # Report tab
            self._export_report()


    def _set_busy_state(
        self,
        busy: bool,
        message: str = "Ready",
        request_id: str | None = None,
        mode: str | None = None,
    ) -> None:
        """Update UI busy cursor and progress bar indicator, scoped to request_id and mode."""
        if busy:
            self.is_busy = True
            if request_id is not None:
                self._current_busy_request_id = request_id
            self._current_busy_mode = mode or getattr(self, "current_mode", "legacy")
        else:
            current_busy_id = getattr(self, "_current_busy_request_id", None)
            if request_id is not None and current_busy_id is not None and request_id != current_busy_id:
                return  # Do not clear busy state belonging to a newer request
            self.is_busy = False
            self._current_busy_request_id = None
            self._current_busy_mode = None

        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=message)
        if busy:
            try:
                self.root.config(cursor="watch")
            except Exception:
                pass
            if hasattr(self, "prog_bar") and self.prog_bar.winfo_exists():
                self.prog_bar.pack(side=tk.RIGHT, padx=4)
                if self.root.winfo_exists() and self.root.state() != "withdrawn":
                    try:
                        self.prog_bar.start(50)
                    except Exception:
                        pass
        else:
            try:
                self.root.config(cursor="")
            except Exception:
                pass
            if hasattr(self, "prog_bar") and self.prog_bar.winfo_exists():
                try:
                    self.prog_bar.stop()
                except Exception:
                    pass
                self.prog_bar.pack_forget()

    def _cleanup_timers(self) -> None:
        """Cancel pending Tk after callbacks when the application window is destroyed."""
        if getattr(self, "_poll_job", None):
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        if getattr(self, "_resize_job", None):
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None

    def _poll_async_queue(self) -> None:
        """Process completed background worker callbacks on the Tkinter main thread."""
        try:
            while not self._async_queue.empty():
                cb, error = self._async_queue.get_nowait()
                if cb and callable(cb):
                    cb()
        except Exception:
            pass

        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return

        try:
            self._poll_job = self.root.after(30, self._poll_async_queue)
        except Exception:
            self._poll_job = None

    def _run_async_task(
        self,
        target: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
        busy_msg: str = "Processing...",
        request_id: str | None = None,
    ) -> threading.Thread:
        """Execute long-running work in a background thread and post results safely via queue."""
        if request_id is None:
            request_id = f"task-{uuid.uuid4().hex[:8]}"
        task_mode = getattr(self, "current_mode", "legacy")
        expected_gen = getattr(self, "_legacy_context_generation", 0)
        session_gen = self._get_current_session_generation()
        self._set_busy_state(True, busy_msg, request_id=request_id, mode=task_mode)

        def worker() -> None:
            try:
                res = target()
                self._async_queue.put((
                    lambda r=res: self._on_task_done(
                        r, on_success, None, task_mode=task_mode, expected_gen=expected_gen, request_id=request_id, session_gen=session_gen
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_task_done(
                        None, on_error, e, task_mode=task_mode, expected_gen=expected_gen, request_id=request_id, session_gen=session_gen
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_task_done(
        self,
        result: Any,
        callback: Callable[[Any], None] | None,
        error: Exception | None,
        task_mode: str = "legacy",
        expected_gen: int = 0,
        request_id: str | None = None,
        session_gen: int | None = None,
    ) -> None:
        """Handle task completion on Tkinter main thread."""
        current_session_gen = self._get_current_session_generation()

        # 1. Auth invalidation check: HTTP 401 must be handled for the current auth session
        # regardless of mode switches, selection changes, or cancellation.
        from packages.tui.client import LinguaLensAuthError
        if error is not None:
            is_auth_error = isinstance(error, LinguaLensAuthError) or (
                hasattr(error, "status_code") and getattr(error, "status_code", None) == 401
            )
            if is_auth_error:
                if session_gen is None or session_gen == current_session_gen:
                    self._set_busy_state(False, "Ready", request_id=request_id)
                    self._handle_auth_error(error, session_generation=session_gen)
                    if callback and callable(callback):
                        try:
                            callback(error)
                        except Exception:
                            pass
                return

        # 2. Check session staleness for successes or non-auth errors
        if session_gen is not None and session_gen != current_session_gen:
            # Discard completion from an earlier invalidated session
            return

        # 3. Check legacy/V2 mode and context staleness
        current_mode = getattr(self, "current_mode", "legacy")
        current_gen = getattr(self, "_legacy_context_generation", 0)
        if task_mode == "legacy" and (current_mode != "legacy" or current_gen != expected_gen):
            # Discard stale legacy worker completion: mode switched to V2 or legacy context was invalidated
            return

        self._set_busy_state(False, "Ready", request_id=request_id)
        if error:
            if callback and callable(callback):
                callback(error)
            else:
                messagebox.showerror("Operation Failed", str(error))
        elif callback and callable(callback):
            callback(result)


    # --- Tab 1: Cases & Sessions UI ---
    def _build_tab_cases(self) -> None:
        frame = ttk.Frame(self.tab_cases, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # Cases Table Header
        lbl_c = ttk.Label(frame, text="Active Child Cases Directory", font=("Helvetica", 12, "bold"))
        lbl_c.pack(anchor=tk.W, pady=(0, 4))

        columns_c = ("case_id", "child_id", "age", "lang", "sessions", "notes")
        self.tree_cases = ttk.Treeview(frame, columns=columns_c, show="headings", height=6)
        self.tree_cases.heading("case_id", text="Case ID")
        self.tree_cases.heading("child_id", text="Child ID")
        self.tree_cases.heading("age", text="Age (Mo)")
        self.tree_cases.heading("lang", text="Lang")
        self.tree_cases.heading("sessions", text="Sessions")
        self.tree_cases.heading("notes", text="Clinical Notes")

        self.tree_cases.column("case_id", width=120)
        self.tree_cases.column("child_id", width=100)
        self.tree_cases.column("age", width=70, anchor=tk.CENTER)
        self.tree_cases.column("lang", width=60, anchor=tk.CENTER)
        self.tree_cases.column("sessions", width=70, anchor=tk.CENTER)
        self.tree_cases.column("notes", width=380)

        self.tree_cases.pack(fill=tk.X, pady=(0, 8))
        self.tree_cases.bind("<<TreeviewSelect>>", self._on_case_selected)

        # Button Bar for Cases
        btn_bar_c = ttk.Frame(frame)
        btn_bar_c.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(btn_bar_c, text="➕ Create New Case", command=self._show_create_case_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_c, text="🔄 Refresh Cases", command=self._refresh_cases).pack(side=tk.LEFT)

        # Sessions Table
        lbl_s = ttk.Label(frame, text="Sessions for Selected Case", font=("Helvetica", 12, "bold"))
        lbl_s.pack(anchor=tk.W, pady=(8, 4))

        columns_s = ("session_id", "date", "number", "status", "transcript", "report")
        self.tree_sessions = ttk.Treeview(frame, columns=columns_s, show="headings", height=5)
        self.tree_sessions.heading("session_id", text="Session ID")
        self.tree_sessions.heading("date", text="Date")
        self.tree_sessions.heading("number", text="Sess #")
        self.tree_sessions.heading("status", text="Workflow Status")
        self.tree_sessions.heading("transcript", text="Transcript")
        self.tree_sessions.heading("report", text="Report")

        self.tree_sessions.column("session_id", width=140)
        self.tree_sessions.column("date", width=110)
        self.tree_sessions.column("number", width=60, anchor=tk.CENTER)
        self.tree_sessions.column("status", width=140)
        self.tree_sessions.column("transcript", width=100, anchor=tk.CENTER)
        self.tree_sessions.column("report", width=100, anchor=tk.CENTER)

        self.tree_sessions.pack(fill=tk.X, pady=(0, 8))
        self.tree_sessions.bind("<<TreeviewSelect>>", self._on_session_selected)

        # Button Bar for Sessions
        btn_bar_s = ttk.Frame(frame)
        btn_bar_s.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(btn_bar_s, text="➕ Start New Session", command=self._show_create_session_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_s, text="🚀 Open in Ingestion Workspace ➔", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT)

        # Active Children Directory (Assessment V2)
        lbl_ch = ttk.Label(frame, text="Active Children Directory (Assessment V2)", font=("Helvetica", 12, "bold"))
        lbl_ch.pack(anchor=tk.W, pady=(8, 4))

        columns_ch = ("child_id", "display_code", "birth_ym", "lang")
        self.tree_children = ttk.Treeview(frame, columns=columns_ch, show="headings", height=4)
        self.tree_children.heading("child_id", text="Child ID")
        self.tree_children.heading("display_code", text="Display Code")
        self.tree_children.heading("birth_ym", text="Birth YYYY-MM")
        self.tree_children.heading("lang", text="Primary Lang")

        self.tree_children.column("child_id", width=160)
        self.tree_children.column("display_code", width=140)
        self.tree_children.column("birth_ym", width=120, anchor=tk.CENTER)
        self.tree_children.column("lang", width=100, anchor=tk.CENTER)

        self.tree_children.pack(fill=tk.X, pady=(0, 6))
        self.tree_children.bind("<<TreeviewSelect>>", self._on_child_selected)

        btn_bar_ch = ttk.Frame(frame)
        btn_bar_ch.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_bar_ch, text="➕ Create Child Profile (V2)", command=self._show_create_child_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_ch, text="➕ Create Assessment (V2)", command=self._show_create_assessment_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_bar_ch, text="🔄 Refresh Children", command=self._refresh_children).pack(side=tk.LEFT)

        # Assessments Directory (Assessment V2)
        lbl_asmt = ttk.Label(frame, text="Assessments Directory (Assessment V2)", font=("Helvetica", 12, "bold"))
        lbl_asmt.pack(anchor=tk.W, pady=(4, 4))

        columns_asmt = ("asmt_id", "child_id", "purpose", "state", "clinician", "version")
        self.tree_assessments = ttk.Treeview(frame, columns=columns_asmt, show="headings", height=4)
        self.tree_assessments.heading("asmt_id", text="Assessment ID")
        self.tree_assessments.heading("child_id", text="Child ID")
        self.tree_assessments.heading("purpose", text="Purpose")
        self.tree_assessments.heading("state", text="State")
        self.tree_assessments.heading("clinician", text="Clinician")
        self.tree_assessments.heading("version", text="Ver")

        self.tree_assessments.column("asmt_id", width=160)
        self.tree_assessments.column("child_id", width=120)
        self.tree_assessments.column("purpose", width=90, anchor=tk.CENTER)
        self.tree_assessments.column("state", width=90, anchor=tk.CENTER)
        self.tree_assessments.column("clinician", width=140)
        self.tree_assessments.column("version", width=50, anchor=tk.CENTER)

        self.tree_assessments.pack(fill=tk.X, pady=(0, 6))
        self.tree_assessments.bind("<<TreeviewSelect>>", self._on_assessment_selected)


    # --- Tab 2: Ingestion UI ---
    def _build_tab_ingestion(self) -> None:
        frame = ttk.Frame(self.tab_ingestion, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_ingest_ctx = ttk.Label(
            frame,
            text="Please select a Session from Tab 1 to begin ingestion.",
            font=("Helvetica", 11, "bold"),
            foreground="#0369a1",
        )
        self.lbl_ingest_ctx.pack(anchor=tk.W, pady=(0, 12))

        # Audio/Video File Picker Card
        card_audio = ttk.LabelFrame(frame, text="🎙️ Option A: Ingest Local Audio / Video Clip", padding=12)
        card_audio.pack(fill=tk.X, pady=(0, 12))

        lbl_desc = ttk.Label(
            card_audio,
            text="Select an audio or video recording from your computer (.wav, .mp3, .m4a, .mp4).\n"
            "The system will extract Pitch/Prosody acoustics (F0) and transcribe dialogue segments.",
            font=("Helvetica", 10),
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 8))

        f_picker = ttk.Frame(card_audio)
        f_picker.pack(fill=tk.X)
        self.entry_audio_path = ttk.Entry(f_picker, font=("Helvetica", 10))
        self.entry_audio_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.btn_select_audio = ttk.Button(f_picker, text="📂 Browse...", command=self._browse_audio_file)
        self.btn_select_audio.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_process_audio = ttk.Button(f_picker, text="⚡ Process", command=self._process_audio_file)
        self.btn_process_audio.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_batch_ingest = ttk.Button(f_picker, text="📦 Batch Ingest...", command=self._batch_ingest_audio_files)
        self.btn_batch_ingest.pack(side=tk.LEFT)

        # Dedicated Audio Ingestion Progress Panel (Hidden by default, shown during processing)
        self.frame_ingest_progress = tk.Frame(
            card_audio,
            bg="#f0fdf4",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#86efac",
        )
        self.lbl_ingest_stage = tk.Label(
            self.frame_ingest_progress,
            text="🚀 Initializing Audio Pipeline...",
            font=("Helvetica", 10, "bold"),
            fg="#166534",
            bg="#f0fdf4",
        )
        self.lbl_ingest_stage.pack(anchor=tk.W, pady=(0, 4))

        self.bar_ingest_progress = ttk.Progressbar(
            self.frame_ingest_progress,
            orient="horizontal",
            mode="determinate",
            length=500,
        )
        self.bar_ingest_progress.pack(fill=tk.X, pady=(0, 4))

        self.lbl_ingest_percent = tk.Label(
            self.frame_ingest_progress,
            text="0% Completed",
            font=("Helvetica", 9),
            fg="#15803d",
            bg="#f0fdf4",
        )
        self.lbl_ingest_percent.pack(anchor=tk.W)

        # CHA / Text File Picker Card
        card_text = ttk.LabelFrame(frame, text="📄 Option B: Load Demo Dialogue or CHAT File", padding=12)
        card_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(card_text)
        btn_row.pack(anchor=tk.W, pady=(0, 8))
        self.btn_ingest_demo = ttk.Button(btn_row, text="✨ Load Demo Thai Play Dialogue", command=self._load_demo_dialogue)
        self.btn_ingest_demo.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_browse_text = ttk.Button(btn_row, text="📂 Load .cha / .txt File...", command=self._browse_text_file)
        self.btn_browse_text.pack(side=tk.LEFT)

        lbl_raw = ttk.Label(card_text, text="Or enter dialogue text manually below (format: 'INV: ...' and 'CHI: ...'):", font=("Helvetica", 9, "italic"))
        lbl_raw.pack(anchor=tk.W, pady=(0, 4))

        self.txt_manual = tk.Text(card_text, height=8, font=("Courier", 10))
        self.txt_manual.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.btn_ingest_text = ttk.Button(card_text, text="📥 Ingest Typed Dialogue Text", command=self._ingest_typed_text)
        self.btn_ingest_text.pack(anchor=tk.E)


    # --- Tab 3: Review UI (TalkBank / CHAT + Table Editor) ---
    def _build_tab_review(self) -> None:
        frame = ttk.Frame(self.tab_review, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top_bar = ttk.Frame(frame)
        top_bar.pack(fill=tk.X, pady=(0, 6))
        self.lbl_review_status = ttk.Label(top_bar, text="Transcript Status: Not loaded", font=("Helvetica", 11, "bold"))
        self.lbl_review_status.pack(side=tk.LEFT)

        self.btn_attest = ttk.Button(top_bar, text="✍️ Clinician Sign-Off & Attest", command=self._attest_transcript)
        self.btn_attest.pack(side=tk.RIGHT)

        # Dual-mode sub-notebook (TalkBank CHAT vs Table Editor)
        self.review_notebook = ttk.Notebook(frame)
        self.review_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Sub-tab A: TalkBank / CHAT Viewer
        self.subtab_chat = ttk.Frame(self.review_notebook, padding=8)
        self.review_notebook.add(self.subtab_chat, text="📜 TalkBank / CHAT Format View")

        chat_bar = ttk.Frame(self.subtab_chat)
        chat_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(chat_bar, text="TalkBank CHAT Canonical Syntax (@Begin ... *CHI / *INV ... @End):", font=("Helvetica", 9, "italic"), foreground="#475569").pack(side=tk.LEFT)
        ttk.Button(chat_bar, text="📋 Copy CHAT", command=self._copy_chat_text).pack(side=tk.RIGHT)

        self.txt_chat_view = tk.Text(
            self.subtab_chat,
            font=("Courier", 10),
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#0284c7",
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            relief=tk.FLAT,
        )
        self.txt_chat_view.pack(fill=tk.BOTH, expand=True)
        # Configure clean light syntax tags for TalkBank style
        self.txt_chat_view.tag_configure("header", foreground="#475569", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("chi", foreground="#1d4ed8", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("inv", foreground="#047857", font=("Courier", 10, "bold"))
        self.txt_chat_view.tag_configure("time", foreground="#b45309", font=("Courier", 10))
        self.txt_chat_view.tag_configure("tier", foreground="#7c3aed", font=("Courier", 10, "italic"))

        # Sub-tab B: Utterance Table & Interactive Editor
        self.subtab_table = ttk.Frame(self.review_notebook, padding=8)
        self.review_notebook.add(self.subtab_table, text="✏️ Utterance Table & Quick Editor")

        # Interactive Audio Waveform Visualizer & Seek Canvas
        self.frame_waveform = tk.Frame(
            self.subtab_table,
            bg="#0f172a",
            height=65,
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.frame_waveform.pack(fill=tk.X, pady=(0, 6))
        self.frame_waveform.pack_propagate(False)

        self.canvas_waveform = tk.Canvas(
            self.frame_waveform,
            bg="#0f172a",
            height=63,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas_waveform.pack(fill=tk.BOTH, expand=True)
        self.canvas_waveform.bind("<Configure>", lambda e: self._redraw_waveform())
        self.canvas_waveform.bind("<Button-1>", self._on_waveform_click)
        self.canvas_waveform.bind("<B1-Motion>", self._on_waveform_drag)

        # Interactive Audio Scrubber & Timeline Bar
        self.frame_scrubber = tk.Frame(
            self.subtab_table,
            bg="#f1f5f9",
            padx=8,
            pady=3,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        self.frame_scrubber.pack(fill=tk.X, pady=(0, 4))

        self.lbl_time_current = tk.Label(
            self.frame_scrubber,
            text="00:00.0",
            font=("Helvetica", 9, "bold"),
            fg="#0f766e",
            bg="#f1f5f9",
            width=7,
        )
        self.lbl_time_current.pack(side=tk.LEFT, padx=(0, 6))

        self.scale_scrubber = ttk.Scale(
            self.frame_scrubber,
            from_=0.0,
            to=100.0,
            orient=tk.HORIZONTAL,
            command=self._on_scrubber_slide,
        )
        self.scale_scrubber.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.scale_scrubber.bind("<Button-1>", self._on_scrubber_press)
        self.scale_scrubber.bind("<ButtonRelease-1>", self._on_scrubber_release)

        self.lbl_time_total = tk.Label(
            self.frame_scrubber,
            text="00:00.0",
            font=("Helvetica", 9),
            fg="#64748b",
            bg="#f1f5f9",
            width=7,
        )
        self.lbl_time_total.pack(side=tk.RIGHT, padx=(6, 0))

        # Audio Player & Synchronized Playback Toolbar
        self.frame_audio_player = tk.Frame(
            self.subtab_table,
            bg="#f8fafc",
            padx=10,
            pady=6,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
        )
        self.frame_audio_player.pack(fill=tk.X, pady=(0, 6))

        self.btn_play_continuous = ttk.Button(
            self.frame_audio_player,
            text="▶️ Play Audio with Follow",
            style="Primary.TButton",
            command=self._toggle_continuous_playback,
        )
        self.btn_play_continuous.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_stop_audio = ttk.Button(
            self.frame_audio_player,
            text="⏹️ Stop",
            command=self._stop_playback,
        )
        self.btn_stop_audio.pack(side=tk.LEFT, padx=(0, 8))

        # Playback speed selector
        ttk.Label(self.frame_audio_player, text="Speed:", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.combo_speed = ttk.Combobox(
            self.frame_audio_player,
            values=["0.75x", "1.0x", "1.25x"],
            width=5,
            state="readonly",
            font=("Helvetica", 9),
        )
        self.combo_speed.set("1.0x")
        self.combo_speed.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_speed.bind("<<ComboboxSelected>>", self._on_speed_changed)

        self.btn_auto_refine = ttk.Button(
            self.frame_audio_player,
            text="🧠 Auto-Refine Speakers",
            command=self._auto_refine_speakers,
        )
        self.btn_auto_refine.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_swap_speakers = ttk.Button(
            self.frame_audio_player,
            text="🔄 Swap CHI ↔ Adult",
            command=self._swap_speakers,
        )
        self.btn_swap_speakers.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_toggle_pitch = ttk.Button(
            self.frame_audio_player,
            text="📈 F0 Curve: ON",
            command=self._toggle_pitch_overlay,
        )
        self.btn_toggle_pitch.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_playback_status = tk.Label(
            self.frame_audio_player,
            text="Audio: Ready (Click ▶️ or press [C]=CHI, [I]=INV, [M]=MOT to tag)",
            font=("Helvetica", 9),
            fg="#475569",
            bg="#f8fafc",
        )
        self.lbl_playback_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        columns_u = ("id", "speaker", "time", "text", "flags")
        self.tree_utterances = ttk.Treeview(self.subtab_table, columns=columns_u, show="headings", height=8)
        self.tree_utterances.heading("id", text="#")
        self.tree_utterances.heading("speaker", text="Speaker")
        self.tree_utterances.heading("time", text="Time (s)")
        self.tree_utterances.heading("text", text="Utterance Text")
        self.tree_utterances.heading("flags", text="QA Flags")

        self.tree_utterances.column("id", width=40, anchor=tk.CENTER)
        self.tree_utterances.column("speaker", width=90, anchor=tk.CENTER)
        self.tree_utterances.column("time", width=100, anchor=tk.CENTER)
        self.tree_utterances.column("text", width=550)
        self.tree_utterances.column("flags", width=140)

        # Configure real-time playing highlight tag
        self.tree_utterances.tag_configure(
            "playing",
            background="#dbeafe",
            foreground="#1e40af",
        )

        self.tree_utterances.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.tree_utterances.bind("<<TreeviewSelect>>", self._on_utterance_selected)
        self.tree_utterances.bind("<KeyPress>", self._on_tree_key_press)

        # Edit controls
        edit_box = ttk.LabelFrame(self.subtab_table, text="✏️ Edit Selected Utterance & Speaker", padding=8)
        edit_box.pack(fill=tk.X, pady=(2, 0))

        e_row = ttk.Frame(edit_box)
        e_row.pack(fill=tk.X, pady=(2, 4))
        e_row.columnconfigure(3, weight=1)

        ttk.Label(e_row, text="Speaker:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self.combo_spk = ttk.Combobox(e_row, values=["CHI", "INV", "MOT", "FAT"], width=7, state="readonly")
        self.combo_spk.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        self.combo_spk.set("CHI")

        ttk.Label(e_row, text="Text:").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        self.entry_u_text = ttk.Entry(e_row, font=("Helvetica", 10))
        self.entry_u_text.grid(row=0, column=3, sticky=tk.EW, padx=(0, 10))

        self.btn_play_snippet = ttk.Button(e_row, text="🔊 Play Snippet", command=self._play_selected_utterance)
        self.btn_play_snippet.grid(row=0, column=4, sticky=tk.E, padx=(0, 6))

        self.btn_save_u_edit = ttk.Button(e_row, text="💾 Save Utterance Edit", style="Primary.TButton", command=self._save_utterance_edit)
        self.btn_save_u_edit.grid(row=0, column=5, sticky=tk.E)

        # Word-level interactive audio chips row
        self.frame_words_chips = ttk.Frame(edit_box)
        self.frame_words_chips.pack(fill=tk.X, pady=(6, 0))
        self.lbl_words_title = ttk.Label(self.frame_words_chips, text="🎯 Word Timings (Click to listen):", font=("Helvetica", 9, "bold"))
        self.lbl_words_title.pack(side=tk.LEFT, padx=(0, 6))
        self.container_word_buttons = ttk.Frame(self.frame_words_chips)
        self.container_word_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- Tab 4: Findings UI (Spider Diagram & 15+ Features Hub) ---
    def _build_tab_findings(self) -> None:
        self.frame_tab_findings = ttk.Frame(self.tab_findings, padding=12)
        self.frame_tab_findings.pack(fill=tk.BOTH, expand=True)

        # Stale state notification banner
        self.frame_stale_findings = tk.Frame(
            self.frame_tab_findings,
            bg="#fffbeb",
            padx=10,
            pady=6,
            highlightthickness=1,
            highlightbackground="#fcd34d",
        )
        tk.Label(
            self.frame_stale_findings,
            text="⚠️ Transcript modified: Findings & Report are currently STALE. Click Recalculate to refresh.",
            font=("Helvetica", 9, "bold"),
            fg="#92400e",
            bg="#fffbeb",
        ).pack(side=tk.LEFT)
        ttk.Button(
            self.frame_stale_findings,
            text="🔄 Recalculate Findings",
            command=self._recalculate_findings,
        ).pack(side=tk.RIGHT)

        # Sub-notebook for Spider Diagram vs Detailed Table
        self.findings_notebook = ttk.Notebook(self.frame_tab_findings)
        self.findings_notebook.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 1: Spider / Radar Diagram View
        self.subtab_radar = ttk.Frame(self.findings_notebook, padding=8)
        self.findings_notebook.add(self.subtab_radar, text="🕸️ Spider Diagram (Norm Comparison)")

        radar_split = ttk.Frame(self.subtab_radar)
        radar_split.pack(fill=tk.BOTH, expand=True)

        # Left Canvas for Radar Plot
        canvas_frame = tk.Frame(radar_split, bg="#ffffff", highlightthickness=1, highlightbackground="#cbd5e1")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.canvas_radar = tk.Canvas(canvas_frame, width=380, height=330, bg="#ffffff", highlightthickness=0)
        self.canvas_radar.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas_radar.bind("<Configure>", self._on_canvas_radar_resize)

        # Right Summary Panel
        sum_frame = ttk.LabelFrame(radar_split, text="📊 Benchmark Comparison vs TD Norms", padding=10)
        sum_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.txt_radar_summary = tk.Text(sum_frame, font=("Helvetica", 10), bg="#f8fafc", padx=8, pady=8, wrap=tk.WORD, relief=tk.FLAT)
        self.txt_radar_summary.pack(fill=tk.BOTH, expand=True)
        self.txt_radar_summary.tag_configure("title", font=("Helvetica", 10, "bold"), foreground="#0f172a")
        self.txt_radar_summary.tag_configure("green", font=("Helvetica", 9, "bold"), foreground="#15803d")
        self.txt_radar_summary.tag_configure("blue", font=("Helvetica", 9, "bold"), foreground="#1d4ed8")

        # Sub-tab 2: Detailed Table View
        self.subtab_table_features = ttk.Frame(self.findings_notebook, padding=8)
        self.findings_notebook.add(self.subtab_table_features, text="📋 Comprehensive 15+ Features & Guidelines Table")

        lbl_f = ttk.Label(self.subtab_table_features, text="📊 Speech-Language, Interaction & Acoustic Profile", font=("Helvetica", 11, "bold"))
        lbl_f.pack(anchor=tk.W, pady=(0, 4))

        columns_m = ("category", "metric", "val", "desc")
        self.tree_metrics = ttk.Treeview(self.subtab_table_features, columns=columns_m, show="headings", height=8)
        self.tree_metrics.heading("category", text="Domain / หมวดหมู่")
        self.tree_metrics.heading("metric", text="Feature Metric")
        self.tree_metrics.heading("val", text="Value")
        self.tree_metrics.heading("desc", text="Clinical Description / ความหมายเชิงคลินิก")

        self.tree_metrics.column("category", width=180)
        self.tree_metrics.column("metric", width=180)
        self.tree_metrics.column("val", width=100, anchor=tk.CENTER)
        self.tree_metrics.column("desc", width=420)
        self.tree_metrics.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        lbl_g = ttk.Label(self.subtab_table_features, text="📑 Clinical Guideline Linkages (Thai ASD Assessment Dimensions)", font=("Helvetica", 10, "bold"))
        lbl_g.pack(anchor=tk.W, pady=(0, 2))

        columns_g = ("construct", "status", "evidence")
        self.tree_guidelines = ttk.Treeview(self.subtab_table_features, columns=columns_g, show="headings", height=3)
        self.tree_guidelines.heading("construct", text="Clinical Construct")
        self.tree_guidelines.heading("status", text="Observation Status")
        self.tree_guidelines.heading("evidence", text="Evidence Summary")

        self.tree_guidelines.column("construct", width=250)
        self.tree_guidelines.column("status", width=180)
        self.tree_guidelines.column("evidence", width=450)
        self.tree_guidelines.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        # Sub-tab 3: Longitudinal Assessment Trajectory
        self.subtab_longitudinal = ttk.Frame(self.findings_notebook, padding=8)
        self.findings_notebook.add(self.subtab_longitudinal, text="📅 Longitudinal Trajectory (Cross-Session)")

        lbl_l = ttk.Label(self.subtab_longitudinal, text="📈 Multi-Session Developmental Trajectory & Growth Tracking", font=("Helvetica", 11, "bold"))
        lbl_l.pack(anchor=tk.W, pady=(0, 4))

        self.lbl_longitudinal_summary = tk.Label(
            self.subtab_longitudinal,
            text="Tracking progress across sessions for active case...",
            font=("Helvetica", 9),
            bg="#f0fdfa",
            fg="#0f766e",
            padx=10,
            pady=6,
            anchor=tk.W,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.lbl_longitudinal_summary.pack(fill=tk.X, pady=(0, 8))

        columns_l = ("date", "session_id", "utts", "chi_turns", "mlu", "ttr", "f0", "status")
        self.tree_longitudinal = ttk.Treeview(self.subtab_longitudinal, columns=columns_l, show="headings", height=8)
        self.tree_longitudinal.heading("date", text="Date / วันที่")
        self.tree_longitudinal.heading("session_id", text="Session ID")
        self.tree_longitudinal.heading("utts", text="Total Utts")
        self.tree_longitudinal.heading("chi_turns", text="Child Turns")
        self.tree_longitudinal.heading("mlu", text="MLU-w")
        self.tree_longitudinal.heading("ttr", text="TTR (Vocab)")
        self.tree_longitudinal.heading("f0", text="F0 Median")
        self.tree_longitudinal.heading("status", text="Attestation")

        self.tree_longitudinal.column("date", width=100, anchor=tk.CENTER)
        self.tree_longitudinal.column("session_id", width=120, anchor=tk.CENTER)
        self.tree_longitudinal.column("utts", width=90, anchor=tk.CENTER)
        self.tree_longitudinal.column("chi_turns", width=90, anchor=tk.CENTER)
        self.tree_longitudinal.column("mlu", width=90, anchor=tk.CENTER)
        self.tree_longitudinal.column("ttr", width=90, anchor=tk.CENTER)
        self.tree_longitudinal.column("f0", width=100, anchor=tk.CENTER)
        self.tree_longitudinal.column("status", width=110, anchor=tk.CENTER)
        self.tree_longitudinal.pack(fill=tk.BOTH, expand=True)
        self.tree_longitudinal.bind("<<TreeviewSelect>>", self._on_longitudinal_session_selected)

    def _on_canvas_radar_resize(self, event: Any) -> None:
        """Handle dynamic resize of the Spider Diagram canvas with debouncing."""
        if self._resize_job:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        try:
            self._resize_job = self.root.after(60, self._do_redraw_radar)
        except Exception:
            self._do_redraw_radar()

    def _do_redraw_radar(self) -> None:
        self._resize_job = None
        if hasattr(self, "active_session_id") and self.active_session_id:
            findings = self.client.get_findings(self.active_session_id)
            self._draw_spider_diagram(findings.get("metrics", {}))

    def _draw_spider_diagram(self, metrics: dict[str, Any]) -> None:
        """Render native radar chart comparing Child values vs Typical Development (TD) Norms."""
        import math
        self.canvas_radar.delete("all")
        self.canvas_radar.update_idletasks()
        width = max(280, self.canvas_radar.winfo_width()) if self.canvas_radar.winfo_width() > 1 else 380
        height = max(240, self.canvas_radar.winfo_height()) if self.canvas_radar.winfo_height() > 1 else 330
        cx, cy = width / 2, height / 2 - 5
        radius = max(60, min(cx, cy) - 45)

        has_child_data = bool(
            metrics
            and (metrics.get("mlu_words") is not None or metrics.get("total_child_utterances", 0) > 0)
            and metrics.get("total_child_utterances", 0) > 0
        )

        # 6 Axes comparing Child to Typical Development (TD) norm baseline
        f0_val = metrics.get("f0_iqr_hz") if has_child_data else None
        f0_float = float(f0_val) if f0_val is not None and f0_val != "N/A" else None
        sp_val = metrics.get("speech_rate_wpm") if has_child_data else None
        sp_float = float(sp_val) if sp_val is not None and sp_val != "N/A" else None

        mlu_val = float(metrics["mlu_words"]) if has_child_data and metrics.get("mlu_words") is not None else None
        ttr_val = float(metrics["ttr"]) if has_child_data and metrics.get("ttr") is not None else None
        tt_val = float(metrics["turn_taking_ratio"]) if has_child_data and metrics.get("turn_taking_ratio") is not None else None
        intel_val = float(metrics["intelligibility_rate"]) if has_child_data and metrics.get("intelligibility_rate") is not None else None

        axes = [
            {"label": "MLU-w\n(ประโยค)", "val": mlu_val, "td": 3.5, "unit": "คำ"},
            {"label": "TTR\n(คำศัพท์)", "val": ttr_val, "td": 0.75, "unit": ""},
            {"label": "Turn-Taking\n(การผลัดกันพูด)", "val": tt_val, "td": 0.90, "unit": ""},
            {"label": "Intelligibility\n(ความชัดเจน)", "val": intel_val, "td": 0.95, "unit": ""},
            {"label": "Speech Rate\n(ความเร็วพูด)", "val": sp_float, "td": 90.0, "unit": "wpm"},
            {"label": "Prosody IQR\n(ช่วงเสียง)", "val": f0_float, "td": 35.0, "unit": "Hz"},
        ]
        n = len(axes)

        # Concentric grid rings
        for r_ratio in [0.25, 0.5, 0.75, 1.0, 1.2]:
            r = radius * (r_ratio / 1.2)
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
            is_norm = (r_ratio == 1.0)
            self.canvas_radar.create_polygon(pts, fill="", outline="#94a3b8" if is_norm else "#e2e8f0", width=1.5 if is_norm else 1, dash=(3, 2) if is_norm else ())

        # Spokes and labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            self.canvas_radar.create_line(cx, cy, cx + radius * math.cos(angle), cy + radius * math.sin(angle), fill="#e2e8f0", width=1)
            x_lbl = cx + (radius + 22) * math.cos(angle)
            y_lbl = cy + (radius + 22) * math.sin(angle)
            self.canvas_radar.create_text(x_lbl, y_lbl, text=ax["label"], font=("Helvetica", 8, "bold"), fill="#475569", justify=tk.CENTER)

        # 1. Typical Development (TD) Baseline Polygon (100% ring)
        td_pts = []
        for i in range(n):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            r_td = radius * (1.0 / 1.2)
            td_pts.extend([cx + r_td * math.cos(angle), cy + r_td * math.sin(angle)])
        self.canvas_radar.create_polygon(td_pts, fill="", outline="#10b981", width=2, dash=(4, 2))

        # 2. Child Session Data Polygon (only if genuine child data exists)
        if has_child_data:
            child_pts = []
            for i, ax in enumerate(axes):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                if ax["val"] is not None:
                    ratio = ax["val"] / ax["td"] if ax["td"] else 1.0
                    ratio = max(0.15, min(1.25, ratio))
                else:
                    ratio = 0.05
                r_child = radius * (ratio / 1.2)
                child_pts.extend([cx + r_child * math.cos(angle), cy + r_child * math.sin(angle)])

            if len(child_pts) >= 6:
                self.canvas_radar.create_polygon(child_pts, fill="#e0f2fe", outline="#0284c7", width=2.5)

            for i, ax in enumerate(axes):
                if ax["val"] is not None:
                    px, py = child_pts[i*2], child_pts[i*2+1]
                    self.canvas_radar.create_oval(px-3.5, py-3.5, px+3.5, py+3.5, fill="#0369a1", outline="white", width=1)

            # Summary text
            self.txt_radar_summary.config(state=tk.NORMAL)
            self.txt_radar_summary.delete("1.0", tk.END)
            self.txt_radar_summary.insert(tk.END, "Spider Diagram (ผลเปรียบเทียบกับเกณฑ์สมวัย):\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "🟢 เส้นประเขียว: ค่าปกติสมวัย (TD Norm Baseline 100%)\n", "green")
            self.txt_radar_summary.insert(tk.END, "🔵 พื้นที่ฟ้า: ผลการตรวจของเด็กในเซสชันนี้\n\n", "blue")
            for ax in axes:
                lbl_clean = ax['label'].split('\n')[0]
                if ax["val"] is not None:
                    pct = int((ax["val"] / ax["td"]) * 100) if ax["td"] else 100
                    unit_str = f" {ax['unit']}" if ax["unit"] else ""
                    status_emoji = "✓" if pct >= 85 else ("⚡" if pct >= 65 else "⚠️")
                    self.txt_radar_summary.insert(tk.END, f"{status_emoji} {lbl_clean}: {ax['val']}{unit_str} (เกณฑ์ปกติ: {ax['td']}{unit_str}) — {pct}%\n")
                else:
                    self.txt_radar_summary.insert(tk.END, f"○ {lbl_clean}: N/A (ไม่มีไฟล์เสียง - ข้อความล้วน)\n")
            self.txt_radar_summary.config(state=tk.DISABLED)
        else:
            # Clean Empty State Display
            self.canvas_radar.create_rectangle(cx - 130, cy - 26, cx + 130, cy + 26, fill="#f8fafc", outline="#cbd5e1", width=1)
            self.canvas_radar.create_text(cx, cy - 7, text="ยังไม่มีข้อมูลการประเมินในเซสชันนี้", font=("Helvetica", 9, "bold"), fill="#64748b")
            self.canvas_radar.create_text(cx, cy + 10, text="(กรุณา Ingest ไฟล์เสียงหรือข้อความใน Tab 2)", font=("Helvetica", 8), fill="#94a3b8")

            self.txt_radar_summary.config(state=tk.NORMAL)
            self.txt_radar_summary.delete("1.0", tk.END)
            self.txt_radar_summary.insert(tk.END, "Spider Diagram (ผลเปรียบเทียบกับเกณฑ์สมวัย):\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "🟢 เส้นประเขียว: ค่าปกติสมวัย (TD Norm Baseline 100%)\n\n", "green")
            self.txt_radar_summary.insert(tk.END, "⚠️ ยังไม่มีข้อมูลการประเมิน\n\n", "title")
            self.txt_radar_summary.insert(tk.END, "กรุณานำเข้าไฟล์เสียงหรือบทสนทนาในแท็บ '2. Ingest Audio & Transcript' เพื่อเริ่มการวิเคราะห์ตัวชี้วัด LSA และ Acoustic Prosody")
            self.txt_radar_summary.config(state=tk.DISABLED)

    # --- Tab 5: Report UI (Data Ground Truth & Clinical Decision Support) ---
    def _build_tab_report(self) -> None:
        frame = ttk.Frame(self.tab_report, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        top_r = ttk.Frame(frame)
        top_r.pack(fill=tk.X, pady=(0, 4))
        self.lbl_report_status = ttk.Label(top_r, text="Report Status: Draft", font=("Helvetica", 11, "bold"))
        self.lbl_report_status.pack(side=tk.LEFT)

        ttk.Button(top_r, text="✨ Generate Draft", command=self._generate_report_draft).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(top_r, text="✍️ Sign-Off Report", command=self._sign_off_report).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(top_r, text="💾 Export Markdown", command=self._export_report).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📊 Export CSV", command=self._export_csv_biomarkers).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📋 Export HTML Report", command=self._export_html_report).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top_r, text="📄 Export TalkBank (.cha)", command=self._export_cha_file).pack(side=tk.RIGHT, padx=4)

        # Ground Truth & Provenance Info Card
        prov_card = tk.Frame(frame, bg="#f8fafc", padx=10, pady=6, highlightthickness=1, highlightbackground="#e2e8f0")
        prov_card.pack(fill=tk.X, pady=(4, 6))
        tk.Label(
            prov_card,
            text="🔒 Ground Truth & Reliability Context: 100% Sourced directly from verified session utterances & deterministic LSA metrics. Clinician sign-off seals report with SHA-256 integrity hash.",
            font=("Helvetica", 9, "italic"),
            fg="#0369a1",
            bg="#f8fafc",
        ).pack(anchor=tk.W)

        lbl_n = ttk.Label(frame, text="Clinical Narrative (Language Sample Analysis):", font=("Helvetica", 10, "bold"))
        lbl_n.pack(anchor=tk.W, pady=(4, 2))
        self.txt_narrative = tk.Text(frame, height=6, font=("Helvetica", 10))
        self.txt_narrative.pack(fill=tk.X, pady=(0, 6))

        lbl_rec = ttk.Label(frame, text="Recommendations & Therapy Goals:", font=("Helvetica", 10, "bold"))
        lbl_rec.pack(anchor=tk.W, pady=(4, 2))
        self.txt_recommendations = tk.Text(frame, height=5, font=("Helvetica", 10))
        self.txt_recommendations.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    # --- Data Operations & Global Context Handlers ---
    def _on_case_search_typing(self, event: Any) -> None:
        query = self.entry_case_search.get().strip().lower()
        try:
            cases = self.client.list_cases()
        except LinguaLensAuthError as exc:
            self._handle_auth_error(exc)
            return
        except LinguaLensPermissionError as exc:
            self._handle_permission_error(exc)
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text="⚠️ Permission denied searching cases.")
            return
        except (LinguaLensApiError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=f"⚠️ Search failed: {exc}")
            return

        matched = []
        for c in cases:
            c_str = f"{c.get('case_id')} {c.get('child_id')} {c.get('clinical_notes')}".lower()
            if not query or query in c_str:
                matched.append(f"{c.get('case_id')} | {c.get('child_id')} ({c.get('age_months', '-')}m, {c.get('primary_language', 'th').upper()})")
        self.combo_global_case["values"] = matched or ["(No matching cases)"]
        if matched:
            self.combo_global_case.current(0)
            self._on_global_case_changed(None)

    def _refresh_all_data(self) -> bool:
        cases_ok = self._refresh_cases()
        sessions_ok = True
        if self.active_case_id:
            sessions_ok = self._refresh_sessions_for_active_case()

        if not cases_ok or not sessions_ok:
            self._refresh_children()
            messagebox.showerror(
                "Refresh Failed",
                "Failed to refresh cases, sessions, or transcript from repository / API. See status bar for details.",
            )
            return False

        def _on_all_success() -> None:
            messagebox.showinfo("Refreshed", "Data refreshed successfully from repository / API.")

        def _on_all_error(exc: Exception) -> None:
            messagebox.showerror(
                "Refresh Failed",
                f"Failed to refresh children from repository / API: {exc}",
            )

        self._refresh_children(on_success=_on_all_success, on_error=_on_all_error)
        return True

    def _load_initial_data(self) -> None:
        cases_ok = self._refresh_cases()
        if cases_ok and self.tree_cases.get_children():
            first_case = self.tree_cases.get_children()[0]
            self.tree_cases.selection_set(first_case)
            self._on_case_selected(None)
        self._refresh_children()

    def _refresh_cases(self) -> bool:
        try:
            cases = self.client.list_cases()
        except LinguaLensAuthError as exc:
            self._handle_auth_error(exc)
            return False
        except LinguaLensPermissionError as exc:
            self._handle_permission_error(exc)
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text="⚠️ Permission denied listing cases.")
            return False
        except (LinguaLensApiError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=f"⚠️ Failed to load cases: {exc}")
            return False

        for item in self.tree_cases.get_children():
            self.tree_cases.delete(item)

        case_options = []
        for c in cases:
            c_id = c.get("case_id")
            self.tree_cases.insert(
                "",
                tk.END,
                iid=c_id,
                values=(
                    c_id,
                    c.get("child_id"),
                    c.get("age_months", "-"),
                    c.get("primary_language", "th").upper(),
                    c.get("session_count", 0),
                    c.get("clinical_notes", ""),
                ),
            )
            case_options.append(f"{c_id} | {c.get('child_id')} ({c.get('age_months', '-')}m, {c.get('primary_language', 'th').upper()})")

        if case_options:
            self.combo_global_case["values"] = case_options
            if not self.combo_global_case.get() or self.combo_global_case.get().startswith("("):
                self.combo_global_case.current(0)
                self.active_case_id = cases[0]["case_id"]
        else:
            self.combo_global_case["values"] = ["(No Cases — Click ➕ New Case)"]
            self.combo_global_case.current(0)
            self.active_case_id = None
            self.combo_global_session["values"] = ["(No Active Case)"]
            self.combo_global_session.current(0)
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text="Active Context: Please create a Case to begin (Click ➕ New Case)")
            self._refresh_transcript_and_findings()

        return True

    def _on_global_case_changed(self, event: Any) -> None:
        sel_text = self.combo_global_case.get()
        if not sel_text or sel_text.startswith("("):
            return
        case_id = sel_text.split(" | ")[0].strip()

        # Transition back to legacy mode and clear V2 context
        self.current_mode = "legacy"
        self._child_selection_generation = getattr(self, "_child_selection_generation", 0) + 1
        self._current_child_request_id = ""
        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None
        self._cached_assessments = []

        if hasattr(self, "tree_children") and self.tree_children.winfo_exists():
            sel_children = self.tree_children.selection()
            if sel_children:
                self.tree_children.selection_remove(*sel_children)
        if hasattr(self, "combo_global_child") and self.combo_global_child.winfo_exists():
            self.combo_global_child.set("")
        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            for item in self.tree_assessments.get_children():
                self.tree_assessments.delete(item)

        self.active_case_id = case_id
        self._update_downstream_tabs_mode()

        # Sync Tab 1 treeview
        if case_id in self.tree_cases.get_children():
            self.tree_cases.selection_set(case_id)
            self.tree_cases.see(case_id)

        # Refresh sessions dropdown and table
        self._refresh_sessions_for_active_case()

    def _on_global_session_changed(self, event: Any) -> None:
        sel_text = self.combo_global_session.get()
        if not sel_text or sel_text.startswith("("):
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > (No Session)")
            self._refresh_transcript_and_findings()
            return
        session_id = sel_text.split(" | ")[0].strip()
        self.active_session_id = session_id

        # Sync Tab 1 treeview
        if session_id in self.tree_sessions.get_children():
            self.tree_sessions.selection_set(session_id)
            self.tree_sessions.see(session_id)

        self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        self._refresh_transcript_and_findings()

    def _invalidate_session_context(self, error_msg: str = "") -> None:
        """Clear active session state, treeview rows, and dependent transcript/findings."""
        for item in self.tree_sessions.get_children():
            self.tree_sessions.delete(item)
        self.active_session_id = None
        self.active_transcript = None
        err_display = f"⚠️ {error_msg}" if error_msg else "(No Active Session)"
        self.combo_global_session["values"] = [err_display]
        self.combo_global_session.current(0)
        self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id or '-'} > {err_display}")
        self._refresh_transcript_and_findings()

    def _refresh_sessions_for_active_case(self) -> bool | None:
        if self._is_v2_mode():
            self._guard_v2_mode("Session refresh")
            return None
        if not self.active_case_id:
            self._invalidate_session_context("(No Active Case)")
            return True

        try:
            sessions = self.client.list_sessions(self.active_case_id)
        except LinguaLensAuthError as exc:
            self._handle_auth_error(exc)
            self._invalidate_session_context("Authentication Error")
            return False
        except LinguaLensPermissionError as exc:
            self._handle_permission_error(exc)
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text="⚠️ Permission denied listing sessions.")
            self._invalidate_session_context("Permission Denied")
            return False
        except (LinguaLensApiError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                self.lbl_status.config(text=f"⚠️ Failed to load sessions: {exc}")
            self._invalidate_session_context(f"Failed to load sessions: {exc}")
            return False

        for item in self.tree_sessions.get_children():
            self.tree_sessions.delete(item)

        session_options = []
        for s in sessions:
            s_id = s.get("session_id")
            tr_badge = "✓ Ready" if s.get("transcript_id") else "None"
            rep_badge = "✓ Ready" if s.get("report_id") else "None"
            self.tree_sessions.insert(
                "",
                tk.END,
                iid=s_id,
                values=(
                    s_id,
                    s.get("session_date"),
                    s.get("session_number", 1),
                    s.get("status", "Intake"),
                    tr_badge,
                    rep_badge,
                ),
            )
            session_options.append(f"{s_id} | Date: {s.get('session_date')} ({s.get('status', 'Intake')})")

        if session_options:
            self.combo_global_session["values"] = session_options
            # Pick latest session by default
            self.combo_global_session.current(len(session_options) - 1)
            self.active_session_id = sessions[-1]["session_id"]
            if self.active_session_id in self.tree_sessions.get_children():
                self.tree_sessions.selection_set(self.active_session_id)
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        else:
            self.combo_global_session["values"] = ["(No sessions - Click ➕ New Session)"]
            self.combo_global_session.current(0)
            self.active_session_id = None
            self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > (No Session - Click ➕ New Session)")

        return self._refresh_transcript_and_findings()

    def _on_case_selected(self, event: Any) -> None:
        selected = self.tree_cases.selection()
        if not selected:
            return
        case_id = selected[0]

        # Transition back to legacy mode and clear V2 context
        self.current_mode = "legacy"
        self._child_selection_generation = getattr(self, "_child_selection_generation", 0) + 1
        self._current_child_request_id = ""
        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None
        self._cached_assessments = []

        if hasattr(self, "tree_children") and self.tree_children.winfo_exists():
            sel_children = self.tree_children.selection()
            if sel_children:
                self.tree_children.selection_remove(*sel_children)
        if hasattr(self, "combo_global_child") and self.combo_global_child.winfo_exists():
            self.combo_global_child.set("")
        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            for item in self.tree_assessments.get_children():
                self.tree_assessments.delete(item)

        self.active_case_id = case_id
        self._update_downstream_tabs_mode()

        # Sync Global Case Dropdown
        for idx, val in enumerate(self.combo_global_case["values"]):
            if val.startswith(self.active_case_id):
                self.combo_global_case.current(idx)
                break

        self._refresh_sessions_for_active_case()

    def _on_session_selected(self, event: Any) -> None:
        selected = self.tree_sessions.selection()
        if not selected:
            return
        self.active_session_id = selected[0]

        # Sync Global Session Dropdown
        for idx, val in enumerate(self.combo_global_session["values"]):
            if val.startswith(self.active_session_id):
                self.combo_global_session.current(idx)
                break

        self.lbl_ingest_ctx.config(text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}")
        self._refresh_transcript_and_findings()

    def _copy_chat_text(self) -> None:
        if self._guard_v2_mode("Copy transcript"):
            return
        chat_content = self.txt_chat_view.get("1.0", tk.END).strip()
        if chat_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(chat_content)
            messagebox.showinfo("Copied", "TalkBank / CHAT transcript copied to clipboard!")

    def _refresh_transcript_and_findings(self) -> bool:
        if self._is_v2_mode():
            return False
        # Invalidate existing transcript immediately
        self.active_transcript = None

        # Clear QA table
        for item in self.tree_utterances.get_children():
            self.tree_utterances.delete(item)

        # Clear TalkBank CHAT View
        self.txt_chat_view.config(state=tk.NORMAL)
        self.txt_chat_view.delete("1.0", tk.END)

        # Clear Metrics & Guidelines
        for item in self.tree_metrics.get_children():
            self.tree_metrics.delete(item)
        for item in self.tree_guidelines.get_children():
            self.tree_guidelines.delete(item)

        if not self.active_session_id:
            self.lbl_review_status.config(text="Transcript Status: No Active Session", foreground="gray")
            self.txt_chat_view.insert(tk.END, "% Please select or create a Case and Session to begin.", "header")
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Session", "กรุณาเลือกหรือสร้าง Case และ Session ก่อน"))
            self._draw_spider_diagram({})
            return True

        try:
            self.active_transcript = self.client.get_session_transcript(self.active_session_id)
        except LinguaLensAuthError as exc:
            self._handle_auth_error(exc)
            return False
        except (LinguaLensApiError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            self.lbl_review_status.config(text=f"Transcript Status: ⚠️ Failed to fetch transcript: {exc}", foreground="red")
            return False

        if not self.active_transcript or not self.active_transcript.get("utterances"):
            self.lbl_review_status.config(text="Transcript Status: No transcript loaded for this session", foreground="gray")
            self.txt_chat_view.insert(tk.END, "% No transcript recorded for this session yet.\n% Ingest audio or text in Tab 2 to begin.", "header")
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Data", "เซสชันนี้ยังไม่มีข้อมูลการประเมิน — กรุณา Ingest ใน Tab 2"))
            self._draw_spider_diagram({})
            return True

        attested = self.active_transcript.get("attested", False)
        status_txt = f"Transcript Status: {'✓ Attested / Signed-Off' if attested else '⚠️ Needs Clinician Review'}"
        self.lbl_review_status.config(text=status_txt, foreground="green" if attested else "#b45309")

        raw_cha = self.active_transcript.get("raw_cha")
        if raw_cha:
            # Authentic original CHAT file text directly rendered
            for line in raw_cha.splitlines():
                if line.startswith("@"):
                    self.txt_chat_view.insert(tk.END, line + "\n", "header")
                elif line.startswith("*CHI:"):
                    self.txt_chat_view.insert(tk.END, "*CHI:\t", "chi")
                    self.txt_chat_view.insert(tk.END, line[5:].strip() + "\n")
                elif line.startswith("*INV") or line.startswith("*MOT") or line.startswith("*FAT") or line.startswith("*EXP"):
                    spk_part = line.split(":", 1)[0]
                    rest = line.split(":", 1)[1] if ":" in line else ""
                    self.txt_chat_view.insert(tk.END, f"{spk_part}:\t", "inv")
                    self.txt_chat_view.insert(tk.END, rest.strip() + "\n")
                elif line.startswith("%"):
                    self.txt_chat_view.insert(tk.END, line + "\n", "tier")
                else:
                    self.txt_chat_view.insert(tk.END, line + "\n")
        else:
            # Build TalkBank CHAT content from utterances
            self.txt_chat_view.insert(tk.END, "@UTF8\n@Begin\n@Languages:\ttha, eng\n@Participants:\tCHI Child, INV Clinician\n", "header")
            self.txt_chat_view.insert(tk.END, f"@ID:\ttha|LinguaLens|CHI|4;00.|male|ASD||Child||\n@Media:\t{self.active_session_id}, audio\n\n", "header")

            for u in self.active_transcript["utterances"]:
                spk = u.get("speaker", "CHI")
                spk_tag = "chi" if spk == "CHI" else "inv"
                self.txt_chat_view.insert(tk.END, f"*{spk}:\t", spk_tag)
                self.txt_chat_view.insert(tk.END, f"{u.get('text')}")
                if u.get("start_time") is not None and u.get("end_time") is not None:
                    t_ms_start = int(u.get('start_time', 0.0) * 1000)
                    t_ms_end = int(u.get('end_time', 0.0) * 1000)
                    self.txt_chat_view.insert(tk.END, f" \x15{t_ms_start}_{t_ms_end}\x15", "time")
                self.txt_chat_view.insert(tk.END, "\n")
                flags = ", ".join(u.get("qa_flags", []))
                if flags and flags != "Clean":
                    self.txt_chat_view.insert(tk.END, f"%xqa:\t[{flags}]\n", "tier")

            self.txt_chat_view.insert(tk.END, "\n@End\n", "header")

        for idx, u in enumerate(self.active_transcript["utterances"], start=1):
            u_id = str(u.get("id") or f"utt-{idx}")
            if u.get("start_time") is not None and u.get("end_time") is not None:
                time_str = f"{u['start_time']:.1f} - {u['end_time']:.1f}"
            else:
                time_str = "-"
            flags = ", ".join(u.get("qa_flags", [])) or "Clean"
            spk = u.get("speaker", "CHI")

            self.tree_utterances.insert(
                "",
                tk.END,
                iid=u_id,
                values=(u_id, spk, time_str, u.get("text"), flags),
            )

        # Load findings (Full 15+ Features across 4 domains)
        findings = self.client.get_findings(self.active_session_id)
        metrics = findings.get("metrics", {})

        if not findings.get("has_data") or not metrics:
            self.tree_metrics.insert("", tk.END, values=("Info", "Status", "No Data", "เซสชันนี้ยังไม่มีข้อมูลการประเมิน — กรุณา Ingest ใน Tab 2"))
            self._draw_spider_diagram({})
            return True

        # Domain 1: Lexical & Syntactic Development
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "MLU-words (MLU-w)", str(metrics.get("mlu_words", "-")), "ความยาวประโยคเฉลี่ย (คำต่อประโยค)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "MLU-morphemes (MLU-m)", str(metrics.get("mlu_morphemes", "-")), "ความยาวประโยคเฉลี่ย (หน่วยคำต่อประโยค)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Type-Token Ratio (TTR)", str(metrics.get("ttr", "-")), "ความหลากหลายของคำศัพท์ (Lexical Diversity)"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Total Child Words (NTW)", str(metrics.get("total_child_words", "-")), "จำนวนคำทั้งหมดที่เด็กพูดในเซสชัน"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Unique Words (NDW)", str(metrics.get("unique_words_count", "-")), "จำนวนคำศัพท์ที่ไม่ซ้ำกัน"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Total Child Utterances", str(metrics.get("total_child_utterances", "-")), "จำนวนประโยคพูดของเด็กทั้งหมด"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Multi-Word Ratio (%)", f"{metrics.get('multi_word_ratio_pct', '-')}%", "สัดส่วนประโยคที่มีความยาวตั้งแต่ 2 คำขึ้นไป"))
        self.tree_metrics.insert("", tk.END, values=("1. Lexical & Syntactic", "Intelligibility Rate", f"{round(float(metrics.get('intelligibility_rate', 0.94))*100, 1)}%", "ความชัดเจนของคำพูดที่ฟังเข้าใจได้"))

        # Domain 2: Pragmatic & Conversational Interaction
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Turn-Taking Ratio", str(metrics.get("turn_taking_ratio", "-")), "อัตราการผลัดกันพูดในบทสนทนาโต้ตอบ"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Turn-Taking Count", str(metrics.get("turn_taking_count", "-")), "จำนวนรอบการสลับบทสนทนากับนักบำบัด"))
        turn_latency_str = f"{metrics.get('turn_taking_latency_sec')} s" if metrics.get("turn_taking_latency_sec") is not None else "-"
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Response Latency", turn_latency_str, "ระยะเวลาหน่วงก่อนเด็กตอบสนองบทสนทนา (Turn Latency)"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Question Asking Ratio", str(metrics.get("question_ratio", "-")), "สัดส่วนประโยคคำถามที่เด็กริเริ่มถาม"))
        self.tree_metrics.insert("", tk.END, values=("2. Pragmatics & Interaction", "Adult Utterances", str(metrics.get("adult_utterance_count", "-")), "จำนวนประโยคพูดของนักบำบัด/ผู้ปกครอง"))

        # Domain 3: Atypical Communication & Repetition Markers
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Echolalia Count", str(metrics.get("echolalia_count", 0)), "จำนวนครั้งที่พบการพูดตามทันที (Immediate Echolalia)"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Echolalia Ratio", str(metrics.get("echolalia_ratio", 0.0)), "สัดส่วนการพูดตามเทียบกับประโยคทั้งหมด"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Pronoun Reversal Count", str(metrics.get("pronoun_reversal_count", 0)), "การสลับการใช้สรรพนาม (เช่น เรียกตัวเองด้วยชื่อ/สรรพนามบุรุษที่ 2)"))
        self.tree_metrics.insert("", tk.END, values=("3. Atypical & Repetitive", "Unintelligible Ratio", f"{round(float(metrics.get('unintelligible_ratio', 0.06))*100, 1)}%", "สัดส่วนเสียงเปล่งที่ไม่เป็นคำพูด"))

        # Domain 4: Acoustic Prosody & Speech Dynamics
        if metrics.get("f0_median_hz") is not None:
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pitch Median (F0)", f"{metrics.get('f0_median_hz')} Hz", "ระดับความถี่เสียงหลัก (Fundamental Pitch)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pitch Range IQR (F0)", f"{metrics.get('f0_iqr_hz')} Hz", "ความแปรผันของระดับเสียงพูด (Prosody Dynamic Range)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Voiced Speech Ratio", f"{metrics.get('voiced_ratio_pct')}%", "สัดส่วนช่วงเวลาที่มีเสียงพูด (Voiced Duration)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Pause Ratio", f"{metrics.get('pause_ratio_pct')}%", "สัดส่วนช่วงเวลาหยุดพัก/ความเงียบ (Silence/Pause)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Speech Rate (WPM)", f"{metrics.get('speech_rate_wpm', '-')} wpm", "อัตราความเร็วในการพูด (Words Per Minute)"))
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Audio Duration", f"{metrics.get('audio_duration_sec')} s", "ความยาวรวมของเซสชันที่บันทึก"))
        else:
            self.tree_metrics.insert("", tk.END, values=("4. Acoustic & Prosody", "Acoustic Features (F0 / Prosody)", "N/A (No Audio)", "เซสชันนี้เป็นไฟล์ข้อความล้วน (.cha / text) — ไม่มีไฟล์เสียงบันทึก"))

        for g in findings.get("guideline_links", []):
            self.tree_guidelines.insert("", tk.END, values=(g.get("construct"), g.get("status"), g.get("description")))

        # Show/hide stale banner in Tab 4 Findings
        if hasattr(self, "frame_stale_findings") and hasattr(self, "findings_notebook"):
            if self.is_findings_stale:
                self.frame_stale_findings.pack(fill=tk.X, pady=(0, 8), before=self.findings_notebook)
            else:
                self.frame_stale_findings.pack_forget()

        # Redraw Spider Diagram with genuine metrics
        self._draw_spider_diagram(metrics)

        # Redraw Audio Waveform with updated speaker ranges
        self._redraw_waveform()

        # Refresh Longitudinal Cross-Session Trajectory View
        self._refresh_longitudinal_view()

        # Update timeline scrubber and playhead
        utts = (self.active_transcript or {}).get("utterances", [])
        total_dur = float(self._audio_waveform_duration or (utts[-1]["end_time"] if utts and utts[-1].get("end_time") else 10.0) or 10.0)
        if hasattr(self, "scale_scrubber"):
            self.scale_scrubber.config(to=max(1.0, total_dur))
            self.scale_scrubber.set(0.0)
        if hasattr(self, "lbl_time_total"):
            self.lbl_time_total.config(text=self._format_time(total_dur))
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text="00:00.0")
        self._playhead_time_sec = 0.0
        self._current_playback_offset_sec = 0.0
        self._draw_playhead(0.0)
        return True

    # --- Actions ---
    @staticmethod
    def _format_time(sec: float) -> str:
        """Format seconds into MM:SS.s clinical timeline format."""
        sec = max(0.0, float(sec))
        m = int(sec // 60)
        s = sec % 60
        return f"{m:02d}:{s:04.1f}"

    def _slice_audio_snippet(
        self,
        audio_path: str,
        start_sec: float,
        end_sec: float | None = None,
    ) -> str | None:
        """Extract a precise slice of audio to a temporary WAV file for playback."""
        if not audio_path or not os.path.exists(audio_path):
            return None
        import tempfile
        out_fd, out_path = tempfile.mkstemp(suffix="_lingualens_slice.wav")
        os.close(out_fd)

        try:
            import soundfile as sf
            info = sf.info(audio_path)
            sr = info.samplerate
            start_frame = max(0, int(start_sec * sr))
            stop_frame = min(info.frames, int(end_sec * sr)) if end_sec is not None else info.frames
            if stop_frame <= start_frame:
                return None
            data, _ = sf.read(audio_path, start=start_frame, stop=stop_frame)
            sf.write(out_path, data, sr)
            return out_path
        except Exception:
            try:
                import librosa
                import soundfile as sf
                dur = (end_sec - start_sec) if end_sec is not None else None
                y, sr = librosa.load(audio_path, sr=16000, offset=start_sec, duration=dur)
                sf.write(out_path, y, sr)
                return out_path
            except Exception:
                return None

    def _build_audio_segment_command(
        self,
        audio_path: str,
        start_sec: float | None = None,
        end_sec: float | None = None,
    ) -> tuple[list[str] | None, str | None]:
        """Build platform-specific CLI command to play an audio file or snippet with speed control.
        Returns (command_list, temp_slice_path_or_none).
        """
        if not audio_path:
            return None, None

        play_target = audio_path
        temp_slice = None

        if start_sec is not None and start_sec > 0.05:
            temp_slice = self._slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice
        elif start_sec is not None and end_sec is not None and end_sec > start_sec:
            temp_slice = self._slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice

        speed = float(getattr(self, "playback_speed", 1.0))

        if sys.platform == "darwin":
            cmd = ["afplay"]
            if abs(speed - 1.0) > 0.05:
                cmd.extend(["-r", str(round(speed, 2))])
            cmd.append(play_target)
            return cmd, temp_slice
        elif sys.platform.startswith("linux"):
            if abs(speed - 1.0) > 0.05:
                return ["ffplay", "-nodisp", "-autoexit", "-af", f"atempo={speed:.2f}", play_target], temp_slice
            if temp_slice:
                return ["aplay", play_target], temp_slice
            elif start_sec is not None:
                to_args = ["-to", str(end_sec)] if end_sec is not None else []
                return ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_sec), *to_args, audio_path], None
            return ["aplay", audio_path], None
        elif sys.platform == "win32":
            return ["powershell", "-c", f"(New-Object Media.SoundPlayer '{play_target}').PlaySync();"], temp_slice
        return None, None

    def _highlight_utterance(self, u_id: str | None) -> None:
        """Highlight an utterance in the Treeview and ensure it is scrolled into view."""
        if not hasattr(self, "tree_utterances"):
            return
        for item in self.tree_utterances.get_children():
            if item == u_id:
                self.tree_utterances.item(item, tags=("playing",))
                self.tree_utterances.see(item)
            else:
                self.tree_utterances.item(item, tags=())

    def _stop_playback(self) -> None:
        """Stop any active audio playback and clear highlights."""
        self._is_continuous_playing = False
        if hasattr(self, "btn_play_continuous"):
            self.btn_play_continuous.config(text="▶️ Play Audio with Follow")
        if hasattr(self, "lbl_playback_status"):
            self.lbl_playback_status.config(text="Audio: Stopped")
        if self._current_play_process:
            try:
                self._current_play_process.terminate()
            except Exception:
                pass
            self._current_play_process = None

        if hasattr(self, "_current_temp_slice") and self._current_temp_slice and os.path.exists(self._current_temp_slice):
            try:
                os.remove(self._current_temp_slice)
            except Exception:
                pass
            self._current_temp_slice = None

        # Clear tags
        if hasattr(self, "tree_utterances"):
            for item in self.tree_utterances.get_children():
                self.tree_utterances.item(item, tags=())
        # Clear scheduled word highlight timers
        if hasattr(self, "_word_highlight_timer_ids"):
            for tid in self._word_highlight_timer_ids:
                try:
                    self.root.after_cancel(tid)
                except Exception:
                    pass
            self._word_highlight_timer_ids.clear()
        # Reset word button text
        for btn, w_txt, w_start, _ in getattr(self, "_word_button_widgets", []):
            try:
                btn.config(text=f"{w_txt} [{w_start:.1f}s]")
            except Exception:
                pass

    def _safe_btn_config(self, b: ttk.Button, text_val: str) -> None:
        """Safely update button text without throwing if the widget was destroyed."""
        try:
            if b.winfo_exists():
                b.config(text=text_val)
        except Exception:
            pass

    def _play_audio_range(
        self,
        start_sec: float,
        end_sec: float | None = None,
        u_id: str | None = None,
        word_btn: ttk.Button | None = None,
        word_text: str = "",
    ) -> None:
        """Unified playback engine supporting Snippet, Continuous, Word, and Scrubber Seeking."""
        if self._guard_v2_mode("Audio playback"):
            return
        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        self._stop_playback()

        total_dur = float(self._audio_waveform_duration or 10.0)
        start_sec = max(0.0, min(total_dur, float(start_sec)))
        if end_sec is not None:
            end_sec = max(start_sec + 0.1, min(total_dur, float(end_sec)))

        self._current_playback_offset_sec = start_sec
        self._playhead_time_sec = start_sec
        self._playback_end_limit_sec = end_sec

        # Update Scrubber & Current Time Label
        if hasattr(self, "scale_scrubber") and not self._is_user_scrubbing:
            self.scale_scrubber.set(start_sec)
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(start_sec))

        # Redraw Playhead Needle on Waveform
        self._draw_playhead(start_sec)

        # Highlight utterance row
        if u_id:
            self._highlight_utterance(u_id)
            self.tree_utterances.see(u_id)
        else:
            active_u = None
            if self.active_transcript and "utterances" in self.active_transcript:
                for u in self.active_transcript["utterances"]:
                    u_start = float(u.get("start_time", 0.0))
                    u_end = float(u.get("end_time", u_start + 2.0))
                    if u_start <= start_sec <= u_end:
                        active_u = u
                        break
            if active_u:
                self._highlight_utterance(active_u["id"])
                self.tree_utterances.see(active_u["id"])
            else:
                self._highlight_utterance(None)

        if word_btn:
            self._safe_btn_config(word_btn, f"🔊 {word_text}")

        # Schedule word highlights if playing utterance snippet
        speed = float(getattr(self, "playback_speed", 1.0)) or 1.0
        if u_id and self.active_transcript:
            for u in self.active_transcript.get("utterances", []):
                if u["id"] == u_id:
                    words = u.get("words", [])
                    if words and self._word_button_widgets:
                        for btn, w_txt, w_start, w_end in self._word_button_widgets:
                            t_start_ms = max(0, int(((w_start - start_sec) / speed) * 1000))
                            t_end_ms = max(t_start_ms + 50, int(((w_end - start_sec) / speed) * 1000))
                            tid1 = self.root.after(
                                t_start_ms,
                                lambda b=btn, txt=w_txt: self._safe_btn_config(b, f"▶️ {txt}"),
                            )
                            tid2 = self.root.after(
                                t_end_ms,
                                lambda b=btn, txt=w_txt, s=w_start: self._safe_btn_config(b, f"{txt} [{s:.1f}s]"),
                            )
                            self._word_highlight_timer_ids.extend([tid1, tid2])
                    break

        cmd, temp_slice = self._build_audio_segment_command(self.active_audio_path, start_sec, end_sec)
        self._current_temp_slice = temp_slice
        if not cmd:
            messagebox.showerror("Audio Playback", "Audio playback is not supported on this platform.")
            return

        try:
            self._current_play_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except Exception as err:
            messagebox.showerror("Audio Playback", f"Could not launch audio playback: {err}")
            return

        self._is_continuous_playing = True
        self._playback_start_wall_time = time.time()
        if hasattr(self, "btn_play_continuous"):
            self.btn_play_continuous.config(text="⏸️ Pause")
        self._poll_continuous_playback_progress()

    def _play_selected_utterance(self) -> None:
        """Play audio snippet for the selected utterance with synchronized word highlights."""
        if self._guard_v2_mode("Audio playback"):
            return None
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            messagebox.showinfo("Playback", "Please select an utterance from the table first.")
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        u_id = sel[0]
        selected_u = None
        for u in self.active_transcript.get("utterances", []):
            if u["id"] == u_id:
                selected_u = u
                break

        if not selected_u:
            return

        start_sec = float(selected_u.get("start_time", 0.0))
        end_sec = float(selected_u.get("end_time", start_sec + 2.0))
        self._play_audio_range(start_sec=start_sec, end_sec=end_sec, u_id=u_id)

    def _play_word_segment(
        self,
        start_sec: float,
        end_sec: float,
        word_text: str = "",
        btn_widget: ttk.Button | None = None,
    ) -> None:
        """Play a precise word audio segment with word button highlighting."""
        if self._guard_v2_mode("Audio playback"):
            return None
        self._play_audio_range(start_sec=start_sec, end_sec=end_sec, word_btn=btn_widget, word_text=word_text)

    def _toggle_continuous_playback(self) -> None:
        """Toggle continuous session playback with real-time sentence tracking and highlighting."""
        if self._guard_v2_mode("Continuous playback"):
            return None
        if self._is_continuous_playing:
            self._stop_playback()
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            messagebox.showinfo(
                "Audio Playback",
                "No audio recording loaded for this session (text-only transcript mode).",
            )
            return

        # Start or resume from current playhead offset
        offset = float(getattr(self, "_playhead_time_sec", 0.0))
        total_dur = float(self._audio_waveform_duration or 10.0)
        if offset >= total_dur - 0.2:
            offset = 0.0
            self._playhead_time_sec = 0.0

        self._play_audio_range(start_sec=offset, end_sec=None)

    def _poll_continuous_playback_progress(self) -> None:
        """Periodically check audio elapsed time and highlight the active utterance in real-time."""
        if not self._is_continuous_playing or not self._current_play_process:
            return

        speed = float(getattr(self, "playback_speed", 1.0)) or 1.0
        elapsed = (time.time() - self._playback_start_wall_time) * speed
        current_audio_time = self._current_playback_offset_sec + elapsed
        total_dur = float(self._audio_waveform_duration or 10.0)

        # Check if snippet end limit reached
        if self._playback_end_limit_sec is not None and current_audio_time >= self._playback_end_limit_sec:
            self._stop_playback()
            self._playhead_time_sec = self._playback_end_limit_sec
            if hasattr(self, "scale_scrubber"):
                self.scale_scrubber.set(self._playback_end_limit_sec)
            if hasattr(self, "lbl_time_current"):
                self.lbl_time_current.config(text=self._format_time(self._playback_end_limit_sec))
            self._draw_playhead(self._playback_end_limit_sec)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(text="Audio: Finished snippet playback.")
            return

        # Check if process finished
        poll_res = self._current_play_process.poll()
        if poll_res is not None:
            self._stop_playback()
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(text="Audio: Finished full playback.")
            return

        # Update Scrubber & Current Time Label
        if not self._is_user_scrubbing and hasattr(self, "scale_scrubber"):
            self.scale_scrubber.set(min(total_dur, current_audio_time))
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(current_audio_time))

        # Update Waveform Playhead Needle
        self._draw_playhead(current_audio_time)

        # Find active utterance at this second
        active_u = None
        if self.active_transcript and "utterances" in self.active_transcript:
            for u in self.active_transcript["utterances"]:
                u_start = float(u.get("start_time", 0.0))
                u_end = float(u.get("end_time", u_start + 2.0))
                if u_start <= current_audio_time <= u_end:
                    active_u = u
                    break

        if active_u:
            u_id = active_u["id"]
            self._highlight_utterance(u_id)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(current_audio_time)}] Utterance #{u_id}: *{active_u.get('speaker', 'CHI')}: {active_u.get('text', '')}"
                )
        else:
            self._highlight_utterance(None)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(current_audio_time)}] (Pause / Silence)"
                )

        self.root.after(33, self._poll_continuous_playback_progress)

    def _browse_audio_file(self) -> None:
        if self._guard_v2_mode("Audio file selection"):
            return
        f_path = filedialog.askopenfilename(
            title="Select Audio or Video File",
            filetypes=[("Media Files", "*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg"), ("All Files", "*.*")],
        )
        if f_path:
            self.entry_audio_path.delete(0, tk.END)
            self.entry_audio_path.insert(0, f_path)


    def _build_ingest_progress_dialog(self, audio_filename: str) -> tk.Toplevel:
        """Construct a real-time progress dialog with smooth progress bar and stage feedback."""
        win = tk.Toplevel(self.root)
        win.title("🎙️ Processing Audio — LinguaLens")
        win.geometry("480x210")
        win.minsize(440, 190)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        # Center dialog relative to main window
        try:
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_w = self.root.winfo_width()
            root_h = self.root.winfo_height()
            dlg_x = root_x + (root_w - 480) // 2
            dlg_y = root_y + (root_h - 210) // 2
            win.geometry(f"480x210+{max(0, dlg_x)}+{max(0, dlg_y)}")
        except Exception:
            pass

        frame = tk.Frame(win, bg="#f8fafc", padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # Header Title
        tk.Label(
            frame,
            text="🎙️ Ingesting Audio & Transcribing Speech",
            font=("Helvetica", 12, "bold"),
            fg="#0f766e",
            bg="#f8fafc",
        ).pack(anchor=tk.W)

        # File Subtitle
        tk.Label(
            frame,
            text=f"File: {audio_filename}",
            font=("Helvetica", 9),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(anchor=tk.W, pady=(2, 10))

        # Stage Description
        self._dlg_lbl_stage = tk.Label(
            frame,
            text="🚀 Initializing ASR and acoustic pipeline...",
            font=("Helvetica", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc",
        )
        self._dlg_lbl_stage.pack(anchor=tk.W, pady=(0, 6))

        # Progress Bar
        self._dlg_bar_progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="determinate",
            length=440,
        )
        self._dlg_bar_progress.pack(fill=tk.X, pady=(0, 6))
        self._dlg_bar_progress["value"] = 5

        # Percentage Text
        self._dlg_lbl_pct = tk.Label(
            frame,
            text="5% Completed",
            font=("Helvetica", 9),
            fg="#0f766e",
            bg="#f8fafc",
        )
        self._dlg_lbl_pct.pack(anchor=tk.W)

        return win

    def _show_ingest_progress_dialog(self, audio_filename: str) -> None:
        """Show the modal progress dialog and activate the inline progress panel in Tab 2."""
        if hasattr(self, "frame_ingest_progress"):
            self.frame_ingest_progress.pack(fill=tk.X, pady=(10, 0))
            self.bar_ingest_progress["value"] = 5
            self.lbl_ingest_percent.config(text="5% Completed")
            self.lbl_ingest_stage.config(text="🚀 Initializing pipeline...")

        try:
            self._progress_dialog = self._build_ingest_progress_dialog(audio_filename)
        except Exception:
            self._progress_dialog = None

    def _update_ingest_progress(self, pct: float, msg: str) -> None:
        """Update both the progress dialog and the inline progress indicator with percentage and stage message."""
        val = max(0, min(100, int(pct * 100)))

        # Update modal dialog if active
        if self._progress_dialog and self._progress_dialog.winfo_exists():
            if self._dlg_bar_progress and self._dlg_bar_progress.winfo_exists():
                self._dlg_bar_progress["value"] = val
            if self._dlg_lbl_pct and self._dlg_lbl_pct.winfo_exists():
                self._dlg_lbl_pct.config(text=f"{val}% Completed")
            if self._dlg_lbl_stage and self._dlg_lbl_stage.winfo_exists():
                self._dlg_lbl_stage.config(text=msg)

        # Update inline progress bar in Tab 2
        if hasattr(self, "bar_ingest_progress") and self.bar_ingest_progress.winfo_exists():
            self.bar_ingest_progress["value"] = val
        if hasattr(self, "lbl_ingest_percent") and self.lbl_ingest_percent.winfo_exists():
            self.lbl_ingest_percent.config(text=f"{val}% Completed")
        if hasattr(self, "lbl_ingest_stage") and self.lbl_ingest_stage.winfo_exists():
            self.lbl_ingest_stage.config(text=msg)

        # Update status bar
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⏳ [{val}%] {msg}")

    def _close_ingest_progress_dialog(self) -> None:
        """Dismiss the modal progress dialog and hide the inline progress panel."""
        if self._progress_dialog and self._progress_dialog.winfo_exists():
            try:
                self._progress_dialog.grab_release()
                self._progress_dialog.destroy()
            except Exception:
                pass
            self._progress_dialog = None

        if hasattr(self, "frame_ingest_progress") and self.frame_ingest_progress.winfo_exists():
            try:
                self.frame_ingest_progress.pack_forget()
            except Exception:
                pass

    def _process_audio_file(self) -> threading.Thread | None:
        if self._guard_v2_mode("Audio processing"):
            return None
        if not self.active_case_id:
            from datetime import date
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Audio ingestion case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()

        # If no session is active, auto-create a new session for this case
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(
                self.active_case_id,
                date.today().isoformat(),
                "Audio ingestion session",
            )
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        f_path = self.entry_audio_path.get().strip()
        if not f_path or not os.path.exists(f_path):
            messagebox.showerror("Error", f"File does not exist: {f_path}")
            return None

        self.active_audio_path = f_path
        f_name = Path(f_path).name
        self._show_ingest_progress_dialog(f_name)

        def _do_ingest_audio():
            def _on_prog(p: float, msg: str) -> None:
                self._async_queue.put((lambda pct=p, m=msg: self._update_ingest_progress(pct, m), None))
            return self.client.ingest_audio_file(self.active_session_id, f_path, progress_callback=_on_prog)

        def _on_audio_success(transcript: dict[str, Any]) -> None:
            self._close_ingest_progress_dialog()
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo(
                "Success",
                f"Audio processed successfully for Session: {self.active_session_id}!\nAcoustic features & transcript extracted.",
            )
            self._refresh_transcript_and_findings()
            self.notebook.select(2)  # Jump to Review tab

        def _on_audio_error(exc: Exception) -> None:
            self._close_ingest_progress_dialog()
            messagebox.showerror("Audio Processing Failed", str(exc))

        return self._run_async_task(
            target=_do_ingest_audio,
            on_success=_on_audio_success,
            on_error=_on_audio_error,
            busy_msg=f"Processing audio {f_name}... (Extracting F0 & transcribing)",
        )

    def _batch_ingest_audio_files(self) -> None:
        """Batch ingest a queue of multiple audio files into separate sessions."""
        if self._guard_v2_mode("Batch audio ingestion"):
            return
        if not self.active_case_id:

            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Batch case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()

        f_paths = filedialog.askopenfilenames(
            title="Select Audio Recordings for Batch Ingestion",
            filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.mp4 *.flac *.aac"), ("All Files", "*.*")],
        )
        if not f_paths:
            return

        batch_win = tk.Toplevel(self.root)
        batch_win.title("📦 Batch Audio Ingestion Queue")
        batch_win.geometry("540x380")
        batch_win.transient(self.root)
        batch_win.grab_set()

        frame = tk.Frame(batch_win, bg="#f8fafc", padx=16, pady=14)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text=f"📦 Ingesting {len(f_paths)} Audio Files into Case {self.active_case_id}", font=("Helvetica", 11, "bold"), fg="#0f766e", bg="#f8fafc").pack(anchor=tk.W)

        bar_batch = ttk.Progressbar(frame, orient="horizontal", mode="determinate", length=480)
        bar_batch.pack(fill=tk.X, pady=(10, 6))
        bar_batch["maximum"] = len(f_paths)
        bar_batch["value"] = 0

        lbl_batch_status = tk.Label(frame, text=f"Queue ready: {len(f_paths)} files pending...", font=("Helvetica", 9), fg="#475569", bg="#f8fafc")
        lbl_batch_status.pack(anchor=tk.W, pady=(0, 8))

        tree_queue = ttk.Treeview(frame, columns=("file", "status"), show="headings", height=7)
        tree_queue.heading("file", text="Audio File Name")
        tree_queue.heading("status", text="Status")
        tree_queue.column("file", width=340)
        tree_queue.column("status", width=120, anchor=tk.CENTER)
        tree_queue.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        for idx, p in enumerate(f_paths):
            tree_queue.insert("", tk.END, iid=str(idx), values=(Path(p).name, "Pending ⏳"))

        def _do_batch_worker():
            fail_count = 0
            for idx, p_str in enumerate(f_paths):
                f_name = Path(p_str).name
                self.root.after_idle(lambda i=idx, n=f_name: (
                    tree_queue.item(str(i), values=(n, "Processing 🚀")),
                    lbl_batch_status.config(text=f"Processing {i+1}/{len(f_paths)}: {n}..."),
                    bar_batch.config(value=i)
                ))
                try:
                    from datetime import date
                    s = self.client.create_session(
                        self.active_case_id,
                        date.today().isoformat(),
                        f"Batch Session: {f_name}"
                    )
                    s_id = s["session_id"]
                    self.client.ingest_audio_file(
                        s_id,
                        p_str,
                        model_size="small",
                        strategy="auto",
                    )
                    self.root.after_idle(lambda i=idx, n=f_name: tree_queue.item(str(i), values=(n, "Completed ✅")))
                except Exception as exc:
                    fail_count += 1
                    self.root.after_idle(lambda i=idx, n=f_name, e=exc: tree_queue.item(str(i), values=(n, f"Error: {e} ❌")))

            def _on_batch_finished(fc=fail_count):
                bar_batch.config(value=len(f_paths))
                self._refresh_sessions_for_active_case()
                self._refresh_longitudinal_view()
                if fc > 0:
                    lbl_batch_status.config(text=f"⚠️ Batch finished with {fc} error(s) out of {len(f_paths)} files.")
                    messagebox.showwarning(
                        "Batch Completed with Errors",
                        f"Batch ingestion finished with {fc} failure(s) out of {len(f_paths)} files.\nCheck queue table for details.",
                    )
                else:
                    lbl_batch_status.config(text=f"🎉 All {len(f_paths)} audio files processed successfully!")
                    messagebox.showinfo(
                        "Batch Complete",
                        f"Batch ingestion complete for {len(f_paths)} sessions!\nCheck Tab 4 for Longitudinal Trajectory.",
                    )

            self.root.after_idle(_on_batch_finished)

        threading.Thread(target=_do_batch_worker, daemon=True).start()


    def _refresh_longitudinal_view(self) -> None:
        """Populate the Longitudinal Trajectory tab with metrics across all sessions for active case."""
        if not hasattr(self, "tree_longitudinal") or not self.tree_longitudinal.winfo_exists():
            return
        for item in self.tree_longitudinal.get_children():
            self.tree_longitudinal.delete(item)

        if not self.active_case_id:
            if hasattr(self, "lbl_longitudinal_summary"):
                self.lbl_longitudinal_summary.config(text="No active case selected.")
            return

        sessions = self.client.list_sessions(self.active_case_id)
        if not sessions:
            if hasattr(self, "lbl_longitudinal_summary"):
                self.lbl_longitudinal_summary.config(text="No sessions recorded yet for this case.")
            return

        session_metrics_list = []
        for s in sessions:
            s_id = s["session_id"]
            s_date = s.get("session_date", "N/A")
            tr = self.client.get_session_transcript(s_id)
            findings = self.client.get_findings(s_id)
            metrics = findings.get("metrics", {})
            utts = tr.get("utterances", []) if tr else []
            chi_turns = sum(1 for u in utts if u.get("speaker") == "CHI")
            mlu = metrics.get("mlu_words", metrics.get("mlu", "-"))
            ttr = metrics.get("ttr", metrics.get("type_token_ratio", "-"))
            f0 = metrics.get("f0_median_hz", "-")
            status = "Attested ✅" if tr and tr.get("attested") else "Draft ⏳"

            self.tree_longitudinal.insert(
                "", tk.END, iid=s_id,
                values=(s_date, s_id, len(utts), chi_turns, mlu, ttr, f0, status)
            )
            if utts:
                session_metrics_list.append({
                    "session_id": s_id,
                    "date": s_date,
                    "utterances": len(utts),
                    "chi_turns": chi_turns,
                    "mlu_w": mlu,
                    "ttr": ttr,
                    "f0_median": f0,
                })

        if hasattr(self, "lbl_longitudinal_summary"):
            if len(session_metrics_list) > 1:
                first = session_metrics_list[0]
                latest = session_metrics_list[-1]
                self.lbl_longitudinal_summary.config(
                    text=f"📊 Longitudinal Trajectory: {len(session_metrics_list)} sessions recorded | Baseline: {first['date']} ({first['utterances']} utts) ➔ Latest: {latest['date']} ({latest['utterances']} utts)"
                )
            else:
                self.lbl_longitudinal_summary.config(
                    text=f"📊 1 session recorded for Case {self.active_case_id}. Ingest more sessions to visualize longitudinal trajectory."
                )

    def _on_longitudinal_session_selected(self, event: Any) -> None:
        """When a clinician clicks a historical session in the longitudinal table, load that session."""
        sel = self.tree_longitudinal.selection()
        if sel:
            s_id = sel[0]
            self.active_session_id = s_id
            self._refresh_sessions_for_active_case()
            self._on_session_selected(None)

    def _load_demo_dialogue(self) -> threading.Thread | None:
        if self._guard_v2_mode("Ingesting demo dialogue"):
            return None
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Sample case for dialogue demo")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "Demo session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        self.active_audio_path = None
        demo_txt = (
            "INV: สวัสดีครับ วันนี้เรามาเล่นของเล่นด้วยกันนะ\n"
            "CHI: เล่น รถ\n"
            "INV: อยากได้รถคันไหนครับ มีสีแดงกับสีน้ำเงิน\n"
            "CHI: แดง รถ แดง ไป\n"
            "INV: รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น\n"
            "CHI: ไป หา แม่\n"
            "INV: เดี๋ยวเล่นเสร็จแล้วไปหาคุณแม่ด้วยกันนะครับ"
        )

        def _do_ingest():
            return self.client.ingest_transcript_text(self.active_session_id, demo_txt)

        def _on_success(transcript: dict[str, Any]) -> None:
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo("Success", f"Sample Thai dialogue ingested into Session {self.active_session_id}!")
            self._refresh_transcript_and_findings()
            self.notebook.select(2)

        return self._run_async_task(
            target=_do_ingest,
            on_success=_on_success,
            busy_msg="Ingesting demo dialogue...",
        )

    def _browse_text_file(self) -> threading.Thread | None:
        if self._guard_v2_mode("Text file ingestion"):
            return None
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "File ingestion case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "File session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        f_path = filedialog.askopenfilename(
            title="Select CHAT or Text File",
            filetypes=[("Transcript Files", "*.cha *.txt"), ("All Files", "*.*")],
        )
        if f_path:
            self.active_audio_path = None
            with open(f_path, "r", encoding="utf-8") as f:
                content = f.read()

            def _do_ingest_file():
                return self.client.ingest_transcript_text(self.active_session_id, content)

            def _on_file_success(transcript: dict[str, Any]) -> None:
                self.active_transcript = transcript
                self.is_findings_stale = False
                messagebox.showinfo("Success", f"Ingested transcript from {Path(f_path).name}")
                self._refresh_transcript_and_findings()
                self.notebook.select(2)

            return self._run_async_task(
                target=_do_ingest_file,
                on_success=_on_file_success,
                busy_msg=f"Parsing {Path(f_path).name}...",
            )
        return None

    def _ingest_typed_text(self) -> threading.Thread | None:
        if self._guard_v2_mode("Manual text ingestion"):
            return None
        if not self.active_case_id:
            new_c = self.client.create_case(f"C-{len(self.client.list_cases()) + 1:03d}", "2021-05", "th", "Manual text case")
            self.active_case_id = new_c["case_id"]
            self._refresh_cases()
        if not self.active_session_id:
            from datetime import date
            new_s = self.client.create_session(self.active_case_id, date.today().isoformat(), "Manual session")
            self.active_session_id = new_s["session_id"]
            self._refresh_sessions_for_active_case()

        raw = self.txt_manual.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Warning", "Please enter dialogue text first.")
            return None

        self.active_audio_path = None

        def _do_ingest_text():
            return self.client.ingest_transcript_text(self.active_session_id, raw)

        def _on_text_success(transcript: dict[str, Any]) -> None:
            self.active_transcript = transcript
            self.is_findings_stale = False
            messagebox.showinfo("Success", "Typed transcript ingested!")
            self._refresh_transcript_and_findings()
            self.notebook.select(2)

        return self._run_async_task(
            target=_do_ingest_text,
            on_success=_on_text_success,
            busy_msg="Processing typed text...",
        )

    def _on_utterance_selected(self, event: Any) -> None:
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            return
        u_id = sel[0]
        selected_u = None
        for u in self.active_transcript["utterances"]:
            if u["id"] == u_id:
                selected_u = u
                self.combo_spk.set(u.get("speaker", "CHI"))
                self.entry_u_text.delete(0, tk.END)
                self.entry_u_text.insert(0, u.get("text", ""))
                break

        if not selected_u or not hasattr(self, "container_word_buttons"):
            return

        # Cancel any pending word highlight timers before clearing buttons
        if hasattr(self, "_word_highlight_timer_ids"):
            for tid in self._word_highlight_timer_ids:
                try:
                    self.root.after_cancel(tid)
                except Exception:
                    pass
            self._word_highlight_timer_ids.clear()

        # Clear existing word timing buttons
        for child in self.container_word_buttons.winfo_children():
            child.destroy()
        self._word_button_widgets.clear()

        words = selected_u.get("words", [])
        if words:
            for w in words:
                w_txt = str(w.get("text", "")).strip()
                if not w_txt:
                    continue
                w_s = float(w.get("start_time", 0.0))
                w_e = float(w.get("end_time", 0.0))
                btn = ttk.Button(
                    self.container_word_buttons,
                    text=f"{w_txt} [{w_s:.1f}s]",
                )
                btn.config(command=lambda s=w_s, e=w_e, t=w_txt, b=btn: self._play_word_segment(s, e, t, b))
                btn.pack(side=tk.LEFT, padx=2)
                self._word_button_widgets.append((btn, w_txt, w_s, w_e))
        else:
            ttk.Label(
                self.container_word_buttons,
                text="No sub-word alignments available for this utterance.",
                font=("Helvetica", 9, "italic"),
                foreground="#64748b",
            ).pack(side=tk.LEFT)

    def _save_utterance_edit(self) -> None:
        if self._guard_v2_mode("Editing utterance"):
            return
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            return
        u_id = sel[0]
        new_spk = self.combo_spk.get()
        new_text = self.entry_u_text.get().strip()

        self.active_transcript = self.client.update_utterance(
            self.active_transcript["transcript_id"], u_id, new_text, new_spk
        )
        self.is_findings_stale = True
        self._refresh_transcript_and_findings()
        messagebox.showinfo(
            "Saved",
            "Utterance updated successfully.\n⚠️ Findings & Report marked as STALE until recalculated.",
        )

    def _on_tree_key_press(self, event: Any) -> str | None:
        """Handle keyboard quick tagging (C=CHI, I=INV, M=MOT) and spacebar playback."""
        sel = self.tree_utterances.selection()
        if not sel or not self.active_transcript:
            return None

        char = (event.char or "").lower()
        if char in ("c", "i", "m"):
            spk_map = {"c": "CHI", "i": "INV", "m": "MOT"}
            target_spk = spk_map[char]
            u_id = sel[0]

            curr_text = ""
            for u in self.active_transcript.get("utterances", []):
                if u["id"] == u_id:
                    curr_text = u.get("text", "")
                    break

            self.active_transcript = self.client.update_utterance(
                self.active_transcript["transcript_id"], u_id, curr_text, target_spk
            )
            self.is_findings_stale = True

            # Update Treeview item visually
            for item in self.tree_utterances.get_children():
                if item == u_id:
                    vals = list(self.tree_utterances.item(item, "values"))
                    if len(vals) >= 2:
                        vals[1] = target_spk
                        self.tree_utterances.item(item, values=vals)
                    break

            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"🏷️ Marked #{u_id} as *{target_spk}* (Press C/I/M on next row)"
                )

            # Move to next row
            all_children = self.tree_utterances.get_children()
            try:
                curr_idx = all_children.index(u_id)
                if curr_idx + 1 < len(all_children):
                    next_id = all_children[curr_idx + 1]
                    self.tree_utterances.selection_set(next_id)
                    self.tree_utterances.see(next_id)
                    self._on_utterance_selected(None)
            except Exception:
                pass

            return "break"
        elif event.keysym == "space":
            self._play_selected_utterance()
            return "break"
        return None

    def _auto_refine_speakers(self) -> None:
        """Run clinical dialogue flow and turn-taking refiner on the current transcript."""
        if self._guard_v2_mode("Auto-refining speakers"):
            return
        tr_id = self.active_transcript.get("transcript_id") or self.active_transcript.get("id") if self.active_transcript else None
        if not self.active_transcript or not tr_id:
            messagebox.showinfo("Auto-Refine", "No transcript loaded to refine.")
            return

        updated = self.client.auto_refine_speakers(tr_id)
        if updated:
            self.active_transcript = updated
            self.is_findings_stale = True
            self._refresh_transcript_and_findings()
            messagebox.showinfo(
                "Speakers Refined",
                "✅ Speakers refined by clinical dialogue flow:\n"
                "• Examiner commands, questions, and praise assigned to INV/MOT\n"
                "• Child answers following prompts assigned to CHI\n"
                "⚠️ Findings marked as STALE until recalculated."
            )

    def _swap_speakers(self) -> None:
        """Swap CHI and Adult (INV/MOT) roles across all utterances."""
        if self._guard_v2_mode("Swapping speakers"):
            return
        tr_id = self.active_transcript.get("transcript_id") or self.active_transcript.get("id") if self.active_transcript else None
        if not self.active_transcript or not tr_id:
            messagebox.showinfo("Swap Speakers", "No transcript loaded to swap.")
            return

        updated = self.client.swap_speakers(tr_id, spk1="CHI", spk2="INV")
        if updated:
            self.active_transcript = updated
            self.is_findings_stale = True
            self._refresh_transcript_and_findings()
            messagebox.showinfo(
                "Speakers Swapped",
                "🔄 All CHI and Adult (INV/MOT) speaker roles swapped across this session.\n"
                "⚠️ Findings marked as STALE until recalculated."
            )

    def _recalculate_findings(self) -> None:
        """Re-extract and compute findings after transcript modifications."""
        if not self.active_session_id:
            return
        self.is_findings_stale = False
        self._refresh_transcript_and_findings()
        messagebox.showinfo("Findings Updated", "Findings and metrics recalculated successfully from latest transcript.")

    def _attest_transcript(self) -> None:
        if self._guard_v2_mode("Attesting transcript"):
            return
        if not self.active_transcript:
            return
        self.active_transcript = self.client.attest_transcript(
            self.active_transcript["transcript_id"], "Kru Aum (SLP)"
        )
        messagebox.showinfo("Sign-Off Complete", "Transcript attested by clinician!")
        self._refresh_transcript_and_findings()
        self.notebook.select(3)  # Jump to Findings tab

    def _generate_report_draft(self) -> None:
        if self._guard_v2_mode("Generating report"):
            return
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning(
                "No Data Available",
                "Cannot generate progress report: No transcript or dialogue recorded for this session yet.\n"
                "Please ingest audio or transcript in Tab 2 first.",
            )
            return
        rep = self.client.draft_report(self.active_session_id, "Standard Progress LSA")
        self.active_report = rep
        self.txt_narrative.delete("1.0", tk.END)
        self.txt_narrative.insert("1.0", rep.get("narrative", ""))
        self.txt_recommendations.delete("1.0", tk.END)
        self.txt_recommendations.insert("1.0", rep.get("recommendations", ""))
        self.lbl_report_status.config(text=f"Report Status: {rep.get('status')}", foreground="#0284c7")

    def _sign_off_report(self) -> None:
        if self._guard_v2_mode("Signing off report"):
            return
        if not self.active_report:
            self._generate_report_draft()
        if not self.active_report:
            return
        if self.is_findings_stale:
            proceed = messagebox.askyesno(
                "Stale Data Warning",
                "Transcript was modified after the last findings calculation.\n"
                "Are you sure you want to sign-off before recalculating?",
            )
            if not proceed:
                return
        rep = self.client.sign_off_report(self.active_report["report_id"], "Kru Aum (SLP)")
        self.active_report = rep
        sha = rep.get("sha256_hash", "")[:16]
        self.lbl_report_status.config(
            text=f"Report Status: Signed Off (SHA-256: {sha}...)",
            foreground="green",
        )
        messagebox.showinfo("Signed Off", f"Report signed off and locked!\nSHA-256: {rep.get('sha256_hash')}")

    def _export_report(self) -> None:
        if self._guard_v2_mode("Exporting report"):
            return
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save Clinical Report",
            defaultextension=".md",
            initialfile=f"report_{self.active_session_id}.md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        findings = self.client.get_findings(self.active_session_id)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"# LinguaLens Progress Report\n\n")
            f.write(f"- Case: {self.active_case_id}\n- Session: {self.active_session_id}\n\n")
            f.write(f"## Metrics\n\n")
            for k, v in findings.get("metrics", {}).items():
                f.write(f"- **{k}:** {v}\n")
            f.write(f"\n## Narrative\n\n{self.txt_narrative.get('1.0', tk.END)}\n")
            f.write(f"## Recommendations\n\n{self.txt_recommendations.get('1.0', tk.END)}\n")
        messagebox.showinfo("Exported", f"Saved report to: {out_file}")

    def _on_speed_changed(self, event: Any) -> None:
        """Update playback speed multiplier from toolbar combobox."""
        if not hasattr(self, "combo_speed"):
            return
        raw_val = self.combo_speed.get().replace("x", "").strip()
        try:
            self.playback_speed = float(raw_val)
        except ValueError:
            self.playback_speed = 1.0

    def _toggle_pitch_overlay(self) -> None:
        """Toggle visualization of F0 fundamental pitch contour on waveform canvas."""
        self._show_pitch_overlay = not self._show_pitch_overlay
        if hasattr(self, "btn_toggle_pitch"):
            self.btn_toggle_pitch.config(
                text="📈 F0 Curve: ON" if self._show_pitch_overlay else "📈 F0 Curve: OFF"
            )
        self._redraw_waveform()

    def _compute_waveform_peaks(self, audio_path: str, num_peaks: int = 200) -> list[float]:
        """Compute downsampled normalized RMS amplitude peaks and F0 pitch contour for visualization."""
        if not audio_path or not os.path.exists(audio_path):
            self._audio_f0_contour = []
            return []
        try:
            import soundfile as sf
            import numpy as np

            info = sf.info(audio_path)
            self._audio_waveform_duration = float(info.duration)
            data, sr = sf.read(audio_path, dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            total_samples = len(data)
            if total_samples == 0:
                self._audio_f0_contour = []
                return []
            chunk_size = max(1, total_samples // num_peaks)
            peaks = []
            f0_contour = []
            dur = self._audio_waveform_duration

            # Sample F0 contour efficiently across segments
            for i in range(0, total_samples, chunk_size):
                chunk = data[i:i + chunk_size]
                if len(chunk) > 0:
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    peaks.append(rms)
                    t_sec = (i / total_samples) * dur

                    # Simple zero-crossing / autocorrelation F0 estimator for fast GUI rendering
                    if rms > 0.01 and len(chunk) > 64:
                        corr = np.correlate(chunk, chunk, mode="full")
                        corr = corr[len(corr) // 2:]
                        d = np.diff(corr)
                        peaks_idx = np.where((d[:-1] > 0) & (d[1:] < 0))[0] + 1
                        if len(peaks_idx) > 0:
                            lag = peaks_idx[0]
                            if lag > 0:
                                f0 = float(sr / lag)
                                if 65.0 <= f0 <= 500.0:
                                    f0_contour.append((t_sec, f0))

            self._audio_f0_contour = f0_contour
            max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
            return [min(1.0, p / max_rms) for p in peaks]
        except Exception:
            try:
                import librosa
                import numpy as np
                y, sr = librosa.load(audio_path, sr=8000)
                self._audio_waveform_duration = float(len(y) / sr)
                chunk_size = max(1, len(y) // num_peaks)
                peaks = []
                f0_contour = []
                dur = self._audio_waveform_duration
                for i in range(0, len(y), chunk_size):
                    chunk = y[i:i + chunk_size]
                    if len(chunk) > 0:
                        rms = float(np.sqrt(np.mean(chunk**2)))
                        peaks.append(rms)
                        t_sec = (i / len(y)) * dur
                        if rms > 0.01 and len(chunk) > 32:
                            corr = np.correlate(chunk, chunk, mode="full")
                            corr = corr[len(corr) // 2:]
                            d = np.diff(corr)
                            peaks_idx = np.where((d[:-1] > 0) & (d[1:] < 0))[0] + 1
                            if len(peaks_idx) > 0:
                                lag = peaks_idx[0]
                                if lag > 0:
                                    f0 = float(sr / lag)
                                    if 65.0 <= f0 <= 500.0:
                                        f0_contour.append((t_sec, f0))
                self._audio_f0_contour = f0_contour
                max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
                return [min(1.0, p / max_rms) for p in peaks]
            except Exception:
                self._audio_f0_contour = []
                return []

    def _redraw_waveform(self) -> None:
        """Render interactive waveform canvas with speaker turn colors, F0 pitch overlay, and timeline."""
        if not hasattr(self, "canvas_waveform") or not self.canvas_waveform.winfo_exists():
            return
        self.canvas_waveform.delete("all")
        w = self.canvas_waveform.winfo_width()
        h = self.canvas_waveform.winfo_height()
        if w <= 10 or h <= 10:
            return

        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            self.canvas_waveform.create_text(
                w // 2, h // 2,
                text="📊 Waveform visualizer (Load audio in Tab 2 to visualize speech turns)",
                fill="#64748b",
                font=("Helvetica", 9, "italic"),
            )
            return

        if not self._audio_waveform_peaks:
            self._audio_waveform_peaks = self._compute_waveform_peaks(self.active_audio_path, num_peaks=max(60, w // 4))

        peaks = self._audio_waveform_peaks
        if not peaks:
            self.canvas_waveform.create_text(
                w // 2, h // 2,
                text="🎵 Audio waveform loaded",
                fill="#94a3b8",
                font=("Helvetica", 9),
            )
            return

        # Utterance speaker color mapping
        utts = (self.active_transcript or {}).get("utterances", [])
        dur = float(self._audio_waveform_duration or (utts[-1]["end_time"] if utts else 10.0) or 10.0)

        cy = h // 2
        self.canvas_waveform.create_line(0, cy, w, cy, fill="#334155", width=1)

        num_bars = len(peaks)
        bar_w = max(2.0, w / num_bars)
        for idx, amp in enumerate(peaks):
            bx = idx * bar_w
            bar_h = max(2, int(amp * (h / 2 - 8)))
            t_bar = (idx / num_bars) * dur

            # Determine speaker color
            color = "#475569"  # background/pause
            for u in utts:
                if u.get("start_time", 0.0) <= t_bar <= u.get("end_time", 0.0):
                    spk = u.get("speaker", "CHI")
                    color = "#14b8a6" if spk == "CHI" else "#f59e0b"
                    break

            self.canvas_waveform.create_line(
                bx + bar_w / 2, cy - bar_h,
                bx + bar_w / 2, cy + bar_h,
                fill=color,
                width=max(1, int(bar_w - 1)),
            )

        # Draw F0 Pitch Contour Overlay
        if self._show_pitch_overlay and self._audio_f0_contour and dur > 0:
            # Child F0 threshold guide line (250 Hz)
            thresh_y = h - int(((250.0 - 65.0) / (500.0 - 65.0)) * (h - 20) + 10)
            self.canvas_waveform.create_line(
                0, thresh_y, w, thresh_y,
                fill="#0f766e",
                dash=(3, 3),
                width=1,
                tags="pitch_guide",
            )
            self.canvas_waveform.create_text(
                w - 55, thresh_y - 6,
                text="250Hz CHI Thresh",
                fill="#0f766e",
                font=("Helvetica", 7, "bold"),
            )

            # Draw pitch curve
            pts: list[tuple[float, float]] = []
            for t_sec, f0 in self._audio_f0_contour:
                px = (t_sec / dur) * w
                py = h - int(((f0 - 65.0) / (500.0 - 65.0)) * (h - 20) + 10)
                pts.append((px, py))

            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                if abs(p2[0] - p1[0]) < w * 0.08:  # Only connect adjacent voiced segments
                    self.canvas_waveform.create_line(
                        p1[0], p1[1], p2[0], p2[1],
                        fill="#38bdf8",
                        width=2,
                        tags="f0_curve",
                    )
                self.canvas_waveform.create_oval(
                    p1[0] - 1.5, p1[1] - 1.5, p1[0] + 1.5, p1[1] + 1.5,
                    fill="#38bdf8",
                    outline="",
                    tags="f0_curve",
                )

        # Legend & time markers
        step = 5 if dur > 20 else (2 if dur > 6 else 1)
        for t_sec in range(0, int(dur) + 1, step):
            tx = (t_sec / dur) * w
            self.canvas_waveform.create_text(
                tx + 12, h - 8,
                text=f"{t_sec}s",
                fill="#94a3b8",
                font=("Helvetica", 7),
            )

        # Redraw existing playhead needle
        self._draw_playhead(float(getattr(self, "_playhead_time_sec", 0.0)))

    def _draw_playhead(self, t_sec: float) -> None:
        """Draw a vibrant cyan playhead cursor line across the waveform canvas."""
        if not hasattr(self, "canvas_waveform") or not self.canvas_waveform.winfo_exists():
            return
        w = self.canvas_waveform.winfo_width()
        h = self.canvas_waveform.winfo_height()
        if w <= 10 or h <= 10:
            return
        dur = float(self._audio_waveform_duration or 10.0)
        if dur <= 0:
            return

        px = max(0.0, min(float(w), (t_sec / dur) * w))
        self.canvas_waveform.delete("playhead")
        # Vertical playhead needle
        self.canvas_waveform.create_line(px, 0, px, h, fill="#38bdf8", width=2, tags="playhead")
        # Needle head handle
        self.canvas_waveform.create_oval(px - 4, 1, px + 4, 9, fill="#38bdf8", outline="#ffffff", width=1, tags="playhead")

    def _seek_to_position(self, target_sec: float) -> None:
        """Seek playhead position safely guarded by V2 mode."""
        if self._guard_v2_mode("Audio seek"):
            return None
        self._seek_and_play(target_sec, auto_play=False)

    def _seek_and_play(self, target_sec: float, auto_play: bool = True) -> None:
        """Seek to a specific timestamp, update playhead needle, highlight matching sentence, and play."""
        if self._guard_v2_mode("Audio seek"):
            return None
        if not self.active_audio_path or not os.path.exists(self.active_audio_path):
            return

        total_dur = float(self._audio_waveform_duration or 10.0)
        target_sec = max(0.0, min(total_dur, target_sec))
        self._playhead_time_sec = target_sec
        self._current_playback_offset_sec = target_sec

        # Update Scrubber & Current Time Label
        if hasattr(self, "scale_scrubber") and not self._is_user_scrubbing:
            self.scale_scrubber.set(target_sec)
        if hasattr(self, "lbl_time_current"):
            self.lbl_time_current.config(text=self._format_time(target_sec))

        # Redraw Playhead Needle on Waveform
        self._draw_playhead(target_sec)

        # Highlight matching utterance at target_sec
        active_u = None
        if self.active_transcript and "utterances" in self.active_transcript:
            for u in self.active_transcript["utterances"]:
                u_start = float(u.get("start_time", 0.0))
                u_end = float(u.get("end_time", u_start + 2.0))
                if u_start <= target_sec <= u_end:
                    active_u = u
                    break

        if active_u:
            u_id = active_u["id"]
            self._highlight_utterance(u_id)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(target_sec)}] Utterance #{u_id}: *{active_u.get('speaker', 'CHI')}: {active_u.get('text', '')}"
                )
        else:
            self._highlight_utterance(None)
            if hasattr(self, "lbl_playback_status"):
                self.lbl_playback_status.config(
                    text=f"▶️ [{self._format_time(target_sec)}] (Pause / Silence)"
                )

        if auto_play:
            self._play_audio_range(start_sec=target_sec, end_sec=None)

    def _on_waveform_click(self, event: Any) -> None:
        """Seek and play the audio from the clicked timestamp on the waveform canvas."""
        w = self.canvas_waveform.winfo_width()
        if w <= 0 or not self.active_audio_path:
            return
        total_dur = float(self._audio_waveform_duration or 10.0)
        t_click = (max(0, event.x) / w) * total_dur
        self._seek_and_play(t_click, auto_play=True)

    def _on_waveform_drag(self, event: Any) -> None:
        """Interactive audio scrubbing preview while dragging across the waveform."""
        w = self.canvas_waveform.winfo_width()
        if w <= 0 or not self.active_audio_path:
            return
        total_dur = float(self._audio_waveform_duration or 10.0)
        t_drag = max(0.0, min(total_dur, (max(0, event.x) / w) * total_dur))
        self._seek_and_play(t_drag, auto_play=False)

    def _on_scrubber_press(self, event: Any) -> None:
        """User started dragging the timeline scrubber slider."""
        self._is_user_scrubbing = True

    def _on_scrubber_slide(self, val_str: str) -> None:
        """Handle scrubber slider position change during drag."""
        if not self._is_user_scrubbing:
            return
        t_val = float(val_str)
        self._seek_and_play(t_val, auto_play=False)

    def _on_scrubber_release(self, event: Any) -> None:
        """User released the timeline scrubber slider."""
        self._is_user_scrubbing = False
        t_val = float(self.scale_scrubber.get())
        self._seek_and_play(t_val, auto_play=self._is_continuous_playing)

    def _export_cha_file(self) -> None:
        """Export authentic TalkBank CHAT (.cha) transcript with %mor: tiers."""
        if self._guard_v2_mode("Export TalkBank CHAT"):
            return
        if not self.active_transcript:
            messagebox.showwarning("No Data", "No transcript available to export.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save TalkBank CHAT File",
            defaultextension=".cha",
            initialfile=f"{self.active_session_id or 'transcript'}.cha",
            filetypes=[("TalkBank CHAT", "*.cha"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        raw_cha = self.active_transcript.get("raw_cha")
        if not raw_cha:
            raw_cha = self.txt_chat_view.get("1.0", tk.END).strip()
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(raw_cha + "\n")
        messagebox.showinfo("Exported", f"Saved TalkBank CHAT file to:\n{out_file}")

    def _export_csv_biomarkers(self) -> None:
        """Export tabular speech, language, and acoustic biomarker parameters to CSV."""
        if self._guard_v2_mode("Export Biomarkers CSV"):
            return
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        findings = self.client.get_findings(self.active_session_id)
        out_file = filedialog.asksaveasfilename(
            title="Save Biomarkers CSV",
            defaultextension=".csv",
            initialfile=f"biomarkers_{self.active_session_id}.csv",
            filetypes=[("CSV File", "*.csv"), ("Text", "*.txt")],
        )
        if not out_file:
            return
        import csv
        with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["case_id", "session_id", "metric_name", "metric_value"])
            for k, v in findings.get("metrics", {}).items():
                writer.writerow([self.active_case_id, self.active_session_id, k, v])
        messagebox.showinfo("Exported", f"Saved Biomarkers CSV to:\n{out_file}")

    def _export_html_report(self) -> None:
        """Export a comprehensive, beautifully styled bilingual clinical HTML report ready for printing/PDF."""
        if self._guard_v2_mode("Export HTML Report"):
            return
        if not self.active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return
        if not self.active_transcript or not self.active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return
        out_file = filedialog.asksaveasfilename(
            title="Save Clinical HTML Report",
            defaultextension=".html",
            initialfile=f"clinical_report_{self.active_session_id}.html",
            filetypes=[("HTML Document", "*.html"), ("All Files", "*.*")],
        )
        if not out_file:
            return

        findings = self.client.get_findings(self.active_session_id)
        narrative = self.txt_narrative.get("1.0", tk.END).strip()
        recommendations = self.txt_recommendations.get("1.0", tk.END).strip()
        case_info = next((c for c in self.client.list_cases() if c.get("case_id") == self.active_case_id), {})
        session_info = next((s for s in self.client.list_sessions(self.active_case_id) if s.get("session_id") == self.active_session_id), {"session_id": self.active_session_id})

        # Collect longitudinal sessions for active case
        longitudinal_sessions = []
        if self.active_case_id:
            for s in self.client.list_sessions(self.active_case_id):
                s_id = s["session_id"]
                s_dt = s.get("session_date", "N/A")
                tr = self.client.get_session_transcript(s_id)
                f = self.client.get_findings(s_id)
                m = f.get("metrics", {})
                u_list = tr.get("utterances", []) if tr else []
                if u_list:
                    longitudinal_sessions.append({
                        "session_id": s_id,
                        "date": s_dt,
                        "utterances": len(u_list),
                        "chi_turns": sum(1 for u in u_list if u.get("speaker") == "CHI"),
                        "mlu_w": m.get("mlu_words", m.get("mlu", "-")),
                        "ttr": m.get("ttr", m.get("type_token_ratio", "-")),
                        "f0_median": m.get("f0_median_hz", "-"),
                    })

        from packages.reports.clinical_report_template import generate_bilingual_clinical_html
        attested_by = self.active_transcript.get("attested_by", "Kru Aum (Certified SLP)") if self.active_transcript.get("attested") else None

        html_content = generate_bilingual_clinical_html(
            case_info=case_info,
            session_info=session_info,
            findings=findings,
            narrative=narrative,
            recommendations=recommendations,
            attested_by=attested_by,
            longitudinal_sessions=longitudinal_sessions,
        )

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        messagebox.showinfo("Exported", f"Saved Bilingual Clinical HTML Report to:\n{out_file}")

    def _build_create_case_window(self) -> tk.Toplevel:
        """Construct the create case dialog window with dynamic geometry."""
        win = tk.Toplevel(self.root)
        win.title("➕ Create Child Case — LinguaLens")
        win.geometry("420x280")
        win.minsize(380, 240)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Child Identifier:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_cid = ttk.Entry(frame)
        cases_count = len(self.tree_cases.get_children()) if hasattr(self, "tree_cases") else 1
        e_cid.insert(0, f"C-{cases_count + 1:03d}")
        e_cid.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Birth (YYYY-MM):").grid(row=1, column=0, sticky=tk.W, pady=6)
        e_dob = ttk.Entry(frame)
        e_dob.insert(0, "2021-05")
        e_dob.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Primary Language:").grid(row=2, column=0, sticky=tk.W, pady=6)
        e_lang = ttk.Entry(frame)
        e_lang.insert(0, "th")
        e_lang.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Clinical Notes:").grid(row=3, column=0, sticky=tk.W, pady=6)
        e_notes = ttk.Entry(frame)
        e_notes.insert(0, "Speech delay referral.")
        e_notes.grid(row=3, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        def _do_create():
            try:
                new_c = self.client.create_case(e_cid.get().strip(), e_dob.get().strip(), e_lang.get().strip(), e_notes.get().strip())
                self._refresh_cases()
                for idx, val in enumerate(self.combo_global_case["values"]):
                    if val.startswith(new_c["case_id"]):
                        self.combo_global_case.current(idx)
                        self.active_case_id = new_c["case_id"]
                        break
                self._refresh_sessions_for_active_case()
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Case Creation Failed", str(exc))

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Create Case", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_cid.focus_set()
        return win

    def _show_create_case_dialog(self) -> tk.Toplevel:
        win = self._build_create_case_window()
        win.grab_set()
        return win

    def _build_create_session_window(self) -> tk.Toplevel:
        """Construct the create session dialog window with dynamic geometry."""
        from datetime import date
        win = tk.Toplevel(self.root)
        win.title("➕ Start Therapy Session — LinguaLens")
        win.geometry("400x220")
        win.minsize(360, 200)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Session Date:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_date = ttk.Entry(frame)
        e_date.insert(0, date.today().isoformat())
        e_date.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Session Notes:").grid(row=1, column=0, sticky=tk.W, pady=6)
        e_notes = ttk.Entry(frame)
        e_notes.insert(0, "Play-based session.")
        e_notes.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        def _do_create():
            if not self.active_case_id:
                return
            try:
                new_s = self.client.create_session(self.active_case_id, e_date.get().strip(), e_notes.get().strip())
                self._refresh_sessions_for_active_case()
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Session Creation Failed", str(exc))

        btn_row = ttk.Frame(frame)

        btn_row.grid(row=2, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Start Session", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_notes.focus_set()
        return win

    def _show_create_session_dialog(self) -> tk.Toplevel | None:
        if self._guard_v2_mode("Create session"):
            return None
        if not self.active_case_id:
            messagebox.showwarning("Warning", "Please select a Case first.")
            return None
        win = self._build_create_session_window()
        win.grab_set()
        return win

    # -------------------------------------------------------------------------
    # Assessment V2 — Stage 1: Child Management & Context
    # -------------------------------------------------------------------------

    def _validate_child_intake(self, display_code: str, birth_year: int, birth_month: int) -> str | None:
        """Validate child intake inputs client-side before network dispatch."""
        if not isinstance(display_code, str):
            return "Child Identifier / Display Code is required."
        trimmed = display_code.strip()
        if not trimmed:
            return "Child Identifier / Display Code is required."
        if len(trimmed) > 64:
            return "Child Identifier / Display Code must be between 1 and 64 characters."

        if isinstance(birth_year, bool):
            return "Invalid birth year format."
        try:
            by = int(birth_year) if not isinstance(birth_year, float) else None
            if by is None or not (1900 <= by <= 2100):
                return "Birth year must be between 1900 and 2100."
        except (ValueError, TypeError):
            return "Invalid birth year format."

        if isinstance(birth_month, bool):
            return "Invalid birth month format."
        try:
            bm = int(birth_month) if not isinstance(birth_month, float) else None
            if bm is None or not (1 <= bm <= 12):
                return "Birth month must be between 1 and 12."
        except (ValueError, TypeError):
            return "Invalid birth month format."

        from packages.tui.validation import validate_child_input, LinguaLensValidationError
        try:
            validate_child_input(trimmed, by, bm)
            return None
        except (LinguaLensValidationError, ValueError) as err:
            return str(err)


    def _get_current_session_generation(self) -> int:
        if hasattr(self.client, "get_session"):
            try:
                sess = self.client.get_session()
                if sess and hasattr(sess, "generation") and isinstance(sess.generation, int):
                    app_gen = getattr(self, "_current_session_generation", 1)
                    return max(sess.generation, app_gen)
            except Exception:
                pass
        return getattr(self, "_current_session_generation", 1)

    def _handle_auth_error(self, error: Exception, session_generation: int | None = None) -> None:
        """Handle HTTP 401 / auth invalidation: wipe clinical context and clear session."""
        current_gen = self._get_current_session_generation()
        if session_generation is not None and session_generation != current_gen:
            return  # Discard stale 401 from an earlier session generation

        if hasattr(self.client, "clear_session"):
            self.client.clear_session()
        self._current_session_generation = current_gen + 1

        # Stop audio playback and reset audio path
        self._stop_playback()
        self.active_audio_path = None

        # Reset legacy clinical state
        self.active_case_id = None
        self.active_session_id = None
        self.active_transcript = None
        self.active_report = None
        self._legacy_context_generation = getattr(self, "_legacy_context_generation", 0) + 1

        # Reset V2 clinical state
        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self._current_consent_status = "not-loaded"
        self._consent_loaded_at = None
        self.active_assessment_id = None
        self.active_assessment = None
        self._cached_assessments = []
        self._presentation_row_iids = set()
        self._assessment_list_error = None
        self._current_child_request_id = None
        self._consent_request_id = None
        self._current_assessment_selection_req_id = None
        self._current_refresh_request_id = None
        self._child_selection_generation = getattr(self, "_child_selection_generation", 0) + 1
        self._assessment_selection_generation = getattr(self, "_assessment_selection_generation", 0) + 1

        # Cancel any active assessment dialog / operation
        if getattr(self, "_current_asmt_cancel_event", None):
            try:
                self._current_asmt_cancel_event.set()
            except Exception:
                pass
        self._current_asmt_cancel_event = None
        self._current_asmt_dialog_token = None

        # Unconditionally clear busy state
        self._set_busy_state(False, "Ready")

        # Clear UI trees and selectors
        for tree_name in (
            "tree_cases",
            "tree_sessions",
            "tree_children",
            "tree_assessments",
            "tree_utterances",
            "tree_metrics",
            "tree_guidelines",
            "tree_longitudinal",
        ):
            tree = getattr(self, tree_name, None)
            if tree is not None and tree.winfo_exists():
                for it in tree.get_children():
                    tree.delete(it)

        # Clear clinical text widgets (preserving disabled state where set)
        for txt_name in (
            "txt_chat_view",
            "txt_narrative",
            "txt_recommendations",
            "txt_manual",
            "txt_radar_summary",
        ):
            w = getattr(self, txt_name, None)
            if w is not None and w.winfo_exists():
                st = w.cget("state")
                w.config(state=tk.NORMAL)
                w.delete("1.0", tk.END)
                w.config(state=st)

        # Clear clinical canvases/plots
        for canvas_name in ("canvas_waveform", "canvas_radar"):
            c = getattr(self, canvas_name, None)
            if c is not None and c.winfo_exists():
                c.delete("all")

        # Clear combobox values and selections (prevent re-selection of old clinical records)
        for combo_name in ("combo_global_case", "combo_global_session", "combo_global_child"):
            combo = getattr(self, combo_name, None)
            if combo is not None and combo.winfo_exists():
                combo["values"] = []
                combo.set("")

        # Clear clinical entry fields
        for entry_name in ("entry_audio_path", "entry_u_text", "entry_case_search"):
            e = getattr(self, entry_name, None)
            if e is not None and e.winfo_exists():
                e.delete(0, tk.END)

        # Reset context labels
        if hasattr(self, "lbl_ingest_ctx") and self.lbl_ingest_ctx.winfo_exists():
            self.lbl_ingest_ctx.config(text="Active Context: Please sign in to begin")
        if hasattr(self, "lbl_longitudinal_summary") and self.lbl_longitudinal_summary.winfo_exists():
            self.lbl_longitudinal_summary.config(text="")
        if hasattr(self, "lbl_review_status") and self.lbl_review_status.winfo_exists():
            self.lbl_review_status.config(text="Transcript Status: Not loaded")
        if hasattr(self, "lbl_report_status") and self.lbl_report_status.winfo_exists():
            self.lbl_report_status.config(text="Report Status: None")
        if hasattr(self, "lbl_playback_status") and self.lbl_playback_status.winfo_exists():
            self.lbl_playback_status.config(text="⏹ Stopped")
        if hasattr(self, "lbl_time_current") and self.lbl_time_current.winfo_exists():
            self.lbl_time_current.config(text="00:00")
        if hasattr(self, "lbl_time_total") and self.lbl_time_total.winfo_exists():
            self.lbl_time_total.config(text="00:00")

        # Close any open child dialogs containing clinical data
        if hasattr(self, "root") and self.root.winfo_exists():
            for child in list(self.root.winfo_children()):
                if isinstance(child, tk.Toplevel):
                    try:
                        child.destroy()
                    except Exception:
                        pass

        self._update_consent_badge("not-loaded", None)
        self._update_downstream_tabs_mode()

        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text="⚠️ Authentication Required: Session expired. Please sign in.")

        # Idempotent dialog storm prevention
        if not getattr(self, "_auth_dialog_active", False):
            self._auth_dialog_active = True
            try:
                messagebox.showerror("Sign-in Required", f"Session expired or authentication required:\n{error}")
            finally:
                self._auth_dialog_active = False

    def _handle_permission_error(
        self,
        error: Exception,
        request_id: str | None = None,
        session_generation: int | None = None,
    ) -> None:
        """Handle HTTP 403 / permission denial: show dialog without clearing session credentials."""
        if session_generation is not None and session_generation != self._get_current_session_generation():
            return
        if request_id is not None and hasattr(self, "_current_child_request_id") and request_id != self._current_child_request_id:
            return  # Discard stale 403 from an older request

        # Only clear active child if the error is for the current request
        if request_id is not None and getattr(self, "_current_child_request_id", None) == request_id:
            self.active_child_id = None
            self.active_child = None

        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⛔ Permission Denied: {error}")
        messagebox.showerror("Permission Denied", f"Access Denied: You do not have permission for this resource.\n{error}")

    def _on_async_child_selected(
        self,
        request_id: str,
        child_data: dict[str, Any],
        session_generation: int | None = None,
    ) -> None:
        """Process loaded child data, discarding if request_id or session_generation is stale."""
        if session_generation is not None and session_generation != self._get_current_session_generation():
            return
        if hasattr(self, "_current_child_request_id") and request_id != self._current_child_request_id:
            return  # Discard stale late response
        if not child_data or not isinstance(child_data, dict):
            return

        # Transition mode to V2 and clear legacy context
        self.current_mode = "v2"
        self._legacy_context_generation = getattr(self, "_legacy_context_generation", 0) + 1
        self._stop_playback()

        self.active_case_id = None
        self.active_session_id = None
        self.active_transcript = None
        self.active_report = None
        self.active_audio_path = None

        if hasattr(self, "tree_cases") and self.tree_cases.winfo_exists():
            sel_cases = self.tree_cases.selection()
            if sel_cases:
                self.tree_cases.selection_remove(*sel_cases)
        if hasattr(self, "tree_sessions") and self.tree_sessions.winfo_exists():
            sel_sess = self.tree_sessions.selection()
            if sel_sess:
                self.tree_sessions.selection_remove(*sel_sess)
        if hasattr(self, "combo_global_case") and self.combo_global_case.winfo_exists():
            self.combo_global_case.set("")
        if hasattr(self, "combo_global_session") and self.combo_global_session.winfo_exists():
            self.combo_global_session.set("")

        self.active_child_id = child_data.get("id")
        self.active_child = child_data
        self._cached_assessments = []
        self.active_assessment_id = None
        self.active_assessment = None
        self._update_downstream_tabs_mode()
        self._current_consent_thread = self._refresh_consent()
        self._current_assessment_thread = self._refresh_assessments()

    def _on_child_load_error(self, request_id: str, error: Exception) -> None:
        if hasattr(self, "_current_child_request_id") and request_id != self._current_child_request_id:
            return
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⚠️ Failed to load child: {error}")
        messagebox.showerror("Child Load Failed", str(error))

    def _resolve_consent_state(
        self,
        consents: list[dict[str, Any]],
        purpose: str = "clinical_assessment",
    ) -> tuple[str, dict[str, Any] | None]:
        """Resolve authoritative consent status from history using latest-version-per-purpose semantics."""
        matching = [c for c in consents if c.get("purpose") == purpose]
        if not matching:
            return "no-record", None
        latest = max(matching, key=lambda c: c.get("version", 0))
        st = latest.get("status")
        if st == "active":
            return "active", latest
        elif st == "withdrawn":
            return "withdrawn", latest
        return st or "unknown", latest

    def _update_consent_badge(
        self,
        status: str,
        consent_rec: dict[str, Any] | None,
        loaded_at: str | None = None,
        error_msg: str | None = None,
    ) -> None:
        """Update consent status badge and loaded timestamp in context bar."""
        self._current_consent_status = status
        if not hasattr(self, "lbl_consent_status") or not self.lbl_consent_status.winfo_exists():
            return

        if status == "not-loaded":
            self.lbl_consent_status.config(text="[Consent Not Loaded]", bg="#f1f5f9", fg="#64748b")
        elif status == "loading":
            self.lbl_consent_status.config(text="⏳ Loading consent...", bg="#fef3c7", fg="#b45309")
        elif status == "active":
            v = consent_rec.get("version", 1) if consent_rec else 1
            self.lbl_consent_status.config(text=f"✓ Active Consent (v{v})", bg="#dcfce7", fg="#15803d")
        elif status == "withdrawn":
            v = consent_rec.get("version", "") if consent_rec else ""
            v_txt = f" (v{v})" if v else ""
            self.lbl_consent_status.config(text=f"⛔ Consent Withdrawn{v_txt}", bg="#fee2e2", fg="#b91c1c")
        elif status == "no-record":
            self.lbl_consent_status.config(text="⚪ No Record", bg="#f1f5f9", fg="#475569")
        elif status == "error":
            msg = error_msg or "Error loading consent"
            self.lbl_consent_status.config(text=f"⚠️ {msg}", bg="#fee2e2", fg="#dc2626")

        if hasattr(self, "lbl_consent_loaded_at") and self.lbl_consent_loaded_at.winfo_exists():
            if loaded_at:
                self.lbl_consent_loaded_at.config(text=f"(Loaded at {loaded_at})")
            elif status == "not-loaded":
                self.lbl_consent_loaded_at.config(text="")

    def _refresh_consent(self) -> threading.Thread | None:
        """Fetch authoritative consent history for the active child asynchronously."""
        if not self.active_child_id:
            self._update_consent_badge("not-loaded", None)
            return None

        child_id = self.active_child_id
        session_gen = self._get_current_session_generation()
        child_sel_gen = self._child_selection_generation
        request_id = f"consent-{child_id}-{uuid.uuid4().hex[:8]}"
        self._consent_request_id = request_id

        self._update_consent_badge("loading", None)

        def worker() -> None:
            try:
                consents = self.client.list_consents(child_id)
                self._async_queue.put((
                    lambda: self._on_consent_refreshed(
                        child_id=child_id,
                        consents=consents,
                        request_id=request_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_consent_refresh_error(
                        child_id=child_id,
                        error=e,
                        request_id=request_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        self._current_consent_thread = t
        t.start()
        return t

    def _on_consent_refreshed(
        self,
        child_id: str,
        consents: list[dict[str, Any]],
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            return
        if request_id != self._consent_request_id:
            return

        status, latest_rec = self._resolve_consent_state(consents, purpose="clinical_assessment")
        self.active_consent = latest_rec if status == "active" else None
        now_str = datetime.now().strftime("%H:%M:%S")
        self._consent_loaded_at = now_str
        self._update_consent_badge(status, latest_rec, loaded_at=now_str)

    def _on_consent_refresh_error(
        self,
        child_id: str,
        error: Exception,
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError
        if isinstance(error, LinguaLensAuthError) or (
            hasattr(error, "status_code") and getattr(error, "status_code", None) == 401
        ):
            if session_gen == self._get_current_session_generation():
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            return
        if request_id != self._consent_request_id:
            return

        if isinstance(error, LinguaLensPermissionError):
            self._update_consent_badge("error", None, error_msg="Permission Denied")
            return
        else:
            self._update_consent_badge("error", None, error_msg="Error loading consent")

    def _show_record_consent_dialog(self) -> tk.Toplevel | None:
        """Display explicit consent recording modal for the active child."""
        if not self.active_child_id:
            messagebox.showwarning("No Child Selected", "Please select a child profile first.")
            return None

        child_id = self.active_child_id
        child_code = self.active_child.get("display_code", child_id) if self.active_child else child_id
        session_gen = self._get_current_session_generation()
        child_sel_gen = self._child_selection_generation

        win = tk.Toplevel(self.root)
        win.title("Record Authorized Consent")
        win.geometry("500x420")
        win.transient(self.root)
        try:
            win.grab_set()
        except Exception:
            pass

        win._dlg_token = f"rec-consent-{child_id}-{uuid.uuid4().hex[:8]}"
        win._target_child_id = child_id
        win._target_child_code = child_code
        win._session_generation = session_gen
        win._child_selection_generation = child_sel_gen
        win._is_submitting = False

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="📋 Record Parental / Guardian Consent", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 6))

        notice_lbl = ttk.Label(
            frame,
            text="Notice: This action records official consent received from or withdrawn by\n"
                 "the child's parent/guardian. Clicking confirm documents authorized status\n"
                 "and does not constitute direct parental consent.",
            font=("Helvetica", 9),
            foreground="#475569",
        )
        notice_lbl.pack(anchor=tk.W, pady=(0, 10))

        # Child display (bound at dialog opening)
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=4)
        ttk.Label(row1, text="Child:", width=14, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(row1, text=f"{child_code} ({child_id})", font=("Helvetica", 9)).pack(side=tk.LEFT)

        # Purpose (strictly fixed to clinical_assessment for Subtask B)
        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=4)
        ttk.Label(row2, text="Purpose:", width=14, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(row2, text="clinical_assessment", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)

        # Scope Version (explicit input, validated against schema 1-64 chars)
        row3 = ttk.Frame(frame)
        row3.pack(fill=tk.X, pady=4)
        ttk.Label(row3, text="Scope Version:", width=14, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        entry_scope = ttk.Entry(row3, width=28)
        entry_scope.insert(0, "2026.1")
        entry_scope.pack(side=tk.LEFT)

        # Action / Status
        row4 = ttk.Frame(frame)
        row4.pack(fill=tk.X, pady=6)
        ttk.Label(row4, text="Consent Action:", width=14, font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        status_var = tk.StringVar(value="active")
        r_active = ttk.Radiobutton(row4, text="Grant Active Consent", variable=status_var, value="active")
        r_active.pack(side=tk.LEFT, padx=(0, 8))
        r_withdrawn = ttk.Radiobutton(row4, text="Withdraw Consent", variable=status_var, value="withdrawn")
        r_withdrawn.pack(side=tk.LEFT)

        # Button Bar
        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill=tk.X, pady=(16, 0))

        def on_confirm():
            if (
                win._target_child_id != self.active_child_id
                or win._session_generation != self._get_current_session_generation()
                or win._child_selection_generation != self._child_selection_generation
            ):
                messagebox.showerror(
                    "Context Changed",
                    "Clinical context changed since this dialog was opened. Consent recording aborted.",
                    parent=win if win.winfo_exists() else self.root,
                )
                if win.winfo_exists():
                    win.destroy()
                return

            scope = entry_scope.get().strip()
            if not scope:
                messagebox.showerror(
                    "Validation Error",
                    "Scope Version is required and cannot be empty.",
                    parent=win if win.winfo_exists() else self.root,
                )
                return
            if len(scope) > 64:
                messagebox.showerror(
                    "Validation Error",
                    "Scope Version must not exceed 64 characters.",
                    parent=win if win.winfo_exists() else self.root,
                )
                return

            st = status_var.get()
            self._submit_record_consent(win, purpose="clinical_assessment", scope_version=scope, status=st)

        win.btn_confirm = ttk.Button(btn_bar, text="✓ Confirm Recording", command=on_confirm)
        win.btn_confirm.pack(side=tk.RIGHT, padx=(6, 0))

        win.btn_cancel = ttk.Button(btn_bar, text="Cancel", command=win.destroy)
        win.btn_cancel.pack(side=tk.RIGHT)

        return win

    def _submit_record_consent(
        self,
        win: tk.Toplevel,
        purpose: str,
        scope_version: str,
        status: str,
    ) -> threading.Thread | None:
        """Submit record consent mutation with explicit confirmation, debouncing, and target verification."""
        if getattr(win, "_is_submitting", False):
            return None

        target_child_id = getattr(win, "_target_child_id", self.active_child_id)
        target_child_code = getattr(win, "_target_child_code", None) or (
            self.active_child.get("display_code", target_child_id) if self.active_child else target_child_id
        )
        target_session_gen = getattr(win, "_session_generation", self._get_current_session_generation())
        target_child_sel_gen = getattr(win, "_child_selection_generation", self._child_selection_generation)

        # Context drift check before confirmation
        if (
            not target_child_id
            or target_child_id != self.active_child_id
            or target_session_gen != self._get_current_session_generation()
            or target_child_sel_gen != self._child_selection_generation
        ):
            messagebox.showerror(
                "Context Changed",
                "Clinical context changed or child is not active. Consent recording aborted.",
                parent=win if win.winfo_exists() else self.root,
            )
            if win.winfo_exists():
                win.destroy()
            return None

        # Validation on scope_version
        scope_clean = (scope_version or "").strip()
        if not scope_clean:
            messagebox.showerror(
                "Validation Error",
                "Scope Version is required and cannot be empty.",
                parent=win if win.winfo_exists() else self.root,
            )
            return None
        if len(scope_clean) > 64:
            messagebox.showerror(
                "Validation Error",
                "Scope Version must not exceed 64 characters.",
                parent=win if win.winfo_exists() else self.root,
            )
            return None

        # Explicit confirmation
        action_desc = "Grant Active Consent" if status == "active" else "Withdraw Consent"
        confirm_msg = (
            f"Please confirm recording the following consent status:\n\n"
            f"• Child: {target_child_code} ({target_child_id})\n"
            f"• Purpose: {purpose}\n"
            f"• Scope Version: {scope_clean}\n"
            f"• Action: {action_desc}\n\n"
            f"Are you sure you wish to record this consent status?"
        )
        parent_win = win if win.winfo_exists() else self.root
        try:
            confirmed = messagebox.askyesno("Confirm Consent Recording", confirm_msg, parent=parent_win)
        except TypeError:
            confirmed = messagebox.askyesno("Confirm Consent Recording", confirm_msg)
        if not confirmed:
            return None

        # Re-verify context drift after confirmation modal returns
        if (
            target_child_id != self.active_child_id
            or target_session_gen != self._get_current_session_generation()
            or target_child_sel_gen != self._child_selection_generation
        ):
            messagebox.showerror(
                "Context Changed",
                "Clinical context changed during confirmation. Consent recording aborted.",
                parent=win if win.winfo_exists() else self.root,
            )
            if win.winfo_exists():
                win.destroy()
            return None

        win._is_submitting = True
        if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
            win.btn_confirm.config(state="disabled")

        dlg_token = getattr(win, "_dlg_token", "")
        req_id = f"rec-req-{uuid.uuid4().hex[:8]}"
        self._set_busy_state(True, "Recording consent...", request_id=req_id)

        def worker() -> None:
            try:
                new_consent = self.client.record_consent(target_child_id, purpose, scope_clean, status)
                self._async_queue.put((
                    lambda: self._on_record_consent_success(
                        win=win,
                        dlg_token=dlg_token,
                        request_id=req_id,
                        child_id=target_child_id,
                        new_consent=new_consent,
                        session_gen=target_session_gen,
                        child_sel_gen=target_child_sel_gen,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_record_consent_error(
                        win=win,
                        dlg_token=dlg_token,
                        request_id=req_id,
                        child_id=target_child_id,
                        error=e,
                        session_gen=target_session_gen,
                        child_sel_gen=target_child_sel_gen,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_record_consent_success(
        self,
        win: tk.Toplevel,
        dlg_token: str,
        request_id: str,
        child_id: str,
        new_consent: dict[str, Any],
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        self._set_busy_state(False, "Ready", request_id=request_id)

        # Session generation check
        if session_gen != self._get_current_session_generation():
            if win.winfo_exists():
                win.destroy()
            return

        # Child selection generation check
        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            if win.winfo_exists():
                win.destroy()
            return

        # Close dialog if matching token
        dialog_was_active = win.winfo_exists() and getattr(win, "_dlg_token", None) == dlg_token
        if dialog_was_active:
            win.destroy()

        if not dialog_was_active:
            # Dialog closed or cancelled before response arrived; discard presentation
            return

        # Transition badge immediately to pending refresh state
        self._update_consent_badge("loading", None, loaded_at=None)

        # Asynchronously fetch authoritative history without blocking UI thread
        self._current_consent_thread = self._refresh_consent_after_mutation(
            child_id=child_id,
            session_gen=session_gen,
            child_sel_gen=child_sel_gen,
            new_consent=new_consent,
        )

    def _refresh_consent_after_mutation(
        self,
        child_id: str,
        session_gen: int,
        child_sel_gen: int,
        new_consent: dict[str, Any],
    ) -> threading.Thread | None:
        """Asynchronously refresh authoritative consent status after successful mutation."""
        refresh_req_id = f"consent-ref-{child_id}-{uuid.uuid4().hex[:8]}"
        self._consent_request_id = refresh_req_id

        def worker() -> None:
            try:
                consents = self.client.list_consents(child_id)
                self._async_queue.put((
                    lambda: self._on_post_mutation_refresh_success(
                        child_id=child_id,
                        consents=consents,
                        request_id=refresh_req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_post_mutation_refresh_error(
                        child_id=child_id,
                        error=e,
                        request_id=refresh_req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                        new_consent=new_consent,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_post_mutation_refresh_success(
        self,
        child_id: str,
        consents: list[dict[str, Any]],
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            return
        if request_id != self._consent_request_id:
            return

        status, latest_rec = self._resolve_consent_state(consents, purpose="clinical_assessment")
        self.active_consent = latest_rec if status == "active" else None
        now_str = datetime.now().strftime("%H:%M:%S")
        self._consent_loaded_at = now_str
        self._update_consent_badge(status, latest_rec, loaded_at=now_str)
        messagebox.showinfo("Success", f"Consent recorded successfully for child {child_id}.")

    def _on_post_mutation_refresh_error(
        self,
        child_id: str,
        error: Exception,
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
        new_consent: dict[str, Any],
    ) -> None:
        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError

        # Invalidate auth is a session-level concern
        if isinstance(error, LinguaLensAuthError):
            if session_gen == self._get_current_session_generation():
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            return
        if request_id != self._consent_request_id:
            return

        if isinstance(error, LinguaLensPermissionError):
            self._update_consent_badge("error", None, error_msg="Permission Denied on Refresh")
            messagebox.showwarning(
                "Consent Recorded (Refresh Denied)",
                f"Consent was recorded successfully, but permission was denied to refresh history: {error}. Session preserved.",
            )
            return

        # General error on refresh
        self._update_consent_badge("error", None, error_msg="Recorded (Refresh Failed)")
        messagebox.showwarning(
            "Consent Recorded (Refresh Failed)",
            f"Consent was recorded successfully, but failed to refresh status: {error}. Please refresh manually.",
        )

    def _on_record_consent_error(
        self,
        win: tk.Toplevel,
        dlg_token: str,
        request_id: str,
        child_id: str,
        error: Exception,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        self._set_busy_state(False, "Ready", request_id=request_id)

        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError, LinguaLensConflictError

        # Invalidate auth is a session-level concern: handle current-session 401 even if dialog is closed
        if isinstance(error, LinguaLensAuthError):
            if session_gen == self._get_current_session_generation():
                if win.winfo_exists():
                    win.destroy()
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            if win.winfo_exists():
                win.destroy()
            return

        if child_sel_gen != self._child_selection_generation or child_id != self.active_child_id:
            if win.winfo_exists():
                win.destroy()
            return

        dialog_is_valid = win.winfo_exists() and getattr(win, "_dlg_token", None) == dlg_token

        if isinstance(error, LinguaLensPermissionError):
            if dialog_is_valid:
                win._is_submitting = False
                if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                    win.btn_confirm.config(state="normal")
                messagebox.showerror("Permission Denied", f"You do not have permission to record consent: {error}")
            return

        if isinstance(error, LinguaLensConflictError):
            if dialog_is_valid:
                win._is_submitting = False
                if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                    win.btn_confirm.config(state="normal")
                messagebox.showerror("Consent Conflict (409)", f"Consent Conflict: {error}")
            # Refresh authoritative state on 409 asynchronously without auto-retry POST
            self._current_consent_thread = self._refresh_consent()
            return

        # General error
        if dialog_is_valid:
            win._is_submitting = False
            if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                win.btn_confirm.config(state="normal")
            messagebox.showerror("Consent Recording Failed", f"Failed to record consent: {error}")

    def _set_active_child(self, child_id: str | None) -> threading.Thread | None:
        """Switch active child asynchronously, flushing previous clinical context immediately."""
        # Always flush previous clinical context immediately on UI thread
        if child_id:
            self.current_mode = "v2"
            self._legacy_context_generation = getattr(self, "_legacy_context_generation", 0) + 1
            self._stop_playback()
            self.active_case_id = None
            self.active_session_id = None
            self.active_transcript = None
            self.active_report = None
            self.active_audio_path = None
            if hasattr(self, "tree_cases") and self.tree_cases.winfo_exists():
                sel_cases = self.tree_cases.selection()
                if sel_cases:
                    self.tree_cases.selection_remove(*sel_cases)
            if hasattr(self, "tree_sessions") and self.tree_sessions.winfo_exists():
                sel_sess = self.tree_sessions.selection()
                if sel_sess:
                    self.tree_sessions.selection_remove(*sel_sess)
            if hasattr(self, "combo_global_case") and self.combo_global_case.winfo_exists():
                self.combo_global_case.set("")
            if hasattr(self, "combo_global_session") and self.combo_global_session.winfo_exists():
                self.combo_global_session.set("")

        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None
        self._cached_assessments = []
        self._presentation_row_iids = set()
        self._assessment_list_error = None
        self._assessment_selection_generation = getattr(self, "_assessment_selection_generation", 0) + 1
        self._current_assessment_selection_req_id = None
        if getattr(self, "_current_asmt_cancel_event", None):
            try:
                self._current_asmt_cancel_event.set()
            except Exception:
                pass
        self._current_asmt_cancel_event = None
        self._current_asmt_dialog_token = None
        self._update_downstream_tabs_mode()
        self._update_consent_badge("not-loaded" if not child_id else "loading", None)

        self._child_selection_generation = getattr(self, "_child_selection_generation", 0) + 1
        req_id = f"child-req-{uuid.uuid4().hex[:8]}"
        self._current_child_request_id = req_id
        session_gen = self._get_current_session_generation()

        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            for item in self.tree_assessments.get_children():
                self.tree_assessments.delete(item)

        if not child_id:
            return None

        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError

        def worker() -> None:
            try:
                child_data = self.client.get_child(child_id)
                self._async_queue.put((
                    lambda: self._on_async_child_selected(req_id, child_data, session_gen),
                    None,
                ))
            except LinguaLensAuthError as exc:
                self._async_queue.put((
                    lambda e=exc: self._handle_auth_error(e, session_generation=session_gen),
                    exc,
                ))
            except LinguaLensPermissionError as exc:
                self._async_queue.put((
                    lambda e=exc: self._handle_permission_error(e, request_id=req_id, session_generation=session_gen),
                    exc,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_child_load_error(req_id, e),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _refresh_children(
        self,
        on_success: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> threading.Thread | None:
        """Refresh children directory list and global selector from API/client asynchronously."""
        refresh_id = f"refresh-{uuid.uuid4().hex[:8]}"
        self._current_refresh_request_id = refresh_id
        session_gen = self._get_current_session_generation()
        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError

        def worker() -> None:
            try:
                children = self.client.list_children()
                self._async_queue.put((
                    lambda: self._on_children_refreshed(refresh_id, children, session_gen, on_success),
                    None,
                ))
            except LinguaLensAuthError as exc:
                def _auth_cb(e=exc):
                    self._handle_auth_error(e, session_generation=session_gen)
                    if on_error:
                        on_error(e)
                self._async_queue.put((_auth_cb, exc))
            except LinguaLensPermissionError as exc:
                def _perm_cb(e=exc):
                    self._handle_permission_error(e, session_generation=session_gen)
                    if on_error:
                        on_error(e)
                self._async_queue.put((_perm_cb, exc))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_children_refresh_error(refresh_id, e, session_gen, on_error),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_children_refreshed(
        self,
        refresh_id: str,
        children: list[dict[str, Any]],
        session_generation: int,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        if session_generation != self._get_current_session_generation():
            return
        if hasattr(self, "_current_refresh_request_id") and refresh_id != self._current_refresh_request_id:
            return  # Discard stale out-of-order refresh

        # Reconcile tree_children: clear previous rows first so no duplicate iid occurs
        if hasattr(self, "tree_children") and self.tree_children.winfo_exists():
            for it in self.tree_children.get_children():
                self.tree_children.delete(it)

        child_options = []
        for ch in children:
            ch_id = ch.get("id")
            display_code = ch.get("display_code", ch_id)
            birth_ym = f"{ch.get('birth_year', '-')}-{ch.get('birth_month', 1):02d}" if ch.get("birth_year") else "-"
            lang_ctx = ch.get("language_context", {})
            primary_lang = lang_ctx.get("primary", "th") if isinstance(lang_ctx, dict) else "th"
            if hasattr(self, "tree_children") and self.tree_children.winfo_exists():
                self.tree_children.insert(
                    "",
                    tk.END,
                    iid=ch_id,
                    values=(
                        ch_id,
                        display_code,
                        birth_ym,
                        primary_lang.upper(),
                    ),
                )
            child_options.append(f"{ch_id} | {display_code} ({birth_ym}, {primary_lang.upper()})")

        if hasattr(self, "combo_global_child") and self.combo_global_child.winfo_exists():
            if child_options:
                self.combo_global_child["values"] = child_options
                if self.active_child_id:
                    for idx, opt in enumerate(child_options):
                        if opt.startswith(self.active_child_id):
                            self.combo_global_child.current(idx)
                            break
            else:
                self.combo_global_child["values"] = ["(No Children — Click ➕ New Child)"]
                self.combo_global_child.current(0)

        if on_success:
            on_success()

    def _on_children_refresh_error(
        self,
        refresh_id: str,
        error: Exception,
        session_generation: int,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if session_generation != self._get_current_session_generation():
            return
        if hasattr(self, "_current_refresh_request_id") and refresh_id != self._current_refresh_request_id:
            return
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⚠️ Failed to list children: {error}")
        if on_error:
            on_error(error)

    def _on_child_selected(self, event: Any = None) -> None:
        """Handle child row selection in Tab 1 tree_children."""
        if not hasattr(self, "tree_children") or not self.tree_children.winfo_exists():
            return
        selected = self.tree_children.selection()
        if not selected:
            return
        child_id = selected[0]
        self._set_active_child(child_id)

        if hasattr(self, "combo_global_child") and self.combo_global_child.winfo_exists():
            for idx, val in enumerate(self.combo_global_child["values"]):
                if val.startswith(child_id):
                    self.combo_global_child.current(idx)
                    break

    def _on_global_child_changed(self, event: Any = None) -> None:
        """Handle selection change in top context bar combo_global_child."""
        if not hasattr(self, "combo_global_child") or not self.combo_global_child.winfo_exists():
            return
        sel_text = self.combo_global_child.get()
        if not sel_text or sel_text.startswith("("):
            return
        child_id = sel_text.split(" | ")[0].strip()
        self._set_active_child(child_id)

        if hasattr(self, "tree_children") and self.tree_children.winfo_exists():
            if child_id in self.tree_children.get_children():
                self.tree_children.selection_set(child_id)
                self.tree_children.see(child_id)

    def _build_create_child_window(self) -> tk.Toplevel:
        """Construct the create child intake dialog window."""
        from datetime import date
        current_year = date.today().year

        win = tk.Toplevel(self.root)
        win._dlg_token = str(uuid.uuid4())
        win.title("➕ Create Child Profile (Assessment V2) — LinguaLens")
        win.geometry("450x280")
        win.minsize(400, 240)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Display Code / Identifier:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_code = ttk.Entry(frame)
        e_code.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Birth Year (YYYY):").grid(row=1, column=0, sticky=tk.W, pady=6)
        e_year = ttk.Entry(frame)
        e_year.insert(0, str(current_year - 3))
        e_year.grid(row=1, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Birth Month (1-12):").grid(row=2, column=0, sticky=tk.W, pady=6)
        e_month = ttk.Entry(frame)
        e_month.insert(0, "1")
        e_month.grid(row=2, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        ttk.Label(frame, text="Primary Language:").grid(row=3, column=0, sticky=tk.W, pady=6)
        c_lang = ttk.Combobox(frame, values=["th", "en"], state="readonly")
        c_lang.set("th")
        c_lang.grid(row=3, column=1, sticky=tk.EW, pady=6, padx=(8, 0))

        def _do_submit() -> None:
            self._submit_create_child(
                win=win,
                display_code=e_code.get().strip(),
                birth_year=e_year.get().strip(),
                birth_month=e_month.get().strip(),
                language=c_lang.get().strip(),
            )

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Create Child Profile", style="Primary.TButton", command=_do_submit).pack(side=tk.RIGHT)
        e_code.focus_set()
        return win

    def _show_create_child_dialog(self) -> tk.Toplevel:
        win = self._build_create_child_window()
        try:
            win.grab_set()
        except tk.TclError:
            pass
        return win

    def _submit_create_child(
        self,
        win: tk.Toplevel,
        display_code: str,
        birth_year: Any,
        birth_month: Any,
        language: str = "th",
    ) -> threading.Thread | None:
        """Validate child intake inputs, call client.create_child asynchronously, and update active context."""
        val_err = self._validate_child_intake(display_code, birth_year, birth_month)
        if val_err:
            messagebox.showwarning("Validation Error", val_err)
            return None

        if win is not None and getattr(win, "_is_submitting", False):
            return None  # Prevent duplicate POST while request is in flight!
        if win is not None:
            win._is_submitting = True

        by = int(birth_year)
        bm = int(birth_month)
        lang_ctx = {"primary": (language or "th").strip(), "additional": []}
        session_gen = self._get_current_session_generation()
        child_sel_gen = getattr(self, "_child_selection_generation", 0)
        dlg_token = getattr(win, "_dlg_token", None) if win else None

        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError

        def worker() -> None:
            try:
                new_child = self.client.create_child(display_code.strip(), by, bm, lang_ctx)
                self._async_queue.put((
                    lambda: self._on_create_child_success(win, dlg_token, new_child, session_gen, child_sel_gen),
                    None,
                ))
            except LinguaLensAuthError as exc:
                self._async_queue.put((
                    lambda e=exc: self._handle_auth_error(e, session_generation=session_gen),
                    exc,
                ))
            except LinguaLensPermissionError as exc:
                self._async_queue.put((
                    lambda e=exc: self._handle_create_child_permission_error(win, dlg_token, e, session_gen),
                    exc,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_create_child_error(win, dlg_token, e, session_gen),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_create_child_success(
        self,
        win: tk.Toplevel | None,
        dlg_token: str | None,
        new_child: dict[str, Any],
        session_generation: int,
        child_selection_generation: int | None = None,
    ) -> None:
        if session_generation != self._get_current_session_generation():
            return
        if win is not None:
            try:
                if not win.winfo_exists():
                    return  # Dialog closed/cancelled, discard completion
                if dlg_token is not None and getattr(win, "_dlg_token", None) != dlg_token:
                    return  # Mismatched token, discard completion
            except Exception:
                return

        self._refresh_children()

        # Only auto-activate if user hasn't made another selection in the interim!
        if (
            child_selection_generation is not None
            and child_selection_generation == getattr(self, "_child_selection_generation", 0)
        ):
            if new_child and "id" in new_child:
                self._set_active_child(new_child["id"])

        if win is not None:
            try:
                if win.winfo_exists():
                    win._is_submitting = False
                    win.destroy()
            except Exception:
                pass

    def _on_create_child_error(
        self,
        win: tk.Toplevel | None,
        dlg_token: str | None,
        error: Exception,
        session_generation: int,
    ) -> None:
        if session_generation != self._get_current_session_generation():
            return
        if win is not None:
            try:
                if not win.winfo_exists():
                    return
                if dlg_token is not None and getattr(win, "_dlg_token", None) != dlg_token:
                    return
                win._is_submitting = False
            except Exception:
                return
        messagebox.showerror("Child Creation Failed", str(error))

    def _handle_create_child_permission_error(
        self,
        win: tk.Toplevel | None,
        dlg_token: str | None,
        error: Exception,
        session_generation: int,
    ) -> None:
        if session_generation != self._get_current_session_generation():
            return
        if win is not None:
            try:
                if not win.winfo_exists():
                    return
                if dlg_token is not None and getattr(win, "_dlg_token", None) != dlg_token:
                    return
                win._is_submitting = False
            except Exception:
                return
        self._handle_permission_error(error, session_generation=session_generation)

    # ============================================================================
    # Subtask C: Assessment Creation & Safe Desktop Context Transition (GUI)
    # ============================================================================

    def _update_downstream_tabs_mode(self) -> None:
        """Update downstream ingestion and review tabs when switching between legacy and V2 modes."""
        is_v2 = self._is_v2_mode()

        # Context bar assessment indicator
        if hasattr(self, "lbl_assessment_ctx") and self.lbl_assessment_ctx.winfo_exists():
            if self.active_assessment_id:
                self.lbl_assessment_ctx.config(
                    text=f"🔬 V2 Assessment: {self.active_assessment_id}",
                    bg="#f3e8ff",
                    fg="#6b21a8",
                )
            elif is_v2 and getattr(self, "active_child_id", None):
                self.lbl_assessment_ctx.config(
                    text=f"🔬 V2 Child: {self.active_child_id}",
                    bg="#f3e8ff",
                    fg="#6b21a8",
                )
            else:
                self.lbl_assessment_ctx.config(text="", bg="#f1f5f9", fg="#7e22ce")

        # Tab 2 Ingestion buttons
        v2_btn_state = "disabled" if is_v2 else "normal"
        for btn_name in (
            "btn_select_audio",
            "btn_process_audio",
            "btn_batch_ingest",
            "btn_ingest_demo",
            "btn_browse_text",
            "btn_ingest_text",
        ):
            if hasattr(self, btn_name):
                w = getattr(self, btn_name)
                if w and w.winfo_exists():
                    w.config(state=v2_btn_state)

        # Tab 2 Ingest Context Label
        if hasattr(self, "lbl_ingest_ctx") and self.lbl_ingest_ctx.winfo_exists():
            if is_v2:
                asmt_txt = f" [{self.active_assessment_id}]" if self.active_assessment_id else f" [Child: {self.active_child_id or '-'}]"
                self.lbl_ingest_ctx.config(
                    text=f"Active Context: Assessment V2{asmt_txt} (Legacy audio/text ingestion disabled in V2 mode)",
                    foreground="#6b21a8",
                )
            elif getattr(self, "active_case_id", None) and getattr(self, "active_session_id", None):
                self.lbl_ingest_ctx.config(
                    text=f"Active Context: Case {self.active_case_id} > Session {self.active_session_id}",
                    foreground="#0369a1",
                )
            else:
                self.lbl_ingest_ctx.config(
                    text="Please select a Session from Tab 1 to begin ingestion.",
                    foreground="#0369a1",
                )

        # Tab 3 Review Attest Button & Label
        if hasattr(self, "btn_attest") and self.btn_attest.winfo_exists():
            self.btn_attest.config(state=v2_btn_state)
        if hasattr(self, "lbl_review_status") and self.lbl_review_status.winfo_exists() and is_v2:
            self.lbl_review_status.config(
                text=f"Assessment V2 Context Active ({self.active_assessment_id or self.active_child_id or 'V2'}) - Review actions reserved for Stage 2",
                foreground="#6b21a8",
            )

    def _on_assessment_selected(self, event: Any = None) -> None:
        """Handle selection in Tab 1 Assessments directory treeview."""
        if not hasattr(self, "tree_assessments") or not self.tree_assessments.winfo_exists():
            return
        sel = self.tree_assessments.selection()
        if not sel:
            return
        asmt_id = sel[0]
        if (
            asmt_id in getattr(self, "_presentation_row_iids", set())
            or "presentation_error" in self.tree_assessments.item(asmt_id, "tags")
        ):
            # Presentation-only rows (e.g. error placeholders) are non-domain and cannot be selected
            self.tree_assessments.selection_remove(asmt_id)
            return

        # Increment monotonic assessment-selection generation
        self._assessment_selection_generation = getattr(self, "_assessment_selection_generation", 0) + 1
        asmt_sel_gen = self._assessment_selection_generation
        req_id = f"sel-asmt-{asmt_id}-{asmt_sel_gen}-{uuid.uuid4().hex[:8]}"
        self._current_assessment_selection_req_id = req_id

        # Check if complete record is already cached for active child
        cached_match = None
        for a in getattr(self, "_cached_assessments", []):
            if a.get("id") == asmt_id and a.get("child_id") == self.active_child_id:
                # Canonical contract requires non-empty id, child_id, purpose, and state
                if all(a.get(k) for k in ("id", "child_id", "purpose", "state")):
                    cached_match = a
                    break

        if cached_match:
            self.active_assessment_id = asmt_id
            self.active_assessment = cached_match
            self._update_downstream_tabs_mode()
            return

        # Cache miss or incomplete record: fetch canonical get_assessment asynchronously
        # Clear active assessment while loading new selection so failure doesn't show old assessment
        self.active_assessment_id = None
        self.active_assessment = None
        self._update_downstream_tabs_mode()
        self._current_assessment_detail_thread = self._fetch_assessment_detail(
            asmt_id=asmt_id,
            asmt_sel_gen=asmt_sel_gen,
            req_id=req_id,
        )

    def _fetch_assessment_detail(
        self,
        asmt_id: str,
        asmt_sel_gen: int | None = None,
        req_id: str | None = None,
    ) -> threading.Thread | None:
        if not self.active_child_id:
            return None

        child_id = self.active_child_id
        session_gen = self._get_current_session_generation()
        child_sel_gen = getattr(self, "_child_selection_generation", 0)
        if asmt_sel_gen is None:
            self._assessment_selection_generation = getattr(self, "_assessment_selection_generation", 0) + 1
            asmt_sel_gen = self._assessment_selection_generation
        if req_id is None:
            req_id = f"get-asmt-{asmt_id}-{asmt_sel_gen}-{uuid.uuid4().hex[:8]}"
            self._current_assessment_selection_req_id = req_id

        def worker() -> None:
            try:
                detail = self.client.get_assessment(asmt_id)
                self._async_queue.put((
                    lambda: self._on_assessment_detail_loaded(
                        asmt_id=asmt_id,
                        detail=detail,
                        child_id=child_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                        asmt_sel_gen=asmt_sel_gen,
                        request_id=req_id,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_assessment_detail_error(
                        asmt_id=asmt_id,
                        error=e,
                        child_id=child_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                        asmt_sel_gen=asmt_sel_gen,
                        request_id=req_id,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_assessment_detail_loaded(
        self,
        asmt_id: str,
        detail: dict[str, Any],
        child_id: str,
        session_gen: int,
        child_sel_gen: int,
        asmt_sel_gen: int,
        request_id: str,
    ) -> None:
        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if asmt_sel_gen != getattr(self, "_assessment_selection_generation", 0):
            return  # Superseded by newer selection
        if request_id != getattr(self, "_current_assessment_selection_req_id", None):
            return

        # Check detail.id matches requested assessment_id
        if not isinstance(detail, dict) or detail.get("id") != asmt_id:
            self.active_assessment_id = None
            self.active_assessment = None
            self._update_downstream_tabs_mode()
            messagebox.showerror(
                "Assessment ID Mismatch",
                f"Expected assessment ID '{asmt_id}', but received '{detail.get('id') if isinstance(detail, dict) else None}'.",
            )
            return

        # Verify assessment child_id matches currently active child
        if detail.get("child_id") != self.active_child_id:
            self.active_assessment_id = None
            self.active_assessment = None
            self._update_downstream_tabs_mode()
            messagebox.showerror(
                "Assessment Context Mismatch",
                f"Assessment '{asmt_id}' belongs to child '{detail.get('child_id')}', but current active child is '{self.active_child_id}'.",
            )
            return

        self.active_assessment_id = asmt_id
        self.active_assessment = detail
        # Update in _cached_assessments
        updated_cached = False
        for idx, a in enumerate(getattr(self, "_cached_assessments", [])):
            if a.get("id") == asmt_id:
                self._cached_assessments[idx] = detail
                updated_cached = True
                break
        if not updated_cached:
            if not hasattr(self, "_cached_assessments") or self._cached_assessments is None:
                self._cached_assessments = []
            self._cached_assessments.append(detail)

        self._update_downstream_tabs_mode()

    def _on_assessment_detail_error(
        self,
        asmt_id: str,
        error: Exception,
        child_id: str,
        session_gen: int,
        child_sel_gen: int,
        asmt_sel_gen: int,
        request_id: str,
    ) -> None:
        from packages.tui.client import LinguaLensAuthError
        if isinstance(error, LinguaLensAuthError) or (
            hasattr(error, "status_code") and getattr(error, "status_code", None) == 401
        ):
            if session_gen == self._get_current_session_generation():
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if asmt_sel_gen != getattr(self, "_assessment_selection_generation", 0):
            return  # Superseded by newer selection
        if request_id != getattr(self, "_current_assessment_selection_req_id", None):
            return

        self.active_assessment_id = None
        self.active_assessment = None
        self._update_downstream_tabs_mode()

        messagebox.showerror(
            "Assessment Load Failed",
            f"Failed to load details for assessment '{asmt_id}':\n{error}",
        )

    def _is_consent_active(self) -> bool:
        """Authoritative typed precheck of consent status before dispatching assessment creation."""
        status = getattr(self, "_current_consent_status", None)
        if status != "active":
            return False
        if not isinstance(getattr(self, "active_consent", None), dict):
            return False
        if self.active_consent.get("status") != "active":
            return False
        return True

    def _show_create_assessment_dialog(self) -> tk.Toplevel | None:
        """Show dialog to create a new clinical assessment context for the active child."""
        if not getattr(self, "active_child_id", None):
            messagebox.showwarning("No Child Selected", "Please select a child before creating an assessment.")
            return None

        if not self._is_consent_active():
            current_st = getattr(self, "_current_consent_status", "not-loaded")
            messagebox.showerror(
                "Active Consent Required",
                f"Cannot create assessment: Active clinical-assessment consent is required.\n"
                f"Current consent status: {current_st}\n\n"
                f"Please record active consent for this child first.",
            )
            return None

        win = tk.Toplevel(self.root)
        win.title("Create Clinical Assessment (V2)")
        win.geometry("520x360")
        win.transient(self.root)

        # Invalidate any prior assessment dialog
        if getattr(self, "_current_asmt_cancel_event", None):
            try:
                self._current_asmt_cancel_event.set()
            except Exception:
                pass

        dlg_token = f"dlg-asmt-{uuid.uuid4().hex[:8]}"
        cancel_event = threading.Event()
        win._dlg_token = dlg_token
        win._cancel_event = cancel_event
        self._current_asmt_dialog_token = dlg_token
        self._current_asmt_cancel_event = cancel_event
        win._bound_child_id = self.active_child_id
        child_code = self.active_child.get("display_code", self.active_child_id) if self.active_child else self.active_child_id
        win._bound_child_code = child_code
        win._bound_session_gen = self._get_current_session_generation()
        win._bound_child_sel_gen = getattr(self, "_child_selection_generation", 0)
        win._is_submitting = False

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frm,
            text=f"Create Assessment: {child_code}",
            font=("Helvetica", 11, "bold"),
            foreground="#1e293b",
        ).pack(anchor=tk.W, pady=(0, 10))

        # Purpose Selection (Canonical: initial, developmental_follow_up, post_intervention_follow_up, additional_evidence)
        ttk.Label(frm, text="Purpose:", font=("Helvetica", 9, "bold")).pack(anchor=tk.W, pady=(4, 2))
        combo_purpose = ttk.Combobox(
            frm,
            values=[
                "initial",
                "developmental_follow_up",
                "post_intervention_follow_up",
                "additional_evidence",
            ],
            state="readonly",
            font=("Helvetica", 10),
        )
        combo_purpose.set("initial")
        combo_purpose.pack(fill=tk.X, pady=(0, 10))

        # Optional Assigned Clinician ID
        ttk.Label(frm, text="Assigned Clinician ID (Optional):", font=("Helvetica", 9, "bold")).pack(anchor=tk.W, pady=(4, 2))
        entry_clinician = ttk.Entry(frm, font=("Helvetica", 10))
        entry_clinician.pack(fill=tk.X, pady=(0, 16))

        # Buttons
        btn_box = ttk.Frame(frm)
        btn_box.pack(fill=tk.X, pady=(10, 0))

        def on_close():
            win._cancel_event.set()
            in_flight_req = getattr(win, "_in_flight_req_id", None)
            if in_flight_req:
                self._set_busy_state(False, "Ready", request_id=in_flight_req)
            if win.winfo_exists():
                win.destroy()

        def on_destroy(event=None):
            if event is None or event.widget == win:
                win._cancel_event.set()
                in_flight_req = getattr(win, "_in_flight_req_id", None)
                if in_flight_req:
                    self._set_busy_state(False, "Ready", request_id=in_flight_req)

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.bind("<Destroy>", on_destroy)
        ttk.Button(btn_box, text="Cancel", command=on_close).pack(side=tk.RIGHT, padx=(6, 0))

        def on_confirm_click():
            p = combo_purpose.get().strip() or "initial"
            c = entry_clinician.get().strip() or None
            self._submit_create_assessment(win, purpose=p, clinician_id=c)

        btn_confirm = ttk.Button(btn_box, text="Create Assessment", command=on_confirm_click)
        btn_confirm.pack(side=tk.RIGHT)
        win.btn_confirm = btn_confirm

        return win

    def _submit_create_assessment(
        self,
        win: tk.Toplevel,
        purpose: str,
        clinician_id: str | None = None,
    ) -> threading.Thread | None:
        """Submit assessment creation with context-drift verification and background dispatch."""
        if getattr(win, "_is_submitting", False):
            return None

        target_child_id = getattr(win, "_bound_child_id", None)
        target_child_code = getattr(win, "_bound_child_code", target_child_id)
        target_session_gen = getattr(win, "_bound_session_gen", -1)
        target_child_sel_gen = getattr(win, "_bound_child_sel_gen", -1)

        # Context drift check before confirmation modal
        if (
            not target_child_id
            or target_child_id != self.active_child_id
            or target_session_gen != self._get_current_session_generation()
            or target_child_sel_gen != getattr(self, "_child_selection_generation", 0)
        ):
            messagebox.showerror(
                "Context Changed",
                "Clinical context changed or child is not active. Assessment creation aborted.",
                parent=win if win.winfo_exists() else self.root,
            )
            if win.winfo_exists():
                win.destroy()
            return None

        # Re-verify consent before dispatch
        if not self._is_consent_active():
            messagebox.showerror(
                "Active Consent Required",
                "Active clinical-assessment consent is required before dispatching assessment creation.",
                parent=win if win.winfo_exists() else self.root,
            )
            if win.winfo_exists():
                win.destroy()
            return None

        # Canonical purpose check - reject unsupported values without fallback
        canonical_purposes = (
            "initial",
            "developmental_follow_up",
            "post_intervention_follow_up",
            "additional_evidence",
        )
        clean_purpose = purpose.strip() if purpose else ""
        if clean_purpose not in canonical_purposes:
            messagebox.showerror(
                "Invalid Assessment Purpose",
                f"Assessment purpose '{clean_purpose}' is not supported.\nMust be one of: {', '.join(canonical_purposes)}.",
                parent=win if win.winfo_exists() else self.root,
            )
            return None

        clean_clinician = clinician_id.strip() if clinician_id else None
        if clean_clinician and len(clean_clinician) > 128:
            messagebox.showerror(
                "Invalid Clinician ID",
                "Assigned Clinician ID must not exceed 128 characters.",
                parent=win if win.winfo_exists() else self.root,
            )
            return None

        # Explicit confirmation
        confirm_msg = (
            f"Please confirm creating a new clinical assessment context:\n\n"
            f"• Child: {target_child_code} ({target_child_id})\n"
            f"• Purpose: {clean_purpose}\n"
            f"• Assigned Clinician: {clean_clinician or '(Default)'}\n\n"
            f"Are you sure you wish to proceed?"
        )
        parent_win = win if win.winfo_exists() else self.root
        try:
            confirmed = messagebox.askyesno("Confirm Assessment Creation", confirm_msg, parent=parent_win)
        except TypeError:
            confirmed = messagebox.askyesno("Confirm Assessment Creation", confirm_msg)
        if not confirmed:
            return None

        # Re-verify context drift after confirmation modal returns
        if (
            target_child_id != self.active_child_id
            or target_session_gen != self._get_current_session_generation()
            or target_child_sel_gen != getattr(self, "_child_selection_generation", 0)
        ):
            messagebox.showerror(
                "Context Changed",
                "Clinical context changed during confirmation. Assessment creation aborted.",
                parent=win if win.winfo_exists() else self.root,
            )
            if win.winfo_exists():
                win.destroy()
            return None

        win._is_submitting = True
        if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
            win.btn_confirm.config(state="disabled")

        dlg_token = getattr(win, "_dlg_token", "")
        self._current_asmt_dialog_token = dlg_token
        req_id = f"asmt-req-{uuid.uuid4().hex[:8]}"
        win._in_flight_req_id = req_id
        cancel_event = getattr(win, "_cancel_event", None)
        if cancel_event is None:
            cancel_event = threading.Event()
            win._cancel_event = cancel_event
        self._current_asmt_cancel_event = cancel_event

        self._set_busy_state(True, "Creating assessment...", request_id=req_id)

        def worker() -> None:
            try:
                # Preflight: Fresh asynchronous read of consent history before POST
                consents = self.client.list_consents(target_child_id)

                # Check cancellation immediately after preflight read
                if (
                    cancel_event.is_set()
                    or getattr(self, "_current_asmt_dialog_token", None) != dlg_token
                ):
                    # Cancelled before mutation dispatch: ZERO POST
                    self._async_queue.put((
                        lambda r=req_id: self._set_busy_state(False, "Ready", request_id=r),
                        None,
                    ))
                    return

                fresh_status, latest_rec = self._resolve_consent_state(consents, purpose="clinical_assessment")
                if fresh_status != "active" or not latest_rec or latest_rec.get("status") != "active":
                    self._async_queue.put((
                        lambda st=fresh_status, rec=latest_rec: self._on_create_assessment_preflight_failed(
                            win=win,
                            dlg_token=dlg_token,
                            request_id=req_id,
                            child_id=target_child_id,
                            fresh_status=st,
                            latest_rec=rec,
                            session_gen=target_session_gen,
                            child_sel_gen=target_child_sel_gen,
                        ),
                        None,
                    ))
                    return

                # Re-verify context drift and dialog lifetime/token after preflight before POST
                current_gen = self._get_current_session_generation()
                current_sel_gen = getattr(self, "_child_selection_generation", 0)
                current_dialog_token = getattr(self, "_current_asmt_dialog_token", None)
                if (
                    target_session_gen != current_gen
                    or target_child_sel_gen != current_sel_gen
                    or target_child_id != self.active_child_id
                    or current_dialog_token != dlg_token
                    or cancel_event.is_set()
                ):
                    # Context changed or cancelled: ZERO POST
                    self._async_queue.put((
                        lambda r=req_id: self._set_busy_state(False, "Ready", request_id=r),
                        None,
                    ))
                    return

                # Canonical contract: POST /api/v2/children/{child_id}/assessments
                # Body: purpose, optional assigned_clinician_id
                new_asmt = self.client.create_assessment(
                    target_child_id,
                    purpose=clean_purpose,
                    assigned_clinician_id=clean_clinician,
                )
                self._async_queue.put((
                    lambda: self._on_create_assessment_success(
                        win=win,
                        dlg_token=dlg_token,
                        request_id=req_id,
                        child_id=target_child_id,
                        new_asmt=new_asmt,
                        session_gen=target_session_gen,
                        child_sel_gen=target_child_sel_gen,
                        cancel_event=cancel_event,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_create_assessment_error(
                        win=win,
                        dlg_token=dlg_token,
                        request_id=req_id,
                        child_id=target_child_id,
                        error=e,
                        session_gen=target_session_gen,
                        child_sel_gen=target_child_sel_gen,
                        cancel_event=cancel_event,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_create_assessment_preflight_failed(
        self,
        win: tk.Toplevel,
        dlg_token: str,
        request_id: str,
        child_id: str,
        fresh_status: str,
        latest_rec: dict[str, Any] | None,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        self._set_busy_state(False, "Ready", request_id=request_id)

        if session_gen != self._get_current_session_generation():
            if win.winfo_exists():
                win.destroy()
            return

        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            if win.winfo_exists():
                win.destroy()
            return

        self.active_consent = latest_rec if fresh_status == "active" else None
        self._current_consent_status = fresh_status
        now_str = datetime.now().strftime("%H:%M:%S")
        self._consent_loaded_at = now_str
        self._update_consent_badge(fresh_status, latest_rec, loaded_at=now_str)

        if win.winfo_exists() and getattr(win, "_dlg_token", None) == dlg_token:
            win.destroy()

        messagebox.showerror(
            "Active Consent Required",
            f"Cannot create assessment: Clinical assessment consent is '{fresh_status}'.\n\n"
            f"Active consent is required before an assessment can be created. Please record active consent first.",
        )

    def _on_create_assessment_success(
        self,
        win: tk.Toplevel,
        dlg_token: str,
        request_id: str,
        child_id: str,
        new_asmt: dict[str, Any],
        session_gen: int,
        child_sel_gen: int,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._set_busy_state(False, "Ready", request_id=request_id)

        if cancel_event and cancel_event.is_set():
            return
        if getattr(self, "_current_asmt_dialog_token", None) != dlg_token:
            return

        if session_gen != self._get_current_session_generation():
            if win.winfo_exists():
                win.destroy()
            return

        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            if win.winfo_exists():
                win.destroy()
            return

        dialog_was_active = win.winfo_exists() and getattr(win, "_dlg_token", None) == dlg_token
        if dialog_was_active:
            win.destroy()

        if not dialog_was_active:
            # Dialog closed before response arrived; discard presentation
            return

        # Store created fact and activate assessment context immediately
        self.active_assessment_id = new_asmt.get("id")
        self.active_assessment = new_asmt
        # ISOLATION: active_session_id must NOT be polluted
        self.active_session_id = None
        self._update_downstream_tabs_mode()

        messagebox.showinfo("Success", f"Assessment created successfully: {self.active_assessment_id}")

        # Asynchronously refresh assessments list without blocking UI thread
        self._current_assessment_thread = self._refresh_assessments_after_creation(
            child_id=child_id,
            session_gen=session_gen,
            child_sel_gen=child_sel_gen,
            created_asmt=new_asmt,
        )

    def _on_create_assessment_error(
        self,
        win: tk.Toplevel,
        dlg_token: str,
        request_id: str,
        child_id: str,
        error: Exception,
        session_gen: int,
        child_sel_gen: int,
        cancel_event: threading.Event | None = None,
    ) -> None:
        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError, LinguaLensConflictError

        if isinstance(error, LinguaLensAuthError) or (
            hasattr(error, "status_code") and getattr(error, "status_code", None) == 401
        ):
            if session_gen == self._get_current_session_generation():
                if win.winfo_exists():
                    win.destroy()
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if cancel_event and cancel_event.is_set():
            return
        if getattr(self, "_current_asmt_dialog_token", None) != dlg_token:
            return

        if session_gen != self._get_current_session_generation():
            if win.winfo_exists():
                win.destroy()
            return

        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            if win.winfo_exists():
                win.destroy()
            return

        dialog_is_valid = win.winfo_exists() and getattr(win, "_dlg_token", None) == dlg_token

        if isinstance(error, LinguaLensPermissionError):
            if dialog_is_valid:
                win._is_submitting = False
                if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                    win.btn_confirm.config(state="normal")
                messagebox.showerror("Permission Denied", f"You do not have permission to create an assessment: {error}")
            return

        if isinstance(error, LinguaLensConflictError) or "409" in str(error):
            self.active_assessment_id = None
            self.active_assessment = None
            if dialog_is_valid:
                win._is_submitting = False
                if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                    win.btn_confirm.config(state="normal")
                messagebox.showerror("Assessment Conflict (409)", f"Consent Conflict: {error}")
            # Refresh authoritative consent state on 409 asynchronously without auto-retry POST
            self._current_consent_thread = self._refresh_consent()
            return

        if dialog_is_valid:
            win._is_submitting = False
            if hasattr(win, "btn_confirm") and win.btn_confirm.winfo_exists():
                win.btn_confirm.config(state="normal")
            messagebox.showerror("Assessment Creation Failed", f"Failed to create assessment:\n{error}")

    def _refresh_assessments(self) -> threading.Thread | None:
        """Asynchronously refresh assessments list for active child."""
        child_id = getattr(self, "active_child_id", None)
        if not child_id:
            if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
                for it in self.tree_assessments.get_children():
                    self.tree_assessments.delete(it)
            return None

        req_id = f"asmt-list-{child_id}-{uuid.uuid4().hex[:8]}"
        self._assessment_list_request_id = req_id
        session_gen = self._get_current_session_generation()
        child_sel_gen = getattr(self, "_child_selection_generation", 0)

        def worker() -> None:
            try:
                asmts = self.client.list_assessments(child_id)
                self._async_queue.put((
                    lambda: self._on_assessments_refreshed(
                        child_id=child_id,
                        assessments=asmts,
                        request_id=req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_assessments_refresh_error(
                        child_id=child_id,
                        error=e,
                        request_id=req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_assessments_refreshed(
        self,
        child_id: str,
        assessments: list[dict[str, Any]],
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if request_id != getattr(self, "_assessment_list_request_id", None):
            return

        self._cached_assessments = assessments
        self._presentation_row_iids = set()
        self._assessment_list_error = None
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            curr = self.lbl_status.cget("text")
            if "Failed to list assessments" in curr:
                self.lbl_status.config(text="Ready")

        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            for it in self.tree_assessments.get_children():
                self.tree_assessments.delete(it)
            for a in assessments:
                a_id = a.get("id", "")
                self.tree_assessments.insert(
                    "",
                    tk.END,
                    iid=a_id,
                    values=(
                        a_id,
                        a.get("child_id", ""),
                        a.get("purpose", ""),
                        a.get("state", ""),
                        a.get("assigned_clinician_id", ""),
                        a.get("version", 1),
                    ),
                )
            if getattr(self, "active_assessment_id", None) and self.active_assessment_id in self.tree_assessments.get_children():
                self.tree_assessments.selection_set(self.active_assessment_id)
                self.tree_assessments.see(self.active_assessment_id)

    def _on_assessments_refresh_error(
        self,
        child_id: str,
        error: Exception,
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        from packages.tui.client import LinguaLensAuthError
        if isinstance(error, LinguaLensAuthError) or (
            hasattr(error, "status_code") and getattr(error, "status_code", None) == 401
        ):
            if session_gen == self._get_current_session_generation():
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if request_id != getattr(self, "_assessment_list_request_id", None):
            return

        self._cached_assessments = []
        self._presentation_row_iids = {"_error"}
        self._assessment_list_error = str(error)

        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            for it in self.tree_assessments.get_children():
                self.tree_assessments.delete(it)
            self.tree_assessments.insert(
                "",
                tk.END,
                iid="_error",
                values=("⚠️ Error", child_id, "Failed to load assessments", str(error), "-", "-"),
                tags=("presentation_error",),
            )

        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.config(text=f"⚠️ Failed to list assessments: {error}")

    def _refresh_assessments_after_creation(
        self,
        child_id: str,
        session_gen: int,
        child_sel_gen: int,
        created_asmt: dict[str, Any],
    ) -> threading.Thread | None:
        """Refresh assessments list after successful creation, preserving creation fact if refresh fails."""
        req_id = f"asmt-post-ref-{child_id}-{uuid.uuid4().hex[:8]}"
        self._assessment_list_request_id = req_id

        def worker() -> None:
            try:
                asmts = self.client.list_assessments(child_id)
                self._async_queue.put((
                    lambda: self._on_post_creation_refresh_success(
                        child_id=child_id,
                        assessments=asmts,
                        request_id=req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                    ),
                    None,
                ))
            except Exception as exc:
                self._async_queue.put((
                    lambda e=exc: self._on_post_creation_refresh_error(
                        child_id=child_id,
                        error=e,
                        request_id=req_id,
                        session_gen=session_gen,
                        child_sel_gen=child_sel_gen,
                        created_asmt=created_asmt,
                    ),
                    exc,
                ))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def _on_post_creation_refresh_success(
        self,
        child_id: str,
        assessments: list[dict[str, Any]],
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
    ) -> None:
        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if request_id != getattr(self, "_assessment_list_request_id", None):
            return

        self._on_assessments_refreshed(child_id, assessments, request_id, session_gen, child_sel_gen)

    def _on_post_creation_refresh_error(
        self,
        child_id: str,
        error: Exception,
        request_id: str,
        session_gen: int,
        child_sel_gen: int,
        created_asmt: dict[str, Any],
    ) -> None:
        from packages.tui.client import LinguaLensAuthError
        if isinstance(error, LinguaLensAuthError):
            if session_gen == self._get_current_session_generation():
                self._handle_auth_error(error, session_generation=session_gen)
            return

        if session_gen != self._get_current_session_generation():
            return
        if child_sel_gen != getattr(self, "_child_selection_generation", 0) or child_id != self.active_child_id:
            return
        if request_id != getattr(self, "_assessment_list_request_id", None):
            return

        # Creation fact is preserved: active_assessment_id and active_assessment remain intact
        # Insert the created assessment into treeview manually if not present
        if hasattr(self, "tree_assessments") and self.tree_assessments.winfo_exists():
            a_id = created_asmt.get("id", "")
            if a_id and a_id not in self.tree_assessments.get_children():
                self.tree_assessments.insert(
                    "",
                    tk.END,
                    iid=a_id,
                    values=(
                        a_id,
                        created_asmt.get("child_id", ""),
                        created_asmt.get("purpose", ""),
                        created_asmt.get("state", ""),
                        created_asmt.get("assigned_clinician_id", ""),
                        created_asmt.get("version", 1),
                    ),
                )
                self.tree_assessments.selection_set(a_id)
                self.tree_assessments.see(a_id)

        messagebox.showwarning(
            "Assessment Created (Refresh Failed)",
            f"Assessment was created successfully on server ({created_asmt.get('id')}), but failed to refresh assessments list: {error}. Please refresh manually.",
        )
