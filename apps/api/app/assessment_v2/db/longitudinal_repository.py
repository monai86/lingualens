"""Tenant-isolated repository for longitudinal assessment comparisons."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.assessment_v2.db.models import (
    AssessmentComparisonFeatureRecord,
    AssessmentComparisonRecord,
)
from app.assessment_v2.longitudinal import (
    AssessmentComparisonSession,
    CompatibilityStatus,
    FeatureComparisonResult,
)


class LongitudinalRepository:
    """Repository handling persistence of longitudinal comparison records and features."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_comparison(
        self,
        comparison_session: AssessmentComparisonSession,
        compared_by_user_id: str,
    ) -> str:
        """Persist or update an assessment comparison session idempotently."""
        org_id = str(comparison_session.organization_id)
        base_run_id = str(comparison_session.baseline_evidence_run_id)
        curr_run_id = str(comparison_session.current_evidence_run_id)
        policy_ver = comparison_session.policy_version

        # Check existing
        existing = self.get_comparison_by_runs(org_id, base_run_id, curr_run_id, policy_ver)
        if existing is not None:
            return existing.comparison_id

        comp_id = uuid4().hex
        status = (
            CompatibilityStatus.COMPATIBLE.value
            if comparison_session.compatible_feature_count > 0
            else CompatibilityStatus.NOT_COMPARABLE.value
        )

        record = AssessmentComparisonRecord(
            comparison_id=comp_id,
            organization_id=org_id,
            child_id=str(comparison_session.child_id),
            baseline_assessment_id=str(comparison_session.baseline_assessment_id),
            current_assessment_id=str(comparison_session.current_assessment_id),
            baseline_evidence_run_id=base_run_id,
            current_evidence_run_id=curr_run_id,
            baseline_evidence_sha256=comparison_session.baseline_evidence_sha256,
            current_evidence_sha256=comparison_session.current_evidence_sha256,
            policy_version=policy_ver,
            status=status,
            is_stale=False,
            compatible_feature_count=comparison_session.compatible_feature_count,
            incompatible_feature_count=comparison_session.incompatible_feature_count,
            compared_by_user_id=compared_by_user_id,
            created_at=comparison_session.created_at,
        )
        self._session.add(record)

        for feat in comparison_session.feature_comparisons:
            feat_id = uuid4().hex
            feat_rec = AssessmentComparisonFeatureRecord(
                comparison_feature_id=feat_id,
                organization_id=org_id,
                comparison_id=comp_id,
                feature_key=feat.feature_key,
                unit=feat.unit,
                status=feat.status.value,
                incompatibility_reasons_json=[r.value for r in feat.incompatibility_reasons],
                baseline_value=float(feat.baseline_value) if feat.baseline_value is not None else None,
                current_value=float(feat.current_value) if feat.current_value is not None else None,
                absolute_delta=feat.absolute_delta,
                percent_change=feat.percent_change,
                percent_change_limitation=feat.percent_change_limitation,
                numerical_trend=feat.numerical_trend.value,
                clinical_interpretation=feat.clinical_interpretation,
                created_at=comparison_session.created_at,
            )
            self._session.add(feat_rec)

        self._session.commit()
        return comp_id

    def get_comparison(
        self, organization_id: str, comparison_id: str
    ) -> AssessmentComparisonRecord | None:
        """Retrieve a comparison record with attached feature comparisons."""
        stmt = (
            select(AssessmentComparisonRecord)
            .where(
                AssessmentComparisonRecord.organization_id == organization_id,
                AssessmentComparisonRecord.comparison_id == comparison_id,
            )
        )
        comp = self._session.execute(stmt).scalar_one_or_none()
        if comp is None:
            return None

        # Fetch child features
        feat_stmt = (
            select(AssessmentComparisonFeatureRecord)
            .where(
                AssessmentComparisonFeatureRecord.organization_id == organization_id,
                AssessmentComparisonFeatureRecord.comparison_id == comparison_id,
            )
            .order_by(AssessmentComparisonFeatureRecord.feature_key)
        )
        features = self._session.execute(feat_stmt).scalars().all()
        comp.features = list(features)
        return comp

    def get_comparison_by_runs(
        self,
        organization_id: str,
        baseline_run_id: str,
        current_run_id: str,
        policy_version: str,
    ) -> AssessmentComparisonRecord | None:
        """Lookup comparison by exact evidence run IDs and policy version."""
        stmt = select(AssessmentComparisonRecord).where(
            AssessmentComparisonRecord.organization_id == organization_id,
            AssessmentComparisonRecord.baseline_evidence_run_id == baseline_run_id,
            AssessmentComparisonRecord.current_evidence_run_id == current_run_id,
            AssessmentComparisonRecord.policy_version == policy_version,
        )
        comp = self._session.execute(stmt).scalar_one_or_none()
        if comp is not None:
            feat_stmt = (
                select(AssessmentComparisonFeatureRecord)
                .where(
                    AssessmentComparisonFeatureRecord.organization_id == organization_id,
                    AssessmentComparisonFeatureRecord.comparison_id == comp.comparison_id,
                )
                .order_by(AssessmentComparisonFeatureRecord.feature_key)
            )
            comp.features = list(self._session.execute(feat_stmt).scalars().all())
        return comp

    def list_comparisons_for_assessment(
        self, organization_id: str, assessment_id: str
    ) -> list[AssessmentComparisonRecord]:
        """List all comparisons where this assessment is either baseline or current."""
        stmt = (
            select(AssessmentComparisonRecord)
            .where(
                AssessmentComparisonRecord.organization_id == organization_id,
                or_(
                    AssessmentComparisonRecord.current_assessment_id == assessment_id,
                    AssessmentComparisonRecord.baseline_assessment_id == assessment_id,
                ),
            )
            .order_by(AssessmentComparisonRecord.created_at.desc())
        )
        records = list(self._session.execute(stmt).scalars().all())
        for r in records:
            feat_stmt = (
                select(AssessmentComparisonFeatureRecord)
                .where(
                    AssessmentComparisonFeatureRecord.organization_id == organization_id,
                    AssessmentComparisonFeatureRecord.comparison_id == r.comparison_id,
                )
                .order_by(AssessmentComparisonFeatureRecord.feature_key)
            )
            r.features = list(self._session.execute(feat_stmt).scalars().all())
        return records

    def mark_stale_comparisons_for_evidence_run(
        self, organization_id: str, superseded_evidence_run_id: str
    ) -> int:
        """Mark comparisons as stale when one of their source runs is superseded."""
        stmt = (
            update(AssessmentComparisonRecord)
            .where(
                AssessmentComparisonRecord.organization_id == organization_id,
                or_(
                    AssessmentComparisonRecord.baseline_evidence_run_id == superseded_evidence_run_id,
                    AssessmentComparisonRecord.current_evidence_run_id == superseded_evidence_run_id,
                ),
                AssessmentComparisonRecord.is_stale.is_(False),
            )
            .values(is_stale=True)
        )
        result = self._session.execute(stmt)
        self._session.commit()
        return int(result.rowcount)
