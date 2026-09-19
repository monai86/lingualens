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
    Text,
    UniqueConstraint,
    text,
    text as sqlalchemy_text,
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
    TranscriptReviewState,
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptSource,
)
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DomainProfileStatus,
    EvidenceSource,
    EvidenceState,
)
from app.assessment_v2.domain.observations import (
    ObservationCategory,
    ObservationSource,
)
from app.assessment_v2.domain.instruments import (
    InstrumentRespondentType,
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
_TRANSCRIPT_SOURCE_VALUES = ", ".join(f"'{source.value}'" for source in TranscriptSource)
_TRANSCRIPT_REVIEW_STATE_VALUES = ", ".join(
    f"'{state.value}'" for state in TranscriptReviewState
)
_TRANSCRIPT_SEGMENT_SPEAKER_ROLE_VALUES = ", ".join(
    f"'{role.value}'" for role in TranscriptSegmentSpeakerRole
)
_TRANSCRIPT_SEGMENT_UNCERTAINTY_REASON_VALUES = ", ".join(
    f"'{reason.value}'" for reason in TranscriptSegmentUncertaintyReason
)
_EVIDENCE_STATE_VALUES = ", ".join(f"'{state.value}'" for state in EvidenceState)
_EVIDENCE_SOURCE_VALUES = ", ".join(f"'{source.value}'" for source in EvidenceSource)
_DEVELOPMENTAL_DOMAIN_VALUES = ", ".join(
    f"'{domain.value}'" for domain in DevelopmentalDomain
)
_DOMAIN_PROFILE_STATUS_VALUES = ", ".join(
    f"'{status.value}'" for status in DomainProfileStatus
)
_OBSERVATION_CATEGORY_VALUES = ", ".join(
    f"'{cat.value}'" for cat in ObservationCategory
)
_OBSERVATION_SOURCE_VALUES = ", ".join(
    f"'{src.value}'" for src in ObservationSource
)
_INSTRUMENT_RESPONDENT_VALUES = ", ".join(
    f"'{resp.value}'" for resp in InstrumentRespondentType
)


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
            name="uq_aps_org_assessment_protocol",
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
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_processing_runs_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "transcript_revision_id"],
            [
                "transcript_revisions.organization_id",
                "transcript_revisions.transcript_revision_id",
            ],
            name="fk_processing_runs_transcript_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_processing_runs_evidence_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "segment_set_id"],
            [
                "transcript_segment_sets.organization_id",
                "transcript_segment_sets.transcript_segment_set_id",
            ],
            name="fk_processing_runs_segment_set_tenant",
        ),
        CheckConstraint(f"stage IN ({_PROCESSING_STAGE_VALUES})", name="ck_processing_runs_stage"),
        CheckConstraint(f"state IN ({_PROCESSING_STATE_VALUES})", name="ck_processing_runs_state"),
        CheckConstraint("length(idempotency_key) > 0", name="ck_processing_runs_idempotency_key"),
        CheckConstraint("attempt_count >= 0", name="ck_processing_runs_attempt_count"),
        CheckConstraint("max_attempts >= 1", name="ck_processing_runs_max_attempts"),
        CheckConstraint("version >= 1", name="ck_processing_runs_version"),
        CheckConstraint(
            "(segment_set_id IS NULL AND segment_set_sha256 IS NULL) OR "
            "(segment_set_id IS NOT NULL AND length(segment_set_sha256) = 64)",
            name="ck_processing_runs_segment_provenance",
        ),
        CheckConstraint(
            "(stage IN ('upload_verification', 'quality_analysis', 'cleanup') "
            "AND recording_id IS NOT NULL AND assessment_id IS NULL "
            "AND transcript_revision_id IS NULL) OR "
            "(stage = 'evidence_extraction' AND recording_id IS NULL "
            "AND assessment_id IS NOT NULL AND transcript_revision_id IS NOT NULL)",
            name="ck_processing_runs_target",
        ),
        Index("ix_processing_runs_organization_recording", "organization_id", "recording_id"),
        Index("ix_processing_runs_organization_state_available", "organization_id", "state", "available_at"),
        Index(
            "ix_processing_runs_organization_stage_state_available",
            "organization_id",
            "stage",
            "state",
            "available_at",
        ),
        Index(
            "ix_processing_runs_organization_stage_lease",
            "organization_id",
            "stage",
            "state",
            "lease_expires_at",
        ),
        Index(
            "ix_processing_runs_organization_segment_set",
            "organization_id",
            "segment_set_id",
        ),
    )

    processing_run_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=opaque_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_processing_runs_organization"),
        nullable=False,
        index=True,
    )
    recording_id: Mapped[str | None] = mapped_column(
        ForeignKey("recordings.recording_id", name="fk_processing_runs_recording"),
        nullable=True,
        index=True,
    )
    assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_processing_runs_assessment"),
        nullable=True,
        index=True,
    )
    transcript_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "transcript_revisions.transcript_revision_id",
            name="fk_processing_runs_transcript_revision",
        ),
        nullable=True,
        index=True,
    )
    evidence_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_processing_runs_evidence_run"),
        nullable=True,
        index=True,
    )
    segment_set_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    segment_set_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), default=ProcessingRunState.QUEUED.value, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default=text("3"),
        nullable=False,
    )
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    lease_token: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pipeline_version: Mapped[str | None] = mapped_column(String(128))
    feature_schema_version: Mapped[str | None] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )
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


