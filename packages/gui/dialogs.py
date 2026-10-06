"""Modal dialog windows factory for PasaScope clinical desktop application."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable
import tkinter as tk
from tkinter import ttk, messagebox


class ClinicalDialogFactory:
    """Constructs focused modal dialog windows with isolated geometry and validation."""

    @staticmethod
    def build_create_case_dialog(
        parent: tk.Widget,
        client: Any,
        default_case_code: str = "C-001",
        on_success: Callable[[dict[str, Any]], None] | None = None,
    ) -> tk.Toplevel:
        win = tk.Toplevel(parent)
        win.title("Create Child Case — PasaScope")
        win.geometry("420x280")
        win.minsize(380, 240)
        win.bind("<Escape>", lambda e: win.destroy())

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Child Identifier:").grid(row=0, column=0, sticky=tk.W, pady=6)
        e_cid = ttk.Entry(frame)
        e_cid.insert(0, default_case_code)
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

        def _do_create() -> None:
            try:
                new_c = client.create_case(
                    e_cid.get().strip(),
                    e_dob.get().strip(),
                    e_lang.get().strip(),
                    e_notes.get().strip(),
                )
                if on_success:
                    on_success(new_c)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Case Creation Failed", str(exc))

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Create Case", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_cid.focus_set()
        return win

    @staticmethod
    def build_create_session_dialog(
        parent: tk.Widget,
        client: Any,
        active_case_id: str,
        on_success: Callable[[dict[str, Any]], None] | None = None,
    ) -> tk.Toplevel:
        win = tk.Toplevel(parent)
        win.title("Start Therapy Session — PasaScope")
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

        def _do_create() -> None:
            if not active_case_id:
                return
            try:
                new_s = client.create_session(
                    active_case_id,
                    e_date.get().strip(),
                    e_notes.get().strip(),
                )
                if on_success:
                    on_success(new_s)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Session Creation Failed", str(exc))

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=2, column=0, columnspan=2, pady=(16, 0), sticky=tk.E)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Start Session", style="Primary.TButton", command=_do_create).pack(side=tk.RIGHT)
        e_date.focus_set()
        return win

    @staticmethod
    def build_ingest_progress_dialog(
        parent: tk.Widget,
        title: str = "Ingesting Audio File...",
    ) -> tuple[tk.Toplevel, ttk.Progressbar, ttk.Label]:
        dialog = tk.Toplevel(parent)
        dialog.title("Processing Audio — PasaScope")
        dialog.geometry("420x160")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()

        frm = ttk.Frame(dialog, padding=20)
        frm.pack(fill=tk.BOTH, expand=True)

        lbl = ttk.Label(frm, text=title, font=("Helvetica", 10, "bold"))
        lbl.pack(pady=(0, 12))

        progress = ttk.Progressbar(frm, mode="determinate", length=360)
        progress.pack(pady=(0, 8))

        detail_lbl = ttk.Label(frm, text="Preparing speech processing...", font=("Helvetica", 9))
        detail_lbl.pack()

        return dialog, progress, detail_lbl
