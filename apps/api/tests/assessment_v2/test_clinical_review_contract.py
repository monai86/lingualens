from datetime import datetime, timezone
import pytest

from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    ClinicalReviewSession,
    CueStatus,
    FollowUpPlan,
    evaluate_attention_cues,
)


def test_attention_cue_contract_structure():
    """Verify AttentionCue enforces non-exclusive representations and policy versioning."""
    cue = AttentionCue(
        cue_id="cue_001",
        assessment_id="asm_123",
        cue_type=AttentionCueType.LEXICAL_DIVERSITY,
        title="ความหลากหลายของคำศัพท์จำกัด (Limited Lexical Diversity)",
        description="ค่า Type-Token Ratio (TTR) ต่ำกว่าเกณฑ์อ้างอิงของช่วงอายุ",
        policy_version="cues-v2.0",
        evidence_run_id="ev_run_456",
        supporting_feature_keys=["type_token_ratio", "moving_average_ttr"],
        conflicting_feature_keys=[],
        limitations=["อิงตามตัวอย่างการพูดสั้นกว่า 50 คำ"],
        status=CueStatus.PENDING_REVIEW,
    )

    assert cue.cue_id == "cue_001"
    assert cue.status == CueStatus.PENDING_REVIEW
    assert cue.policy_version == "cues-v2.0"
    assert "type_token_ratio" in cue.supporting_feature_keys
    assert cue.clinician_feedback is None


def test_multiple_concerns_are_non_exclusive():
    """
    Ensure concerns (e.g. lexical diversity, response latency, interaction)
    are independent cues and NOT ranked as exclusive ASD vs Developmental Delay percentages.
    """
    cues = [
        AttentionCue(
            cue_id="cue_lex",
            assessment_id="asm_123",
            cue_type=AttentionCueType.LEXICAL_DIVERSITY,
            title="Lexical Diversity Cue",
            description="Low vocabulary variety",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            supporting_feature_keys=["type_token_ratio"],
            conflicting_feature_keys=[],
            limitations=[],
            status=CueStatus.PENDING_REVIEW,
        ),
        AttentionCue(
            cue_id="cue_lat",
            assessment_id="asm_123",
            cue_type=AttentionCueType.RESPONSE_LATENCY,
            title="Response Latency Cue",
            description="Long pause before responding to clinician prompts",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            supporting_feature_keys=["response_latency_mean"],
            conflicting_feature_keys=[],
            limitations=[],
            status=CueStatus.PENDING_REVIEW,
        ),
        AttentionCue(
            cue_id="cue_turn",
            assessment_id="asm_123",
            cue_type=AttentionCueType.INTERACTION_TURN_TAKING,
            title="Turn Taking Cue",
            description="Reduced interactive turn-taking balance",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_456",
            supporting_feature_keys=["turn_taking_ratio"],
            conflicting_feature_keys=[],
            limitations=[],
            status=CueStatus.PENDING_REVIEW,
        ),
    ]

    # Every cue is distinct and non-exclusive
    cue_types = [c.cue_type for c in cues]
    assert len(cue_types) == 3
    assert len(set(cue_types)) == 3
    # No cue carries a diagnostic probability or percentage ranking
    for c in cues:
        assert not hasattr(c, "probability")
        assert not hasattr(c, "asd_risk_percentage")


def test_clinician_feedback_lifecycle():
    """Verify clinician can acknowledge, disagree, or request more evidence with rationale."""
    cue = AttentionCue(
        cue_id="cue_001",
        assessment_id="asm_123",
        cue_type=AttentionCueType.LEXICAL_DIVERSITY,
        title="Lexical Cue",
        description="Desc",
        policy_version="cues-v2.0",
        evidence_run_id="ev_run_456",
        supporting_feature_keys=["type_token_ratio"],
        conflicting_feature_keys=[],
        limitations=[],
        status=CueStatus.PENDING_REVIEW,
    )

    # 1. Clinician disagrees with rationale
    cue.apply_feedback(
        reviewer_id="clinician_01",
        status=CueStatus.DISAGREED,
        rationale="บริบทการเล่นเด็กกำลังจดจ่อกับของเล่นตัวเดียว ทำให้ใช้คำซ้ำ ไม่ใช่ข้อจำกัดทางภาษาทั่วไป",
    )
    assert cue.status == CueStatus.DISAGREED
    assert cue.clinician_feedback is not None
    assert cue.clinician_feedback.reviewer_id == "clinician_01"
    assert "บริบทการเล่น" in cue.clinician_feedback.rationale

    # 2. Clinician requests more evidence
    cue.apply_feedback(
        reviewer_id="clinician_01",
        status=CueStatus.MORE_EVIDENCE_REQUESTED,
        rationale="ตัวอย่างเสียงสั้นเกินไป ควรประเมินซ้ำในกิจกรรมเล่าเรื่อง",
    )
    assert cue.status == CueStatus.MORE_EVIDENCE_REQUESTED
    assert cue.clinician_feedback.rationale.startswith("ตัวอย่างเสียงสั้นเกินไป")


def test_clinical_review_session_disposition_and_followup():
    """Verify review session stores disposition, follow-up plan, and versioning."""
    session = ClinicalReviewSession(
        review_id="rev_101",
        assessment_id="asm_123",
        tenant_id="tenant_abc",
        child_id="child_789",
        evidence_run_id="ev_run_456",
        version=1,
        cues=[],
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        disposition_notes="ติดตามพัฒนาการทางภาษาต่อเนื่องในอีก 3 เดือน",
        follow_up=FollowUpPlan(
            target_date="2026-12-15",
            recommended_protocol="story_retell",
            focus_areas=["turn_taking", "vocabulary_expansion"],
            monitoring_notes="เน้นกิจกรรมเล่าเรื่องและการมีส่วนร่วม",
        ),
        reviewed_by="clinician_01",
        reviewed_at=datetime.now(timezone.utc),
        is_stale=False,
    )

    assert session.version == 1
    assert session.disposition == ClinicalDispositionType.CONTINUE_MONITORING
    assert session.follow_up.recommended_protocol == "story_retell"
    assert "turn_taking" in session.follow_up.focus_areas
    assert not session.is_stale


def test_evaluate_attention_cues_from_features():
    """Verify rule evaluation generates non-exclusive cues based on measured evidence."""
    features = {
        "type_token_ratio": 0.28,  # low lexical diversity
        "turn_taking_ratio": 0.15,  # low turn taking
        "speech_rate_wpm": 30.0,
    }
    limitations = ["audio_duration_short"]

    cues = evaluate_attention_cues(
        assessment_id="asm_123",
        evidence_run_id="ev_run_456",
        features=features,
        limitations=limitations,
        policy_version="cues-v2.0",
    )

    assert len(cues) >= 2
    types = [c.cue_type for c in cues]
    assert AttentionCueType.LEXICAL_DIVERSITY in types
    assert AttentionCueType.INTERACTION_TURN_TAKING in types
    # All cues start as pending_review
    for cue in cues:
        assert cue.status == CueStatus.PENDING_REVIEW
        assert "audio_duration_short" in cue.limitations
