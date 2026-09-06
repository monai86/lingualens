"""Tenant and care-team scoped persistence for the assessment v2 foundation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assessment_v2.correlation import sanitize_correlation_id
from app.assessment_v2.db.models import (
    AssessmentRecord,
    AssessmentProtocolSelectionRecord,
    AuditEventRecord,
    CareTeamAssignmentRecord,
    ChildRecord,
    ConsentRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingQualityResultRecord,
    RecordingRecord,
    UserProfileRecord,
)
from app.assessment_v2.domain.models import (
    AccessScope,
    AssessmentSnapshot,
    AssessmentState,
    CaptureSnapshot,
    ChildSnapshot,
    CompleteCapture,
    CompleteRecordingUpload,
    ConsentPurpose,
    ConsentSnapshot,
    CreateRecording,
    CreateAssessment,
    CreateChild,
    MarkRecordingUploading,
    ProcessingRunSnapshot,
    ProcessingRunStage,
    ProcessingRunState,
    ProtocolActivity,
    RecordConsent,
    RecordingIntentSnapshot,
    RecordingQualitySnapshot,
    RecordingQualityStatus,
    RecordingSnapshot,
    RecordingUploadState,
    SelectProtocol,
    StartCapture,
    TransitionAssessment,
    VerifyRecordingUpload,
)
from app.assessment_v2.domain.transitions import InvalidAssessmentTransition, transition_assessment
from app.core.security import CurrentUser


_ASSIGNABLE_MEMBERSHIP_ROLES = frozenset({"therapist", "clinical_supervisor"})
_CAPTURE_UPLOAD_INTENT_TTL = timedelta(hours=2)
_AUDIT_CHANGED_FIELDS = frozenset(
    {
        "activity_code",
        "age_months",
        "assigned_clinician_id",
        "birth_month",
        "birth_year",
        "child_id",
        "content_type",
        "expires_at",
        "language_context",
        "processing_stage",
        "processing_state",
        "protocol_version_key",
        "purpose",
        "quality_status",
        "scope_version",
        "size_bytes",
        "state",
        "status",
        "upload_state",
        "verified_at",
        "version",
    }
)


class RepositoryError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(value: datetime, now: datetime | None = None) -> bool:
    normalized_value = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    current = now or _utc_now()
    normalized_current = current if current.tzinfo is not None else current.replace(tzinfo=timezone.utc)
    return normalized_value <= normalized_current


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
        self._locked_child(scope, child_id)
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
        with self.session.begin_nested():
            self._locked_child(scope, command.child_id)
            self._require_locked_assignee_eligibility(scope, command.child_id, command.assigned_clinician_id)
            return self._insert_assessment(scope, command, correlation_id)

    def create_assessment_if_consented(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        """Lock the child while checking consent and inserting the assessment."""

        with self.session.begin_nested():
            self._locked_child(scope, command.child_id)
            self._require_locked_assignee_eligibility(scope, command.child_id, command.assigned_clinician_id)
            latest = self.session.scalar(
                select(ConsentRecord)
                .where(
                    ConsentRecord.organization_id == scope.organization_id,
                    ConsentRecord.child_id == command.child_id,
                    ConsentRecord.purpose == ConsentPurpose.CLINICAL_ASSESSMENT.value,
                )
                .order_by(desc(ConsentRecord.version))
                .with_for_update()
                .limit(1)
            )
            if latest is None or latest.status != "active":
                raise RepositoryError("active_consent_required")
            return self._insert_assessment(scope, command, correlation_id)

    def can_assign_clinician(self, scope: AccessScope, child_id: str, clinician_id: str) -> bool:
        if not self._can_access_child(scope, child_id):
            return False
        return (
            self.session.scalar(
                select(CareTeamAssignmentRecord.assignment_id)
                .join(
                    OrganizationMembershipRecord,
                    and_(
                        OrganizationMembershipRecord.organization_id
                        == CareTeamAssignmentRecord.organization_id,
                        OrganizationMembershipRecord.user_id == CareTeamAssignmentRecord.user_id,
                    ),
                )
                .where(
                    CareTeamAssignmentRecord.organization_id == scope.organization_id,
                    CareTeamAssignmentRecord.child_id == child_id,
                    CareTeamAssignmentRecord.user_id == clinician_id,
                    CareTeamAssignmentRecord.active.is_(True),
                    OrganizationMembershipRecord.active.is_(True),
                    OrganizationMembershipRecord.role.in_(_ASSIGNABLE_MEMBERSHIP_ROLES),
                )
            )
            is not None
        )

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

    def select_protocol_and_ready(
        self,
        scope: AccessScope,
        command: SelectProtocol,
        correlation_id: str,
    ) -> CaptureSnapshot:
        """Persist one immutable catalog selection and atomically enter capture-ready state."""

        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, command.assessment_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            selection = self.session.scalar(
                select(AssessmentProtocolSelectionRecord)
                .where(
                    AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == command.assessment_id,
                )
                .with_for_update()
            )
            if selection is not None:
                if selection.protocol_version_key != command.protocol_version_key:
                    raise RepositoryError("protocol_unavailable")
                if assessment.state == AssessmentState.DRAFT.value:
                    self._transition_locked_assessment(
                        scope,
                        assessment,
                        AssessmentState.READY_FOR_CAPTURE,
                        command.expected_version,
                        correlation_id,
                    )
                elif assessment.state not in {
                    AssessmentState.READY_FOR_CAPTURE.value,
                    AssessmentState.CAPTURING.value,
                    AssessmentState.PROCESSING.value,
                }:
                    raise RepositoryError("capture_not_ready")
            else:
                if assessment.state != AssessmentState.DRAFT.value:
                    raise RepositoryError("capture_not_ready")
                catalog_entry = self.session.scalar(
                    select(ProtocolVersionRecord.protocol_version_key).where(
                        ProtocolVersionRecord.protocol_version_key == command.protocol_version_key,
                    )
                )
                if catalog_entry is None:
                    raise RepositoryError("protocol_unavailable")
                now = _utc_now()
                self.session.add(
                    AssessmentProtocolSelectionRecord(
                        assessment_protocol_selection_id=uuid4().hex,
                        organization_id=scope.organization_id,
                        assessment_id=command.assessment_id,
                        protocol_version_key=command.protocol_version_key,
                        selected_by_user_id=scope.user_id,
                        selected_at=now,
                        version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
                self._transition_locked_assessment(
                    scope,
                    assessment,
                    AssessmentState.READY_FOR_CAPTURE,
                    command.expected_version,
                    correlation_id,
                )
                self._append_audit(
                    scope,
                    "assessment.protocol_selected",
                    "assessment",
                    command.assessment_id,
                    correlation_id,
                    ["protocol_version_key", "state", "version"],
                    target_version=command.expected_version + 1,
                )
            self.session.flush()

        capture = self.get_capture(scope, command.assessment_id)
        if capture is None:
            raise RepositoryError("assessment_not_found")
        return capture

    def start_capture_if_consented(
        self,
        scope: AccessScope,
        command: StartCapture,
        correlation_id: str,
    ) -> AssessmentSnapshot:
        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, command.assessment_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            selection_exists = self.session.scalar(
                select(AssessmentProtocolSelectionRecord.assessment_protocol_selection_id).where(
                    AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == command.assessment_id,
                )
            )
            if selection_exists is None or assessment.state != AssessmentState.READY_FOR_CAPTURE.value:
                raise RepositoryError("capture_not_ready")
            updated = self._transition_locked_assessment(
                scope,
                assessment,
                AssessmentState.CAPTURING,
                assessment.version,
                correlation_id,
            )
            self.session.flush()
            return updated

    def create_recording_if_capture_active(
        self,
        scope: AccessScope,
        command: CreateRecording,
        correlation_id: str,
    ) -> RecordingIntentSnapshot:
        """Create the pending recording and its idempotency anchor in one transaction."""

        try:
            with self.session.begin_nested():
                assessment = self._locked_assessment(scope, command.assessment_id)
                self._require_current_capture_consent(scope, assessment.child_id)
                if assessment.state != AssessmentState.CAPTURING.value:
                    raise RepositoryError("capture_not_active")
                selection = self.session.scalar(
                    select(AssessmentProtocolSelectionRecord)
                    .where(
                        AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                        AssessmentProtocolSelectionRecord.assessment_id == command.assessment_id,
                    )
                    .with_for_update()
                )
                if selection is None:
                    raise RepositoryError("capture_not_ready")
                activity = self.session.scalar(
                    select(ProtocolActivityRecord).where(
                        ProtocolActivityRecord.protocol_version_key == selection.protocol_version_key,
                        ProtocolActivityRecord.activity_key == command.activity_code,
                    )
                )
                if activity is None:
                    raise RepositoryError("recording_activity_invalid")

                existing_run = self.session.scalar(
                    select(ProcessingRunRecord)
                    .where(
                        ProcessingRunRecord.organization_id == scope.organization_id,
                        ProcessingRunRecord.idempotency_key == command.idempotency_key,
                    )
                    .with_for_update()
                )
                if existing_run is not None:
                    return self._resolve_existing_recording_intent(scope, existing_run, command)

                now = _utc_now()
                recording = RecordingRecord(
                    recording_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    assessment_id=command.assessment_id,
                    protocol_version_key=selection.protocol_version_key,
                    activity_key=command.activity_code,
                    declared_content_type=command.content_type,
                    declared_size_bytes=command.size_bytes,
                    declared_checksum=command.checksum,
                    object_key=f"capture/{uuid4().hex}",
                    upload_state=RecordingUploadState.PENDING.value,
                    expires_at=now + _CAPTURE_UPLOAD_INTENT_TTL,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                run = ProcessingRunRecord(
                    processing_run_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    recording_id=recording.recording_id,
                    stage=ProcessingRunStage.UPLOAD_VERIFICATION.value,
                    state=ProcessingRunState.QUEUED.value,
                    idempotency_key=command.idempotency_key,
                    attempt_count=0,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                )
                self.session.add_all((recording, run))
                self.session.flush()
                self._append_audit(
                    scope,
                    "recording.created",
                    "recording",
                    recording.recording_id,
                    correlation_id,
                    ["activity_code", "content_type", "size_bytes", "upload_state", "expires_at"],
                    target_version=recording.version,
                )
                self._append_audit(
                    scope,
                    "processing_run.queued",
                    "processing_run",
                    run.processing_run_id,
                    correlation_id,
                    ["processing_stage", "processing_state"],
                )
                self.session.flush()
                return RecordingIntentSnapshot(
                    recording=self._recording_snapshot(recording),
                    processing_run=self._processing_run_snapshot(run),
                )
        except IntegrityError:
            existing_run = self.session.scalar(
                select(ProcessingRunRecord).where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.idempotency_key == command.idempotency_key,
                )
            )
            if existing_run is None:
                raise
            return self._resolve_existing_recording_intent(scope, existing_run, command)

    def get_capture(self, scope: AccessScope, assessment_id: str) -> CaptureSnapshot | None:
        assessment = self._assessment_record(scope, assessment_id)
        if assessment is None:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        selection = self.session.scalar(
            select(AssessmentProtocolSelectionRecord).where(
                AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                AssessmentProtocolSelectionRecord.assessment_id == assessment_id,
            )
        )
        activities: tuple[ProtocolActivity, ...] = ()
        if selection is not None:
            activity_records = self.session.scalars(
                select(ProtocolActivityRecord)
                .where(ProtocolActivityRecord.protocol_version_key == selection.protocol_version_key)
                .order_by(ProtocolActivityRecord.sort_order)
            ).all()
            activities = tuple(
                ProtocolActivity(
                    activity_key=record.activity_key,
                    required=record.required,
                    target_duration_seconds=record.target_duration_seconds,
                    minimum_duration_seconds=record.minimum_duration_seconds,
                )
                for record in activity_records
            )
        recording_records = self.session.scalars(
            select(RecordingRecord)
            .where(
                RecordingRecord.organization_id == scope.organization_id,
                RecordingRecord.assessment_id == assessment_id,
            )
            .order_by(RecordingRecord.created_at)
        ).all()
        recording_ids = [record.recording_id for record in recording_records]
        quality_records: list[RecordingQualityResultRecord] = []
        if recording_ids:
            quality_records = self.session.scalars(
                select(RecordingQualityResultRecord)
                .where(
                    RecordingQualityResultRecord.organization_id == scope.organization_id,
                    RecordingQualityResultRecord.recording_id.in_(recording_ids),
                )
                .order_by(RecordingQualityResultRecord.evaluated_at)
            ).all()
        return CaptureSnapshot(
            assessment=self._assessment_snapshot(assessment),
            protocol_selection=(
                self._protocol_selection_snapshot(selection) if selection is not None else None
            ),
            activities=activities,
            recordings=tuple(self._recording_snapshot(record) for record in recording_records),
            quality_results=tuple(self._quality_snapshot(record) for record in quality_records),
        )

    def get_recording_if_consented(
        self, scope: AccessScope, recording_id: str
    ) -> RecordingSnapshot | None:
        context = self._recording_with_assessment(scope, recording_id)
        if context is None:
            return None
        recording, assessment = context
        self._require_current_capture_consent(scope, assessment.child_id)
        return self._recording_snapshot(recording)

    def get_recording_quality_if_consented(
        self, scope: AccessScope, recording_id: str
    ) -> RecordingQualitySnapshot | None:
        context = self._recording_with_assessment(scope, recording_id)
        if context is None:
            return None
        _, assessment = context
        self._require_current_capture_consent(scope, assessment.child_id)
        quality = self.session.scalar(
            select(RecordingQualityResultRecord).where(
                RecordingQualityResultRecord.organization_id == scope.organization_id,
                RecordingQualityResultRecord.recording_id == recording_id,
            )
        )
        return self._quality_snapshot(quality) if quality is not None else None

    def get_processing_run_if_consented(
        self, scope: AccessScope, processing_run_id: str
    ) -> ProcessingRunSnapshot | None:
        run = self.session.scalar(
            select(ProcessingRunRecord).where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                ProcessingRunRecord.processing_run_id == processing_run_id,
            )
        )
        if run is None:
            return None
        context = self._recording_with_assessment(scope, run.recording_id)
        if context is None or context[0].recording_id != run.recording_id:
            return None
        self._require_current_capture_consent(scope, context[1].child_id)
        return self._processing_run_snapshot(run)

    def mark_recording_deleted_if_consented(
        self,
        scope: AccessScope,
        recording_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> RecordingSnapshot | None:
        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, recording_id, lock=True)
            if context is None:
                return None
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if recording.upload_state == RecordingUploadState.FAILED.value:
                return self._recording_snapshot(recording)
            result = self.session.execute(
                update(RecordingRecord)
                .where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == recording_id,
                    RecordingRecord.version == expected_version,
                )
                .values(
                    upload_state=RecordingUploadState.FAILED.value,
                    verified_content_type=None,
                    verified_size_bytes=None,
                    verified_checksum=None,
                    verified_at=None,
                    version=recording.version + 1,
                    updated_at=_utc_now(),
                )
            )
            if result.rowcount != 1:
                refreshed = self.session.scalar(
                    select(RecordingRecord).where(
                        RecordingRecord.organization_id == scope.organization_id,
                        RecordingRecord.recording_id == recording_id,
                    )
                )
                if refreshed is not None and refreshed.upload_state == RecordingUploadState.FAILED.value:
                    return self._recording_snapshot(refreshed)
                raise RepositoryError("upload_verification_failed")
            self.session.execute(
                update(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == recording_id,
                    ProcessingRunRecord.state.in_(
                        (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                    ),
                )
                .values(
                    state=ProcessingRunState.CANCELLED.value,
                    updated_at=_utc_now(),
                )
            )
            updated = self.session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == recording_id,
                )
            )
            if updated is None:
                return None
            self._append_audit(
                scope,
                "recording.deleted",
                "recording",
                recording_id,
                correlation_id,
                ["upload_state", "verified_at", "version"],
                target_version=updated.version,
            )
            self.session.flush()
            return self._recording_snapshot(updated)

    def mark_recording_uploading_if_capture_active(
        self,
        scope: AccessScope,
        command: MarkRecordingUploading,
        correlation_id: str,
    ) -> RecordingSnapshot:
        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, command.recording_id, lock=True)
            if context is None:
                raise RepositoryError("recording_not_found")
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if assessment.state != AssessmentState.CAPTURING.value:
                raise RepositoryError("capture_not_active")
            if _is_expired(recording.expires_at):
                raise RepositoryError("upload_intent_expired")
            if recording.upload_state not in {
                RecordingUploadState.PENDING.value,
                RecordingUploadState.UPLOADING.value,
            }:
                raise RepositoryError("upload_verification_failed")
            result = self.session.execute(
                update(RecordingRecord)
                .where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                    RecordingRecord.version == command.expected_version,
                )
                .values(
                    upload_state=RecordingUploadState.UPLOADING.value,
                    expires_at=command.expires_at,
                    version=recording.version + 1,
                    updated_at=_utc_now(),
                )
            )
            if result.rowcount != 1:
                raise RepositoryError("upload_verification_failed")
            updated = self.session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                )
            )
            if updated is None:
                raise RepositoryError("recording_not_found")
            self._append_audit(
                scope,
                "recording.upload_intent_issued",
                "recording",
                updated.recording_id,
                correlation_id,
                ["upload_state", "expires_at", "version"],
                target_version=updated.version,
            )
            self.session.flush()
            return self._recording_snapshot(updated)

    def complete_recording_upload_if_capture_active(
        self,
        scope: AccessScope,
        command: CompleteRecordingUpload,
        correlation_id: str,
    ) -> RecordingIntentSnapshot:
        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, command.recording_id, lock=True)
            if context is None:
                raise RepositoryError("recording_not_found")
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if assessment.state != AssessmentState.CAPTURING.value:
                raise RepositoryError("capture_not_active")
            if recording.upload_state == RecordingUploadState.VERIFIED.value:
                quality_run = self._quality_run_for_recording(scope, recording.recording_id)
                if quality_run is None:
                    quality_run = self._queue_quality_run(scope, recording)
                return RecordingIntentSnapshot(
                    recording=self._recording_snapshot(recording),
                    processing_run=self._processing_run_snapshot(quality_run),
                )
            if recording.upload_state == RecordingUploadState.UPLOADED.value:
                upload_run = self.session.scalar(
                    select(ProcessingRunRecord)
                    .where(
                        ProcessingRunRecord.organization_id == scope.organization_id,
                        ProcessingRunRecord.recording_id == recording.recording_id,
                        ProcessingRunRecord.stage == ProcessingRunStage.UPLOAD_VERIFICATION.value,
                    )
                    .with_for_update()
                )
                if upload_run is None:
                    raise RepositoryError("upload_verification_failed")
                return RecordingIntentSnapshot(
                    recording=self._recording_snapshot(recording),
                    processing_run=self._processing_run_snapshot(upload_run),
                )
            if recording.upload_state != RecordingUploadState.UPLOADING.value:
                raise RepositoryError("upload_verification_failed")
            if (
                command.observed_content_type != recording.declared_content_type
                or command.observed_size_bytes != recording.declared_size_bytes
            ):
                raise RepositoryError("upload_verification_failed")
            result = self.session.execute(
                update(RecordingRecord)
                .where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                    RecordingRecord.version == command.expected_version,
                )
                .values(
                    upload_state=RecordingUploadState.UPLOADED.value,
                    version=recording.version + 1,
                    updated_at=_utc_now(),
                )
            )
            if result.rowcount != 1:
                raise RepositoryError("upload_verification_failed")
            updated = self.session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                )
            )
            if updated is None:
                raise RepositoryError("recording_not_found")
            upload_run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == updated.recording_id,
                    ProcessingRunRecord.stage == ProcessingRunStage.UPLOAD_VERIFICATION.value,
                )
                .with_for_update()
            )
            if upload_run is None:
                raise RepositoryError("upload_verification_failed")
            if upload_run.state not in {
                ProcessingRunState.QUEUED.value,
                ProcessingRunState.RUNNING.value,
            }:
                raise RepositoryError("upload_verification_failed")
            self._append_audit(
                scope,
                "recording.upload_completed",
                "recording",
                updated.recording_id,
                correlation_id,
                ["upload_state", "version"],
                target_version=updated.version,
            )
            self.session.flush()
            return RecordingIntentSnapshot(
                recording=self._recording_snapshot(updated),
                processing_run=self._processing_run_snapshot(upload_run),
            )

    def verify_recording_upload(
        self,
        scope: AccessScope,
        command: VerifyRecordingUpload,
        correlation_id: str,
    ) -> RecordingIntentSnapshot:
        """Persist verification only when a worker supplies an authoritative checksum."""

        if not command.server_computed_checksum:
            raise RepositoryError("upload_verification_failed")
        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, command.recording_id, lock=True)
            if context is None:
                raise RepositoryError("recording_not_found")
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if recording.upload_state == RecordingUploadState.VERIFIED.value:
                quality_run = self._quality_run_for_recording(scope, recording.recording_id)
                if quality_run is None:
                    quality_run = self._queue_quality_run(scope, recording)
                return RecordingIntentSnapshot(
                    recording=self._recording_snapshot(recording),
                    processing_run=self._processing_run_snapshot(quality_run),
                )
            if recording.upload_state != RecordingUploadState.UPLOADED.value:
                raise RepositoryError("upload_verification_failed")
            if (
                command.verified_content_type != recording.declared_content_type
                or command.verified_size_bytes != recording.declared_size_bytes
            ):
                raise RepositoryError("upload_verification_failed")
            result = self.session.execute(
                update(RecordingRecord)
                .where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                    RecordingRecord.version == command.expected_version,
                )
                .values(
                    upload_state=RecordingUploadState.VERIFIED.value,
                    verified_content_type=command.verified_content_type,
                    verified_size_bytes=command.verified_size_bytes,
                    verified_checksum=command.server_computed_checksum,
                    verified_at=command.verified_at,
                    version=recording.version + 1,
                    updated_at=_utc_now(),
                )
            )
            if result.rowcount != 1:
                raise RepositoryError("upload_verification_failed")
            updated = self.session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == command.recording_id,
                )
            )
            if updated is None:
                raise RepositoryError("recording_not_found")
            upload_run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == updated.recording_id,
                    ProcessingRunRecord.stage == ProcessingRunStage.UPLOAD_VERIFICATION.value,
                )
                .with_for_update()
            )
            if upload_run is None:
                raise RepositoryError("upload_verification_failed")
            if upload_run.state in {
                ProcessingRunState.QUEUED.value,
                ProcessingRunState.RUNNING.value,
            }:
                upload_run.state = ProcessingRunState.SUCCEEDED.value
                upload_run.error_code = None
                upload_run.updated_at = _utc_now()
            elif upload_run.state != ProcessingRunState.SUCCEEDED.value:
                raise RepositoryError("upload_verification_failed")
            quality_run = self._queue_quality_run(scope, updated)
            self._append_audit(
                scope,
                "recording.upload_verified",
                "recording",
                updated.recording_id,
                correlation_id,
                ["upload_state", "verified_at", "version"],
                target_version=updated.version,
            )
            self._append_audit(
                scope,
                "processing_run.queued",
                "processing_run",
                quality_run.processing_run_id,
                correlation_id,
                ["processing_stage", "processing_state"],
            )
            self.session.flush()
            return RecordingIntentSnapshot(
                recording=self._recording_snapshot(updated),
                processing_run=self._processing_run_snapshot(quality_run),
            )

    def complete_capture_if_required_usable(
        self,
        scope: AccessScope,
        command: CompleteCapture,
        correlation_id: str,
    ) -> AssessmentSnapshot:
        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, command.assessment_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            if assessment.state != AssessmentState.CAPTURING.value:
                raise RepositoryError("capture_not_active")
            selection = self.session.scalar(
                select(AssessmentProtocolSelectionRecord)
                .where(
                    AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == assessment.assessment_id,
                )
                .with_for_update()
            )
            if selection is None:
                raise RepositoryError("capture_incomplete")
            required_activities = self.session.scalars(
                select(ProtocolActivityRecord).where(
                    ProtocolActivityRecord.protocol_version_key == selection.protocol_version_key,
                    ProtocolActivityRecord.required.is_(True),
                )
            ).all()
            for activity in required_activities:
                verified_recordings = self.session.scalars(
                    select(RecordingRecord).where(
                        RecordingRecord.organization_id == scope.organization_id,
                        RecordingRecord.assessment_id == assessment.assessment_id,
                        RecordingRecord.protocol_version_key == selection.protocol_version_key,
                        RecordingRecord.activity_key == activity.activity_key,
                        RecordingRecord.upload_state == RecordingUploadState.VERIFIED.value,
                    )
                ).all()
                if not verified_recordings:
                    raise RepositoryError("capture_incomplete")
                verified_recording_ids = [record.recording_id for record in verified_recordings]
                usable_quality = self.session.scalar(
                    select(RecordingQualityResultRecord.recording_quality_result_id).where(
                        RecordingQualityResultRecord.organization_id == scope.organization_id,
                        RecordingQualityResultRecord.recording_id.in_(verified_recording_ids),
                        RecordingQualityResultRecord.status == RecordingQualityStatus.USABLE.value,
                    )
                )
                if usable_quality is None:
                    raise RepositoryError("required_activity_not_usable")
            updated = self._transition_locked_assessment(
                scope,
                assessment,
                AssessmentState.PROCESSING,
                command.expected_version,
                correlation_id,
            )
            self.session.flush()
            return updated

    def _recording_with_assessment(
        self,
        scope: AccessScope,
        recording_id: str,
        *,
        lock: bool = False,
    ) -> tuple[RecordingRecord, AssessmentRecord] | None:
        query = (
            select(RecordingRecord, AssessmentRecord)
            .join(
                AssessmentRecord,
                and_(
                    AssessmentRecord.organization_id == RecordingRecord.organization_id,
                    AssessmentRecord.assessment_id == RecordingRecord.assessment_id,
                ),
            )
            .where(
                RecordingRecord.organization_id == scope.organization_id,
                RecordingRecord.recording_id == recording_id,
                AssessmentRecord.organization_id == scope.organization_id,
            )
        )
        if lock:
            query = query.with_for_update()
        row = self.session.execute(query).one_or_none()
        if row is None:
            return None
        recording, assessment = row
        if not self._can_access_child(scope, assessment.child_id):
            return None
        return recording, assessment

    def _quality_run_for_recording(
        self, scope: AccessScope, recording_id: str
    ) -> ProcessingRunRecord | None:
        return self.session.scalar(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                ProcessingRunRecord.recording_id == recording_id,
                ProcessingRunRecord.stage == ProcessingRunStage.QUALITY_ANALYSIS.value,
            )
            .with_for_update()
        )

    def _queue_quality_run(
        self, scope: AccessScope, recording: RecordingRecord
    ) -> ProcessingRunRecord:
        existing = self._quality_run_for_recording(scope, recording.recording_id)
        if existing is not None:
            if existing.state == ProcessingRunState.FAILED.value:
                existing.state = ProcessingRunState.QUEUED.value
                existing.error_code = None
                existing.updated_at = _utc_now()
            return existing
        now = _utc_now()
        run = ProcessingRunRecord(
            processing_run_id=uuid4().hex,
            organization_id=scope.organization_id,
            recording_id=recording.recording_id,
            stage=ProcessingRunStage.QUALITY_ANALYSIS.value,
            state=ProcessingRunState.QUEUED.value,
            idempotency_key=f"quality-{recording.recording_id}",
            attempt_count=0,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def _resolve_existing_recording_intent(
        self,
        scope: AccessScope,
        run: ProcessingRunRecord,
        command: CreateRecording,
    ) -> RecordingIntentSnapshot:
        recording = self.session.scalar(
            select(RecordingRecord).where(
                RecordingRecord.organization_id == scope.organization_id,
                RecordingRecord.recording_id == run.recording_id,
            )
        )
        if (
            recording is None
            or run.stage != ProcessingRunStage.UPLOAD_VERIFICATION.value
            or recording.assessment_id != command.assessment_id
            or recording.activity_key != command.activity_code
            or recording.declared_content_type != command.content_type
            or recording.declared_size_bytes != command.size_bytes
            or recording.declared_checksum != command.checksum
        ):
            raise RepositoryError("idempotency_conflict")
        return RecordingIntentSnapshot(
            recording=self._recording_snapshot(recording),
            processing_run=self._processing_run_snapshot(run),
        )

    def _locked_assessment(self, scope: AccessScope, assessment_id: str) -> AssessmentRecord:
        assessment = self.session.scalar(
            select(AssessmentRecord)
            .where(
                AssessmentRecord.organization_id == scope.organization_id,
                AssessmentRecord.assessment_id == assessment_id,
            )
            .with_for_update()
        )
        if assessment is None or not self._can_access_child(scope, assessment.child_id):
            raise RepositoryError("assessment_not_found")
        return assessment

    def _require_current_capture_consent(self, scope: AccessScope, child_id: str) -> None:
        latest = self.session.scalar(
            select(ConsentRecord)
            .where(
                ConsentRecord.organization_id == scope.organization_id,
                ConsentRecord.child_id == child_id,
                ConsentRecord.purpose == ConsentPurpose.CLINICAL_ASSESSMENT.value,
            )
            .order_by(desc(ConsentRecord.version))
            .with_for_update()
            .limit(1)
        )
        if latest is None or latest.status != "active":
            raise RepositoryError("consent_revoked")

    def _transition_locked_assessment(
        self,
        scope: AccessScope,
        assessment: AssessmentRecord,
        target_state: AssessmentState,
        expected_version: int,
        correlation_id: str,
    ) -> AssessmentSnapshot:
        current = self._assessment_snapshot(assessment)
        try:
            updated = transition_assessment(current, target_state, expected_version)
        except InvalidAssessmentTransition as error:
            raise RepositoryError(error.code) from error
        result = self.session.execute(
            update(AssessmentRecord)
            .where(
                AssessmentRecord.organization_id == scope.organization_id,
                AssessmentRecord.assessment_id == assessment.assessment_id,
                AssessmentRecord.version == expected_version,
            )
            .values(state=updated.state.value, version=updated.version, updated_at=_utc_now())
        )
        if result.rowcount != 1:
            exists = self.session.scalar(
                select(AssessmentRecord.assessment_id).where(
                    AssessmentRecord.organization_id == scope.organization_id,
                    AssessmentRecord.assessment_id == assessment.assessment_id,
                )
            )
            raise RepositoryError("stale_assessment_version" if exists is not None else "assessment_not_found")
        self._append_audit(
            scope,
            "assessment.transitioned",
            "assessment",
            assessment.assessment_id,
            correlation_id,
            ["state", "version"],
            target_version=updated.version,
        )
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

    def has_active_membership(self, scope: AccessScope) -> bool:
        """Return the persisted membership state for an authenticated scope."""

        return self._has_active_membership(scope)

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

    def _locked_child(self, scope: AccessScope, child_id: str) -> ChildRecord:
        child = self.session.scalar(
            select(ChildRecord)
            .where(
                ChildRecord.child_id == child_id,
                ChildRecord.organization_id == scope.organization_id,
            )
            .with_for_update()
        )
        if child is None or not self._can_access_child(scope, child_id):
            raise RepositoryError("child_not_found")
        return child

    def _require_locked_assignee_eligibility(
        self,
        scope: AccessScope,
        child_id: str,
        clinician_id: str,
    ) -> None:
        membership = self.session.scalar(
            select(OrganizationMembershipRecord)
            .where(
                OrganizationMembershipRecord.organization_id == scope.organization_id,
                OrganizationMembershipRecord.user_id == clinician_id,
            )
            .with_for_update()
        )
        if (
            membership is None
            or not membership.active
            or membership.role not in _ASSIGNABLE_MEMBERSHIP_ROLES
        ):
            raise RepositoryError("clinician_assignment_not_permitted")

        assignment = self.session.scalar(
            select(CareTeamAssignmentRecord)
            .where(
                CareTeamAssignmentRecord.organization_id == scope.organization_id,
                CareTeamAssignmentRecord.child_id == child_id,
                CareTeamAssignmentRecord.user_id == clinician_id,
            )
            .with_for_update()
        )
        if assignment is None or not assignment.active:
            raise RepositoryError("clinician_assignment_not_permitted")

    def _insert_assessment(
        self, scope: AccessScope, command: CreateAssessment, correlation_id: str
    ) -> AssessmentSnapshot:
        now = _utc_now()
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
        self._append_audit(
            scope,
            "assessment.created",
            "assessment",
            assessment.assessment_id,
            correlation_id,
            ["child_id", "purpose", "age_months", "language_context", "assigned_clinician_id"],
        )
        self.session.flush()
        return self._assessment_snapshot(assessment)

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
        safe_changed_fields = [
            field for field in changed_fields if field in _AUDIT_CHANGED_FIELDS
        ]
        self.session.add(
            AuditEventRecord(
                audit_event_id=uuid4().hex,
                organization_id=scope.organization_id,
                actor_user_id=scope.user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                outcome="success",
                correlation_id=sanitize_correlation_id(correlation_id),
                target_version=target_version,
                metadata_json={"changed_fields": safe_changed_fields},
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
            age_months=assessment.age_months,
            language_context=_context_from_storage(assessment.language_context),
        )

    @staticmethod
    def _protocol_selection_snapshot(
        selection: AssessmentProtocolSelectionRecord,
    ):
        from app.assessment_v2.domain.models import ProtocolSelectionSnapshot

        return ProtocolSelectionSnapshot(
            assessment_id=selection.assessment_id,
            protocol_version_key=selection.protocol_version_key,
            selected_at=selection.selected_at,
            version=selection.version,
        )

    @staticmethod
    def _recording_snapshot(recording: RecordingRecord) -> RecordingSnapshot:
        return RecordingSnapshot(
            id=recording.recording_id,
            organization_id=recording.organization_id,
            assessment_id=recording.assessment_id,
            protocol_version_key=recording.protocol_version_key,
            activity_code=recording.activity_key,
            declared_content_type=recording.declared_content_type,
            declared_size_bytes=recording.declared_size_bytes,
            declared_checksum=recording.declared_checksum,
            object_key=recording.object_key,
            upload_state=RecordingUploadState(recording.upload_state),
            expires_at=recording.expires_at,
            verified_content_type=recording.verified_content_type,
            verified_size_bytes=recording.verified_size_bytes,
            verified_checksum=recording.verified_checksum,
            verified_at=recording.verified_at,
            version=recording.version,
        )

    @staticmethod
    def _processing_run_snapshot(run: ProcessingRunRecord) -> ProcessingRunSnapshot:
        return ProcessingRunSnapshot(
            id=run.processing_run_id,
            organization_id=run.organization_id,
            recording_id=run.recording_id,
            stage=ProcessingRunStage(run.stage),
            state=ProcessingRunState(run.state),
            attempt_count=run.attempt_count,
            available_at=run.available_at,
            error_code=run.error_code,
        )

    @staticmethod
    def _quality_snapshot(quality: RecordingQualityResultRecord) -> RecordingQualitySnapshot:
        unavailable_checks = quality.unavailable_checks_json
        return RecordingQualitySnapshot(
            id=quality.recording_quality_result_id,
            organization_id=quality.organization_id,
            recording_id=quality.recording_id,
            status=RecordingQualityStatus(quality.status),
            measured_duration_seconds=quality.measured_duration_seconds,
            measured_loudness_db=quality.measured_loudness_db,
            measured_silence_ratio=quality.measured_silence_ratio,
            measured_decodability=quality.measured_decodability,
            unavailable_checks=tuple(
                item for item in unavailable_checks if isinstance(item, str)
            ),
            provenance=quality.provenance,
            evaluated_at=quality.evaluated_at,
            version=quality.version,
        )
