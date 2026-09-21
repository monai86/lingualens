"""Radar / Spider chart renderer for LinguaLens clinical developmental comparisons."""

from __future__ import annotations

import math
from typing import Any
import tkinter as tk


def get_normative_benchmarks(age_months: int | None = None) -> dict[str, Any]:
    """Retrieve developmental normative benchmarks tailored to child age bracket (24-60m)."""
    if not age_months or age_months < 24:
        return {
            "label": "Standard TD Norm (36m)",
            "mlu_td": 3.0,
            "ttr_td": 0.65,
            "tt_td": 0.80,
            "intel_td": 0.85,
            "sp_td": 70.0,
            "f0_td": 35.0,
        }
    elif age_months < 36:  # 24-35m
        return {
            "label": "24–35m Cohort Norm",
            "mlu_td": 2.2,
            "ttr_td": 0.52,
            "tt_td": 0.65,
            "intel_td": 0.75,
            "sp_td": 55.0,
            "f0_td": 40.0,
        }
    elif age_months < 48:  # 36-47m
        return {
            "label": "36–47m Cohort Norm",
            "mlu_td": 3.2,
            "ttr_td": 0.62,
            "tt_td": 0.80,
            "intel_td": 0.88,
            "sp_td": 75.0,
            "f0_td": 35.0,
        }
    else:  # 48-60+ m
        return {
            "label": "48–60m Cohort Norm",
            "mlu_td": 4.2,
            "ttr_td": 0.70,
            "tt_td": 0.90,
            "intel_td": 0.95,
            "sp_td": 95.0,
            "f0_td": 32.0,
        }


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

    def draw(self, metrics: dict[str, Any], age_months: int | None = None) -> None:
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

        if age_months is None:
            try:
                age_months = int(metrics.get("age_months") or 0) or None
            except Exception:
                age_months = None
        norm = get_normative_benchmarks(age_months)

        axes = [
            {"label": "MLU-w\n(Sentence)", "val": mlu_val, "td": norm["mlu_td"], "unit": "words"},
            {"label": "TTR\n(Vocab)", "val": ttr_val, "td": norm["ttr_td"], "unit": ""},
            {"label": "Turn-Taking\n(Reciprocity)", "val": tt_val, "td": norm["tt_td"], "unit": ""},
            {"label": "Intelligibility\n(Clarity)", "val": intel_val, "td": norm["intel_td"], "unit": ""},
            {"label": "Speech Rate\n(WPM)", "val": sp_float, "td": norm["sp_td"], "unit": "wpm"},
            {"label": "Prosody IQR\n(F0 Range)", "val": f0_float, "td": norm["f0_td"], "unit": "Hz"},
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

    @staticmethod
    def render_svg(metrics: dict[str, Any], width: int = 400, height: int = 340, age_months: int | None = None) -> str:
        """Generate a standalone SVG string of the radar spider chart for printable HTML reports."""
        cx, cy = width / 2, height / 2 - 12
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

        if age_months is None:
            try:
                age_months = int(metrics.get("age_months") or 0) or None
            except Exception:
                age_months = None
        norm = get_normative_benchmarks(age_months)

        axes = [
            {"label": "MLU-w", "val": mlu_val, "td": norm["mlu_td"], "unit": "words"},
            {"label": "TTR", "val": ttr_val, "td": norm["ttr_td"], "unit": ""},
            {"label": "Turn-Taking", "val": tt_val, "td": norm["tt_td"], "unit": ""},
            {"label": "Intelligibility", "val": intel_val, "td": norm["intel_td"], "unit": ""},
            {"label": "Speech Rate", "val": sp_float, "td": norm["sp_td"], "unit": "wpm"},
            {"label": "Prosody IQR", "val": f0_float, "td": norm["f0_td"], "unit": "Hz"},
        ]
        n = len(axes)
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; display: inline-block;">',
            f'<rect width="{width}" height="{height}" fill="#ffffff" rx="8" />',
        ]

        # Background grid rings
        for r_ratio in [0.25, 0.5, 0.75, 1.0, 1.2]:
            r = radius * (r_ratio / 1.2)
            is_td = (r_ratio == 1.0)
            stroke_color = "#10b981" if is_td else "#e2e8f0"
            stroke_width = 2 if is_td else 1
            dash_attr = 'stroke-dasharray="4,4"' if is_td else ''
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                pts.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
            svg_parts.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}" {dash_attr} />')

        # Axis rays & labels
        for i, ax in enumerate(axes):
            angle = -math.pi / 2 + (2 * math.pi * i / n)
            x_end = cx + radius * math.cos(angle)
            y_end = cy + radius * math.sin(angle)
            svg_parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x_end:.1f}" y2="{y_end:.1f}" stroke="#cbd5e1" stroke-width="1" />')

            lbl_r = radius + 22
            lx = cx + lbl_r * math.cos(angle)
            ly = cy + lbl_r * math.sin(angle)
            anchor = "middle" if abs(math.cos(angle)) < 0.2 else ("start" if math.cos(angle) > 0 else "end")
            val_str = f" ({ax['val']:.1f})" if ax["val"] is not None else ""
            svg_parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="11" font-weight="600" fill="#475569">{ax["label"]}{val_str}</text>')

        # Child polygon
        if has_child_data:
            child_pts = []
            for i, ax in enumerate(axes):
                angle = -math.pi / 2 + (2 * math.pi * i / n)
                val = ax["val"]
                ratio = min(max(val / ax["td"], 0.0), 1.2) if val is not None and ax["td"] else 0.0
                r = radius * (ratio / 1.2)
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                child_pts.append((px, py))
            pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in child_pts)
            svg_parts.append(f'<polygon points="{pts_str}" fill="rgba(3, 105, 161, 0.25)" stroke="#0284c7" stroke-width="2.5" />')
            for px, py in child_pts:
                svg_parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#0369a1" stroke="#ffffff" stroke-width="1.5" />')
        else:
            svg_parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="12" fill="#94a3b8">No session evaluation data</text>')

        # Legend
        svg_parts.append(f'<g transform="translate({cx - 140}, {height - 18})">')
        svg_parts.append('<line x1="0" y1="6" x2="22" y2="6" stroke="#10b981" stroke-width="2" stroke-dasharray="4,3" />')
        svg_parts.append('<text x="26" y="10" font-size="10" fill="#047857">TD Benchmark Norm (100%)</text>')
        svg_parts.append('<rect x="160" y="2" width="16" height="8" fill="rgba(3, 105, 161, 0.4)" stroke="#0284c7" stroke-width="1.5" />')
        svg_parts.append('<text x="182" y="10" font-size="10" fill="#0369a1">Child Session Evaluation</text>')
        svg_parts.append('</g>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)
