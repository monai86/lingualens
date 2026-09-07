from __future__ import annotations

from collections.abc import Iterator
import re
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentRecord,
    AuditEventRecord,
    CareTeamAssignmentRecord,
    ConsentRecord,
    OrganizationMembershipRecord,
)
from app.assessment_v2.db.repositories import AssessmentRepository, RepositoryError
from app.assessment_v2.dependencies import get_assessment_service
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
from app.assessment_v2.services import ClinicalPolicyError


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
    membership = repo.session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == scope_value.organization_id,
            OrganizationMembershipRecord.user_id == scope_value.user_id,
        )
    )
    if membership is None:
        repo.session.add(
            OrganizationMembershipRecord(
                membership_id=uuid4().hex,
                organization_id=scope_value.organization_id,
                user_id=scope_value.user_id,
                role=scope_value.role,
                active=True,
            )
        )
        repo.session.flush()


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


def assign_clinician(
    session: Session,
    clinician: AccessScope,
    child_id: str,
) -> CareTeamAssignmentRecord:
    assignment = CareTeamAssignmentRecord(
        assignment_id=uuid4().hex,
        organization_id=clinician.organization_id,
        child_id=child_id,
        user_id=clinician.user_id,
        role="assigned_clinician",
        active=True,
    )
    session.add(assignment)
    session.flush()
    return assignment


def grant_active_clinical_assessment_consent(
    repo: AssessmentRepository,
    scope_value: AccessScope,
    child_id: str,
) -> None:
    repo.add_consent(
        scope_value,
        child_id,
        RecordConsent(
            purpose=ConsentPurpose.CLINICAL_ASSESSMENT,
            scope_version="clinical-v1",
            status=ConsentStatus.ACTIVE,
        ),
        correlation_id="consent-active",
    )


def assessment_command(child_id: str, clinician_id: str) -> CreateAssessment:
    return CreateAssessment(
        child_id=child_id,
        purpose=AssessmentPurpose.INITIAL,
        age_months=36,
        language_context={"primary": "th", "additional": []},
        assigned_clinician_id=clinician_id,
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


def test_synchronize_principal_does_not_provision_unknown_membership(session: Session) -> None:
    repo = AssessmentRepository(session)
    unknown = scope("unknown_principal")

    repo.synchronize_principal(user(unknown), correlation_id="sync-unknown")

    assert session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == unknown.organization_id,
            OrganizationMembershipRecord.user_id == unknown.user_id,
        )
    ) is None
    assert repo.has_active_membership(unknown) is False


def test_persisted_membership_role_is_available_for_authorization_scope(session: Session) -> None:
    therapist = scope("therapist_01", role="org_admin")
    synchronize(repo := AssessmentRepository(session), scope("therapist_01", role="therapist"))
    membership = session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == therapist.organization_id,
            OrganizationMembershipRecord.user_id == therapist.user_id,
        )
    )
    assert membership is not None
    membership.role = "therapist"
    membership.active = True
    session.flush()

    assert repo.active_membership_role(therapist) == "therapist"


def test_dependency_does_not_allow_stale_admin_claim_to_bypass_care_team_scope(session: Session) -> None:
    repo = AssessmentRepository(session)
    owner = scope("owner_01")
    stale_admin = scope("stale_admin_01", role="therapist")
    synchronize(repo, owner)
    synchronize(repo, stale_admin)
    child = create_child(repo, owner, "LL-STALE-ROLE")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/api/v2/children/{child.id}",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
        }
    )

    stale_admin_claim = scope(stale_admin.user_id, role="org_admin")
    service = get_assessment_service(request, user(stale_admin_claim), repo, object())

    with pytest.raises(ClinicalPolicyError) as error:
        service.get_child(child.id)

    assert error.value.code == "child_not_found"


