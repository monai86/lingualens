import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.assessment_v2.clinical_review import (
    AttentionCue,
    AttentionCueType,
    ClinicalDispositionType,
    CueStatus,
    FollowUpPlan,
)
from app.assessment_v2.db.clinical_review_repository import ClinicalReviewRepository
from app.assessment_v2.db.models import AssessmentBase


@pytest.fixture
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    AssessmentBase.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_clinical_review_repository_crud(sqlite_session):
    repo = ClinicalReviewRepository(sqlite_session)

    initial_cues = [
        AttentionCue(
            cue_id="cue_test_1",
            assessment_id="asm_test_1",
            cue_type=AttentionCueType.LEXICAL_DIVERSITY,
            title="Lexical Diversity Cue",
            description="Low TTR",
            policy_version="cues-v2.0",
            evidence_run_id="ev_run_1",
            supporting_feature_keys=["type_token_ratio"],
            limitations=["sample_short"],
            status=CueStatus.PENDING_REVIEW,
        )
    ]

    # 1. Create review session
    review = repo.get_or_create_review_session(
        organization_id="org_1",
        assessment_id="asm_test_1",
        child_id="child_1",
        evidence_run_id="ev_run_1",
        initial_cues=initial_cues,
    )
    assert review.review_id.startswith("rev_")
    assert review.version == 1
    assert len(review.cues) == 1
    assert review.cues[0].status == CueStatus.PENDING_REVIEW

    # 2. Update cue feedback (clinician acknowledges)
    updated_cue = repo.update_cue_feedback(
        organization_id="org_1",
        review_id=review.review_id,
        cue_id="cue_test_1",
        reviewer_id="clinician_01",
        status=CueStatus.ACKNOWLEDGED,
        rationale="ตรวจพบว่าเด็กใช้คำจำกัดในกิจกรรมเล่นอิสระ",
    )
    assert updated_cue.status == CueStatus.ACKNOWLEDGED
    assert updated_cue.clinician_feedback is not None
    assert updated_cue.clinician_feedback.reviewer_id == "clinician_01"

    # 3. Update disposition with optimistic lock
    updated_review = repo.update_disposition(
        organization_id="org_1",
        review_id=review.review_id,
        disposition=ClinicalDispositionType.CONTINUE_MONITORING,
        disposition_notes="วางแผนติดตามผลใน 3 เดือน",
        follow_up_plan=FollowUpPlan(target_date="2026-12-01", focus_areas=["vocabulary"]),
        reviewer_id="clinician_01",
        expected_version=1,
    )
    assert updated_review.version == 2
    assert updated_review.disposition == ClinicalDispositionType.CONTINUE_MONITORING
    assert updated_review.follow_up.target_date == "2026-12-01"

    # 4. Optimistic concurrency conflict test
    with pytest.raises(ValueError, match="concurrency conflict"):
        repo.update_disposition(
            organization_id="org_1",
            review_id=review.review_id,
            disposition=ClinicalDispositionType.REFERRAL_SPECIALIST,
            disposition_notes=None,
            follow_up_plan=None,
            reviewer_id="clinician_01",
            expected_version=1,  # Stale! Current version is 2
        )
