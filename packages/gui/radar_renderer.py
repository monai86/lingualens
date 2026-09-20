"""Radar / Spider chart renderer for LinguaLens clinical developmental comparisons."""

from __future__ import annotations

import math
from typing import Any
import tkinter as tk


class RadarChartRenderer:
    """Renders native radar chart comparing Child values vs Typical Development (TD) Norms."""

    def __init__(
        self,
        canvas: tk.Canvas,
        summary_widget: tk.Text | None = None,
        font_family: str = "Helvetica",
    ) -> None:
        self.canvas = canvas
        self.summary_widget = summary_widget
        self.font_family = font_family

    def draw(self, metrics: dict[str, Any]) -> None:
        """Render radar chart comparing Child session metrics to TD norm baselines."""
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        width = max(280, self.canvas.winfo_width()) if self.canvas.winfo_width() > 1 else 380
        height = max(240, self.canvas.winfo_height()) if self.canvas.winfo_height() > 1 else 330
        cx, cy = width / 2, height / 2 - 5
        radius = max(60, min(cx, cy) - 45)

        has_child_data = bool(
            metrics
            and (metrics.get("mlu_words") is not None or metrics.get("total_child_utterances", 0) > 0)
            and metrics.get("total_child_utterances", 0) > 0
        )

        f0_val = metrics.get("f0_iqr_hz") if has_child_data else None
        f0_float = float(f0_val) if f0_val is not None and f0_val != "N/A" else None
        sp_val = metrics.get("speech_rate_wpm") if has_child_data else None
        sp_float = float(sp_val) if sp_val is not None and sp_val != "N/A" else None

        mlu_val = float(metrics["mlu_words"]) if has_child_data and metrics.get("mlu_words") is not None else None
        ttr_val = float(metrics["ttr"]) if has_child_data and metrics.get("ttr") is not None else None
        tt_val = float(metrics["turn_taking_ratio"]) if has_child_data and metrics.get("turn_taking_ratio") is not None else None
        intel_val = float(metrics["intelligibility_rate"]) if has_child_data and metrics.get("intelligibility_rate") is not None else None

        axes = [
            {"label": "MLU-w\n(Sentence)", "val": mlu_val, "td": 3.5, "unit": "words"},
            {"label": "TTR\n(Vocab)", "val": ttr_val, "td": 0.75, "unit": ""},
            {"label": "Turn-Taking\n(Reciprocity)", "val": tt_val, "td": 0.90, "unit": ""},
            {"label": "Intelligibility\n(Clarity)", "val": intel_val, "td": 0.95, "unit": ""},
            {"label": "Speech Rate\n(WPM)", "val": sp_float, "td": 90.0, "unit": "wpm"},
            {"label": "Prosody IQR\n(F0 Range)", "val": f0_float, "td": 35.0, "unit": "Hz"},
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
            self.canvas.create_polygon(
                pts,
                fill="",
                outline="#94a3b8" if is_norm else "#e2e8f0",
                width=1.5 if is_norm else 1,
                dash=(3, 2) if is_norm else (),
            )

        # Spokes and labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            self.canvas.create_line(
                cx, cy, cx + radius * math.cos(angle), cy + radius * math.sin(angle),
                fill="#e2e8f0", width=1
            )
            x_lbl = cx + (radius + 22) * math.cos(angle)
            y_lbl = cy + (radius + 22) * math.sin(angle)
            self.canvas.create_text(
                x_lbl, y_lbl,
                text=ax["label"],
                font=(self.font_family, 8, "bold"),
                fill="#475569",
                justify=tk.CENTER,
            )

        # Typical Development (TD) Baseline Polygon (100% ring)
        td_pts = []
        for i in range(n):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            r_td = radius * (1.0 / 1.2)
            td_pts.extend([cx + r_td * math.cos(angle), cy + r_td * math.sin(angle)])
        self.canvas.create_polygon(td_pts, fill="", outline="#10b981", width=2, dash=(4, 2))

        # Child Session Data Polygon
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
                self.canvas.create_polygon(child_pts, fill="#e0f2fe", outline="#0284c7", width=2.5)

            for i, ax in enumerate(axes):
                if ax["val"] is not None:
                    px, py = child_pts[i * 2], child_pts[i * 2 + 1]
                    self.canvas.create_oval(
                        px - 3.5, py - 3.5, px + 3.5, py + 3.5,
                        fill="#0369a1", outline="white", width=1
                    )

            # Summary text
            if self.summary_widget:
                self.summary_widget.config(state=tk.NORMAL)
                self.summary_widget.delete("1.0", tk.END)
                self.summary_widget.insert(tk.END, "Spider Diagram (Developmental Comparison vs Norms):\n\n", "title")
                self.summary_widget.insert(tk.END, "● Green Dashed Line: Typical Development (TD Norm 100%)\n", "green")
                self.summary_widget.insert(tk.END, "■ Blue Shaded Area: Child Session Evaluation\n\n", "blue")
                for ax in axes:
                    lbl_clean = ax["label"].split("\n")[0]
                    if ax["val"] is not None:
                        pct = int((ax["val"] / ax["td"]) * 100) if ax["td"] else 100
                        unit_str = f" {ax['unit']}" if ax["unit"] else ""
                        status_mark = "✓" if pct >= 85 else ("▲" if pct >= 65 else "●")
                        self.summary_widget.insert(
                            tk.END,
                            f"{status_mark} {lbl_clean}: {ax['val']}{unit_str} (Norm: {ax['td']}{unit_str}) — {pct}%\n",
                        )
                    else:
                        self.summary_widget.insert(tk.END, f"○ {lbl_clean}: N/A (Audio acoustic data required)\n")
                self.summary_widget.config(state=tk.DISABLED)
        else:
            # Clean Empty State
            self.canvas.create_rectangle(
                cx - 130, cy - 26, cx + 130, cy + 26,
                fill="#f8fafc", outline="#cbd5e1", width=1
            )
            self.canvas.create_text(
                cx, cy - 7,
                text="No evaluation data in this session",
                font=(self.font_family, 9, "bold"),
                fill="#64748b",
            )
            self.canvas.create_text(
                cx, cy + 10,
                text="(Ingest audio or transcript in Tab 2)",
                font=(self.font_family, 8),
                fill="#94a3b8",
            )

            if self.summary_widget:
                self.summary_widget.config(state=tk.NORMAL)
                self.summary_widget.delete("1.0", tk.END)
                self.summary_widget.insert(tk.END, "Spider Diagram (Developmental Comparison vs Norms):\n\n", "title")
                self.summary_widget.insert(tk.END, "● Green Dashed Line: Typical Development (TD Norm 100%)\n\n", "green")
                self.summary_widget.insert(tk.END, "No Evaluation Data Available\n\n", "title")
                self.summary_widget.insert(
                    tk.END,
                    "Please ingest session audio or dialogue transcript in Tab 2 (Ingest Material) to compute LSA metrics and acoustic prosody profile.",
                )
                self.summary_widget.config(state=tk.DISABLED)
