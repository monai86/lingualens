"""Unit tests for ClinicalExportEngine and clinical_report_template."""

from __future__ import annotations

from packages.gui.radar_renderer import RadarChartRenderer
from packages.reports.clinical_report_template import generate_bilingual_clinical_html


def test_radar_svg_generation():
    metrics = {
        "mlu_words": 3.42,
        "ttr": 0.68,
        "turn_taking_ratio": 0.85,
        "intelligibility_rate": 0.94,
        "speech_rate_wpm": 88.5,
        "f0_median_hz": 308.2,
        "f0_iqr_hz": 28.4,
        "total_child_utterances": 14,
    }
    svg = RadarChartRenderer.render_svg(metrics)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "<polygon" in svg
    assert "MLU-w" in svg
    assert "TD Benchmark Norm" in svg


def test_bilingual_clinical_html_report_generation():
    metrics = {
        "mlu_words": 3.42,
        "ttr": 0.68,
        "total_child_words": 48,
        "unique_words_count": 33,
        "question_count": 4,
        "negation_count": 2,
        "pronoun_count": 6,
        "polite_particle_count": 5,
        "echolalia_count": 1,
        "turn_taking_count": 12,
        "intelligibility_rate": 0.94,
        "f0_median_hz": 308.2,
    }
    svg = RadarChartRenderer.render_svg(metrics)

    longitudinal = [
        {"session_id": "SESS-001", "date": "2026-09-01", "utterances": 20, "chi_turns": 8, "mlu_w": 2.2, "ttr": 0.54, "f0_median": 320},
        {"session_id": "SESS-002", "date": "2026-09-20", "utterances": 35, "chi_turns": 14, "mlu_w": 3.42, "ttr": 0.68, "f0_median": 308},
    ]

    html = generate_bilingual_clinical_html(
        case_info={"case_id": "CASE-101", "child_id": "CHI-101", "birth_year_month": "2021-05", "primary_language": "th"},
        session_info={"session_id": "SESS-002", "session_date": "2026-09-20", "notes": "Play-based assessment"},
        findings={"metrics": metrics, "guideline_links": [{"construct": "Expressive", "status": "Age Expected", "evidence": "Normal"}]},
        narrative="Child engaged well with toy kitchen set.",
        recommendations="Continue conversational turn-taking practice.",
        attested_by="Kru Aum (Certified SLP)",
        longitudinal_sessions=longitudinal,
        radar_svg=svg,
    )

    assert "CASE-101" in html
    assert "CHI-101" in html
    assert "🗣️ LinguaLens Clinical LSA Report" in html
    assert "Thai Clinical Language Structure" in html
    assert "MLU-w (ความยาวประโยค)" in html
    assert "Longitudinal Assessment Trajectory" in html
    assert "SESS-001" in html
    assert "SESS-002" in html
    assert "btn-print" in html
    assert "พิมพ์รายงาน / Save as PDF" in html
    assert "Kru Aum (Certified SLP)" in html
    assert "Clinical Safety Boundary" in html


def test_render_reportlab_pdf(tmp_path):
    from packages.gui.export_engine import ClinicalExportEngine
    out_pdf = str(tmp_path / "test_report.pdf")
    metrics = {
        "mlu_words": 3.42,
        "ttr": 0.68,
        "question_count": 2,
        "negation_count": 1,
        "pronoun_count": 3,
        "polite_particle_count": 4,
        "mood_particle_count": 2,
        "conjunction_count": 2,
        "filler_word_count": 1,
        "turn_taking_ratio": 0.85,
    }
    ClinicalExportEngine._render_reportlab_pdf(
        out_path=out_pdf,
        case_info={"case_id": "CASE-101", "child_id": "CHI-101", "primary_language": "th"},
        session_info={"session_id": "SESS-002", "session_date": "2026-09-20"},
        findings={"metrics": metrics},
        narrative="Child engaged well with toy blocks.",
        recommendations="Continue conversational turn-taking practice.",
        attested_by="Kru Aum (Certified SLP)",
    )
    import os
    assert os.path.exists(out_pdf)
    assert os.path.getsize(out_pdf) > 2000

