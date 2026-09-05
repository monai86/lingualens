"""Tenant and care-team scoped persistence for the assessment v2 foundation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.orm import Session

from app.assessment_v2.db.models import (
    AssessmentRecord,
    AuditEventRecord,
    CareTeamAssignmentRecord,
    ChildRecord,
    ConsentRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    UserProfileRecord,
)
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentSnapshot,
    ChildSnapshot,
    ConsentPurpose,
    ConsentSnapshot,
    CreateAssessment,
    CreateChild,
    RecordConsent,
    TransitionAssessment,
)
from app.assessment_v2.domain.transitions import InvalidAssessmentTransition, transition_assessment
from app.core.security import CurrentUser


class RepositoryError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _context_to_storage(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _context_from_storage(value: str) -> dict[str, object]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RepositoryError("invalid_language_context")
    return parsed


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def synchronize_principal(self, principal: CurrentUser, correlation_id: str) -> None:
        with self.session.begin_nested():
            organization = self.session.get(OrganizationRecord, principal.organization_id)
            if organization is None:
                organization = OrganizationRecord(
                    organization_id=principal.organization_id,
                    display_label="Synthetic organization",
                    active=True,
                )
                self.session.add(organization)

            profile = self.session.get(UserProfileRecord, principal.user_id)
            if profile is None:
                self.session.add(
                    UserProfileRecord(user_id=principal.user_id, display_label=principal.display_name)
                )
            else:
                profile.display_label = principal.display_name

            membership = self.session.scalar(
                select(OrganizationMembershipRecord).where(
                    OrganizationMembershipRecord.organization_id == principal.organization_id,
                    OrganizationMembershipRecord.user_id == principal.user_id,
                )
            )
            if membership is None:
                self.session.add(
                    OrganizationMembershipRecord(
                        membership_id=uuid4().hex,
                        organization_id=principal.organization_id,
                        user_id=principal.user_id,
                        role=principal.role,
                        active=True,
                    )
                )
            elif membership.active:
                membership.role = principal.role
            self.session.flush()

    def create_child(self, scope: AccessScope, command: CreateChild, correlation_id: str) -> ChildSnapshot:
        self._require_active_membership(scope)
        now = _utc_now()
        with self.session.begin_nested():
            child = ChildRecord(
                child_id=uuid4().hex,
                organization_id=scope.organization_id,
                display_code=command.display_code,
                birth_year=command.birth_year,
                birth_month=command.birth_month,
                language_context=_context_to_storage(command.language_context),
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(child)
            self.session.flush()
            self.session.add(
                CareTeamAssignmentRecord(
                    assignment_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    child_id=child.child_id,
                    user_id=scope.user_id,
                    role="assigned_clinician",
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            self._append_audit(scope, "child.created", "child", child.child_id, correlation_id, [
                "display_code",
                "birth_month",
                "birth_year",
                "language_context",
            ])
            self.session.flush()
            return self._child_snapshot(child)

    def get_child(self, scope: AccessScope, child_id: str) -> ChildSnapshot | None:
        child = self.session.scalar(
            select(ChildRecord).where(
                ChildRecord.child_id == child_id,
                ChildRecord.organization_id == scope.organization_id,
            )
        )
        if child is None or not self._can_access_child(scope, child_id):
            return None
        return self._child_snapshot(child)

    def list_children(self, scope: AccessScope) -> list[ChildSnapshot]:
        if not self._has_active_membership(scope):
            return []
        query = select(ChildRecord).where(ChildRecord.organization_id == scope.organization_id)
        if scope.role != "org_admin":
            query = query.join(
                CareTeamAssignmentRecord,
                and_(
                    CareTeamAssignmentRecord.child_id == ChildRecord.child_id,
                    CareTeamAssignmentRecord.organization_id == scope.organization_id,
                    CareTeamAssignmentRecord.user_id == scope.user_id,
                    CareTeamAssignmentRecord.active.is_(True),
                ),
            )
        return [self._child_snapshot(child) for child in self.session.scalars(query).all()]

    def add_consent(
        self, scope: AccessScope, child_id: str, command: RecordConsent, correlation_id: str
    ) -> ConsentSnapshot:
        self._require_child_access(scope, child_id)
        now = _utc_now()
        with self.session.begin_nested():
            latest_version = self.session.scalar(
                select(func.max(ConsentRecord.version)).where(
                    ConsentRecord.organization_id == scope.organization_id,
                    ConsentRecord.child_id == child_id,
                    ConsentRecord.purpose == command.purpose.value,
                )
            ) or 0
            consent = ConsentRecord(
                consent_record_id=uuid4().hex,
                organization_id=scope.organization_id,
                child_id=child_id,
                purpose=command.purpose.value,
                scope_version=command.scope_version,
                status=command.status.value,
                granted_at=now,
                withdrawn_at=now if command.status.value == "withdrawn" else None,
                recorded_by_user_id=scope.user_id,
                version=latest_version + 1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(consent)
            self._append_audit(scope, "consent.recorded", "consent", consent.consent_record_id, correlation_id, [
                "purpose",
                "scope_version",
                "status",
            ])
            self.session.flush()
            return self._consent_snapshot(consent)

    def has_active_consent(self, scope: AccessScope, child_id: str, purpose: ConsentPurpose) -> bool:
        if not self._can_access_child(scope, child_id):
            return False
        latest = self.session.scalar(
            select(ConsentRecord)
            .where(
                ConsentRecord.organization_id == scope.organization_id,
                ConsentRecord.child_id == child_id,
                ConsentRecord.purpose == purpose.value,
            )
            .order_by(desc(ConsentRecord.version))
            .limit(1)
        )
        return latest is not None and latest.status == "active"

    def create_assessment(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        self._require_child_access(scope, command.child_id)
        now = _utc_now()
        with self.session.begin_nested():
            assessment = AssessmentRecord(
                assessment_id=uuid4().hex,
                organization_id=scope.organization_id,
                child_id=command.child_id,
                purpose=command.purpose.value,
                state="draft",
                age_months=command.age_months,
                language_context=_context_to_storage(command.language_context),
                assigned_clinician_id=command.assigned_clinician_id,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(assessment)
            self._append_audit(scope, "assessment.created", "assessment", assessment.assessment_id, correlation_id, [
                "child_id",
                "purpose",
                "age_months",
                "language_context",
                "assigned_clinician_id",
            ])
            self.session.flush()
            return self._assessment_snapshot(assessment)

    def get_assessment(self, scope: AccessScope, assessment_id: str) -> AssessmentSnapshot | None:
        record = self._assessment_record(scope, assessment_id)
        return self._assessment_snapshot(record) if record is not None else None

    def list_assessments(self, scope: AccessScope, child_id: str) -> list[AssessmentSnapshot]:
        if not self._can_access_child(scope, child_id):
            return []
        records = self.session.scalars(
            select(AssessmentRecord)
            .where(
                AssessmentRecord.organization_id == scope.organization_id,
                AssessmentRecord.child_id == child_id,
            )
            .order_by(AssessmentRecord.created_at)
        ).all()
        return [self._assessment_snapshot(record) for record in records]

    def transition_assessment(
        self, scope: AccessScope, command: TransitionAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        current_record = self._assessment_record(scope, command.assessment_id)
        if current_record is None:
            raise RepositoryError("assessment_not_found")
        current = self._assessment_snapshot(current_record)
        try:
            updated = transition_assessment(current, command.target_state, command.expected_version)
        except InvalidAssessmentTransition as error:
            raise RepositoryError(error.code) from error

        with self.session.begin_nested():
            result = self.session.execute(
                update(AssessmentRecord)
                .where(
                    AssessmentRecord.assessment_id == command.assessment_id,
                    AssessmentRecord.organization_id == scope.organization_id,
                    AssessmentRecord.version == command.expected_version,
                )
                .values(state=updated.state.value, version=updated.version, updated_at=_utc_now())
            )
            if result.rowcount != 1:
                exists = self.session.scalar(
                    select(AssessmentRecord.assessment_id).where(
                        AssessmentRecord.assessment_id == command.assessment_id,
                        AssessmentRecord.organization_id == scope.organization_id,
                    )
                )
                raise RepositoryError("stale_assessment_version" if exists is not None else "assessment_not_found")
            self._append_audit(
                scope,
                "assessment.transitioned",
                "assessment",
                command.assessment_id,
                correlation_id,
                ["state", "version"],
                target_version=updated.version,
            )
            self.session.flush()
            return updated

    def _has_active_membership(self, scope: AccessScope) -> bool:
        return (
            self.session.scalar(
                select(OrganizationMembershipRecord.membership_id)
                .join(
                    OrganizationRecord,
                    OrganizationRecord.organization_id == OrganizationMembershipRecord.organization_id,
                )
                .where(
                    OrganizationMembershipRecord.organization_id == scope.organization_id,
                    OrganizationMembershipRecord.user_id == scope.user_id,
                    OrganizationMembershipRecord.active.is_(True),
                    OrganizationRecord.active.is_(True),
                )
            )
            is not None
        )

    def _require_active_membership(self, scope: AccessScope) -> None:
        if not self._has_active_membership(scope):
            raise RepositoryError("inactive_membership")

    def _can_access_child(self, scope: AccessScope, child_id: str) -> bool:
        if not self._has_active_membership(scope):
            return False
        child_exists = self.session.scalar(
            select(ChildRecord.child_id).where(
                ChildRecord.child_id == child_id,
                ChildRecord.organization_id == scope.organization_id,
            )
        )
        if child_exists is None:
            return False
        if scope.role == "org_admin":
            return True
        return (
            self.session.scalar(
                select(CareTeamAssignmentRecord.assignment_id).where(
                    CareTeamAssignmentRecord.organization_id == scope.organization_id,
                    CareTeamAssignmentRecord.child_id == child_id,
                    CareTeamAssignmentRecord.user_id == scope.user_id,
                    CareTeamAssignmentRecord.active.is_(True),
                )
            )
            is not None
        )

    def _require_child_access(self, scope: AccessScope, child_id: str) -> None:
        if not self._can_access_child(scope, child_id):
            raise RepositoryError("child_not_found")

    def _assessment_record(self, scope: AccessScope, assessment_id: str) -> AssessmentRecord | None:
        record = self.session.scalar(
            select(AssessmentRecord).where(
                AssessmentRecord.assessment_id == assessment_id,
                AssessmentRecord.organization_id == scope.organization_id,
            )
        )
        if record is None or not self._can_access_child(scope, record.child_id):
            return None
        return record

    def _append_audit(
        self,
        scope: AccessScope,
        action: str,
        target_type: str,
        target_id: str,
        correlation_id: str,
        changed_fields: list[str],
        *,
        target_version: int | None = None,
    ) -> None:
        self.session.add(
            AuditEventRecord(
                audit_event_id=uuid4().hex,
                organization_id=scope.organization_id,
                actor_user_id=scope.user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                outcome="success",
                correlation_id=correlation_id,
                target_version=target_version,
                metadata_json={"changed_fields": changed_fields},
                occurred_at=_utc_now(),
            )
        )

    @staticmethod
    def _child_snapshot(child: ChildRecord) -> ChildSnapshot:
        return ChildSnapshot(
            id=child.child_id,
            organization_id=child.organization_id,
            display_code=child.display_code,
            birth_year=child.birth_year,
            birth_month=child.birth_month,
            language_context=_context_from_storage(child.language_context),
            version=child.version,
        )

    @staticmethod
    def _consent_snapshot(consent: ConsentRecord) -> ConsentSnapshot:
        from app.assessment_v2.domain.models import ConsentStatus

        return ConsentSnapshot(
            id=consent.consent_record_id,
            organization_id=consent.organization_id,
            child_id=consent.child_id,
            purpose=ConsentPurpose(consent.purpose),
            scope_version=consent.scope_version,
            status=ConsentStatus(consent.status),
            granted_at=consent.granted_at,
            withdrawn_at=consent.withdrawn_at,
            recorded_by_user_id=consent.recorded_by_user_id,
            version=consent.version,
        )

    @staticmethod
    def _assessment_snapshot(assessment: AssessmentRecord) -> AssessmentSnapshot:
        from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState

        return AssessmentSnapshot(
            id=assessment.assessment_id,
            organization_id=assessment.organization_id,
            child_id=assessment.child_id,
            purpose=AssessmentPurpose(assessment.purpose),
            state=AssessmentState(assessment.state),
            assigned_clinician_id=assessment.assigned_clinician_id,
            version=assessment.version,
        )
