from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    AuditEventRecord,
    CareTeamAssignmentRecord,
    ConsentRecord,
    OrganizationMembershipRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository, RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentState,
    CreateAssessment,
    CreateChild,
    RecordConsent,
    ConsentPurpose,
    ConsentStatus,
    TransitionAssessment,
)
from app.core.security import CurrentUser


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AssessmentBase.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as value:
        yield value
    AssessmentBase.metadata.drop_all(engine)


def scope(user_id: str, organization_id: str = "org_alpha", role: str = "therapist") -> AccessScope:
    return AccessScope(user_id=user_id, organization_id=organization_id, role=role)


def user(scope_value: AccessScope) -> CurrentUser:
    return CurrentUser(
        user_id=scope_value.user_id,
        organization_id=scope_value.organization_id,
        role=scope_value.role,
        display_name="Synthetic User",
    )


def synchronize(repo: AssessmentRepository, scope_value: AccessScope) -> None:
    repo.synchronize_principal(user(scope_value), correlation_id=f"sync-{scope_value.user_id}")


def create_child(repo: AssessmentRepository, scope_value: AccessScope, code: str = "LL-0001"):
    return repo.create_child(
        scope_value,
        CreateChild(
            display_code=code,
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": []},
        ),
        correlation_id=f"create-{code}",
    )


def test_create_child_assigns_creator_and_audits(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_01")
    synchronize(repo, therapist)

    child = create_child(repo, therapist)

    assert repo.get_child(therapist, child.id) == child
    assert session.scalar(select(func.count()).select_from(CareTeamAssignmentRecord)) == 1
    assert session.scalar(select(func.count()).select_from(AuditEventRecord)) == 1


def test_synchronize_principal_does_not_reactivate_inactive_membership(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_01")
    synchronize(repo, therapist)
    create_child(repo, therapist)
    membership = session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == therapist.organization_id,
            OrganizationMembershipRecord.user_id == therapist.user_id,
        )
    )
    assert membership is not None
    membership.active = False
    session.flush()

    repo.synchronize_principal(user(therapist), correlation_id="sync-again")

    assert membership.active is False
    assert repo.list_children(therapist) == []


def test_tenant_and_care_team_isolation_and_admin_access(session: Session) -> None:
    repo = AssessmentRepository(session)
    alpha_therapist = scope("therapist_alpha")
    beta_therapist = scope("therapist_beta", organization_id="org_beta")
    outsider = scope("therapist_outside")
    admin = scope("admin_alpha", role="org_admin")
    for current in (alpha_therapist, beta_therapist, outsider, admin):
        synchronize(repo, current)
    alpha_child = create_child(repo, alpha_therapist, "LL-ALPHA")
    beta_child = create_child(repo, beta_therapist, "LL-BETA")

    assert repo.get_child(alpha_therapist, beta_child.id) is None
    assert repo.get_child(outsider, alpha_child.id) is None
    assert repo.get_child(admin, alpha_child.id) == alpha_child
    assert repo.get_child(admin, beta_child.id) is None


def test_assignee_must_be_an_active_member_of_the_child_care_team(session: Session) -> None:
    repo = AssessmentRepository(session)
    alpha_therapist = scope("therapist_alpha")
    beta_therapist = scope("therapist_beta", organization_id="org_beta")
    synchronize(repo, alpha_therapist)
    synchronize(repo, beta_therapist)
    alpha_child = create_child(repo, alpha_therapist, "LL-ASSIGN")

    assert repo.can_assign_clinician(alpha_therapist, alpha_child.id, alpha_therapist.user_id) is True
    assert repo.can_assign_clinician(alpha_therapist, alpha_child.id, beta_therapist.user_id) is False


def test_assessment_creation_rechecks_consent_inside_the_insert_transaction(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_atomic")
    synchronize(repo, therapist)
    child = create_child(repo, therapist, "LL-ATOMIC")
    repo.add_consent(
        therapist,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id="consent-atomic",
    )
    repo.add_consent(
        therapist,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.WITHDRAWN,
        ),
        correlation_id="consent-atomic-withdrawn",
    )

    with pytest.raises(RepositoryError, match="active_consent_required"):
        repo.create_assessment_if_consented(
            therapist,
            CreateAssessment(
                child_id=child.id,
                purpose=AssessmentPurpose.INITIAL,
                age_months=36,
                language_context={"primary": "th", "additional": []},
                assigned_clinician_id=therapist.user_id,
            ),
            correlation_id="assessment-atomic",
        )


def test_consent_is_append_only_and_withdrawal_removes_active_access(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_01")
    synchronize(repo, therapist)
    child = create_child(repo, therapist)

    granted = repo.add_consent(
        therapist,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id="consent-active",
    )
    withdrawn = repo.add_consent(
        therapist,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.WITHDRAWN,
        ),
        correlation_id="consent-withdrawn",
    )

    assert granted.id != withdrawn.id
    assert session.scalar(select(func.count()).select_from(ConsentRecord)) == 2
    assert repo.has_active_consent(therapist, child.id, ConsentPurpose.CLINICAL_ASSESSMENT) is False
    assert session.scalar(select(func.count()).select_from(AuditEventRecord)) == 3


def test_transition_uses_optimistic_version_and_rolls_back_stale_write(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_01")
    synchronize(repo, therapist)
    child = create_child(repo, therapist)
    repo.add_consent(
        therapist,
        child.id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id="consent-active",
    )
    assessment = repo.create_assessment(
        therapist,
        CreateAssessment(
            child_id=child.id,
            purpose=AssessmentPurpose.INITIAL,
            age_months=36,
            language_context={"primary": "th", "additional": []},
            assigned_clinician_id=therapist.user_id,
        ),
        correlation_id="assessment-create",
    )
    transitioned = repo.transition_assessment(
        therapist,
        TransitionAssessment(
            assessment_id=assessment.id,
            target_state=AssessmentState.READY_FOR_CAPTURE,
            expected_version=1,
        ),
        correlation_id="assessment-transition",
    )
    audit_count = session.scalar(select(func.count()).select_from(AuditEventRecord))

    assert transitioned.state is AssessmentState.READY_FOR_CAPTURE
    assert transitioned.version == 2
    with pytest.raises(RepositoryError, match="stale_assessment_version") as error:
        repo.transition_assessment(
            therapist,
            TransitionAssessment(
                assessment_id=assessment.id,
                target_state=AssessmentState.CAPTURING,
                expected_version=1,
            ),
            correlation_id="assessment-stale",
        )

    assert error.value.code == "stale_assessment_version"
    assert session.scalar(select(func.count()).select_from(AuditEventRecord)) == audit_count
    stored = session.get(AssessmentRecord, assessment.id)
    assert stored is not None
    assert stored.state == AssessmentState.READY_FOR_CAPTURE.value
    assert stored.version == 2
