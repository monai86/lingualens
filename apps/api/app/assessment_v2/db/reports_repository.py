from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.assessment_v2.db.models import AssessmentReportRecord
from app.assessment_v2.reports import ReportStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_report_draft(
        self,
        organization_id: str,
        assessment_id: str,
        child_id: str,
        evidence_run_id: str,
        review_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
        limitations: list[str],
        comparison_id: str | None = None,
        amends_report_id: str | None = None,
        amendment_sequence: int = 0,
    ) -> AssessmentReportRecord:
        report_id = f"rep_{uuid.uuid4().hex[:16]}"
        record = AssessmentReportRecord(
            report_id=report_id,
            organization_id=organization_id,
            assessment_id=assessment_id,
            child_id=child_id,
            evidence_run_id=evidence_run_id,
            comparison_id=comparison_id,
            review_id=review_id,
            amends_report_id=amends_report_id,
            amendment_sequence=amendment_sequence,
            version=1,
            status=ReportStatus.DRAFT.value,
            title=title,
            purpose=purpose,
            content_markdown=content_markdown,
            limitations_json=limitations,
            is_stale=False,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_report(self, organization_id: str, report_id: str) -> AssessmentReportRecord | None:
        stmt = (
            select(AssessmentReportRecord)
            .where(
                AssessmentReportRecord.organization_id == organization_id,
                AssessmentReportRecord.report_id == report_id,
            )
        )
        return self.session.scalar(stmt)

    def get_current_report(self, organization_id: str, assessment_id: str) -> AssessmentReportRecord | None:
        stmt = (
            select(AssessmentReportRecord)
            .where(
                AssessmentReportRecord.organization_id == organization_id,
                AssessmentReportRecord.assessment_id == assessment_id,
            )
            .order_by(
                desc(AssessmentReportRecord.amendment_sequence),
                desc(AssessmentReportRecord.created_at),
            )
        )
        return self.session.scalar(stmt)

    def update_report_draft(
        self,
        organization_id: str,
        report_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
        limitations: list[str] | None = None,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        record = self.get_report(organization_id, report_id)
        if record is None:
            raise ValueError(f"Report '{report_id}' not found.")

        if record.status != ReportStatus.DRAFT.value:
            raise ValueError(f"Cannot edit report in status '{record.status}'. Signed reports are immutable.")

        if expected_version is not None and record.version != expected_version:
            raise ValueError(
                f"Optimistic concurrency conflict: report version is {record.version}, expected {expected_version}."
            )

        now = utc_now()
        record.title = title
        record.purpose = purpose
        record.content_markdown = content_markdown
        if limitations is not None:
            record.limitations_json = limitations
        record.version += 1
        record.updated_at = now
        self.session.flush()
        return record

    def sign_off_report(
        self,
        organization_id: str,
        report_id: str,
        signed_by: str,
        signed_at: datetime,
        signed_snapshot: dict[str, Any],
        signed_snapshot_hash: str,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        record = self.get_report(organization_id, report_id)
        if record is None:
            raise ValueError(f"Report '{report_id}' not found.")

        # Idempotency check: if already signed with matching hash, return existing record
        if record.status == ReportStatus.SIGNED_OFF.value:
            if record.signed_snapshot_hash == signed_snapshot_hash:
                return record
            raise ValueError(f"Report '{report_id}' is already signed with a different snapshot.")

        if expected_version is not None and record.version != expected_version:
            raise ValueError(
                f"Optimistic concurrency conflict: report version is {record.version}, expected {expected_version}."
            )

        now = utc_now()
        record.status = ReportStatus.SIGNED_OFF.value
        record.signed_by = signed_by
        record.signed_at = signed_at
        record.signed_snapshot = signed_snapshot
        record.signed_snapshot_hash = signed_snapshot_hash
        record.updated_at = now
        self.session.flush()
        return record

    def create_amendment_draft(
        self,
        organization_id: str,
        signed_report_id: str,
        new_title: str,
        new_purpose: str,
        new_content_markdown: str,
        limitations: list[str] | None = None,
    ) -> AssessmentReportRecord:
        signed_record = self.get_report(organization_id, signed_report_id)
        if signed_record is None:
            raise ValueError(f"Signed report '{signed_report_id}' not found.")
        if signed_record.status != ReportStatus.SIGNED_OFF.value:
            raise ValueError(f"Only signed reports can be amended. Current status: '{signed_record.status}'.")

        # Mark previous report as AMENDED
        signed_record.status = ReportStatus.AMENDED.value
        signed_record.updated_at = utc_now()

        # Create new linked draft
        amendment_draft = self.create_report_draft(
            organization_id=organization_id,
            assessment_id=signed_record.assessment_id,
            child_id=signed_record.child_id,
            evidence_run_id=signed_record.evidence_run_id,
            review_id=signed_record.review_id,
            comparison_id=signed_record.comparison_id,
            title=new_title,
            purpose=new_purpose,
            content_markdown=new_content_markdown,
            limitations=limitations if limitations is not None else list(signed_record.limitations_json or []),
            amends_report_id=signed_record.report_id,
            amendment_sequence=signed_record.amendment_sequence + 1,
        )
        return amendment_draft

    def get_amendment_lineage(self, organization_id: str, report_id: str) -> list[AssessmentReportRecord]:
        """Returns the full amendment lineage from initial report to latest."""
        curr = self.get_report(organization_id, report_id)
        if curr is None:
            return []

        # Find the root
        root = curr
        while root.amends_report_id:
            parent = self.get_report(organization_id, root.amends_report_id)
            if parent is None:
                break
            root = parent

        # Traverse descendants forward
        stmt = (
            select(AssessmentReportRecord)
            .where(
                AssessmentReportRecord.organization_id == organization_id,
                AssessmentReportRecord.assessment_id == curr.assessment_id,
            )
            .order_by(AssessmentReportRecord.amendment_sequence.asc())
        )
        return list(self.session.scalars(stmt).all())
