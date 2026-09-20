from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
from io import BytesIO
import json
import os
from typing import Any

from app.assessment_v2.clinical_review import (
    AttentionCue,
    ClinicalDispositionType,
    CueStatus,
    FollowUpPlan,
)
from app.services.report_safety_validator import ReportSafetyValidator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportStatus(str, Enum):
    DRAFT = "draft"
    SIGNED_OFF = "signed_off"
    AMENDED = "amended"
    SUPERSEDED = "superseded"


@dataclass
class ReportReadiness:
    can_sign_off: bool
    blocking_reasons: list[str] = field(default_factory=list)


def check_report_signoff_readiness(
    consent_status: str,
    evidence_is_current: bool,
    cues: list[AttentionCue],
    disposition: ClinicalDispositionType | None,
    assigned_therapist_id: str | None,
    signing_user_id: str | None,
    markdown_text: str,
    expected_version: int | None = None,
    current_version: int | None = None,
) -> ReportReadiness:
    """
    Validates all server-side prerequisites before allowing immutable sign-off.
    Fails closed if any clinical safety or governance constraint is violated.
    """
    reasons: list[str] = []

    # 1. Caregiver consent check
    if consent_status != "consented":
        reasons.append(f"Caregiver consent is not active (current status: '{consent_status}').")

    # 2. Evidence currency
    if not evidence_is_current:
        reasons.append("Report findings are based on superseded or stale evidence; please regenerate.")

    # 3. Attention cues review completeness
    unreviewed = [c for c in cues if c.status == CueStatus.PENDING_REVIEW]
    if unreviewed:
        reasons.append(f"{len(unreviewed)} attention cue(s) are pending_review. All cues must be acknowledged or disagreed.")

    # 4. Clinician disposition presence
    if not disposition:
        reasons.append("Clinician disposition and action plan are required before sign-off.")

    # 5. Assigned clinician match
    if not assigned_therapist_id:
        reasons.append("No primary clinician is assigned to this child case.")
    elif signing_user_id is not None and signing_user_id != assigned_therapist_id:
        reasons.append(
            f"Report sign-off is restricted to the assigned clinician ('{assigned_therapist_id}'), caller is '{signing_user_id}'."
        )

    # 6. Concurrency version match
    if expected_version is not None and current_version is not None and expected_version != current_version:
        reasons.append(
            f"Optimistic concurrency mismatch: expected version {expected_version}, but report is at version {current_version}."
        )

    # 7. Text safety validation
    validator = ReportSafetyValidator()
    safety_res = validator.validate_report(markdown_text, source="finalization")
    if safety_res.finalization_blocked or safety_res.status == "failed":
        reasons.append(f"Safety violations detected in report text: {', '.join(safety_res.prohibited_phrases_found or safety_res.missing_required_disclaimers)}")

    return ReportReadiness(can_sign_off=len(reasons) == 0, blocking_reasons=reasons)


