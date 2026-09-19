"""Tests for Assessment V2 Observations & Instruments repository."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    CareTeamAssignmentRecord,
    ChildRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    UserProfileRecord,
)
from app.assessment_v2.db.observations_repository import ObservationsRepository
from app.assessment_v2.domain.instruments import (
    InstrumentAdministration,
    InstrumentItemResponse,
    InstrumentRespondentType,
)
from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState
from app.assessment_v2.domain.observations import (
    ObservationCategory,
    ObservationRecordValue,
    ObservationSource,
)


@pytest.fixture
def repo_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AssessmentBase.metadata.create_all(engine)
    with Session(engine) as session:
        # Organization 1
        org1 = OrganizationRecord(organization_id="org_1", display_label="Clinic 1")
        session.add(org1)

        # Users
        u1 = UserProfileRecord(user_id="usr_clinician", display_label="Dr. Clinician")
        u2 = UserProfileRecord(user_id="usr_observer", display_label="Nurse Observer")
        session.add_all([u1, u2])
        session.flush()

        # Memberships
        m1 = OrganizationMembershipRecord(
            membership_id="mem_1",
            organization_id="org_1",
            user_id="usr_clinician",
            role="therapist",
        )
        m2 = OrganizationMembershipRecord(
            membership_id="mem_2",
            organization_id="org_1",
            user_id="usr_observer",
            role="therapist",
        )
        session.add_all([m1, m2])
        session.flush()

        # Child
        child = ChildRecord(
            child_id="child_1",
            organization_id="org_1",
            display_code="CH-101",
            birth_month=1,
            birth_year=2022,
            language_context="th-TH",
        )
        session.add(child)
        session.flush()

        # Care Team: Clinician is assigned_clinician, Observer is observer
        ct1 = CareTeamAssignmentRecord(
            assignment_id="ct_1",
            organization_id="org_1",
            child_id="child_1",
            user_id="usr_clinician",
            role="assigned_clinician",
        )
        ct2 = CareTeamAssignmentRecord(
            assignment_id="ct_2",
            organization_id="org_1",
            child_id="child_1",
            user_id="usr_observer",
            role="observer",
        )
        session.add_all([ct1, ct2])

        # Assessment
        assessment = AssessmentRecord(
            assessment_id="asm_1",
            organization_id="org_1",
            child_id="child_1",
            purpose=AssessmentPurpose.INITIAL.value,
            state=AssessmentState.DRAFT.value,
            age_months=40,
            language_context="th-TH",
            assigned_clinician_id="usr_clinician",
        )
        session.add(assessment)
        session.commit()

        yield session


def test_create_and_list_observation(repo_session: Session):
    repo = ObservationsRepository(repo_session)
    now = datetime.now(timezone.utc)
    obs = ObservationRecordValue(
        observation_id="obs_01",
        organization_id="org_1",
        assessment_id="asm_1",
        category=ObservationCategory.COMMUNICATION,
        source=ObservationSource.CLINICIAN,
        observer_name="Dr. Clinician",
        observer_role="slp",
        observed_at=now,
        activity_context="Picture card description",
        notes="Child named 4 of 5 target pictures.",
        structured_flags=("single_word_naming",),
    )

    created = repo.create_observation(obs, actor_user_id="usr_clinician")
    assert created.observation_id == "obs_01"

    listed = repo.list_observations(organization_id="org_1", assessment_id="asm_1")
    assert len(listed) == 1
    assert listed[0].observation_id == "obs_01"
    assert listed[0].notes == "Child named 4 of 5 target pictures."


def test_observer_role_denied_from_creating_observation(repo_session: Session):
    repo = ObservationsRepository(repo_session)
    now = datetime.now(timezone.utc)
    obs = ObservationRecordValue(
        observation_id="obs_02",
        organization_id="org_1",
        assessment_id="asm_1",
        category=ObservationCategory.SOCIAL_ENGAGEMENT,
        source=ObservationSource.CLINICIAN,
        observer_name="Nurse Observer",
        observer_role="observer",
        observed_at=now,
        activity_context="Free play",
        notes="Notes from observer",
    )

    with pytest.raises(PermissionError, match="editor-capable"):
        repo.create_observation(obs, actor_user_id="usr_observer")


def test_observation_amendment_lifecycle(repo_session: Session):
    repo = ObservationsRepository(repo_session)
    now = datetime.now(timezone.utc)
    obs1 = ObservationRecordValue(
        observation_id="obs_orig",
        organization_id="org_1",
        assessment_id="asm_1",
        category=ObservationCategory.COMMUNICATION,
        source=ObservationSource.CLINICIAN,
        observer_name="Dr. Clinician",
        observer_role="slp",
        observed_at=now,
        activity_context="Play",
        notes="Child spoke 10 words.",
    )
    repo.create_observation(obs1, actor_user_id="usr_clinician")

    # Create amendment
    amendment = ObservationRecordValue(
        observation_id="obs_amend",
        organization_id="org_1",
        assessment_id="asm_1",
        category=ObservationCategory.COMMUNICATION,
        source=ObservationSource.CLINICIAN,
        observer_name="Dr. Clinician",
        observer_role="slp",
        observed_at=now,
        activity_context="Play",
        notes="Correction: child spoke 12 words (including 2 self-corrections).",
        is_amendment=True,
        amends_observation_id="obs_orig",
        version=2,
    )
    repo.create_observation(amendment, actor_user_id="usr_clinician")

    listed = repo.list_observations(organization_id="org_1", assessment_id="asm_1")
    assert len(listed) == 2


def test_instrument_administration_repository_lifecycle(repo_session: Session):
    repo = ObservationsRepository(repo_session)
    now = datetime.now(timezone.utc)
    item = InstrumentItemResponse(
        item_key="item_q1",
        prompt_label="Responds when called by name",
        response_value=True,
        score=1.0,
    )
    admin = InstrumentAdministration(
        administration_id="admin_01",
        organization_id="org_1",
        assessment_id="asm_1",
        instrument_name="Generic-Comm-Screen",
        instrument_version="1.0",
        respondent_type=InstrumentRespondentType.CAREGIVER,
        administered_by_user_id="usr_clinician",
        administered_at=now,
        licensing_verified=True,
        summary_scores={"score": 1.0},
        items=(item,),
    )

    created = repo.create_instrument_administration(admin, actor_user_id="usr_clinician")
    assert created.administration_id == "admin_01"

    listed = repo.list_instrument_administrations(organization_id="org_1", assessment_id="asm_1")
    assert len(listed) == 1
    assert listed[0].administration_id == "admin_01"
    assert len(listed[0].items) == 1
    assert listed[0].items[0].item_key == "item_q1"
