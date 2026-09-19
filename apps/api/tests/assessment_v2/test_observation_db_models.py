"""Tests for assessment v2 observation and instrument database models."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentObservationRecord,
    AssessmentInstrumentRecord,
    AssessmentInstrumentItemRecord,
    ChildRecord,
    OrganizationRecord,
    OrganizationMembershipRecord,
    UserProfileRecord,
    AssessmentRecord,
)
from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState
from app.assessment_v2.domain.observations import ObservationCategory, ObservationSource
from app.assessment_v2.domain.instruments import InstrumentRespondentType


@pytest.fixture
def sqlite_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AssessmentBase.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed org, user, membership, child, assessment
        org = OrganizationRecord(organization_id="org_test", display_label="Test Clinic")
        session.add(org)
        session.flush()

        user = UserProfileRecord(user_id="usr_01", display_label="Dr. Taylor")
        session.add(user)
        session.flush()

        membership = OrganizationMembershipRecord(
            membership_id="mem_01",
            organization_id="org_test",
            user_id="usr_01",
            role="therapist",
        )
        session.add(membership)
        session.flush()

        child = ChildRecord(
            child_id="child_01",
            organization_id="org_test",
            display_code="CH-01",
            birth_month=5,
            birth_year=2022,
            language_context="th-TH",
        )
        session.add(child)
        session.flush()

        assessment = AssessmentRecord(
            assessment_id="asm_01",
            organization_id="org_test",
            child_id="child_01",
            purpose=AssessmentPurpose.INITIAL.value,
            state=AssessmentState.DRAFT.value,
            age_months=42,
            language_context="th-TH",
            assigned_clinician_id="usr_01",
        )
        session.add(assessment)
        session.flush()

        yield session


def test_observation_db_lifecycle(sqlite_session: Session):
    now = datetime.now(timezone.utc)
    obs = AssessmentObservationRecord(
        observation_id="obs_100",
        organization_id="org_test",
        assessment_id="asm_01",
        category=ObservationCategory.COMMUNICATION.value,
        source=ObservationSource.CLINICIAN.value,
        observer_name="Dr. Taylor",
        observer_role="slp",
        observed_at=now,
        activity_context="Free play with blocks",
        notes="Child vocalized during play and initiated joint attention.",
        structured_flags_json=["joint_attention_present"],
        is_amendment=False,
        version=1,
    )
    sqlite_session.add(obs)
    sqlite_session.commit()

    saved = sqlite_session.scalar(
        select(AssessmentObservationRecord).where(
            AssessmentObservationRecord.observation_id == "obs_100"
        )
    )
    assert saved is not None
    assert saved.notes == "Child vocalized during play and initiated joint attention."
    assert saved.structured_flags_json == ["joint_attention_present"]
    assert saved.version == 1
    assert saved.is_amendment is False


def test_instrument_db_lifecycle(sqlite_session: Session):
    now = datetime.now(timezone.utc)
    admin = AssessmentInstrumentRecord(
        administration_id="inst_admin_100",
        organization_id="org_test",
        assessment_id="asm_01",
        instrument_name="CommCheck-v1",
        instrument_version="1.0",
        respondent_type=InstrumentRespondentType.CAREGIVER.value,
        administered_by_user_id="usr_01",
        administered_at=now,
        licensing_verified=True,
        summary_scores_json={"total": 2.0},
        version=1,
    )
    sqlite_session.add(admin)
    sqlite_session.flush()

    item = AssessmentInstrumentItemRecord(
        item_id="item_rec_1",
        organization_id="org_test",
        administration_id="inst_admin_100",
        item_key="item_01",
        prompt_label="Waves goodbye",
        response_value="yes",
        score=1.0,
        notes="Spontaneous wave",
    )
    sqlite_session.add(item)
    sqlite_session.commit()

    saved_admin = sqlite_session.scalar(
        select(AssessmentInstrumentRecord).where(
            AssessmentInstrumentRecord.administration_id == "inst_admin_100"
        )
    )
    assert saved_admin is not None
    assert saved_admin.instrument_name == "CommCheck-v1"
    assert saved_admin.summary_scores_json == {"total": 2.0}

    saved_item = sqlite_session.scalar(
        select(AssessmentInstrumentItemRecord).where(
            AssessmentInstrumentItemRecord.item_id == "item_rec_1"
        )
    )
    assert saved_item is not None
    assert saved_item.response_value == "yes"
