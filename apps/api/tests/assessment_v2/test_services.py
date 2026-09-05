from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.assessment_v2.db.repositories import RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentPurpose,
    AssessmentSnapshot,
    AssessmentState,
    ChildSnapshot,
    ConsentPurpose,
    CreateChild,
    RecordConsent,
    StartAssessment,
    TransitionAssessment,
)
from app.assessment_v2.services import AssessmentService, ClinicalPolicyError
from app.core.security import CurrentUser


def therapist(role: str = "therapist", user_id: str = "therapist_01") -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        role=role,
        display_name="Synthetic Therapist",
        organization_id="org_alpha",
    )


def child() -> ChildSnapshot:
    return ChildSnapshot(
        id="child_01",
        organization_id="org_alpha",
        display_code="LL-0001",
        birth_year=2021,
        birth_month=6,
        language_context={"primary": "th", "additional": []},
        version=1,
    )


def assessment(state: AssessmentState = AssessmentState.DRAFT) -> AssessmentSnapshot:
    return AssessmentSnapshot(
        id="assessment_01",
        organization_id="org_alpha",
        child_id="child_01",
        purpose=AssessmentPurpose.INITIAL,
        state=state,
        assigned_clinician_id="therapist_01",
        version=1,
    )


class FakeRepository:
    def __init__(
        self,
        *,
        child_value: ChildSnapshot | None = None,
        active_consent: bool = True,
        withdraw_after_child_load: bool = False,
    ) -> None:
        self.child_value = child_value
        self.active_consent = active_consent
        self.withdraw_after_child_load = withdraw_after_child_load
        self.assessment_value = assessment()
        self.create_assessment_command = None
        self.transition_command = None

    def synchronize_principal(self, principal: CurrentUser, correlation_id: str) -> None:
        return None

    def create_child(self, scope: AccessScope, command: CreateChild, correlation_id: str):
        if scope.user_id == "inactive":
            raise RepositoryError("inactive_membership")
        return self.child_value or child()

    def get_child(self, scope: AccessScope, child_id: str):
        if self.withdraw_after_child_load:
            self.active_consent = False
        return self.child_value

    def list_children(self, scope: AccessScope):
        return [self.child_value] if self.child_value else []

    def add_consent(self, scope: AccessScope, child_id: str, command: RecordConsent, correlation_id: str):
        return None

    def has_active_consent(self, scope: AccessScope, child_id: str, purpose: ConsentPurpose) -> bool:
        return self.active_consent

    def create_assessment(self, scope: AccessScope, command, correlation_id: str):
        self.create_assessment_command = command
        return self.assessment_value

    def get_assessment(self, scope: AccessScope, assessment_id: str):
        return self.assessment_value

    def list_assessments(self, scope: AccessScope, child_id: str):
        return [self.assessment_value]

    def transition_assessment(self, scope: AccessScope, command: TransitionAssessment, correlation_id: str):
        self.transition_command = command
        return replace(self.assessment_value, state=command.target_state, version=2)


def service_for(repository: FakeRepository, user: CurrentUser | None = None) -> AssessmentService:
    service = AssessmentService(repository, user or therapist())
    service.now = lambda: datetime(2026, 9, 1, tzinfo=timezone.utc)
    return service


def test_inactive_membership_is_denied() -> None:
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(FakeRepository(), therapist(user_id="inactive")).create_child(
            CreateChild("LL-0001", 2021, 6, {"primary": "th", "additional": []}), "req-01"
        )

    assert error.value.code == "inactive_membership"


def test_role_outside_clinical_workflow_is_denied() -> None:
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(FakeRepository(child_value=child()), therapist(role="researcher")).get_child("child_01")

    assert error.value.code == "role_not_permitted"


@pytest.mark.parametrize("active_consent", [False])
def test_assessment_requires_latest_active_clinical_consent(active_consent: bool) -> None:
    repository = FakeRepository(child_value=child(), active_consent=active_consent)
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(repository).create_assessment(
            "child_01",
            StartAssessment(AssessmentPurpose.DEVELOPMENTAL_FOLLOW_UP),
            "req-02",
        )

    assert error.value.code == "active_consent_required"
    assert repository.create_assessment_command is None


def test_consent_is_checked_again_after_child_load_before_insert() -> None:
    repository = FakeRepository(
        child_value=child(), active_consent=True, withdraw_after_child_load=True
    )

    with pytest.raises(ClinicalPolicyError) as error:
        service_for(repository).create_assessment(
            "child_01",
            StartAssessment(AssessmentPurpose.INITIAL),
            "req-02b",
        )

    assert error.value.code == "active_consent_required"
    assert repository.create_assessment_command is None


def test_assigned_clinician_cannot_be_changed_by_ordinary_therapist() -> None:
    repository = FakeRepository(child_value=child(), active_consent=True)
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(repository).create_assessment(
            "child_01",
            StartAssessment(AssessmentPurpose.INITIAL, assigned_clinician_id="therapist_02"),
            "req-03",
        )

    assert error.value.code == "clinician_assignment_not_permitted"


def test_legal_assessment_creation_is_draft_version_one_with_child_context() -> None:
    repository = FakeRepository(child_value=child(), active_consent=True)
    created = service_for(repository).create_assessment(
        "child_01",
        StartAssessment(AssessmentPurpose.DEVELOPMENTAL_FOLLOW_UP),
        "req-04",
    )

    assert created.state is AssessmentState.DRAFT
    assert created.version == 1
    assert repository.create_assessment_command.age_months == 63
    assert repository.create_assessment_command.language_context == {"primary": "th", "additional": []}


def test_child_outside_tenant_or_care_team_is_not_disclosed() -> None:
    with pytest.raises(ClinicalPolicyError) as error:
        service_for(FakeRepository(child_value=None)).get_child("child_other")

    assert error.value.code == "child_not_found"
    assert error.value.status_code == 404


def test_capture_stage_is_fail_closed_but_draft_can_be_cancelled() -> None:
    repository = FakeRepository(child_value=child())
    service = service_for(repository)
    with pytest.raises(ClinicalPolicyError) as error:
        service.transition_assessment(
            "assessment_01",
            TransitionAssessment("assessment_01", AssessmentState.READY_FOR_CAPTURE, 1),
            "req-05",
        )
    assert error.value.code == "workflow_stage_unavailable"
    assert repository.transition_command is None

    cancelled = service.transition_assessment(
        "assessment_01",
        TransitionAssessment("assessment_01", AssessmentState.CANCELLED, 1),
        "req-06",
    )
    assert cancelled.state is AssessmentState.CANCELLED


def test_policy_error_details_are_fresh_and_safe() -> None:
    first = ClinicalPolicyError("example", 409, "Safe message")
    second = ClinicalPolicyError("example", 409, "Safe message")

    assert first.details == {}
    assert second.details == {}
    assert first.details is not second.details
    assert "child" not in str(first)
