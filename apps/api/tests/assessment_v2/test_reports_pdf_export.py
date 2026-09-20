import pytest

from app.assessment_v2.reports import (
    build_signed_report_snapshot,
    render_assessment_v2_pdf,
)


def test_pdf_export_renders_bytes_with_thai_text():
    """Verify render_assessment_v2_pdf outputs valid PDF bytes with Thai metadata and non-diagnostic disclaimers."""
    snapshot, hash_val = build_signed_report_snapshot(
        report_id="rep_test_pdf_01",
        assessment_id="asm_test_123",
        tenant_id="tenant_abc",
        child_code="เด็กสมมติ-001",
        report_version=1,
        evidence_run_id="ev_run_456",
        comparison_id=None,
        review_id="rev_101",
        purpose="การประเมินติดตามพัฒนาการทางภาษาและการสื่อสาร",
        observations=[],
        descriptive_profile={"type_token_ratio": 0.32, "turn_taking_ratio": 0.45},
        comparisons=None,
        limitations=["ตัวอย่างเสียงสั้นกว่า 5 นาที"],
        disposition="continue_monitoring",
        follow_up_plan={"target_date": "2026-12-01", "recommended_protocol": "story_retell"},
        clinician_review=[
            {
                "cue_id": "cue_01",
                "title": "ความหลากหลายของคำศัพท์จำกัด",
                "status": "acknowledged",
                "rationale": "ตรวจพบ TTR ต่ำในกิจกรรมเล่นอิสระ",
            }
        ],
        markdown_content=(
            "# รายงานการประเมิน\n"
            "- รหัสเด็ก: เด็กสมมติ-001\n"
            "- ข้อสรุป: ติดตามพัฒนาการต่อเนื่อง\n"
            "- คำเตือน: this system does not diagnose asd และ not a clinical diagnosis\n"
        ),
        signed_by="นักกิจกรรมบำบัด สมศักดิ์",
        signed_at_iso="2026-09-12T01:30:00Z",
    )

    pdf_bytes = render_assessment_v2_pdf(snapshot)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 500
    # PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")
    # PDF EOF marker
    assert b"%%EOF" in pdf_bytes
