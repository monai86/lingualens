"""Unit tests for LongitudinalRepository with SQLite and tenant isolation."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.longitudinal_repository import LongitudinalRepository
from app.assessment_v2.db.models import (
    AssessmentComparisonFeatureRecord,
    AssessmentComparisonRecord,
    AssessmentRecord,
    ChildRecord,
    EvidenceRunRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    UserProfileRecord,
)
from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DevelopmentalEvidenceProfile,
    DomainProfile,
    DomainProfileStatus,
    EvidenceProvenance,
    EvidenceRunSnapshot,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.longitudinal import (
    AssessmentComparisonSession,
    CompatibilityStatus,
    FeatureComparisonResult,
    IncompatibilityReason,
    NumericalTrend,
    compare_evidence_runs,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AssessmentBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _seed_org_child_assessments(session: Session) -> tuple[str, str, str, str, str, str]:
    org_id = uuid4().hex
    child_id = uuid4().hex
    user_id = uuid4().hex
    base_asmt_id = uuid4().hex
    curr_asmt_id = uuid4().hex
    base_run_id = uuid4().hex
    curr_run_id = uuid4().hex

    org = OrganizationRecord(organization_id=org_id, display_label="Test Clinic")
    session.add(org)
    session.flush()

    user = UserProfileRecord(user_id=user_id, display_label="Dr. Taylor")
    session.add(user)
    session.flush()

    membership = OrganizationMembershipRecord(
        membership_id=uuid4().hex,
        organization_id=org_id,
        user_id=user_id,
        role="therapist",
    )
    session.add(membership)
    session.flush()

    child = ChildRecord(
        child_id=child_id,
        organization_id=org_id,
        display_code="CH-001",
        birth_month=5,
        birth_year=2022,
        language_context="th-TH",
    )
    session.add(child)
    session.flush()

    asmt_base = AssessmentRecord(
        assessment_id=base_asmt_id,
        organization_id=org_id,
        child_id=child_id,
        purpose=AssessmentPurpose.INITIAL.value,
        state=AssessmentState.FINALIZED.value,
        age_months=36,
        language_context="th-TH",
        assigned_clinician_id=user_id,
    )
    asmt_curr = AssessmentRecord(
        assessment_id=curr_asmt_id,
        organization_id=org_id,
        child_id=child_id,
        purpose=AssessmentPurpose.DEVELOPMENTAL_FOLLOW_UP.value,
        state=AssessmentState.FINALIZED.value,
        age_months=42,
        language_context="th-TH",
        assigned_clinician_id=user_id,
    )
    session.add_all([asmt_base, asmt_curr])
    session.flush()

    prov = {
        "input_ref": "seg-1",
        "input_sha256": "a" * 64,
        "protocol_version_key": "thai_guided_language_sample:v0",
        "extractor": "ext_v1",
        "pipeline_version": "1.0",
        "feature_schema_version": "f_v1",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    now = datetime.now(timezone.utc)
    run_base = EvidenceRunRecord(
        evidence_run_id=base_run_id,
        organization_id=org_id,
        assessment_id=base_asmt_id,
        transcript_revision_id=uuid4().hex,
        state="completed",
        input_ref=prov["input_ref"],
        input_sha256=prov["input_sha256"],
        protocol_version_key=prov["protocol_version_key"],
        extractor=prov["extractor"],
        pipeline_version=prov["pipeline_version"],
        feature_schema_version=prov["feature_schema_version"],
        limitations_json=[],
        generated_at=now,
        version=1,
    )
    run_curr = EvidenceRunRecord(
        evidence_run_id=curr_run_id,
        organization_id=org_id,
        assessment_id=curr_asmt_id,
        transcript_revision_id=uuid4().hex,
        state="completed",
        input_ref=prov["input_ref"],
        input_sha256=prov["input_sha256"],
        protocol_version_key=prov["protocol_version_key"],
        extractor=prov["extractor"],
        pipeline_version=prov["pipeline_version"],
        feature_schema_version=prov["feature_schema_version"],
        limitations_json=[],
        generated_at=now,
        version=1,
    )
    session.add_all([run_base, run_curr])
    session.commit()
    return org_id, child_id, base_asmt_id, curr_asmt_id, base_run_id, curr_run_id


def test_save_and_retrieve_comparison_session(db_session: Session) -> None:
    org_id, child_id, base_asmt_id, curr_asmt_id, base_run_id, curr_run_id = (
        _seed_org_child_assessments(db_session)
    )

    repo = LongitudinalRepository(db_session)

    feat_res = FeatureComparisonResult(
        feature_key="mluw",
        unit="words_per_utterance",
        status=CompatibilityStatus.COMPATIBLE,
        incompatibility_reasons=(),
        baseline_value=2.0,
        current_value=3.5,
        absolute_delta=1.5,
        percent_change=75.0,
        percent_change_limitation=None,
        numerical_trend=NumericalTrend.INCREASED,
        clinical_interpretation="indeterminate",
        policy_version="longitudinal_v1",
    )

    session_obj = AssessmentComparisonSession(
        baseline_assessment_id=base_asmt_id,
        baseline_evidence_run_id=base_run_id,
        baseline_evidence_sha256="a" * 64,
        current_assessment_id=curr_asmt_id,
        current_evidence_run_id=curr_run_id,
        current_evidence_sha256="b" * 64,
        child_id=child_id,
        organization_id=org_id,
        policy_version="longitudinal_v1",
        created_at=datetime.now(timezone.utc),
        feature_comparisons=(feat_res,),
        compatible_feature_count=1,
        incompatible_feature_count=0,
    )

    created_id = repo.save_comparison(session_obj, compared_by_user_id="usr-123")
    assert created_id is not None

    record = repo.get_comparison(org_id, created_id)
    assert record is not None
    assert record.child_id == child_id
    assert record.baseline_assessment_id == base_asmt_id
    assert record.current_assessment_id == curr_asmt_id
    assert record.status == "compatible"
    assert record.is_stale is False
    assert len(record.features) == 1
    assert record.features[0].feature_key == "mluw"
    assert record.features[0].absolute_delta == 1.5
    assert record.features[0].clinical_interpretation == "indeterminate"


def test_mark_stale_comparisons(db_session: Session) -> None:
    org_id, child_id, base_asmt_id, curr_asmt_id, base_run_id, curr_run_id = (
        _seed_org_child_assessments(db_session)
    )
    repo = LongitudinalRepository(db_session)

    session_obj = AssessmentComparisonSession(
        baseline_assessment_id=base_asmt_id,
        baseline_evidence_run_id=base_run_id,
        baseline_evidence_sha256="a" * 64,
        current_assessment_id=curr_asmt_id,
        current_evidence_run_id=curr_run_id,
        current_evidence_sha256="b" * 64,
        child_id=child_id,
        organization_id=org_id,
        policy_version="longitudinal_v1",
        created_at=datetime.now(timezone.utc),
        feature_comparisons=(),
        compatible_feature_count=0,
        incompatible_feature_count=0,
    )

    created_id = repo.save_comparison(session_obj, compared_by_user_id="usr-123")

    # Supersede current run
    staled_count = repo.mark_stale_comparisons_for_evidence_run(org_id, curr_run_id)
    assert staled_count == 1

    record = repo.get_comparison(org_id, created_id)
    assert record is not None
    assert record.is_stale is True
