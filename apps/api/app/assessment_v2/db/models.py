"""Relational contract for the fresh assessment v2 database."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.domain.models import AssessmentPurpose, AssessmentState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


_PURPOSE_VALUES = ", ".join(f"'{purpose.value}'" for purpose in AssessmentPurpose)
_STATE_VALUES = ", ".join(f"'{state.value}'" for state in AssessmentState)


class OrganizationRecord(AssessmentBase):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_label: Mapped[str] = mapped_column(String(256), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserProfileRecord(AssessmentBase):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_label: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OrganizationMembershipRecord(AssessmentBase):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_organization_user"),
        CheckConstraint(
            "role IN ('therapist', 'clinical_supervisor', 'org_admin', 'researcher')",
            name="ck_membership_role",
        ),
    )

    membership_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_membership_organization"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.user_id", name="fk_membership_user"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ChildRecord(AssessmentBase):
    __tablename__ = "children"
    __table_args__ = (
        UniqueConstraint("organization_id", "display_code", name="uq_child_organization_display_code"),
        CheckConstraint("birth_month BETWEEN 1 AND 12", name="ck_children_birth_month"),
        CheckConstraint("birth_year BETWEEN 1900 AND 2100", name="ck_children_birth_year"),
        CheckConstraint("version >= 1", name="ck_children_version"),
    )

    child_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_children_organization"),
        nullable=False,
        index=True,
    )
    display_code: Mapped[str] = mapped_column(String(128), nullable=False)
    birth_month: Mapped[int] = mapped_column(Integer, nullable=False)
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)
    language_context: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CareTeamAssignmentRecord(AssessmentBase):
    __tablename__ = "care_team_assignments"
    __table_args__ = (
        UniqueConstraint("organization_id", "child_id", "user_id", name="uq_care_team_organization_child_user"),
        CheckConstraint(
            "role IN ('assigned_clinician', 'supervisor', 'observer')",
            name="ck_care_team_role",
        ),
    )

    assignment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_care_team_organization"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_care_team_child"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.user_id", name="fk_care_team_user"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ConsentRecord(AssessmentBase):
    __tablename__ = "consent_records"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('clinical_assessment', 'research_reuse')",
            name="ck_consent_records_purpose",
        ),
        CheckConstraint("status IN ('active', 'withdrawn')", name="ck_consent_records_status"),
        CheckConstraint("version >= 1", name="ck_consent_records_version"),
    )

    consent_record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_consent_organization"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_consent_child"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentRecord(AssessmentBase):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(f"purpose IN ({_PURPOSE_VALUES})", name="ck_assessments_purpose"),
        CheckConstraint(f"state IN ({_STATE_VALUES})", name="ck_assessments_state"),
        CheckConstraint("age_months BETWEEN 0 AND 216", name="ck_assessments_age_months"),
        CheckConstraint("version >= 1", name="ck_assessments_version"),
    )

    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_assessments_organization"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_assessments_child"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    language_context: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_clinician_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.user_id", name="fk_assessments_clinician"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEventRecord(AssessmentBase):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_audit_events_organization"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_version: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
