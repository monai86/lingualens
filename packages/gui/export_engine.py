"""Clinical Export Engine for TalkBank CHAT, Biomarkers CSV, and Bilingual HTML Reports."""

from __future__ import annotations

import csv
from typing import Any
import tkinter as tk
from tkinter import filedialog, messagebox


class ClinicalExportEngine:
    """Encapsulates report and transcript exports outside the GUI view shell."""

    @staticmethod
    def export_cha_file(
        active_transcript: dict[str, Any] | None,
        active_session_id: str | None,
        fallback_text: str = "",
    ) -> str | None:
        """Export authentic TalkBank CHAT (.cha) transcript with %mor: tiers."""
        if not active_transcript:
            messagebox.showwarning("No Data", "No transcript available to export.")
            return None

        out_file = filedialog.asksaveasfilename(
            title="Save TalkBank CHAT File",
            defaultextension=".cha",
            initialfile=f"{active_session_id or 'transcript'}.cha",
            filetypes=[("TalkBank CHAT", "*.cha"), ("Text", "*.txt")],
        )
        if not out_file:
            return None

        raw_cha = active_transcript.get("raw_cha")
        if not raw_cha:
            raw_cha = fallback_text.strip()
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(raw_cha + "\n")
        messagebox.showinfo("Exported", f"Saved TalkBank CHAT file to:\n{out_file}")
        return out_file

    @staticmethod
    def export_csv_biomarkers(
        client: Any,
        active_case_id: str | None,
        active_session_id: str | None,
    ) -> str | None:
        """Export tabular speech, language, and acoustic biomarker parameters to CSV."""
        if not active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return None

        findings = client.get_findings(active_session_id)
        out_file = filedialog.asksaveasfilename(
            title="Save Biomarkers CSV",
            defaultextension=".csv",
            initialfile=f"biomarkers_{active_session_id}.csv",
            filetypes=[("CSV File", "*.csv"), ("Text", "*.txt")],
        )
        if not out_file:
            return None

        with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["case_id", "session_id", "metric_name", "metric_value"])
            for k, v in findings.get("metrics", {}).items():
                writer.writerow([active_case_id, active_session_id, k, v])
        messagebox.showinfo("Exported", f"Saved Biomarkers CSV to:\n{out_file}")
        return out_file

    @staticmethod
    def export_html_report(
        client: Any,
        active_case_id: str | None,
        active_session_id: str | None,
        active_transcript: dict[str, Any] | None,
        narrative: str,
        recommendations: str,
    ) -> str | None:
        """Export a comprehensive, beautifully styled bilingual clinical HTML report ready for printing/PDF."""
        if not active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return None
        if not active_transcript or not active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return None

        out_file = filedialog.asksaveasfilename(
            title="Save Clinical HTML Report",
            defaultextension=".html",
            initialfile=f"clinical_report_{active_session_id}.html",
            filetypes=[("HTML Document", "*.html"), ("All Files", "*.*")],
        )
        if not out_file:
            return None

        findings = client.get_findings(active_session_id)
        case_info = next((c for c in client.list_cases() if c.get("case_id") == active_case_id), {})
        session_info = next(
            (s for s in client.list_sessions(active_case_id) if s.get("session_id") == active_session_id),
            {"session_id": active_session_id},
        )

        longitudinal_sessions = []
        if active_case_id:
            for s in client.list_sessions(active_case_id):
                s_id = s["session_id"]
                s_dt = s.get("session_date", "N/A")
                tr = client.get_session_transcript(s_id)
                f = client.get_findings(s_id)
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
        attested_by = (
            active_transcript.get("attested_by", "Kru Aum (Certified SLP)")
            if active_transcript.get("attested")
            else None
        )

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

        messagebox.showinfo("Exported", f"Saved bilingual clinical HTML report to:\n{out_file}")
        return out_file
