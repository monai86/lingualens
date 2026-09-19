from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    ClinicalReviewSession,
    ClinicianFeedback,
    CueStatus,
    FollowUpPlan,
)
from app.assessment_v2.db.models import (
    AssessmentAttentionCueRecord,
    AssessmentClinicalReviewRecord,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClinicalReviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create_review_session(
        self,
        organization_id: str,
        assessment_id: str,
        child_id: str,
        evidence_run_id: str,
        initial_cues: list[AttentionCue] | None = None,
    ) -> ClinicalReviewSession:
        stmt = (
            select(AssessmentClinicalReviewRecord)
            .where(
                AssessmentClinicalReviewRecord.organization_id == organization_id,
                AssessmentClinicalReviewRecord.assessment_id == assessment_id,
            )
        )
        record = self.session.scalar(stmt)
        if record is None:
            review_id = f"rev_{uuid.uuid4().hex[:16]}"
            record = AssessmentClinicalReviewRecord(
                review_id=review_id,
                organization_id=organization_id,
                assessment_id=assessment_id,
                child_id=child_id,
                evidence_run_id=evidence_run_id,
                status="in_progress",
                version=1,
                is_stale=False,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.session.add(record)
            self.session.flush()

            if initial_cues:
                for cue in initial_cues:
                    cue_rec = AssessmentAttentionCueRecord(
                        cue_id=cue.cue_id,
                        organization_id=organization_id,
                        review_id=review_id,
                        assessment_id=assessment_id,
                        cue_type=cue.cue_type.value,
                        title=cue.title,
                        description=cue.description,
                        policy_version=cue.policy_version,
                        evidence_run_id=cue.evidence_run_id,
                        supporting_feature_keys_json=cue.supporting_feature_keys,
                        conflicting_feature_keys_json=cue.conflicting_feature_keys,
                        limitations_json=cue.limitations,
                        status=cue.status.value,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                    self.session.add(cue_rec)
                self.session.flush()

        return self._to_domain_session(record)

    def get_review_session(self, organization_id: str, assessment_id: str) -> ClinicalReviewSession | None:
        stmt = (
            select(AssessmentClinicalReviewRecord)
            .where(
                AssessmentClinicalReviewRecord.organization_id == organization_id,
                AssessmentClinicalReviewRecord.assessment_id == assessment_id,
            )
        )
        record = self.session.scalar(stmt)
        if record is None:
            return None
        return self._to_domain_session(record)

    def update_cue_feedback(
        self,
        organization_id: str,
        review_id: str,
        cue_id: str,
        reviewer_id: str,
        status: CueStatus,
        rationale: str | None = None,
    ) -> AttentionCue:
        stmt = (
            select(AssessmentAttentionCueRecord)
            .where(
                AssessmentAttentionCueRecord.organization_id == organization_id,
                AssessmentAttentionCueRecord.review_id == review_id,
                AssessmentAttentionCueRecord.cue_id == cue_id,
            )
        )
        cue_rec = self.session.scalar(stmt)
        if cue_rec is None:
            raise ValueError(f"Attention cue '{cue_id}' not found in review '{review_id}'.")

        now = utc_now()
        cue_rec.status = status.value
        cue_rec.reviewer_id = reviewer_id
        cue_rec.reviewed_at = now
        cue_rec.rationale = rationale
        cue_rec.updated_at = now
        self.session.flush()

        return self._to_domain_cue(cue_rec)

    def update_disposition(
        self,
        organization_id: str,
        review_id: str,
        disposition: ClinicalDispositionType,
        disposition_notes: str | None,
        follow_up_plan: FollowUpPlan | None,
        reviewer_id: str,
        expected_version: int | None = None,
    ) -> ClinicalReviewSession:
        stmt = (
            select(AssessmentClinicalReviewRecord)
            .where(
                AssessmentClinicalReviewRecord.organization_id == organization_id,
                AssessmentClinicalReviewRecord.review_id == review_id,
            )
        )
        record = self.session.scalar(stmt)
        if record is None:
            raise ValueError(f"Clinical review '{review_id}' not found.")

        if expected_version is not None and record.version != expected_version:
            raise ValueError(
                f"Optimistic concurrency conflict: review version is {record.version}, expected {expected_version}."
            )

        now = utc_now()
        record.disposition = disposition.value
        record.disposition_notes = disposition_notes
        if follow_up_plan:
            record.follow_up_plan_json = {
                "target_date": follow_up_plan.target_date,
                "recommended_protocol": follow_up_plan.recommended_protocol,
                "focus_areas": follow_up_plan.focus_areas,
                "monitoring_notes": follow_up_plan.monitoring_notes,
            }
        record.reviewed_by = reviewer_id
        record.reviewed_at = now
        record.version += 1
        record.updated_at = now
        self.session.flush()

        return self._to_domain_session(record)

    def mark_review_stale(self, organization_id: str, assessment_id: str) -> None:
        self.session.execute(
            update(AssessmentClinicalReviewRecord)
            .where(
                AssessmentClinicalReviewRecord.organization_id == organization_id,
                AssessmentClinicalReviewRecord.assessment_id == assessment_id,
            )
            .values(is_stale=True, updated_at=utc_now())
        )
        self.session.flush()

    def _to_domain_session(self, record: AssessmentClinicalReviewRecord) -> ClinicalReviewSession:
        cue_stmt = (
            select(AssessmentAttentionCueRecord)
            .where(
                AssessmentAttentionCueRecord.organization_id == record.organization_id,
                AssessmentAttentionCueRecord.review_id == record.review_id,
            )
            .order_by(AssessmentAttentionCueRecord.created_at.asc())
        )
        cue_records = list(self.session.scalars(cue_stmt).all())
        cues = [self._to_domain_cue(c) for c in cue_records]

        follow_up = None
        if record.follow_up_plan_json:
            fp = record.follow_up_plan_json
            follow_up = FollowUpPlan(
                target_date=fp.get("target_date"),
                recommended_protocol=fp.get("recommended_protocol"),
                focus_areas=fp.get("focus_areas", []),
                monitoring_notes=fp.get("monitoring_notes"),
            )

        disp = ClinicalDispositionType(record.disposition) if record.disposition else None

        return ClinicalReviewSession(
            review_id=record.review_id,
            assessment_id=record.assessment_id,
            tenant_id=record.organization_id,
            child_id=record.child_id,
            evidence_run_id=record.evidence_run_id,
            version=record.version,
            cues=cues,
            disposition=disp,
            disposition_notes=record.disposition_notes,
            follow_up=follow_up,
            reviewed_by=record.reviewed_by,
            reviewed_at=record.reviewed_at,
            is_stale=record.is_stale,
        )

    def _to_domain_cue(self, rec: AssessmentAttentionCueRecord) -> AttentionCue:
        feedback = None
        if rec.reviewer_id and rec.reviewed_at:
            feedback = ClinicianFeedback(
                reviewer_id=rec.reviewer_id,
                reviewed_at=rec.reviewed_at,
                status=CueStatus(rec.status),
                rationale=rec.rationale,
            )

        return AttentionCue(
            cue_id=rec.cue_id,
            assessment_id=rec.assessment_id,
            cue_type=AttentionCueType(rec.cue_type),
            title=rec.title,
            description=rec.description,
            policy_version=rec.policy_version,
            evidence_run_id=rec.evidence_run_id,
            supporting_feature_keys=list(rec.supporting_feature_keys_json or []),
            conflicting_feature_keys=list(rec.conflicting_feature_keys_json or []),
            limitations=list(rec.limitations_json or []),
            status=CueStatus(rec.status),
            clinician_feedback=feedback,
        )
