from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AttentionCueType(str, Enum):
    LEXICAL_DIVERSITY = "lexical_diversity"
    RESPONSE_LATENCY = "response_latency"
    ACOUSTIC_PROSODIC = "acoustic_prosodic"
    INTERACTION_TURN_TAKING = "interaction_turn_taking"
    ARTICULATION_CLARITY = "articulation_clarity"
    SPARSE_COMMUNICATION = "sparse_communication"


class CueStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    ACKNOWLEDGED = "acknowledged"
    DISAGREED = "disagreed"
    MORE_EVIDENCE_REQUESTED = "more_evidence_requested"


class ClinicalDispositionType(str, Enum):
    CONTINUE_MONITORING = "continue_monitoring"
    REFERRAL_SPECIALIST = "referral_specialist"
    HOME_ACTIVITIES_PLAN = "home_activities_plan"
    TARGETED_SPEECH_THERAPY = "targeted_speech_therapy"
    COLLECT_MORE_EVIDENCE = "collect_more_evidence"


@dataclass(frozen=True)
class ClinicianFeedback:
    reviewer_id: str
    reviewed_at: datetime
    status: CueStatus
    rationale: str | None = None


@dataclass
class AttentionCue:
    cue_id: str
    assessment_id: str
    cue_type: AttentionCueType
    title: str
    description: str
    policy_version: str
    evidence_run_id: str
    supporting_feature_keys: list[str] = field(default_factory=list)
    conflicting_feature_keys: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    status: CueStatus = CueStatus.PENDING_REVIEW
    clinician_feedback: ClinicianFeedback | None = None

    def apply_feedback(
        self,
        reviewer_id: str,
        status: CueStatus,
        rationale: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> None:
        self.status = status
        self.clinician_feedback = ClinicianFeedback(
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at or utc_now(),
            status=status,
            rationale=rationale,
        )


@dataclass
class FollowUpPlan:
    target_date: str | None = None
    recommended_protocol: str | None = None
    focus_areas: list[str] = field(default_factory=list)
    monitoring_notes: str | None = None


@dataclass
class ClinicalReviewSession:
    review_id: str
    assessment_id: str
    tenant_id: str
    child_id: str
    evidence_run_id: str
    version: int = 1
    cues: list[AttentionCue] = field(default_factory=list)
    disposition: ClinicalDispositionType | None = None
    disposition_notes: str | None = None
    follow_up: FollowUpPlan | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    is_stale: bool = False


def evaluate_attention_cues(
    assessment_id: str,
    evidence_run_id: str,
    features: dict[str, Any],
    limitations: list[str] | None = None,
    policy_version: str = "cues-v2.0",
) -> list[AttentionCue]:
    """
    Evaluates rule-based, non-exclusive descriptive attention cues from measured features.
    
    CRITICAL CLINICAL SAFETY:
    - Never generates ASD vs Delay percentage distributions or probabilities.
    - Multiple cues are independent and descriptive of the speech/language sample.
    - All cues start as PENDING_REVIEW and must be explicitly reviewed by the therapist.
    """
    base_limitations = list(limitations or [])
    cues: list[AttentionCue] = []

    # 1. Lexical Diversity rule: TTR < 0.35 or moving average TTR < 0.35
    ttr = features.get("type_token_ratio")
    mattr = features.get("moving_average_ttr")
    if (ttr is not None and isinstance(ttr, (int, float)) and ttr < 0.35) or (
        mattr is not None and isinstance(mattr, (int, float)) and mattr < 0.35
    ):
        sup = []
        if ttr is not None:
            sup.append("type_token_ratio")
        if mattr is not None:
            sup.append("moving_average_ttr")
        cues.append(
            AttentionCue(
                cue_id=f"cue_lex_{uuid.uuid4().hex[:8]}",
                assessment_id=assessment_id,
                cue_type=AttentionCueType.LEXICAL_DIVERSITY,
                title="ความหลากหลายของคำศัพท์จำกัด (Limited Lexical Diversity)",
                description="ตรวจพบสัดส่วนคำศัพท์ไม่ซ้ำ (Type-Token Ratio) ต่ำกว่าเกณฑ์อ้างอิงทั่วไปของตัวอย่างภาษา",
                policy_version=policy_version,
                evidence_run_id=evidence_run_id,
                supporting_feature_keys=sup,
                conflicting_feature_keys=[],
                limitations=base_limitations,
                status=CueStatus.PENDING_REVIEW,
            )
        )

    # 2. Interaction / Turn-taking rule: turn_taking_ratio < 0.25
    turn_ratio = features.get("turn_taking_ratio")
    if turn_ratio is not None and isinstance(turn_ratio, (int, float)) and turn_ratio < 0.25:
        cues.append(
            AttentionCue(
                cue_id=f"cue_turn_{uuid.uuid4().hex[:8]}",
                assessment_id=assessment_id,
                cue_type=AttentionCueType.INTERACTION_TURN_TAKING,
                title="การสลับบทสนทนาลดลง (Reduced Turn-Taking)",
                description="ตรวจพบสัดส่วนการผลัดเปลี่ยนบทสนทนากับคู่สนทนาต่ำกว่าค่าเฉลี่ยของกิจกรรมสื่อสารแบบมีโครงสร้าง",
                policy_version=policy_version,
                evidence_run_id=evidence_run_id,
                supporting_feature_keys=["turn_taking_ratio"],
                conflicting_feature_keys=[],
                limitations=base_limitations,
                status=CueStatus.PENDING_REVIEW,
            )
        )

    # 3. Response latency rule: response_latency_mean > 2.5s
    latency = features.get("response_latency_mean")
    if latency is not None and isinstance(latency, (int, float)) and latency > 2.5:
        cues.append(
            AttentionCue(
                cue_id=f"cue_lat_{uuid.uuid4().hex[:8]}",
                assessment_id=assessment_id,
                cue_type=AttentionCueType.RESPONSE_LATENCY,
                title="ช่วงเวลาก่อนตอบสนองยาวนาน (Extended Response Latency)",
                description="ระยะเวลาหยุดก่อนตอบสนองต่อคำถามหรือสิ่งเร้าในการสื่อสารยาวนานกว่าปกติ",
                policy_version=policy_version,
                evidence_run_id=evidence_run_id,
                supporting_feature_keys=["response_latency_mean"],
                conflicting_feature_keys=[],
                limitations=base_limitations,
                status=CueStatus.PENDING_REVIEW,
            )
        )

    # 4. Sparse Communication rule: total_utterances < 10 or words_per_minute < 20.0
    utterances = features.get("total_utterances")
    wpm = features.get("speech_rate_wpm") or features.get("words_per_minute")
    if (utterances is not None and isinstance(utterances, (int, float)) and utterances < 10) or (
        wpm is not None and isinstance(wpm, (int, float)) and wpm < 20.0
    ):
        sup = []
        if utterances is not None:
            sup.append("total_utterances")
        if wpm is not None:
            sup.append("speech_rate_wpm")
        cues.append(
            AttentionCue(
                cue_id=f"cue_sparse_{uuid.uuid4().hex[:8]}",
                assessment_id=assessment_id,
                cue_type=AttentionCueType.SPARSE_COMMUNICATION,
                title="ปริมาณการสื่อสารมีจำกัด (Sparse Communication Sample)",
                description="ปริมาณตัวอย่างการพูดหรืออัตราความเร็วคำในการประเมินต่ำกว่าระดับเพียงพอสำหรับการวิเคราะห์สมบูรณ์",
                policy_version=policy_version,
                evidence_run_id=evidence_run_id,
                supporting_feature_keys=sup,
                conflicting_feature_keys=[],
                limitations=base_limitations + ["sample_volume_sparse"],
                status=CueStatus.PENDING_REVIEW,
            )
        )

    return cues