class TranscriptRevisionRecord(AssessmentBase):
    __tablename__ = "transcript_revisions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "transcript_revision_id",
            name="uq_transcript_revisions_organization_revision_id",
        ),
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            "revision",
            name="uq_transcript_revisions_organization_assessment_revision",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_transcript_revisions_assessment_tenant",
        ),
        CheckConstraint(
            f"source IN ({_TRANSCRIPT_SOURCE_VALUES})",
            name="ck_transcript_revisions_source",
        ),
        CheckConstraint(
            f"review_state IN ({_TRANSCRIPT_REVIEW_STATE_VALUES})",
            name="ck_transcript_revisions_review_state",
        ),
        CheckConstraint("length(content) > 0", name="ck_transcript_revisions_content"),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_transcript_revisions_content_sha256",
        ),
        CheckConstraint("revision >= 1", name="ck_transcript_revisions_revision"),
        CheckConstraint("version >= 1", name="ck_transcript_revisions_version"),
        Index(
            "ix_transcript_revisions_organization_assessment_revision",
            "organization_id",
            "assessment_id",
            "revision",
        ),
    )

    transcript_revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_transcript_revisions_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_transcript_revisions_assessment"),
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    attested_by_user_id: Mapped[str | None] = mapped_column(String(128))
    attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class TranscriptSegmentSetRecord(AssessmentBase):
    __tablename__ = "transcript_segment_sets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "transcript_segment_set_id",
            name="uq_segment_sets_organization_set_id",
        ),
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            "revision",
            name="uq_segment_sets_organization_assessment_revision",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_segment_sets_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "transcript_revision_id"],
            [
                "transcript_revisions.organization_id",
                "transcript_revisions.transcript_revision_id",
            ],
            name="fk_segment_sets_transcript_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_segment_sets_recording_tenant",
        ),
        CheckConstraint(
            f"source IN ({_TRANSCRIPT_SOURCE_VALUES})",
            name="ck_segment_sets_source",
        ),
        CheckConstraint(
            f"review_state IN ({_TRANSCRIPT_REVIEW_STATE_VALUES})",
            name="ck_segment_sets_review_state",
        ),
        CheckConstraint(
            "length(segments_sha256) = 64",
            name="ck_segment_sets_sha256",
        ),
        CheckConstraint(
            "length(transcript_content_sha256) = 64",
            name="ck_segment_sets_transcript_sha256",
        ),
        CheckConstraint(
            "(attested_by_user_id IS NULL AND attested_at IS NULL) OR "
            "(attested_by_user_id IS NOT NULL AND attested_at IS NOT NULL)",
            name="ck_segment_sets_attestation_metadata",
        ),
        CheckConstraint("revision >= 1", name="ck_segment_sets_revision"),
        CheckConstraint("version >= 1", name="ck_segment_sets_version"),
        Index(
            "ix_segment_sets_organization_assessment_revision",
            "organization_id",
            "assessment_id",
            "revision",
        ),
    )

    transcript_segment_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_segment_sets_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_segment_sets_assessment"),
        nullable=False,
        index=True,
    )
    transcript_revision_id: Mapped[str] = mapped_column(
        ForeignKey("transcript_revisions.transcript_revision_id", name="fk_segment_sets_transcript"),
        nullable=False,
        index=True,
    )
    transcript_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    recording_id: Mapped[str | None] = mapped_column(
        ForeignKey("recordings.recording_id", name="fk_segment_sets_recording"),
        nullable=True,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False)
    segments_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    attested_by_user_id: Mapped[str | None] = mapped_column(String(128))
    attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class TranscriptSegmentRecord(AssessmentBase):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "transcript_segment_id",
            name="uq_segments_organization_segment_id",
        ),
        UniqueConstraint(
            "organization_id",
            "transcript_segment_set_id",
            "ordinal",
            name="uq_segments_organization_set_ordinal",
        ),
        ForeignKeyConstraint(
            ["organization_id", "transcript_segment_set_id"],
            [
                "transcript_segment_sets.organization_id",
                "transcript_segment_sets.transcript_segment_set_id",
            ],
            name="fk_segments_segment_set_tenant",
        ),
        CheckConstraint("ordinal >= 1", name="ck_segments_ordinal"),
        CheckConstraint("start_ms >= 0", name="ck_segments_start_ms"),
        CheckConstraint("end_ms > start_ms", name="ck_segments_end_ms"),
        CheckConstraint(
            f"speaker_role IN ({_TRANSCRIPT_SEGMENT_SPEAKER_ROLE_VALUES})",
            name="ck_segments_speaker_role",
        ),
        CheckConstraint("length(text) > 0", name="ck_segments_text"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_segments_confidence",
        ),
        CheckConstraint(
            f"uncertainty_reason IN ({_TRANSCRIPT_SEGMENT_UNCERTAINTY_REASON_VALUES})",
            name="ck_segments_uncertainty_reason",
        ),
        Index(
            "ix_segments_organization_set_ordinal",
            "organization_id",
            "transcript_segment_set_id",
            "ordinal",
        ),
    )

    transcript_segment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_segments_organization"),
        nullable=False,
        index=True,
    )
    transcript_segment_set_id: Mapped[str] = mapped_column(
        ForeignKey(
            "transcript_segment_sets.transcript_segment_set_id",
            name="fk_segments_segment_set",
        ),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    speaker_role: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    uncertainty_reason: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=TranscriptSegmentUncertaintyReason.NONE.value,
        server_default=sqlalchemy_text("'none'"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class EvidenceRunRecord(AssessmentBase):
    __tablename__ = "evidence_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            name="uq_evidence_runs_organization_run",
        ),
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            "transcript_revision_id",
            "segment_set_id",
            "segment_set_sha256",
            "pipeline_version",
            "feature_schema_version",
            name="uq_evidence_runs_segment_identity",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_evidence_runs_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "transcript_revision_id"],
            [
                "transcript_revisions.organization_id",
                "transcript_revisions.transcript_revision_id",
            ],
            name="fk_evidence_runs_transcript_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "segment_set_id"],
            [
                "transcript_segment_sets.organization_id",
                "transcript_segment_sets.transcript_segment_set_id",
            ],
            name="fk_evidence_runs_segment_set_tenant",
        ),
        CheckConstraint(
            f"state IN ({_EVIDENCE_STATE_VALUES})",
            name="ck_evidence_runs_state",
        ),
        CheckConstraint(
            "length(input_ref) > 0",
            name="ck_evidence_runs_input_ref",
        ),
        CheckConstraint(
            "length(input_sha256) = 64",
            name="ck_evidence_runs_input_sha256",
        ),
        CheckConstraint(
            "length(protocol_version_key) > 0",
            name="ck_evidence_runs_protocol",
        ),
        CheckConstraint(
            "length(extractor) > 0",
            name="ck_evidence_runs_extractor",
        ),
        CheckConstraint(
            "length(pipeline_version) > 0",
            name="ck_evidence_runs_pipeline",
        ),
        CheckConstraint(
            "length(feature_schema_version) > 0",
            name="ck_evidence_runs_schema",
        ),
        CheckConstraint("version >= 1", name="ck_evidence_runs_version"),
        CheckConstraint(
            "(segment_set_id IS NULL AND segment_set_sha256 IS NULL) OR "
            "(segment_set_id IS NOT NULL AND length(segment_set_sha256) = 64)",
            name="ck_evidence_runs_segment_provenance",
        ),
        Index(
            "ix_evidence_runs_organization_assessment_created",
            "organization_id",
            "assessment_id",
            "created_at",
        ),
        Index(
            "ix_evidence_runs_organization_segment_set",
            "organization_id",
            "segment_set_id",
        ),
    )

    evidence_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_evidence_runs_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_evidence_runs_assessment"),
        nullable=False,
        index=True,
    )
    transcript_revision_id: Mapped[str] = mapped_column(
        ForeignKey(
            "transcript_revisions.transcript_revision_id",
            name="fk_evidence_runs_transcript_revision",
        ),
        nullable=False,
        index=True,
    )
    segment_set_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    segment_set_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_version_key: Mapped[str] = mapped_column(String(128), nullable=False)
    extractor: Mapped[str] = mapped_column(String(128), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    limitations_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class EvidenceFeatureRecord(AssessmentBase):
    __tablename__ = "evidence_feature_values"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "evidence_feature_id",
            name="uq_evidence_features_organization_feature",
        ),
        UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            "feature_key",
            name="uq_evidence_features_run_key",
        ),
        ForeignKeyConstraint(
            ["organization_id", "evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_evidence_features_run_tenant",
        ),
        CheckConstraint(
            f"source IN ({_EVIDENCE_SOURCE_VALUES})",
            name="ck_evidence_features_source",
        ),
        CheckConstraint(
            f"state IN ({_EVIDENCE_STATE_VALUES})",
            name="ck_evidence_features_state",
        ),
        CheckConstraint(
            "(state = 'completed' AND value_json IS NOT NULL) OR "
            "(state <> 'completed' AND value_json IS NULL AND length(limitation) > 0)",
            name="ck_evidence_features_value_state",
        ),
        CheckConstraint("length(feature_key) > 0", name="ck_evidence_features_key"),
        CheckConstraint("length(unit) > 0", name="ck_evidence_features_unit"),
        CheckConstraint("version >= 1", name="ck_evidence_features_version"),
        Index(
            "ix_evidence_features_organization_run",
            "organization_id",
            "evidence_run_id",
        ),
    )

    evidence_feature_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_evidence_features_organization"),
        nullable=False,
        index=True,
    )
    evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_evidence_features_run"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(128), nullable=False)
    value_json: Mapped[object | None] = mapped_column(JSON)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    limitation: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class EvidenceDomainProfileRecord(AssessmentBase):
    __tablename__ = "evidence_domain_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "domain_profile_id",
            name="uq_evidence_domains_organization_profile",
        ),
        UniqueConstraint(
            "organization_id",
            "evidence_run_id",
            "domain",
            name="uq_evidence_domains_run_domain",
        ),
        ForeignKeyConstraint(
            ["organization_id", "evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_evidence_domains_run_tenant",
        ),
        CheckConstraint(
            f"domain IN ({_DEVELOPMENTAL_DOMAIN_VALUES})",
            name="ck_evidence_domains_domain",
        ),
        CheckConstraint(
            f"status IN ({_DOMAIN_PROFILE_STATUS_VALUES})",
            name="ck_evidence_domains_status",
        ),
        CheckConstraint("length(summary) > 0", name="ck_evidence_domains_summary"),
        CheckConstraint("version >= 1", name="ck_evidence_domains_version"),
        Index(
            "ix_evidence_domains_organization_run",
            "organization_id",
            "evidence_run_id",
        ),
    )

    domain_profile_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_evidence_domains_organization"),
        nullable=False,
        index=True,
    )
    evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_evidence_domains_run"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    feature_keys_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    supporting_features_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    conflicting_features_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    limitations_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentObservationRecord(AssessmentBase):
    __tablename__ = "assessment_observations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "observation_id",
            name="uq_observations_organization_observation",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_observations_assessment_tenant",
        ),
        CheckConstraint(
            f"category IN ({_OBSERVATION_CATEGORY_VALUES})",
            name="ck_observations_category",
        ),
        CheckConstraint(
            f"source IN ({_OBSERVATION_SOURCE_VALUES})",
            name="ck_observations_source",
        ),
        CheckConstraint("length(notes) > 0", name="ck_observations_notes_non_empty"),
        CheckConstraint("version >= 1", name="ck_observations_version"),
        CheckConstraint(
            "(NOT is_amendment AND amends_observation_id IS NULL AND version = 1) OR "
            "(is_amendment AND amends_observation_id IS NOT NULL AND version >= 2)",
            name="ck_observations_amendment_integrity",
        ),
        Index(
            "ix_observations_organization_assessment_created",
            "organization_id",
            "assessment_id",
            "created_at",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_observations_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_observations_assessment"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    observer_name: Mapped[str] = mapped_column(String(256), nullable=False)
    observer_role: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activity_context: Mapped[str] = mapped_column(String(512), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    structured_flags_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    is_amendment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    amends_observation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentInstrumentRecord(AssessmentBase):
    __tablename__ = "assessment_instruments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "administration_id",
            name="uq_instruments_organization_administration",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_instruments_assessment_tenant",
        ),
        CheckConstraint(
            f"respondent_type IN ({_INSTRUMENT_RESPONDENT_VALUES})",
            name="ck_instruments_respondent_type",
        ),
        CheckConstraint("length(instrument_name) > 0", name="ck_instruments_name_non_empty"),
        CheckConstraint("length(instrument_version) > 0", name="ck_instruments_version_non_empty"),
        CheckConstraint("version >= 1", name="ck_instruments_version"),
        Index(
            "ix_instruments_organization_assessment_administered",
            "organization_id",
            "assessment_id",
            "administered_at",
        ),
    )

    administration_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_instruments_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_instruments_assessment"),
        nullable=False,
        index=True,
    )
    instrument_name: Mapped[str] = mapped_column(String(128), nullable=False)
    instrument_version: Mapped[str] = mapped_column(String(64), nullable=False)
    respondent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    administered_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    licensing_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    summary_scores_json: Mapped[dict[str, float]] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentInstrumentItemRecord(AssessmentBase):
    __tablename__ = "assessment_instrument_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "item_id",
            name="uq_instrument_items_organization_item",
        ),
        UniqueConstraint(
            "organization_id",
            "administration_id",
            "item_key",
            name="uq_instrument_items_admin_item_key",
        ),
        ForeignKeyConstraint(
            ["organization_id", "administration_id"],
            ["assessment_instruments.organization_id", "assessment_instruments.administration_id"],
            name="fk_instrument_items_administration_tenant",
        ),
        CheckConstraint("length(item_key) > 0", name="ck_instrument_items_key_non_empty"),
        CheckConstraint("length(prompt_label) > 0", name="ck_instrument_items_label_non_empty"),
        Index(
            "ix_instrument_items_organization_admin",
            "organization_id",
            "administration_id",
        ),
    )

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_instrument_items_organization"),
        nullable=False,
        index=True,
    )
    administration_id: Mapped[str] = mapped_column(
        ForeignKey(
            "assessment_instruments.administration_id",
            name="fk_instrument_items_administration",
        ),
        nullable=False,
        index=True,
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_label: Mapped[str] = mapped_column(String(512), nullable=False)
    response_value: Mapped[str] = mapped_column(String(512), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentComparisonRecord(AssessmentBase):
    __tablename__ = "assessment_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "comparison_id",
            name="uq_comparisons_organization_comparison",
        ),
        UniqueConstraint(
            "organization_id",
            "baseline_evidence_run_id",
            "current_evidence_run_id",
            "policy_version",
            name="uq_comparisons_org_baseline_current_policy",
        ),
        ForeignKeyConstraint(
            ["organization_id", "child_id"],
            ["children.organization_id", "children.child_id"],
            name="fk_comparisons_child_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "baseline_assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_comparisons_baseline_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "current_assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_comparisons_current_assessment_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "baseline_evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_comparisons_baseline_evidence_run_tenant",
        ),
        ForeignKeyConstraint(
            ["organization_id", "current_evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_comparisons_current_evidence_run_tenant",
        ),
        Index("ix_comparisons_organization_child", "organization_id", "child_id"),
        Index("ix_comparisons_organization_current", "organization_id", "current_assessment_id"),
    )

    comparison_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_comparisons_organization"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_comparisons_child"),
        nullable=False,
        index=True,
    )
    baseline_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_comparisons_baseline_assessment"),
        nullable=False,
        index=True,
    )
    current_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_comparisons_current_assessment"),
        nullable=False,
        index=True,
    )
    baseline_evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_comparisons_baseline_evidence_run"),
        nullable=False,
        index=True,
    )
    current_evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_comparisons_current_evidence_run"),
        nullable=False,
        index=True,
    )
    baseline_evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    current_evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), default="longitudinal_v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compatible_feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incompatible_feature_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compared_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentComparisonFeatureRecord(AssessmentBase):
    __tablename__ = "assessment_comparison_features"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "comparison_feature_id",
            name="uq_comparison_features_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "comparison_id",
            "feature_key",
            name="uq_comparison_features_org_comp_feature",
        ),
        ForeignKeyConstraint(
            ["organization_id", "comparison_id"],
            ["assessment_comparisons.organization_id", "assessment_comparisons.comparison_id"],
            name="fk_comparison_features_comparison_tenant",
        ),
        Index("ix_comparison_features_org_comp", "organization_id", "comparison_id"),
    )

    comparison_feature_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_comparison_features_organization"),
        nullable=False,
        index=True,
    )
    comparison_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_comparisons.comparison_id", name="fk_comparison_features_comparison"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    incompatibility_reasons_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    baseline_value: Mapped[float | None] = mapped_column(Float)
    current_value: Mapped[float | None] = mapped_column(Float)
    absolute_delta: Mapped[float | None] = mapped_column(Float)
    percent_change: Mapped[float | None] = mapped_column(Float)
    percent_change_limitation: Mapped[str | None] = mapped_column(String(64))
    numerical_trend: Mapped[str] = mapped_column(String(32), nullable=False)
    clinical_interpretation: Mapped[str] = mapped_column(String(64), default="indeterminate", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssessmentClinicalReviewRecord(AssessmentBase):
    __tablename__ = "assessment_clinical_reviews"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "review_id",
            name="uq_clinical_reviews_org_id",
        ),
        UniqueConstraint(
            "organization_id",
            "assessment_id",
            name="uq_clinical_reviews_org_assessment",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_clinical_reviews_assessment_tenant",
        ),
        Index("ix_clinical_reviews_org_assessment", "organization_id", "assessment_id"),
    )

    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_clinical_reviews_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_clinical_reviews_assessment"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_clinical_reviews_child"),
        nullable=False,
        index=True,
    )
    evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_clinical_reviews_evidence_run"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False)
    disposition: Mapped[str | None] = mapped_column(String(64))
    disposition_notes: Mapped[str | None] = mapped_column(Text)
    follow_up_plan_json: Mapped[dict | None] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AssessmentAttentionCueRecord(AssessmentBase):
    __tablename__ = "assessment_attention_cues"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "cue_id",
            name="uq_attention_cues_org_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "review_id"],
            ["assessment_clinical_reviews.organization_id", "assessment_clinical_reviews.review_id"],
            name="fk_attention_cues_review_tenant",
        ),
        Index("ix_attention_cues_org_review", "organization_id", "review_id"),
        Index("ix_attention_cues_org_assessment", "organization_id", "assessment_id"),
    )

    cue_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_attention_cues_organization"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_clinical_reviews.review_id", name="fk_attention_cues_review"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_attention_cues_assessment"),
        nullable=False,
        index=True,
    )
    cue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), default="cues-v2.0", nullable=False)
    evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_attention_cues_evidence_run"),
        nullable=False,
    )
    supporting_feature_keys_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    conflicting_feature_keys_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    limitations_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="pending_review", nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String(128))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AssessmentReportRecord(AssessmentBase):
    __tablename__ = "assessment_reports"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "report_id",
            name="uq_reports_org_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_reports_assessment_tenant",
        ),
        Index("ix_reports_org_assessment", "organization_id", "assessment_id"),
        Index("ix_reports_org_status", "organization_id", "status"),
        Index("ix_reports_snapshot_hash", "signed_snapshot_hash"),
    )

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.organization_id", name="fk_reports_organization"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.assessment_id", name="fk_reports_assessment"),
        nullable=False,
        index=True,
    )
    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.child_id", name="fk_reports_child"),
        nullable=False,
        index=True,
    )
    evidence_run_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_runs.evidence_run_id", name="fk_reports_evidence_run"),
        nullable=False,
        index=True,
    )
    comparison_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessment_comparisons.comparison_id", name="fk_reports_comparison"),
        nullable=True,
    )
    review_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_clinical_reviews.review_id", name="fk_reports_review"),
        nullable=False,
        index=True,
    )
    amends_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessment_reports.report_id", name="fk_reports_amends_report"),
        nullable=True,
    )
    amendment_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    limitations_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    signed_by: Mapped[str | None] = mapped_column(String(128))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_snapshot: Mapped[dict | None] = mapped_column(JSON)
    signed_snapshot_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