def test_assessment_service_dependency_rejects_unknown_membership(session: Session) -> None:
    repo = AssessmentRepository(session)
    unknown = scope("unknown_dependency_principal")
    repo.synchronize_principal(user(unknown), correlation_id="sync-unknown-dependency")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v2/children",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
        }
    )

    with pytest.raises(ClinicalPolicyError) as error:
        get_assessment_service(request, user(unknown), repo, object())

    assert error.value.code == "inactive_membership"


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


def test_assessment_creation_rechecks_a_deactivated_assignee_care_team_assignment(
    session: Session,
) -> None:
    repo = AssessmentRepository(session)
    supervisor = scope("supervisor_01", role="clinical_supervisor")
    assignee = scope("therapist_assignee")
    synchronize(repo, supervisor)
    synchronize(repo, assignee)
    child = create_child(repo, supervisor, "LL-ASSIGNMENT-STATE")
    assignment = assign_clinician(session, assignee, child.id)
    grant_active_clinical_assessment_consent(repo, supervisor, child.id)

    assert repo.can_assign_clinician(supervisor, child.id, assignee.user_id) is True
    assignment.active = False
    session.flush()
    audit_count = session.scalar(select(func.count()).select_from(AuditEventRecord))

    with pytest.raises(RepositoryError) as error:
        repo.create_assessment_if_consented(
            supervisor,
            assessment_command(child.id, assignee.user_id),
            correlation_id="assessment-after-assignment-change",
        )

    assert error.value.code == "clinician_assignment_not_permitted"
    assert session.scalar(select(func.count()).select_from(AssessmentRecord)) == 0
    assert session.scalar(select(func.count()).select_from(AuditEventRecord)) == audit_count


def test_assessment_creation_rechecks_a_deactivated_assignee_membership(
    session: Session,
) -> None:
    repo = AssessmentRepository(session)
    supervisor = scope("supervisor_01", role="clinical_supervisor")
    assignee = scope("therapist_assignee")
    synchronize(repo, supervisor)
    synchronize(repo, assignee)
    child = create_child(repo, supervisor, "LL-MEMBERSHIP-STATE")
    assign_clinician(session, assignee, child.id)
    grant_active_clinical_assessment_consent(repo, supervisor, child.id)

    assert repo.can_assign_clinician(supervisor, child.id, assignee.user_id) is True
    membership = session.scalar(
        select(OrganizationMembershipRecord).where(
            OrganizationMembershipRecord.organization_id == assignee.organization_id,
            OrganizationMembershipRecord.user_id == assignee.user_id,
        )
    )
    assert membership is not None
    membership.active = False
    session.flush()
    audit_count = session.scalar(select(func.count()).select_from(AuditEventRecord))

    with pytest.raises(RepositoryError) as error:
        repo.create_assessment_if_consented(
            supervisor,
            assessment_command(child.id, assignee.user_id),
            correlation_id="assessment-after-membership-change",
        )

    assert error.value.code == "clinician_assignment_not_permitted"
    assert session.scalar(select(func.count()).select_from(AssessmentRecord)) == 0
    assert session.scalar(select(func.count()).select_from(AuditEventRecord)) == audit_count


def test_repository_audit_boundary_sanitizes_direct_correlation_input(session: Session) -> None:
    repo = AssessmentRepository(session)
    therapist = scope("therapist_01")
    synchronize(repo, therapist)
    untrusted_correlation_id = "operator-supplied-correlation-value"

    child = repo.create_child(
        therapist,
        CreateChild(
            display_code="LL-AUDIT-CORRELATION-UNTRUSTED",
            birth_year=2021,
            birth_month=6,
            language_context={"primary": "th", "additional": []},
        ),
        correlation_id=untrusted_correlation_id,
    )

    audit = session.scalar(
        select(AuditEventRecord)
        .where(AuditEventRecord.action == "child.created")
        .where(AuditEventRecord.target_id == child.id)
        .order_by(AuditEventRecord.occurred_at.desc())
    )

    assert audit is not None
    assert re.fullmatch(r"[0-9a-f]{32}", audit.correlation_id)
    assert audit.correlation_id != untrusted_correlation_id


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
