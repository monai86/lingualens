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

        from packages.gui.radar_renderer import RadarChartRenderer
        radar_svg = RadarChartRenderer.render_svg(findings.get("metrics", {}))

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
            radar_svg=radar_svg,
        )

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        messagebox.showinfo("Exported", f"Saved bilingual clinical HTML report to:\n{out_file}")
        return out_file

    @staticmethod
    def export_pdf_report(
        client: Any,
        active_case_id: str | None,
        active_session_id: str | None,
        active_transcript: dict[str, Any] | None,
        narrative: str,
        recommendations: str,
    ) -> str | None:
        """Export a professional, print-ready bilingual clinical PDF report with embedded Spider Diagram and SHA-256 seal."""
        import os
        import shutil
        import subprocess
        import tempfile

        if not active_session_id:
            messagebox.showwarning("Warning", "Please select a Session first.")
            return None
        if not active_transcript or not active_transcript.get("utterances"):
            messagebox.showwarning("No Data", "Cannot export report: No session data recorded yet.")
            return None

        out_file = filedialog.asksaveasfilename(
            title="Save Clinical PDF Report",
            defaultextension=".pdf",
            initialfile=f"clinical_report_{active_session_id}.pdf",
            filetypes=[("PDF Document", "*.pdf"), ("All Files", "*.*")],
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

        from packages.gui.radar_renderer import RadarChartRenderer
        radar_svg = RadarChartRenderer.render_svg(findings.get("metrics", {}))

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
            radar_svg=radar_svg,
        )

        # First attempt: Headless browser with pixel-perfect font rendering
        chrome_bins = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "google-chrome",
            "chromium",
        ]
        chrome_path = next((p for p in chrome_bins if os.path.exists(p) or shutil.which(p)), None)

        pdf_done = False
        if chrome_path:
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp_html:
                tmp_html.write(html_content)
                tmp_html_path = tmp_html.name
            try:
                cmd = [
                    chrome_path,
                    "--headless",
                    "--disable-gpu",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={out_file}",
                    f"file://{tmp_html_path}",
                ]
                subprocess.run(cmd, check=True, capture_output=True, timeout=15)
                pdf_done = True
            except Exception:
                pass
            finally:
                if os.path.exists(tmp_html_path):
                    try:
                        os.remove(tmp_html_path)
                    except Exception:
                        pass

        if not pdf_done:
            # Fallback: ReportLab builder
            ClinicalExportEngine._render_reportlab_pdf(
                out_path=out_file,
                case_info=case_info,
                session_info=session_info,
                findings=findings,
                narrative=narrative,
                recommendations=recommendations,
                attested_by=attested_by,
            )

        messagebox.showinfo("Exported", f"Saved bilingual clinical PDF report to:\n{out_file}")
        return out_file

    @staticmethod
    def _render_reportlab_pdf(
        out_path: str,
        case_info: dict[str, Any],
        session_info: dict[str, Any],
        findings: dict[str, Any],
        narrative: str,
        recommendations: str,
        attested_by: str | None,
    ) -> None:
        import os
        import hashlib
        from datetime import datetime
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_thai = "Helvetica"
        for p in [
            "/System/Library/Fonts/Supplemental/Thonburi.ttc",
            "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
            os.path.expanduser("~/Library/Fonts/Poppins-Regular.ttf"),
        ]:
            if os.path.exists(p):
                try:
                    pdfmetrics.registerFont(TTFont("ClinicalFont", p))
                    font_thai = "ClinicalFont"
                    break
                except Exception:
                    pass

        doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            "TitleStyle",
            fontName=font_thai,
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#1e1e62"),
        )
        style_sub = ParagraphStyle(
            "SubStyle",
            fontName=font_thai,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        style_body = ParagraphStyle(
            "BodyStyle",
            fontName=font_thai,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
        )
        style_meta = ParagraphStyle(
            "MetaStyle",
            fontName=font_thai,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
        )

        story = []
        story.append(Paragraph("<b>✦ LinguaLens</b> — Clinical Speech-Language Assessment Report", style_title))
        story.append(Paragraph("รายงานผลการประเมินพัฒนาการภาษาและการพูดทางคลินิก (Clinical Prototype)", style_sub))
        story.append(Spacer(1, 8))

        # Notice Banner
        banner_data = [[Paragraph("<b>Clinical Decision-Support Prototype • Non-Diagnostic • Requires Clinician Sign-off</b><br/>ระบบสนับสนุนการตัดสินใจทางคลินิก • มิใช่เครื่องมือวินิจฉัยโรค • ต้องได้รับการรับรองจากนักบำบัด", style_meta)]]
        banner_tab = Table(banner_data, colWidths=[520])
        banner_tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fef3c7")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(banner_tab)
        story.append(Spacer(1, 10))

        # Metadata Table
        case_id = case_info.get("case_id", "N/A")
        child_id = case_info.get("child_id", "N/A")
        sess_id = session_info.get("session_id", "N/A")
        sess_dt = session_info.get("session_date", "N/A")
        lang = str(case_info.get("primary_language", "th")).upper()

        meta_data = [
            [Paragraph(f"<b>Case ID:</b> {case_id}", style_meta), Paragraph(f"<b>Child ID:</b> {child_id}", style_meta), Paragraph(f"<b>Language:</b> {lang}", style_meta)],
            [Paragraph(f"<b>Session ID:</b> {sess_id}", style_meta), Paragraph(f"<b>Date:</b> {sess_dt}", style_meta), Paragraph(f"<b>Attestation:</b> {'Attested' if attested_by else 'Draft'}", style_meta)],
        ]
        meta_tab = Table(meta_data, colWidths=[170, 175, 175])
        meta_tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8faff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e0e7ff")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_tab)
        story.append(Spacer(1, 12))

        # Thai LSA Table
        story.append(Paragraph("<b>1. Thai Language Sample Analysis (LSA) Metrics / ดัชนีโครงสร้างภาษาไทย</b>", style_title))
        story.append(Spacer(1, 5))

        metrics = findings.get("metrics", {})
        metrics_data = [
            [Paragraph("<b>Metric / ตัวชี้วัด</b>", style_meta), Paragraph("<b>Value / ค่า</b>", style_meta), Paragraph("<b>Clinical Description / คำอธิบายทางคลินิก</b>", style_meta)],
            [Paragraph("MLU-w (Mean Length of Utterance)", style_meta), Paragraph(str(metrics.get("mlu_words", "-")), style_meta), Paragraph("ความยาวประโยคเฉลี่ย (คำ/ประโยค)", style_meta)],
            [Paragraph("TTR (Type-Token Ratio)", style_meta), Paragraph(str(metrics.get("ttr", "-")), style_meta), Paragraph("ความหลากหลายของคลังคำศัพท์", style_meta)],
            [Paragraph("Questions (ประโยคคำถาม)", style_meta), Paragraph(f"{metrics.get('question_count', '-')} ครั้ง", style_meta), Paragraph("การใช้คำถามเพื่อสืบค้นข้อมูล", style_meta)],
            [Paragraph("Negations (ประโยคปฏิเสธ)", style_meta), Paragraph(f"{metrics.get('negation_count', '-')} ครั้ง", style_meta), Paragraph("การใช้คำปฏิเสธ (ไม่/อย่า)", style_meta)],
            [Paragraph("Pronouns (คำสรรพนาม)", style_meta), Paragraph(f"{metrics.get('pronoun_count', '-')} ครั้ง", style_meta), Paragraph("การใช้สรรพนามแทนบุคคล", style_meta)],
            [Paragraph("Polite Particles (คำลงท้ายสุภาพ)", style_meta), Paragraph(f"{metrics.get('polite_particle_count', '-')} ครั้ง", style_meta), Paragraph("คำลงท้ายสุภาพ (ครับ/ค่ะ/จ๊ะ)", style_meta)],
            [Paragraph("Mood Particles (คำแสดงอารมณ์)", style_meta), Paragraph(f"{metrics.get('mood_particle_count', '-')} ครั้ง", style_meta), Paragraph("คำแสดงอารมณ์/เจตนา (นะ/สิ/ด้วย)", style_meta)],
            [Paragraph("Conjunctions (คำเชื่อมประโยค)", style_meta), Paragraph(f"{metrics.get('conjunction_count', '-')} ครั้ง", style_meta), Paragraph("คำเชื่อมประโยค (และ/หรือ/เพราะ)", style_meta)],
            [Paragraph("Fillers (คำเสริม/คำลังเล)", style_meta), Paragraph(f"{metrics.get('filler_word_count', '-')} ครั้ง", style_meta), Paragraph("คำเสริมหรือคำลังเล (เอ่อ/อ่า)", style_meta)],
            [Paragraph("Turn-Taking Ratio (การผลัดกันพูด)", style_meta), Paragraph(str(metrics.get("turn_taking_ratio", "-")), style_meta), Paragraph("การมีส่วนร่วมและผลัดกันพูด", style_meta)],
        ]
        lsa_tab = Table(metrics_data, colWidths=[180, 100, 240])
        lsa_tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e7ff")),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(lsa_tab)
        story.append(Spacer(1, 10))

        # Narrative & Recommendations
        story.append(Paragraph("<b>2. Clinical Narrative & Observations / บทวิเคราะห์ของนักอรรถบำบัด</b>", style_title))
        story.append(Spacer(1, 3))
        story.append(Paragraph(narrative.replace("\n", "<br/>") if narrative else "No narrative entered.", style_body))
        story.append(Spacer(1, 10))

        story.append(Paragraph("<b>3. Therapy Recommendations & Goals / ข้อเสนอแนะและเป้าหมายการบำบัด</b>", style_title))
        story.append(Spacer(1, 3))
        story.append(Paragraph(recommendations.replace("\n", "<br/>") if recommendations else "No recommendations entered.", style_body))
        story.append(Spacer(1, 12))

        # Attestation & Hash
        sha = hashlib.sha256(f"{case_id}:{sess_id}:{datetime.now().isoformat()}".encode()).hexdigest()
        signer = attested_by or "Draft — Pending Clinician Attestation"
        sig_data = [
            [
                Paragraph(f"<b>Clinician Sign-off:</b><br/>{signer}<br/>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M')}", style_meta),
                Paragraph(f"<b>Digital Integrity Hash (SHA-256):</b><br/>{sha}<br/><i>Sealed & Verified via LinguaLens Export Engine</i>", style_meta),
            ]
        ]
        sig_tab = Table(sig_data, colWidths=[260, 260])
        sig_tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sig_tab)

        doc.build(story)