def generate_report_draft_markdown(
    child_code: str,
    assessment_date: str,
    purpose: str,
    features: dict[str, Any],
    limitations: list[str],
    cues: list[AttentionCue],
    disposition: ClinicalDispositionType | None,
    disposition_notes: str | None,
    follow_up: FollowUpPlan | None,
    comparisons: dict[str, Any] | None = None,
) -> str:
    """Generates standard therapist report markdown with full disclaimers and structured sections."""
    lines: list[str] = [
        f"# รายงานการประเมินพัฒนาการทางภาษาและการสื่อสาร (Speech-Language Assessment Report)",
        f"- **รหัสประจำตัวเด็ก (Child Code):** {child_code}",
        f"- **วันที่ประเมิน (Assessment Date):** {assessment_date}",
        f"- **วัตถุประสงค์ (Purpose):** {purpose}",
        "",
        "## 1. ผลการวัดลักษณะทางภาษา (Measured Language Sample Features)",
    ]

    if not features:
        lines.append("- *ไม่พบข้อมูลคุณลักษณะที่ประเมินได้จากตัวอย่างการพูด (Limited or unavailable evidence)*")
    else:
        for k, v in sorted(features.items()):
            lines.append(f"- **{k}**: {v}")

    lines.extend([
        "",
        "## 2. จุดสังเกตทางคลินิกที่ผ่านการทบทวน (Reviewed Clinical Attention Cues)",
    ])
    if not cues:
        lines.append("- *ไม่พบจุดสังเกตเฉพาะเจาะจงที่เข้าข่ายต้องเฝ้าระวังในการประเมินนี้*")
    else:
        for c in cues:
            status_th = "รับทราบแล้ว (Acknowledged)" if c.status == CueStatus.ACKNOWLEDGED else "ไม่เห็นด้วย (Disagreed)" if c.status == CueStatus.DISAGREED else "ขอหลักฐานเพิ่ม (More Evidence Requested)" if c.status == CueStatus.MORE_EVIDENCE_REQUESTED else "รอการตรวจทาน (Pending Review)"
            lines.append(f"### • {c.title}")
            lines.append(f"- รายละเอียด: {c.description}")
            lines.append(f"- สถานะการตรวจทาน: {status_th}")
            if c.clinician_feedback and c.clinician_feedback.rationale:
                lines.append(f"- ความเห็นนักบำบัด: {c.clinician_feedback.rationale}")

    if comparisons:
        lines.extend([
            "",
            "## 3. การเปรียบเทียบพัฒนาการตามช่วงเวลา (Longitudinal Comparison)",
            "- *การเปรียบเทียบเป็นข้อมูลเชิงพรรณนาเพื่อสนับสนุนการติดตามทางคลินิกเท่านั้น*",
        ])
        for feat_key, cmp_data in comparisons.items():
            b_val = cmp_data.get("baseline")
            t_val = cmp_data.get("target")
            delta = cmp_data.get("delta")
            unit = cmp_data.get("unit", "")
            lines.append(f"- **{feat_key}**: baseline={b_val}, target={t_val}, delta={delta} {unit}")

    lines.extend([
        "",
        "## 4. ข้อจำกัดของข้อมูลและการประเมิน (Limitations & Data Boundaries)",
    ])
    if limitations:
        for lim in limitations:
            lines.append(f"- {lim}")
    else:
        lines.append("- ข้อมูลการประเมินอยู่ภายใต้ข้อจำกัดของบริบทกิจกรรมและระยะเวลาบันทึกเสียง")

    disp_val = disposition.value if disposition else "ยังไม่ได้ระบุ"
    lines.extend([
        "",
        "## 5. แผนการดูแลและข้อสรุปทางคลินิก (Clinical Disposition & Plan)",
        f"- **ข้อสรุปแนวทาง (Disposition):** {disp_val}",
    ])
    if disposition_notes:
        lines.append(f"- **บันทึกเพิ่มเติม:** {disposition_notes}")

    if follow_up:
        lines.append(f"- **วันนัดติดตามผล:** {follow_up.target_date or 'ตามดุลยพินิจ'}")
        if follow_up.recommended_protocol:
            lines.append(f"- **โพรโทคอลที่แนะนำ:** {follow_up.recommended_protocol}")
        if follow_up.focus_areas:
            lines.append(f"- **ประเด็นมุ่งเน้น:** {', '.join(follow_up.focus_areas)}")
        if follow_up.monitoring_notes:
            lines.append(f"- **คำแนะนำผู้ปกครอง/นักบำบัด:** {follow_up.monitoring_notes}")

    lines.extend([
        "",
        "## 6. คำเตือนและความปลอดภัยทางคลินิก (Clinical Safety Disclaimer)",
        "- ระบบนี้เป็นเครื่องมือสนับสนุนการทำงานวิจัยและการศึกษาทางคลินิกของนักบำบัด (not a clinical diagnosis)",
        "- ไม่สามารถใช้เพื่อการวินิจฉัยทางการแพทย์โดยตรง หรือใช้ระบุระดับความรุนแรงของโรคออทิซึม (this system does not diagnose asd)",
        "- การแปลผลและการตัดสินใจทุกประการขึ้นอยู่กับการตรวจวินิจฉัยโดยตรงของแพทย์และนักกิจกรรมบำบัด/แก้ไขการพูดผู้เชี่ยวชาญ",
    ])

    return "\n".join(lines)


