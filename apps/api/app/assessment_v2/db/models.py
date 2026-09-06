"""Relational contract for the fresh assessment v2 database."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentState,
    ProcessingRunStage,
    ProcessingRunState,
    RecordingQualityStatus,
    RecordingUploadState,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def opaque_id() -> str:
    return uuid4().hex


_PURPOSE_VALUES = ", ".join(f"'{purpose.value}'" for purpose in AssessmentPurpose)
_STATE_VALUES = ", ".join(f"'{state.value}'" for state in AssessmentState)
_UPLOAD_STATE_VALUES = ", ".join(f"'{state.value}'" for state in RecordingUploadState)
_PROCESSING_STAGE_VALUES = ", ".join(f"'{stage.value}'" for stage in ProcessingRunStage)
_PROCESSING_STATE_VALUES = ", ".join(f"'{state.value}'" for state in ProcessingRunState)
_QUALITY_STATUS_VALUES = ", ".join(f"'{status.value}'" for status in RecordingQualityStatus)


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
        UniqueConstraint("organization_id", "child_id", name="uq_children_organization_child"),
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
        ForeignKeyConstraint(
            ["organization_id", "child_id"],
            ["children.organization_id", "children.child_id"],
            name="fk_care_team_child_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_care_team_membership_tenant",
        ),
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
        UniqueConstraint(
            "organization_id",
            "child_id",
            "purpose",
            "version",
            name="uq_consent_organization_child_purpose_version",
        ),
        ForeignKeyConstraint(
            ["organization_id", "child_id"],
            ["children.organization_id", "children.child_id"],
            name="fk_consent_child_tenant",
        ),
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
        UniqueConstraint("organization_id", "assessment_id", name="uq_assessments_organization_assessment"),
        ForeignKeyConstraint(
            ["organization_id", "child_id"],
            ["children.organization_id", "children.child_id"],
            name="fk_assessments_child_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assigned_clinician_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_assessments_clinician_membership_tenant",
        ),
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
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProtocolVersionRecord(AssessmentBase):
    __tablename__ = "protocol_versions"
    __table_args__ = (
        CheckConstraint("length(primary_language) > 0", name="ck_protocol_versions_primary_language"),
        CheckConstraint("minimum_age_months >= 0", name="ck_protocol_versions_minimum_age"),
        CheckConstraint(
            "maximum_age_months >= minimum_age_months",
            name="ck_protocol_versions_age_range",
        ),
        CheckConstraint("length(supported_purposes) > 0", name="ck_protocol_versions_supported_purposes"),
    )

    protocol_version_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    primary_language: Mapped[str] = mapped_column(String(16), nullable=False)
    minimum_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    supported_purposes: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProtocolActivityRecord(AssessmentBase):
    __tablename__ = "protocol_activities"
    __table_args__ = (
        CheckConstraint("target_duration_seconds > 0", name="ck_protocol_activities_target_duration"),
        CheckConstraint("minimum_duration_seconds > 0", name="ck_protocol_activities_minimum_duration"),
        CheckConstraint(
            "target_duration_seconds >= minimum_duration_seconds",
            name="ck_protocol_activities_duration_range",
        ),
        CheckConstraint("sort_order >= 1", name="ck_protocol_activities_sort_order"),
        Index("ix_protocol_activities_protocol_version_key", "protocol_version_key"),
    )

    protocol_version_key: Mapped[str] = mapped_column(
        ForeignKey("protocol_versions.protocol_version_key", name="fk_protocol_activities_protocol_version"),
        primary_key=True,
    )
    activity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    target_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentProtocolSelectionRecord(AssessmentBase):
    __tablename__ = "assessment_protocol_selections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            name="uq_assessment_protocol_selections_organization_assessment",
        ),
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            "protocol_version_key",
            name="uq_assessment_protocol_selections_organization_assessment_protocol",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_assessment_protocol_selections_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "selected_by_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_assessment_protocol_selections_actor_membership_tenant",
        ),
        CheckConstraint("version >= 1", name="ck_assessment_protocol_selections_version"),
    )

    assessment_protocol_selection_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=opaque_id
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_assessment_protocol_selections_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_assessment_protocol_selections_assessment"),
        nullable=False,
        index=True,
    )
    protocol_version_key: Mapped[str] = mapped_column(
        ForeignKey("protocol_versions.protocol_version_key", name="fk_assessment_protocol_selections_protocol"),
        nullable=False,
    )
    selected_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.user_id", name="fk_assessment_protocol_selections_actor"),
        nullable=False,
        index=True,
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RecordingRecord(AssessmentBase):
    __tablename__ = "recordings"
    __table_args__ = (
        UniqueConstraint("organization_id", "recording_id", name="uq_recordings_organization_recording"),
        UniqueConstraint("object_key", name="uq_recordings_object_key"),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_recordings_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id", "protocol_version_key"],
            [
                "assessment_protocol_selections.organization_id",
                "assessment_protocol_selections.assessment_id",
                "assessment_protocol_selections.protocol_version_key",
            ],
            name="fk_recordings_assessment_protocol_selection_tenant",
        ),
        ForeignKeyConstraint(
            ["protocol_version_key", "activity_key"],
            ["protocol_activities.protocol_version_key", "protocol_activities.activity_key"],
            name="fk_recordings_protocol_activity",
        ),
        CheckConstraint("declared_size_bytes > 0", name="ck_recordings_declared_size"),
        CheckConstraint("length(declared_content_type) > 0", name="ck_recordings_declared_content_type"),
        CheckConstraint("length(declared_checksum) > 0", name="ck_recordings_declared_checksum"),
        CheckConstraint("length(object_key) > 0", name="ck_recordings_object_key"),
        CheckConstraint(f"upload_state IN ({_UPLOAD_STATE_VALUES})", name="ck_recordings_upload_state"),
        CheckConstraint(
            "verified_size_bytes IS NULL OR verified_size_bytes > 0",
            name="ck_recordings_verified_size",
        ),
        CheckConstraint(
            "(verified_content_type IS NULL AND verified_size_bytes IS NULL "
            "AND verified_checksum IS NULL AND verified_at IS NULL) OR "
            "(verified_content_type IS NOT NULL AND verified_size_bytes IS NOT NULL "
            "AND verified_checksum IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_recordings_verified_metadata_complete",
        ),
        CheckConstraint("version >= 1", name="ck_recordings_version"),
        Index("ix_recordings_organization_assessment", "organization_id", "assessment_id"),
        Index("ix_recordings_organization_upload_state_expiry", "organization_id", "upload_state", "expires_at"),
    )

    recording_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=opaque_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_recordings_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_recordings_assessment"),
        nullable=False,
        index=True,
    )
    protocol_version_key: Mapped[str] = mapped_column(
        ForeignKey("protocol_versions.protocol_version_key", name="fk_recordings_protocol_version"),
        nullable=False,
    )
    activity_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    declared_content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    declared_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    declared_checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    upload_state: Mapped[str] = mapped_column(
        String(32), default=RecordingUploadState.PENDING.value, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_content_type: Mapped[str | None] = mapped_column(String(128))
    verified_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    verified_checksum: Mapped[str | None] = mapped_column(String(128))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProcessingRunRecord(AssessmentBase):
    __tablename__ = "processing_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_processing_runs_organization_idempotency",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_processing_runs_recording_tenant",
        ),
        CheckConstraint(f"stage IN ({_PROCESSING_STAGE_VALUES})", name="ck_processing_runs_stage"),
        CheckConstraint(f"state IN ({_PROCESSING_STATE_VALUES})", name="ck_processing_runs_state"),
        CheckConstraint("length(idempotency_key) > 0", name="ck_processing_runs_idempotency_key"),
        CheckConstraint("attempt_count >= 0", name="ck_processing_runs_attempt_count"),
        Index("ix_processing_runs_organization_recording", "organization_id", "recording_id"),
        Index("ix_processing_runs_organization_state_available", "organization_id", "state", "available_at"),
    )

    processing_run_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=opaque_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_processing_runs_organization"),
        nullable=False,
        index=True,
    )
    recording_id: Mapped[str] = mapped_column(
        ForeignKey("recordings.recording_id", name="fk_processing_runs_recording"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), default=ProcessingRunState.QUEUED.value, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RecordingQualityResultRecord(AssessmentBase):
    __tablename__ = "recording_quality_results"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "recording_id",
            name="uq_recording_quality_results_organization_recording",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_recording_quality_results_recording_tenant",
        ),
        CheckConstraint(f"status IN ({_QUALITY_STATUS_VALUES})", name="ck_recording_quality_results_status"),
        CheckConstraint(
            "measured_duration_seconds IS NULL OR measured_duration_seconds >= 0",
            name="ck_recording_quality_results_duration",
        ),
        CheckConstraint(
            "measured_silence_ratio IS NULL OR measured_silence_ratio BETWEEN 0 AND 1",
            name="ck_recording_quality_results_silence_ratio",
        ),
        CheckConstraint(
            "measured_decodability IS NULL OR measured_decodability BETWEEN 0 AND 1",
            name="ck_recording_quality_results_decodability",
        ),
        CheckConstraint("length(provenance) > 0", name="ck_recording_quality_results_provenance"),
        CheckConstraint("version >= 1", name="ck_recording_quality_results_version"),
        Index("ix_recording_quality_results_organization_status", "organization_id", "status"),
    )

    recording_quality_result_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=opaque_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_recording_quality_results_organization"),
        nullable=False,
        index=True,
    )
    recording_id: Mapped[str] = mapped_column(
        ForeignKey("recordings.recording_id", name="fk_recording_quality_results_recording"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=RecordingQualityStatus.USABLE.value,
        server_default=text("'usable'"),
        nullable=False,
    )
    measured_duration_seconds: Mapped[float | None] = mapped_column(Float)
    measured_loudness_db: Mapped[float | None] = mapped_column(Float)
    measured_silence_ratio: Mapped[float | None] = mapped_column(Float)
    measured_decodability: Mapped[float | None] = mapped_column(Float)
    unavailable_checks_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    provenance: Mapped[str] = mapped_column(String(256), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
