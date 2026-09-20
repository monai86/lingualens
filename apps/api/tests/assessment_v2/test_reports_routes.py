"""Route tests for assessment v2 reports, immutable sign-off, export, and amendments (Slice C2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any
import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.db.models import AssessmentReportRecord
from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.reports import ReportStatus
from app.assessment_v2.services import ClinicalPolicyError
from app.main import app


class FakeReportsService:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.reports: dict[str, AssessmentReportRecord] = {
            "rep_001": AssessmentReportRecord(
                report_id="rep_001",
                organization_id="tenant_a",
                assessment_id="asmt_001",
                child_id="child_001",
                evidence_run_id="ev_run_001",
                review_id="rev_001",
                amendment_sequence=0,
                version=1,
                status=ReportStatus.DRAFT.value,
                title="Draft Assessment Report",
                purpose="Language evaluation",
                content_markdown="# Draft Report\nValid content not a clinical diagnosis",
                limitations_json=["audio_short"],
                signed_by=None,
                signed_at=None,
                signed_snapshot=None,
                signed_snapshot_hash=None,
                is_stale=False,
                created_at=now,
                updated_at=now,
            )
        }

    def create_report_draft(
        self,
        assessment_id: str,
        purpose: str | None = None,
        comparison_id: str | None = None,
    ) -> AssessmentReportRecord:
        now = datetime.now(timezone.utc)
        rep = AssessmentReportRecord(
            report_id="rep_002",
            organization_id="tenant_a",
            assessment_id=assessment_id,
            child_id="child_001",
            evidence_run_id="ev_run_001",
            review_id="rev_001",
            comparison_id=comparison_id,
            amendment_sequence=0,
            version=1,
            status=ReportStatus.DRAFT.value,
            title="Generated Draft",
            purpose=purpose or "Purpose",
            content_markdown="# Draft\nContent with this system does not diagnose asd",
            limitations_json=[],
            is_stale=False,
            created_at=now,
            updated_at=now,
        )
        self.reports["rep_002"] = rep
        return rep

    def get_current_report(self, assessment_id: str) -> AssessmentReportRecord:
        for rep in reversed(list(self.reports.values())):
            if rep.assessment_id == assessment_id:
                return rep
        raise ClinicalPolicyError("report_not_found", 404, "Report was not found.")

    def get_report(self, assessment_id: str, report_id: str) -> AssessmentReportRecord:
        rep = self.reports.get(report_id)
        if rep is None or rep.assessment_id != assessment_id:
            raise ClinicalPolicyError("report_not_found", 404, "Report was not found.")
        return rep

    def update_report_draft(
        self,
        assessment_id: str,
        report_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
        limitations: list[str] | None = None,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        rep = self.get_report(assessment_id, report_id)
        if rep.status != ReportStatus.DRAFT.value:
            raise ClinicalPolicyError("report_immutable", 409, "Signed reports are immutable.")
        if expected_version is not None and rep.version != expected_version:
            raise ClinicalPolicyError("stale_report_version", 409, "The report version is stale.")
        rep.title = title
        rep.purpose = purpose
        rep.content_markdown = content_markdown
        rep.version += 1
        rep.updated_at = datetime.now(timezone.utc)
        return rep

    def sign_off_report(
        self,
        assessment_id: str,
        report_id: str,
        expected_version: int | None = None,
    ) -> AssessmentReportRecord:
        rep = self.get_report(assessment_id, report_id)
        if expected_version is not None and rep.version != expected_version:
            raise ClinicalPolicyError("stale_report_version", 409, "The report version is stale.")
        now = datetime.now(timezone.utc)
        rep.status = ReportStatus.SIGNED_OFF.value
        rep.signed_by = "clinician_01"
        rep.signed_at = now
        rep.signed_snapshot = {"report_id": report_id, "signed_by": "clinician_01"}
        rep.signed_snapshot_hash = "sha256_hash_mock_123"
        rep.updated_at = now
        return rep

    def create_report_amendment(
        self,
        assessment_id: str,
        report_id: str,
        title: str,
        purpose: str,
        content_markdown: str,
    ) -> AssessmentReportRecord:
        signed_rep = self.get_report(assessment_id, report_id)
        signed_rep.status = ReportStatus.AMENDED.value
        now = datetime.now(timezone.utc)
        amended = AssessmentReportRecord(
            report_id="rep_amend_001",
            organization_id=signed_rep.organization_id,
            assessment_id=assessment_id,
            child_id=signed_rep.child_id,
            evidence_run_id=signed_rep.evidence_run_id,
            review_id=signed_rep.review_id,
            amends_report_id=signed_rep.report_id,
            amendment_sequence=signed_rep.amendment_sequence + 1,
            version=1,
            status=ReportStatus.DRAFT.value,
            title=title,
            purpose=purpose,
            content_markdown=content_markdown,
            limitations_json=list(signed_rep.limitations_json or []),
            is_stale=False,
            created_at=now,
            updated_at=now,
        )
        self.reports["rep_amend_001"] = amended
        return amended

    def export_report(
        self,
        assessment_id: str,
        report_id: str,
        export_format: str,
    ) -> dict[str, Any]:
        rep = self.get_report(assessment_id, report_id)
        if rep.status != ReportStatus.SIGNED_OFF.value:
            raise ClinicalPolicyError("report_export_not_ready", 409, "Report must be signed off before export.")
        now = datetime.now(timezone.utc)
        return {
            "report_id": rep.report_id,
            "format": export_format,
            "content_type": "application/pdf" if export_format == "pdf" else "text/markdown",
            "filename": f"{rep.report_id}.{export_format}",
            "content": rep.content_markdown if export_format != "pdf" else None,
            "base64_content": "JVBERi0xLjQK..." if export_format == "pdf" else None,
            "report_hash": rep.signed_snapshot_hash,
            "signed_by": rep.signed_by,
            "export_timestamp": now,
        }

    def get_report_lineage(self, assessment_id: str, report_id: str) -> list[AssessmentReportRecord]:
        return list(self.reports.values())


@pytest.fixture
def fake_service() -> FakeReportsService:
    return FakeReportsService()


@pytest.fixture
def client(fake_service: FakeReportsService) -> Iterator[TestClient]:
    app.dependency_overrides[get_assessment_service] = lambda: fake_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_report_draft(client: TestClient):
    resp = client.post(
        "/api/v2/assessments/asmt_001/reports/draft",
        json={"purpose": "Routine follow-up evaluation"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_id"] == "rep_002"
    assert data["status"] == "draft"

    # Get current report
    resp_cur = client.get("/api/v2/assessments/asmt_001/reports/current")
    assert resp_cur.status_code == 200
    assert resp_cur.json()["report_id"] == "rep_002"


def test_edit_draft_and_signoff_lifecycle(client: TestClient):
    # 1. Edit draft
    resp = client.put(
        "/api/v2/assessments/asmt_001/reports/rep_001",
        json={
            "title": "Therapist Edited Report",
            "purpose": "Updated Purpose",
            "content_markdown": "# Updated Report Content",
            "expected_version": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 2
    assert data["title"] == "Therapist Edited Report"

    # 2. Sign-off report
    resp_sign = client.post(
        "/api/v2/assessments/asmt_001/reports/rep_001/sign",
        json={"expected_version": 2},
    )
    assert resp_sign.status_code == 200
    signed_data = resp_sign.json()
    assert signed_data["status"] == "signed_off"
    assert signed_data["signed_by"] == "clinician_01"
    assert signed_data["signed_snapshot_hash"] == "sha256_hash_mock_123"

    # 3. Editing signed report is forbidden
    resp_illegal = client.put(
        "/api/v2/assessments/asmt_001/reports/rep_001",
        json={
            "title": "Illegal Edit",
            "purpose": "Illegal",
            "content_markdown": "Illegal",
        },
    )
    assert resp_illegal.status_code == 409


def test_amendment_and_export_lifecycle(client: TestClient, fake_service: FakeReportsService):
    # Ensure rep_001 is signed off first
    fake_service.reports["rep_001"].status = ReportStatus.SIGNED_OFF.value
    fake_service.reports["rep_001"].signed_snapshot_hash = "hash_123"
    fake_service.reports["rep_001"].signed_by = "Dr. Therapist"

    # 1. Export signed report as PDF
    resp_export = client.get("/api/v2/assessments/asmt_001/reports/rep_001/export?format=pdf")
    assert resp_export.status_code == 200
    export_data = resp_export.json()
    assert export_data["format"] == "pdf"
    assert export_data["content_type"] == "application/pdf"
    assert export_data["base64_content"] is not None

    # 2. Create amendment draft
    resp_amend = client.post(
        "/api/v2/assessments/asmt_001/reports/rep_001/amend",
        json={
            "title": "Amended Report v2",
            "purpose": "Add parental home activity observations",
            "content_markdown": "# Amended Report Content",
        },
    )
    assert resp_amend.status_code == 201
    amend_data = resp_amend.json()
    assert amend_data["report_id"] == "rep_amend_001"
    assert amend_data["amends_report_id"] == "rep_001"
    assert amend_data["amendment_sequence"] == 1
    assert amend_data["status"] == "draft"

    # 3. Check lineage
    resp_lineage = client.get("/api/v2/assessments/asmt_001/reports/rep_amend_001/history")
    assert resp_lineage.status_code == 200
    lineage = resp_lineage.json()
    assert len(lineage) >= 2
