"""Clinical policy boundary for the assessment v2 persistence layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Protocol, TypeVar

from app.assessment_v2.db.repositories import RepositoryError
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentSnapshot,
    AssessmentState,
    ChildSnapshot,
    ConsentPurpose,
    CreateAssessment,
    CreateChild,
    RecordConsent,
    StartAssessment,
    TransitionAssessment,
)
from app.core.security import CurrentUser


class AssessmentRepository(Protocol):
    def create_child(self, scope: AccessScope, command: CreateChild, correlation_id: str) -> ChildSnapshot: ...

    def get_child(self, scope: AccessScope, child_id: str) -> ChildSnapshot | None: ...

    def list_children(self, scope: AccessScope) -> list[ChildSnapshot]: ...

    def add_consent(
        self, scope: AccessScope, child_id: str, command: RecordConsent, correlation_id: str
    ): ...

    def has_active_consent(self, scope: AccessScope, child_id: str, purpose: ConsentPurpose) -> bool: ...

    def create_assessment(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot: ...

    def get_assessment(self, scope: AccessScope, assessment_id: str) -> AssessmentSnapshot | None: ...

    def list_assessments(self, scope: AccessScope, child_id: str) -> list[AssessmentSnapshot]: ...

    def transition_assessment(
        self, scope: AccessScope, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot: ...


class ClinicalPolicyError(Exception):
    """A safe, user-facing policy failure from the clinical service boundary."""

    def __init__(
        self,
        code: str,
        status_code: int,
        safe_message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.safe_message = safe_message
        self.details = dict(details) if details is not None else {}
        super().__init__(safe_message)


_CLINICAL_ROLES = frozenset({"therapist", "clinical_supervisor", "org_admin"})
_OVERSIGHT_ROLES = frozenset({"clinical_supervisor", "org_admin"})
_MAX_ASSESSMENT_AGE_MONTHS = 216
_POLICY_MESSAGES: dict[str, tuple[int, str]] = {
    "inactive_membership": (403, "Active organization membership is required."),
    "role_not_permitted": (403, "This role is not permitted for the clinical workflow."),
    "child_not_found": (404, "Child was not found."),
    "assessment_not_found": (404, "Assessment was not found."),
    "active_consent_required": (409, "Active clinical-assessment consent is required."),
    "clinician_assignment_not_permitted": (403, "Clinician assignment is not permitted."),
    "age_out_of_range": (422, "Child age is outside the supported assessment range."),
    "workflow_stage_unavailable": (409, "This workflow stage is not yet available."),
    "stale_assessment_version": (409, "The assessment version is stale."),
    "invalid_assessment_transition": (409, "The assessment transition is not permitted."),
}

_Result = TypeVar("_Result")


class AssessmentService:
    def __init__(self, repository: AssessmentRepository, user: CurrentUser) -> None:
        self.repository = repository
        self.user = user
        self.now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def create_child(self, command: CreateChild, correlation_id: str) -> ChildSnapshot:
        self._require_clinical_role()
        return self._repository_call(
            lambda: self.repository.create_child(self.scope, command, correlation_id)
        )

    def get_child(self, child_id: str) -> ChildSnapshot:
        self._require_clinical_role()
        child = self._repository_call(lambda: self.repository.get_child(self.scope, child_id))
        if child is None:
            raise self._policy_error("child_not_found")
        return child

    def list_children(self) -> list[ChildSnapshot]:
        self._require_clinical_role()
        return self._repository_call(lambda: self.repository.list_children(self.scope))

    def grant_consent(self, child_id: str, command: RecordConsent, correlation_id: str):
        self._require_clinical_role()
        return self._repository_call(
            lambda: self.repository.add_consent(self.scope, child_id, command, correlation_id)
        )

    def create_assessment(
        self, child_id: str, command: StartAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self._require_clinical_role()
        child = self.get_child(child_id)

        assigned_clinician_id = command.assigned_clinician_id or self.user.user_id
        if (
            assigned_clinician_id != self.user.user_id
            and self.user.role not in _OVERSIGHT_ROLES
        ):
            raise self._policy_error("clinician_assignment_not_permitted")

        # Keep this check immediately adjacent to insertion so a previously loaded
        # child cannot turn a withdrawn consent into an assessment.
        if not self._repository_call(
            lambda: self.repository.has_active_consent(
                self.scope, child_id, ConsentPurpose.CLINICAL_ASSESSMENT
            )
        ):
            raise self._policy_error("active_consent_required")

        age_months = self._age_in_months(child)
        create_command = CreateAssessment(
            child_id=child_id,
            purpose=command.purpose,
            age_months=age_months,
            language_context=dict(child.language_context),
            assigned_clinician_id=assigned_clinician_id,
        )
        return self._repository_call(
            lambda: self.repository.create_assessment(self.scope, create_command, correlation_id)
        )

    def get_assessment(self, assessment_id: str) -> AssessmentSnapshot:
        self._require_clinical_role()
        assessment = self._repository_call(
            lambda: self.repository.get_assessment(self.scope, assessment_id)
        )
        if assessment is None:
            raise self._policy_error("assessment_not_found")
        return assessment

    def list_assessments(self, child_id: str) -> list[AssessmentSnapshot]:
        self._require_clinical_role()
        self.get_child(child_id)
        return self._repository_call(lambda: self.repository.list_assessments(self.scope, child_id))

    def transition_assessment(
        self, assessment_id: str, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self._require_clinical_role()
        current = self.get_assessment(assessment_id)
        if (
            current.state is not AssessmentState.DRAFT
            or command.target_state is not AssessmentState.CANCELLED
        ):
            raise self._policy_error("workflow_stage_unavailable")
        return self._repository_call(
            lambda: self.repository.transition_assessment(self.scope, command, correlation_id)
        )

    @property
    def scope(self) -> AccessScope:
        return AccessScope(
            user_id=self.user.user_id,
            organization_id=self.user.organization_id,
            role=self.user.role,
        )

    def _require_clinical_role(self) -> None:
        if not self.user.membership_active:
            raise self._policy_error("inactive_membership")
        if self.user.role not in _CLINICAL_ROLES:
            raise self._policy_error("role_not_permitted")

    def _age_in_months(self, child: ChildSnapshot) -> int:
        current = self.now()
        age_months = (current.year - child.birth_year) * 12 + current.month - child.birth_month
        if not 0 <= age_months <= _MAX_ASSESSMENT_AGE_MONTHS:
            raise self._policy_error("age_out_of_range")
        return age_months

    def _repository_call(self, operation: Callable[[], _Result]) -> _Result:
        try:
            return operation()
        except RepositoryError as error:
            raise self._policy_error(error.code) from error

    @staticmethod
    def _policy_error(code: str) -> ClinicalPolicyError:
        status_code, safe_message = _POLICY_MESSAGES.get(
            code, (409, "The clinical operation could not be completed.")
        )
        return ClinicalPolicyError(code, status_code, safe_message)
