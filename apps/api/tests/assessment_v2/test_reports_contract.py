import hashlib
import json
from datetime import datetime, timezone
import pytest

from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    CueStatus,
    FollowUpPlan,
)
from app.assessment_v2.reports import (
    ReportReadiness,
    ReportStatus,
    build_signed_report_snapshot,
    check_report_signoff_readiness,
    generate_report_draft_markdown,
)


def test_report_draft_generation_with_cues_and_disposition():
    """Verify draft markdown includes descriptive profile, limitations, clinician review, and disclaimers."""
    cues = [
        AttentionCue(
            cue_id="cue_01",
            assessment_id="asm_123",
            cue_type=AttentionCueType.LEXICAL_DIVERSITY,
            title="ความหลากหลายของคำศัพท์จำกัด",
            description="TTR ต่ำกว่าเกณฑ์อ้างอิง",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            supporting_feature_keys=["type_token_ratio"],
            limitations=["audio_duration_short"],
            status=CueStatus.ACKNOWLEDGED,
        )
    ]
    cues[0].apply_feedback("clinician_01", CueStatus.ACKNOWLEDGED, rationale="สอดคล้องกับพฤติกรรมในห้องตรวจ")

    follow_up = FollowUpPlan(
        target_date="2026-12-01",
        recommended_protocol="story_retell",
        focus_areas=["lexical_expansion"],
        monitoring_notes="นัดติดตามผล 3 เดือน",
    )

    md = generate_report_draft_markdown(
        child_code="C-101",
        assessment_date="2026-09-12",
        purpose="การประเมินเพื่อวางแผนการส่งเสริมพัฒนาการทางภาษาและการสื่อสาร",
        features={"type_token_ratio": 0.29, "words_per_minute": 35.0},
        limitations=["audio_duration_short"],
        cues=cues,
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        disposition_notes="วางแผนกระตุ้นภาษาที่บ้านและติดตามอาการ",
        follow_up=follow_up,
        comparisons={"mean_length_of_utterance": {"baseline": 2.1, "target": 2.8, "delta": 0.7, "unit": "morphemes"}},
    )

    assert "C-101" in md
    assert "การประเมินเพื่อวางแผนการส่งเสริมพัฒนาการทางภาษา" in md
    assert "ความหลากหลายของคำศัพท์จำกัด" in md
    assert "สอดคล้องกับพฤติกรรมในห้องตรวจ" in md
    assert "continue_monitoring" in md.lower() or "ติดตามพัฒนาการต่อเนื่อง" in md
    assert "ไม่สามารถใช้เพื่อการวินิจฉัยทางการแพทย์โดยตรง" in md  # Clinical safety disclaimer
    assert "mean_length_of_utterance" in md


def test_report_signoff_readiness_validation():
    """Verify readiness check fails closed if consent is revoked, cues are unreviewed, or disposition is missing."""
    cues_pending = [
        AttentionCue(
            cue_id="cue_01",
            assessment_id="asm_123",
            cue_type=AttentionCueType.LEXICAL_DIVERSITY,
            title="Lexical Cue",
            description="Desc",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            status=CueStatus.PENDING_REVIEW,  # NOT reviewed!
        )
    ]

    # 1. Blocked because cue is still pending review
    readiness = check_report_signoff_readiness(
        consent_status="consented",
        evidence_is_current=True,
        cues=cues_pending,
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        assigned_therapist_id="clinician_01",
        signing_user_id="clinician_01",
        markdown_text="Report markdown with valid disclaimers not a clinical diagnosis",
    )
    assert not readiness.can_sign_off
    assert any("pending_review" in r.lower() or "unreviewed" in r.lower() for r in readiness.blocking_reasons)

    # 2. Blocked because consent is revoked/withdrawn
    cues_reviewed = [
        AttentionCue(
            cue_id="cue_01",
            assessment_id="asm_123",
            cue_type=AttentionCueType.LEXICAL_DIVERSITY,
            title="Lexical Cue",
            description="Desc",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            status=CueStatus.ACKNOWLEDGED,
        )
    ]
    readiness_consent = check_report_signoff_readiness(
        consent_status="withdrawn",
        evidence_is_current=True,
        cues=cues_reviewed,
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        assigned_therapist_id="clinician_01",
        signing_user_id="clinician_01",
        markdown_text="Report markdown with valid disclaimers not a clinical diagnosis",
    )
    assert not readiness_consent.can_sign_off
    assert any("consent" in r.lower() for r in readiness_consent.blocking_reasons)

    # 3. Blocked because wrong clinician is attempting sign-off
    readiness_clinician = check_report_signoff_readiness(
        consent_status="consented",
        evidence_is_current=True,
        cues=cues_reviewed,
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        assigned_therapist_id="clinician_01",
        signing_user_id="clinician_99",  # WRONG CLINICIAN!
        markdown_text="Report markdown with valid disclaimers not a clinical diagnosis",
    )
    assert not readiness_clinician.can_sign_off
    assert any("assigned" in r.lower() or "clinician" in r.lower() for r in readiness_clinician.blocking_reasons)


def test_immutable_signed_snapshot_and_hash():
    """Verify signed snapshot payload produces deterministic bit-reproducible SHA-256 hash."""
    snapshot, hash_1 = build_signed_report_snapshot(
        report_id="rep_001",
        assessment_id="asm_123",
        tenant_id="tenant_abc",
        child_code="C-101",
        report_version=1,
        evidence_run_id="ev_run_456",
        comparison_id="cmp_789",
        review_id="rev_101",
        purpose="Speech and language follow-up",
        observations=[],
        descriptive_profile={"type_token_ratio": 0.35},
        comparisons=None,
        limitations=["short_sample"],
        disposition="continue_monitoring",
        follow_up_plan={"target_date": "2026-12-01"},
        clinician_review=[{"cue_id": "cue_01", "status": "acknowledged"}],
        markdown_content="# Report for C-101\nValid content",
        signed_by="Dr. Somsak",
        signed_at_iso="2026-09-12T01:00:00Z",
    )

    # Rebuilding with exact same input must yield identical hash
    _, hash_2 = build_signed_report_snapshot(
        report_id="rep_001",
        assessment_id="asm_123",
        tenant_id="tenant_abc",
        child_code="C-101",
        report_version=1,
        evidence_run_id="ev_run_456",
        comparison_id="cmp_789",
        review_id="rev_101",
        purpose="Speech and language follow-up",
        observations=[],
        descriptive_profile={"type_token_ratio": 0.35},
        comparisons=None,
        limitations=["short_sample"],
        disposition="continue_monitoring",
        follow_up_plan={"target_date": "2026-12-01"},
        clinician_review=[{"cue_id": "cue_01", "status": "acknowledged"}],
        markdown_content="# Report for C-101\nValid content",
        signed_by="Dr. Somsak",
        signed_at_iso="2026-09-12T01:00:00Z",
    )

    assert hash_1 == hash_2
    assert len(hash_1) == 64
    assert snapshot["signed_by"] == "Dr. Somsak"
    assert snapshot["snapshot_hash"] == hash_1