def build_signed_report_snapshot(
    report_id: str,
    assessment_id: str,
    tenant_id: str,
    child_code: str,
    report_version: int,
    evidence_run_id: str,
    comparison_id: str | None,
    review_id: str,
    purpose: str,
    observations: list[dict[str, Any]],
    descriptive_profile: dict[str, Any],
    comparisons: dict[str, Any] | None,
    limitations: list[str],
    disposition: str,
    follow_up_plan: dict[str, Any] | None,
    clinician_review: list[dict[str, Any]],
    markdown_content: str,
    signed_by: str,
    signed_at_iso: str,
) -> tuple[dict[str, Any], str]:
    """
    Builds a canonical, deterministic signed snapshot payload and computes its SHA-256 hash.
    Once created, this snapshot must never be modified.
    """
    payload: dict[str, Any] = {
        "report_id": report_id,
        "assessment_id": assessment_id,
        "tenant_id": tenant_id,
        "child_code": child_code,
        "report_version": report_version,
        "evidence_run_id": evidence_run_id,
        "comparison_id": comparison_id,
        "review_id": review_id,
        "purpose": purpose,
        "observations": observations,
        "descriptive_profile": descriptive_profile,
        "comparisons": comparisons,
        "limitations": limitations,
        "disposition": disposition,
        "follow_up_plan": follow_up_plan,
        "clinician_review": clinician_review,
        "markdown_content": markdown_content,
        "signed_by": signed_by,
        "signed_at": signed_at_iso,
    }

    # Canonical sorted JSON string for bit-reproducible hash
    canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    snapshot_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    payload["snapshot_hash"] = snapshot_hash
    return payload, snapshot_hash


def render_assessment_v2_pdf(snapshot: dict[str, Any]) -> bytes | None:
    """Renders signed report snapshot to PDF bytes using ReportLab with Thai font support."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        return None

    # Register Thai font if available
    font_name = "Helvetica"
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
        "/System/Library/Fonts/Supplemental/Thonburi.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in font_candidates:
        if os.path.exists(candidate):
            try:
                pdfmetrics.registerFont(TTFont("LinguaLensThai", candidate))
                font_name = "LinguaLensThai"
                break
            except Exception:
                continue

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title & Header
    pdf.setFont(font_name, 14)
    pdf.drawString(48, height - 48, f"LinguaLens Assessment Report - {snapshot.get('child_code')}")
    pdf.setFont(font_name, 9)
    pdf.drawString(48, height - 64, f"Report ID: {snapshot.get('report_id')} | Hash: {snapshot.get('snapshot_hash', '')[:16]}...")
    pdf.drawString(48, height - 76, f"Signed By: {snapshot.get('signed_by')} on {snapshot.get('signed_at')}")
    pdf.line(48, height - 82, width - 48, height - 82)

    # Content body
    text = pdf.beginText(48, height - 100)
    text.setFont(font_name, 9)

    md = snapshot.get("markdown_content", "")
    for raw_line in md.splitlines():
        line = raw_line[:95]
        if text.getY() < 60:
            pdf.drawText(text)
            pdf.showPage()
            text = pdf.beginText(48, height - 48)
            text.setFont(font_name, 9)
        text.textLine(line)

    pdf.drawText(text)

    # Footer Disclaimer
    pdf.setFont(font_name, 8)
    pdf.drawString(48, 30, "Non-diagnostic clinical research prototype. LinguaLens does not diagnose ASD.")
    pdf.save()

    return buffer.getvalue()
