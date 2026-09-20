from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.assessment_v2.db.models import AssessmentBase
from app.assessment_v2.db.reports_repository import ReportsRepository
from app.assessment_v2.reports import ReportStatus


@pytest.fixture
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    AssessmentBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_reports_repository_lifecycle_and_amendment(sqlite_session):
    repo = ReportsRepository(sqlite_session)

    # 1. Create draft
    draft = repo.create_report_draft(
        organization_id="org_1",
        assessment_id="asm_1",
        child_id="child_1",
        evidence_run_id="ev_1",
        review_id="rev_1",
        title="Assessment Report Draft v1",
        purpose="Speech and language evaluation",
        content_markdown="# Draft Content",
        limitations=["short_sample"],
    )
    assert draft.status == ReportStatus.DRAFT.value
    assert draft.amendment_sequence == 0
    assert draft.version == 1

    # 2. Update draft
    updated = repo.update_report_draft(
        organization_id="org_1",
        report_id=draft.report_id,
        title="Updated Title",
        purpose="Updated Purpose",
        content_markdown="# Updated Markdown",
        expected_version=1,
    )
    assert updated.version == 2
    assert updated.title == "Updated Title"

    # 3. Sign off report (immutable snapshot)
    now = datetime.now(timezone.utc)
    snapshot = {"report_id": draft.report_id, "signed_by": "Dr. Smith"}
    signed = repo.sign_off_report(
        organization_id="org_1",
        report_id=draft.report_id,
        signed_by="Dr. Smith",
        signed_at=now,
        signed_snapshot=snapshot,
        signed_snapshot_hash="hash_abc_123",
        expected_version=2,
    )
    assert signed.status == ReportStatus.SIGNED_OFF.value
    assert signed.signed_snapshot_hash == "hash_abc_123"

    # Repeated sign-off is idempotent
    idempotent_signed = repo.sign_off_report(
        organization_id="org_1",
        report_id=draft.report_id,
        signed_by="Dr. Smith",
        signed_at=now,
        signed_snapshot=snapshot,
        signed_snapshot_hash="hash_abc_123",
    )
    assert idempotent_signed.report_id == signed.report_id

    # Modifying signed report directly is forbidden
    with pytest.raises(ValueError, match="Signed reports are immutable"):
        repo.update_report_draft(
            organization_id="org_1",
            report_id=draft.report_id,
            title="Illegal Edit",
            purpose="Illegal Purpose",
            content_markdown="Illegal Content",
        )

    # 4. Create amendment draft
    amendment = repo.create_amendment_draft(
        organization_id="org_1",
        signed_report_id=draft.report_id,
        new_title="Amended Report Title",
        new_purpose="Add parent input",
        new_content_markdown="# Amended Report Content",
    )
    assert amendment.amends_report_id == draft.report_id
    assert amendment.amendment_sequence == 1
    assert amendment.status == ReportStatus.DRAFT.value

    # Previous signed report is now marked as AMENDED
    prev = repo.get_report("org_1", draft.report_id)
    assert prev.status == ReportStatus.AMENDED.value

    # Check lineage
    lineage = repo.get_amendment_lineage("org_1", amendment.report_id)
    assert len(lineage) == 2
    assert lineage[0].report_id == draft.report_id
    assert lineage[1].report_id == amendment.report_id
