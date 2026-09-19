"""Tenant and care-team scoped persistence for the assessment v2 foundation."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import and_, desc, func, or_, select, text, update
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
    EvidenceDomainProfileRecord,
    EvidenceFeatureRecord,
    EvidenceRunRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    ProcessingRunRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingQualityResultRecord,
    RecordingRecord,
    TranscriptRevisionRecord,
    TranscriptSegmentRecord,
    TranscriptSegmentSetRecord,
    UserProfileRecord,
)
from app.assessment_v2.domain.models import (
    AccessScope,
    AttestTranscript,
    AssessmentSnapshot,
    AssessmentState,
    CaptureSnapshot,
    ChildSnapshot,
    CompleteCapture,
    CompleteRecordingUpload,
    ConsentPurpose,
    ConsentStatus,
    ConsentSnapshot,
    CreateRecording,
    CreateAssessment,
    CreateChild,
    CreateTranscriptRevision,
    CreateTranscriptSegmentSet,
    AttestTranscriptSegmentSet,
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
    TranscriptRevisionSnapshot,
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptReviewState,
    TranscriptSource,
    VerifyRecordingUpload,
)
from app.assessment_v2.domain.transitions import InvalidAssessmentTransition, transition_assessment
from app.assessment_v2.evidence import (
    DevelopmentalDomain,
    DevelopmentalEvidenceProfile,
    DomainProfileStatus,
    EvidenceSource,
    DomainProfile,
    EvidenceProvenance,
    EvidenceRunSnapshot,
    EvidenceState,
    MeasuredFeature,
    build_developmental_profile,
)
from app.assessment_v2.evidence_adapter import AdaptedEvidence
from app.assessment_v2.domain.segments import (
    TranscriptSegment,
    TranscriptSegmentSnapshot,
    TranscriptSegmentSetSnapshot,
    canonicalize_transcript_segments,
    compute_transcript_segments_sha256,
)
from app.core.security import CurrentUser


_ASSIGNABLE_MEMBERSHIP_ROLES = frozenset({"therapist", "clinical_supervisor"})
_SEGMENT_EDITOR_MEMBERSHIP_ROLES = frozenset({"therapist", "clinical_supervisor"})
_SEGMENT_EDITOR_ASSIGNMENT_ROLES = frozenset({"assigned_clinician", "supervisor"})
_CAPTURE_UPLOAD_INTENT_TTL = timedelta(hours=2)
_CAPTURE_LEASE_DURATION = timedelta(seconds=120)
_SYSTEM_PROCESSING_KEY_PREFIX = "__system__:"
_EVIDENCE_PIPELINE_VERSION = "reviewed-transcript-descriptors-v1"
_EVIDENCE_FEATURE_SCHEMA_VERSION = "descriptive-transcript-features-v1"
_EVIDENCE_LEASE_DURATION = timedelta(seconds=120)
_EVIDENCE_RETRY_BACKOFF = (timedelta(seconds=5), timedelta(seconds=30))
_EVIDENCE_SYSTEM_CANCEL_CODES = frozenset(
    {
        "consent_revoked",
        "transcript_superseded",
        "transcript_not_attested",
        "analysis_contract_superseded",
        "segment_set_superseded",
        "segment_provenance_missing",
    }
)
_EVIDENCE_USER_CANCEL_CODE = "cancel_requested"
_AUDIT_CHANGED_FIELDS = frozenset(
    {
        "activity_code",
        "attested_at",
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
        "review_state",
        "revision",
        "scope_version",
        "size_bytes",
        "source",
        "state",
        "status",
        "upload_state",
        "verified_at",
        "version",
        "evidence_state",
        "segments_sha256",
        "transcript_content_sha256",
        "start_ms",
        "end_ms",
        "speaker_role",
        "uncertainty_reason",
    }
)


class RepositoryError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EvidenceWorkItem:
    """Private worker envelope; transcript content never crosses the API seam."""

    run_id: str
    organization_id: str
    assessment_id: str
    transcript_revision_id: str
    protocol_version_key: str
    pipeline_version: str
    feature_schema_version: str
    content_sha256: str
    lease_token: str
    lease_expires_at: datetime
    attempt_count: int
    max_attempts: int
    transcript: TranscriptRevisionSnapshot = field(repr=False)
    segment_set: TranscriptSegmentSetSnapshot | None = field(default=None, repr=False)
    segment_set_id: str | None = None
    segment_set_sha256: str | None = None


def _evidence_idempotency_key(
    assessment_id: str,
    transcript_revision_id: str,
    *identity_parts: str,
) -> str:
    if len(identity_parts) == 2:
        # Keep the pre-segment key shape readable for historical callers and
        # rows. New evidence enqueue paths use the checksum-bound v2 form.
        identity = [assessment_id, transcript_revision_id, *identity_parts]
        prefix = "evidence:v1:"
    elif len(identity_parts) == 4:
        transcript_sha256, segment_set_sha256, pipeline_version, feature_schema_version = identity_parts
        identity = [
            assessment_id,
            transcript_revision_id,
            transcript_sha256,
            segment_set_sha256,
            pipeline_version,
            feature_schema_version,
        ]
        prefix = "evidence:v2:"
    elif len(identity_parts) == 5:
        (
            transcript_sha256,
            segment_set_id,
            segment_set_sha256,
            pipeline_version,
            feature_schema_version,
        ) = identity_parts
        identity = [
            assessment_id,
            transcript_revision_id,
            transcript_sha256,
            segment_set_id,
            segment_set_sha256,
            pipeline_version,
            feature_schema_version,
        ]
        prefix = "evidence:v3:"
    else:
        raise TypeError(
            "evidence idempotency requires pipeline/schema or transcript/segment checksums "
            "plus pipeline/schema"
        )
    canonical = json.dumps(identity, ensure_ascii=True, separators=(",", ":"))
    return prefix + sha256(canonical.encode("utf-8")).hexdigest()


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


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _merge_texts(*groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(text for group in groups for text in group if text))


def _string_values(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


class AssessmentRepository:
    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] | None = None,
        worker_organization_id: str | None = None,
        worker_user_id: str = "capture-worker",
    ) -> None:
        self.session = session
        self._clock = clock or _utc_now
        self._worker_organization_id = worker_organization_id
        self._worker_user_id = worker_user_id

    def _now(self) -> datetime:
        return _as_utc(self._clock())

    def commit_transaction(self) -> None:
        """Durably commit an external-side-effect boundary.

        Capture deletion writes a tombstone and cleanup run before asking
        private Storage to delete bytes.  The service calls this explicit
        boundary so a provider failure cannot roll those records back.
        """

        self.session.commit()
        if (
            self._worker_organization_id is not None
            and self.session.bind is not None
            and self.session.bind.dialect.name == "postgresql"
        ):
            # PostgreSQL `set_config(..., true)` is transaction-local. A
            # worker commits the claim before extraction or storage, so
            # establish the tenant context for the next transaction.
            self.session.execute(
                text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
                {"organization_id": self._worker_organization_id},
            )
            self.session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": self._worker_user_id},
            )

    @staticmethod
    def _worker_scope(organization_id: str) -> AccessScope:
        return AccessScope("capture-worker", organization_id, "org_admin")

    @staticmethod
    def _worker_correlation(run_id: str) -> str:
        # Processing run IDs are generated opaque 32-hex identifiers and are
        # accepted by the correlation sanitizer, giving worker events a stable
        # trace without putting a human-readable label in the audit field.
        return run_id

    def _audit_worker_run(
        self,
        run: ProcessingRunRecord,
        action: str,
        changed_fields: list[str],
        *,
        outcome: str = "success",
    ) -> None:
        self._append_audit(
            self._worker_scope(run.organization_id),
            action,
            "processing_run",
            run.processing_run_id,
            self._worker_correlation(run.processing_run_id),
            changed_fields,
            outcome=outcome,
        )

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
        query = select(ChildRecord).where(ChildRecord.organization_id == scope.organization_id).join(
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
            if (
                command.purpose is ConsentPurpose.CLINICAL_ASSESSMENT
                and command.status is ConsentStatus.WITHDRAWN
            ):
                self._cancel_evidence_runs_for_child(
                    scope,
                    child_id,
                    "consent_revoked",
                    correlation_id,
                )
            self.session.flush()
            return self._consent_snapshot(consent)

    def list_consents(self, scope: AccessScope, child_id: str) -> list[ConsentSnapshot]:
        if not self._can_access_child(scope, child_id):
            return []
        records = self.session.scalars(
            select(ConsentRecord)
            .where(
                ConsentRecord.organization_id == scope.organization_id,
                ConsentRecord.child_id == child_id,
            )
            .order_by(ConsentRecord.purpose, desc(ConsentRecord.version))
        ).all()
        return [self._consent_snapshot(record) for record in records]

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

    def get_current_transcript(
        self, scope: AccessScope, assessment_id: str
    ) -> TranscriptRevisionSnapshot | None:
        assessment = self._assessment_record(scope, assessment_id)
        if assessment is None:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        record = self.session.scalar(
            select(TranscriptRevisionRecord)
            .where(
                TranscriptRevisionRecord.organization_id == scope.organization_id,
                TranscriptRevisionRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptRevisionRecord.revision))
            .limit(1)
        )
        return self._transcript_snapshot(record) if record is not None else None

    def get_current_evidence(
        self, scope: AccessScope, assessment_id: str
    ) -> EvidenceRunSnapshot | None:
        assessment = self._assessment_record(scope, assessment_id)
        if assessment is None:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        current_transcript_id = self.session.scalar(
            select(TranscriptRevisionRecord.transcript_revision_id)
            .where(
                TranscriptRevisionRecord.organization_id == scope.organization_id,
                TranscriptRevisionRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptRevisionRecord.revision))
            .limit(1)
        )
        if current_transcript_id is None:
            return None
        evidence_query = select(EvidenceRunRecord).where(
            EvidenceRunRecord.organization_id == scope.organization_id,
            EvidenceRunRecord.assessment_id == assessment_id,
            EvidenceRunRecord.transcript_revision_id == current_transcript_id,
            EvidenceRunRecord.pipeline_version == _EVIDENCE_PIPELINE_VERSION,
            EvidenceRunRecord.feature_schema_version == _EVIDENCE_FEATURE_SCHEMA_VERSION,
        )
        current_segment_set = self.session.scalar(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
                .limit(1)
        )
        if current_segment_set is None:
            # Preserve read access to completed A1 evidence as historical
            # evidence until an A2 segment snapshot exists. Once a segment
            # revision is present, only evidence bound to that revision can be
            # current; an old transcript-only result must not silently pass as
            # evidence for the reviewed segments.
            evidence_query = evidence_query.where(
                EvidenceRunRecord.segment_set_id.is_(None),
                EvidenceRunRecord.segment_set_sha256.is_(None),
            )
        elif current_segment_set.review_state != TranscriptReviewState.ATTESTED.value:
            return None
        else:
            evidence_query = evidence_query.where(
                EvidenceRunRecord.segment_set_id == current_segment_set.transcript_segment_set_id,
                EvidenceRunRecord.segment_set_sha256 == current_segment_set.segments_sha256,
            )
        run = self.session.scalar(
            evidence_query
            .order_by(
                desc(EvidenceRunRecord.created_at),
                desc(EvidenceRunRecord.evidence_run_id),
            )
            .limit(1)
        )
        return self._evidence_snapshot(run) if run is not None else None

    def create_evidence_run(
        self,
        scope: AccessScope,
        assessment_id: str,
        transcript_revision_id: str,
        adapted: AdaptedEvidence,
        correlation_id: str,
    ) -> EvidenceRunSnapshot:
        provenance = adapted.provenance
        if provenance is None:
            raise RepositoryError("evidence_provenance_required")

        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, assessment_id)
            # Consent withdrawal serializes on the child row. Acquire that
            # same lock before checking consent so a withdrawal cannot commit
            # between the check and a protected evidence mutation.
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.transcript_revision_id == transcript_revision_id,
                )
                .with_for_update()
            )
            if transcript is None or transcript.assessment_id != assessment_id:
                raise RepositoryError("transcript_not_found")
            current_transcript_id = self.session.scalar(
                select(TranscriptRevisionRecord.transcript_revision_id)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .limit(1)
            )
            if current_transcript_id != transcript_revision_id:
                raise RepositoryError("transcript_not_reviewable")
            if transcript.review_state != TranscriptReviewState.ATTESTED.value:
                raise RepositoryError("transcript_not_reviewable")
            if transcript.content_sha256 != provenance.input_sha256:
                raise RepositoryError("stale_evidence_input")

            selection = self.session.scalar(
                select(AssessmentProtocolSelectionRecord).where(
                    AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == assessment_id,
                )
            )
            if selection is None or selection.protocol_version_key != provenance.protocol_version_key:
                raise RepositoryError("evidence_protocol_mismatch")
            if any(feature.provenance != provenance for feature in adapted.features):
                raise RepositoryError("evidence_provenance_mismatch")
            if adapted.state is EvidenceState.COMPLETED and not adapted.features:
                raise RepositoryError("evidence_no_measurements")

            existing = self.session.scalar(
                select(EvidenceRunRecord)
                .where(
                    EvidenceRunRecord.organization_id == scope.organization_id,
                    EvidenceRunRecord.assessment_id == assessment_id,
                    EvidenceRunRecord.transcript_revision_id == transcript_revision_id,
                    EvidenceRunRecord.pipeline_version == provenance.pipeline_version,
                    EvidenceRunRecord.feature_schema_version
                    == provenance.feature_schema_version,
                )
                .with_for_update()
            )
            if existing is not None:
                return self._evidence_snapshot(existing)

            generated_at = _as_utc(provenance.analyzed_at)
            profile = build_developmental_profile(
                assessment_id=assessment_id,
                features=adapted.features,
                generated_at=generated_at,
            )
            profile = replace(
                profile,
                state=adapted.state,
                limitations=_merge_texts(profile.limitations, adapted.limitations),
            )
            now = _utc_now()
            run = EvidenceRunRecord(
                evidence_run_id=uuid4().hex,
                organization_id=scope.organization_id,
                assessment_id=assessment_id,
                transcript_revision_id=transcript_revision_id,
                state=adapted.state.value,
                input_ref=provenance.input_ref,
                input_sha256=provenance.input_sha256,
                protocol_version_key=provenance.protocol_version_key,
                extractor=provenance.extractor,
                pipeline_version=provenance.pipeline_version,
                feature_schema_version=provenance.feature_schema_version,
                limitations_json=list(profile.limitations),
                generated_at=generated_at,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(run)
            self.session.flush()
            self.session.add_all(
                EvidenceFeatureRecord(
                    evidence_feature_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    evidence_run_id=run.evidence_run_id,
                    feature_key=feature.key,
                    value_json=feature.value,
                    unit=feature.unit,
                    source=feature.source.value,
                    state=feature.state.value,
                    limitation=feature.limitation,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                for feature in profile.features
            )
            self.session.add_all(
                EvidenceDomainProfileRecord(
                    domain_profile_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    evidence_run_id=run.evidence_run_id,
                    domain=domain.domain.value,
                    status=domain.status.value,
                    summary=domain.summary,
                    feature_keys_json=list(domain.feature_keys),
                    supporting_features_json=list(domain.supporting_features),
                    conflicting_features_json=list(domain.conflicting_features),
                    limitations_json=list(domain.limitations),
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                for domain in profile.domains
            )
            self._append_audit(
                scope,
                "evidence.run_created",
                "evidence_run",
                run.evidence_run_id,
                correlation_id,
                ["state", "version"],
                target_version=run.version,
            )
            self.session.flush()
            return self._evidence_snapshot(run)

    def enqueue_current_evidence_processing(
        self,
        scope: AccessScope,
        assessment_id: str,
        correlation_id: str,
    ) -> ProcessingRunSnapshot:
        """Durably enqueue extraction for the current attested transcript."""

        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, assessment_id)
            child = self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, child.child_id)
            self._require_locked_assignee_eligibility(
                scope,
                child.child_id,
                assessment.assigned_clinician_id,
            )
            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .with_for_update()
                .limit(1)
            )
            if transcript is None:
                raise RepositoryError("transcript_not_found")
            if transcript.review_state != TranscriptReviewState.ATTESTED.value:
                raise RepositoryError("transcript_not_reviewable")

            segment_set = self._current_attested_segment_set(
                scope.organization_id,
                assessment_id,
                transcript,
                lock=True,
            )
            if segment_set is None:
                raise RepositoryError("segment_set_not_reviewable")

            selection = self.session.scalar(
                select(AssessmentProtocolSelectionRecord)
                .where(
                    AssessmentProtocolSelectionRecord.organization_id == scope.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == assessment_id,
                )
                .with_for_update()
            )
            if selection is None:
                raise RepositoryError("evidence_protocol_mismatch")

            pipeline_version = _EVIDENCE_PIPELINE_VERSION
            feature_schema_version = _EVIDENCE_FEATURE_SCHEMA_VERSION
            idempotency_key = _evidence_idempotency_key(
                assessment_id,
                transcript.transcript_revision_id,
                transcript.content_sha256,
                segment_set.transcript_segment_set_id,
                segment_set.segments_sha256,
                pipeline_version,
                feature_schema_version,
            )
            existing = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if existing is not None:
                return self._processing_run_snapshot(existing)

            self._cancel_evidence_runs_for_assessment(
                scope,
                assessment_id,
                "analysis_contract_superseded",
                correlation_id,
                keep_transcript_revision_id=transcript.transcript_revision_id,
                keep_segment_set_id=segment_set.transcript_segment_set_id,
                keep_segment_set_sha256=segment_set.segments_sha256,
                keep_pipeline_version=pipeline_version,
                keep_feature_schema_version=feature_schema_version,
            )
            now = self._now()
            run = ProcessingRunRecord(
                processing_run_id=uuid4().hex,
                organization_id=scope.organization_id,
                recording_id=None,
                assessment_id=assessment_id,
                transcript_revision_id=transcript.transcript_revision_id,
                evidence_run_id=None,
                segment_set_id=segment_set.transcript_segment_set_id,
                segment_set_sha256=segment_set.segments_sha256,
                stage=ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                state=ProcessingRunState.QUEUED.value,
                idempotency_key=idempotency_key,
                attempt_count=0,
                max_attempts=3,
                available_at=now,
                error_code=None,
                lease_token=None,
                lease_expires_at=None,
                cancel_requested_at=None,
                completed_at=None,
                pipeline_version=pipeline_version,
                feature_schema_version=feature_schema_version,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(run)
            self.session.flush()
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.queued",
                ["processing_stage", "processing_state"],
                correlation_id=correlation_id,
            )
            self.session.flush()
            return self._processing_run_snapshot(run)

    def claim_next_evidence_processing_run(self) -> EvidenceWorkItem | None:
        """Claim one queued or expired evidence job with a tenant-safe lease."""

        now = self._now()
        candidate_query = select(ProcessingRunRecord.processing_run_id).where(
            ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
            or_(
                and_(
                    or_(
                        ProcessingRunRecord.segment_set_id.is_(None),
                        ProcessingRunRecord.segment_set_sha256.is_(None),
                    ),
                    ProcessingRunRecord.state.in_(
                        (
                            ProcessingRunState.QUEUED.value,
                            ProcessingRunState.RUNNING.value,
                        )
                    ),
                ),
                and_(
                    ProcessingRunRecord.state == ProcessingRunState.QUEUED.value,
                    ProcessingRunRecord.available_at <= now,
                ),
                and_(
                    ProcessingRunRecord.state == ProcessingRunState.RUNNING.value,
                    ProcessingRunRecord.lease_expires_at.is_not(None),
                    ProcessingRunRecord.lease_expires_at <= now,
                ),
            ),
        )
        if self._worker_organization_id is not None:
            candidate_query = candidate_query.where(
                ProcessingRunRecord.organization_id == self._worker_organization_id
            )
        candidate_ids = list(
            self.session.scalars(
                candidate_query.order_by(
                    ProcessingRunRecord.available_at,
                    ProcessingRunRecord.created_at,
                ).limit(100)
            )
        )
        for candidate_id in candidate_ids:
            with self.session.begin_nested():
                # The initial read is deliberately unlocked. Valid candidates
                # then acquire the shared lock order: assessment -> child ->
                # transcript -> processing run. This keeps worker polling from
                # racing with transcript edits, consent withdrawal, or actions.
                candidate = self.session.scalar(
                    select(ProcessingRunRecord).where(
                        ProcessingRunRecord.processing_run_id == candidate_id,
                        ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                    )
                )
                if candidate is None:
                    continue

                def lock_run() -> ProcessingRunRecord | None:
                    return self.session.scalar(
                        select(ProcessingRunRecord)
                        .where(
                            ProcessingRunRecord.organization_id == candidate.organization_id,
                            ProcessingRunRecord.processing_run_id == candidate.processing_run_id,
                            ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                        )
                        .with_for_update(skip_locked=True)
                    )

                if candidate.assessment_id is None or candidate.transcript_revision_id is None:
                    run = lock_run()
                    if run is None or not self._processing_run_is_claimable(run, now):
                        continue
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="invalid_processing_target",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue

                assessment = self.session.scalar(
                    select(AssessmentRecord)
                    .where(
                        AssessmentRecord.organization_id == candidate.organization_id,
                        AssessmentRecord.assessment_id == candidate.assessment_id,
                    )
                    .with_for_update()
                )
                if assessment is None:
                    run = lock_run()
                    if run is None or not self._processing_run_is_claimable(run, now):
                        continue
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="assessment_not_found",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue

                child = self.session.scalar(
                    select(ChildRecord)
                    .where(
                        ChildRecord.organization_id == candidate.organization_id,
                        ChildRecord.child_id == assessment.child_id,
                    )
                    .with_for_update()
                )
                if child is None:
                    run = lock_run()
                    if run is None or not self._processing_run_is_claimable(run, now):
                        continue
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="child_not_found",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue

                transcript = self.session.scalar(
                    select(TranscriptRevisionRecord)
                    .where(
                        TranscriptRevisionRecord.organization_id == candidate.organization_id,
                        TranscriptRevisionRecord.transcript_revision_id
                        == candidate.transcript_revision_id,
                    )
                    .with_for_update()
                )
                run = lock_run()
                if run is None or transcript is None:
                    continue
                # A1 evidence jobs predate segment provenance. They may still
                # hold an unexpired lease, but the new worker must never let
                # them continue or be reclaimed as if they were A2 work.
                if run.segment_set_id is None or run.segment_set_sha256 is None:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="segment_provenance_missing",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(
                        run,
                        "processing_run.cancelled",
                        ["processing_state"],
                    )
                    continue
                if not self._processing_run_is_claimable(run, now):
                    continue
                if run.cancel_requested_at is not None:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code=_EVIDENCE_USER_CANCEL_CODE,
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                if run.attempt_count >= run.max_attempts:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="retry_limit_exceeded",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue
                if not self._has_current_capture_consent(run.organization_id, child.child_id):
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="consent_revoked",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                current_transcript_id = self.session.scalar(
                    select(TranscriptRevisionRecord.transcript_revision_id)
                    .where(
                        TranscriptRevisionRecord.organization_id == run.organization_id,
                        TranscriptRevisionRecord.assessment_id == assessment.assessment_id,
                    )
                    .order_by(desc(TranscriptRevisionRecord.revision))
                    .limit(1)
                )
                if current_transcript_id != run.transcript_revision_id:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="transcript_superseded",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                if transcript.review_state != TranscriptReviewState.ATTESTED.value:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="transcript_not_attested",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                try:
                    segment_set = self._current_attested_segment_set(
                        run.organization_id,
                        assessment.assessment_id,
                        transcript,
                        lock=True,
                    )
                except RepositoryError:
                    segment_set = None
                if (
                    segment_set is None
                    or segment_set.transcript_segment_set_id != run.segment_set_id
                    or segment_set.segments_sha256 != run.segment_set_sha256
                ):
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="segment_set_superseded",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(
                        run,
                        "processing_run.cancelled",
                        ["processing_state"],
                    )
                    continue
                selection = self.session.scalar(
                    select(AssessmentProtocolSelectionRecord)
                    .where(
                        AssessmentProtocolSelectionRecord.organization_id == run.organization_id,
                        AssessmentProtocolSelectionRecord.assessment_id == assessment.assessment_id,
                    )
                    .with_for_update()
                )
                if (
                    selection is None
                    or run.pipeline_version != _EVIDENCE_PIPELINE_VERSION
                    or run.feature_schema_version != _EVIDENCE_FEATURE_SCHEMA_VERSION
                ):
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="analysis_contract_superseded",
                        lease_token=None,
                        lease_expires_at=None,
                        now=now,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                token = uuid4().hex
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.RUNNING.value,
                    error_code=None,
                    attempt_count=run.attempt_count + 1,
                    lease_token=token,
                    lease_expires_at=now + _EVIDENCE_LEASE_DURATION,
                    cancel_requested_at=None,
                    now=now,
                )
                self._audit_worker_run(run, "processing_run.claimed", ["processing_state"])
                self.session.flush()
                return EvidenceWorkItem(
                    run_id=run.processing_run_id,
                    organization_id=run.organization_id,
                    assessment_id=run.assessment_id,
                    transcript_revision_id=run.transcript_revision_id,
                    segment_set_id=run.segment_set_id,
                    segment_set_sha256=run.segment_set_sha256,
                    protocol_version_key=selection.protocol_version_key,
                    pipeline_version=run.pipeline_version,
                    feature_schema_version=run.feature_schema_version,
                    content_sha256=transcript.content_sha256,
                    lease_token=token,
                    lease_expires_at=now + _EVIDENCE_LEASE_DURATION,
                    attempt_count=run.attempt_count,
                    max_attempts=run.max_attempts,
                    transcript=self._transcript_snapshot(transcript),
                    segment_set=self._transcript_segment_set_snapshot(segment_set),
                )
        return None

    def complete_evidence_processing_run(
        self,
        item: EvidenceWorkItem,
        adapted: AdaptedEvidence,
    ) -> EvidenceRunSnapshot | None:
        """Persist evidence only when the worker still owns the lease."""

        with self.session.begin_nested():
            # Match claim/cancel/transcript mutation ordering before touching
            # the processing row: assessment -> child -> transcript -> run.
            # This prevents a slow extractor completion from deadlocking a
            # clinician cancellation or a newer transcript revision.
            assessment = self.session.scalar(
                select(AssessmentRecord)
                .where(
                    AssessmentRecord.organization_id == item.organization_id,
                    AssessmentRecord.assessment_id == item.assessment_id,
                )
                .with_for_update()
            )
            if assessment is None:
                return None
            child = self.session.scalar(
                select(ChildRecord)
                .where(
                    ChildRecord.organization_id == item.organization_id,
                    ChildRecord.child_id == assessment.child_id,
                )
                .with_for_update()
            )
            if child is None:
                run = self.session.scalar(
                    select(ProcessingRunRecord)
                    .where(
                        ProcessingRunRecord.organization_id == item.organization_id,
                        ProcessingRunRecord.processing_run_id == item.run_id,
                    )
                    .with_for_update()
                )
                if run is not None and run.state == ProcessingRunState.RUNNING.value:
                    self._cancel_worker_evidence_run(run, "consent_revoked")
                return None
            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == item.organization_id,
                    TranscriptRevisionRecord.transcript_revision_id == item.transcript_revision_id,
                )
                .with_for_update()
            )
            run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == item.organization_id,
                    ProcessingRunRecord.processing_run_id == item.run_id,
                    ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                )
                .with_for_update()
            )
            if (
                run is None
                or run.state != ProcessingRunState.RUNNING.value
                or run.lease_token != item.lease_token
            ):
                return None
            if run.assessment_id != item.assessment_id or run.transcript_revision_id != item.transcript_revision_id:
                return None
            now = self._now()
            if run.lease_expires_at is None or _is_expired(run.lease_expires_at, now):
                return None
            if run.cancel_requested_at is not None:
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code=_EVIDENCE_USER_CANCEL_CODE,
                    lease_token=None,
                    lease_expires_at=None,
                    now=now,
                )
                self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                return None
            if transcript is None:
                self._cancel_worker_evidence_run(run, "transcript_superseded")
                return None
            if not self._has_current_capture_consent(run.organization_id, child.child_id):
                self._cancel_worker_evidence_run(run, "consent_revoked")
                return None
            current_transcript_id = self.session.scalar(
                select(TranscriptRevisionRecord.transcript_revision_id)
                .where(
                    TranscriptRevisionRecord.organization_id == run.organization_id,
                    TranscriptRevisionRecord.assessment_id == assessment.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .limit(1)
            )
            if (
                current_transcript_id != run.transcript_revision_id
                or transcript.review_state != TranscriptReviewState.ATTESTED.value
                or transcript.content_sha256 != item.content_sha256
                or sha256(transcript.content.encode("utf-8")).hexdigest() != item.content_sha256
            ):
                self._cancel_worker_evidence_run(run, "transcript_superseded")
                return None
            if (
                item.segment_set_id != run.segment_set_id
                or item.segment_set_sha256 != run.segment_set_sha256
            ):
                self._cancel_worker_evidence_run(run, "segment_set_superseded")
                return None
            if run.segment_set_id is None or run.segment_set_sha256 is None or item.segment_set is None:
                self._cancel_worker_evidence_run(run, "segment_provenance_missing")
                return None
            try:
                segment_set = self._current_attested_segment_set(
                    run.organization_id,
                    assessment.assessment_id,
                    transcript,
                    lock=True,
                )
            except RepositoryError:
                segment_set = None
            if (
                segment_set is None
                or segment_set.transcript_segment_set_id != run.segment_set_id
                or segment_set.segments_sha256 != run.segment_set_sha256
                or item.segment_set.id != run.segment_set_id
                or item.segment_set.segments_sha256 != run.segment_set_sha256
            ):
                self._cancel_worker_evidence_run(run, "segment_set_superseded")
                return None
            selection = self.session.scalar(
                select(AssessmentProtocolSelectionRecord)
                .where(
                    AssessmentProtocolSelectionRecord.organization_id == run.organization_id,
                    AssessmentProtocolSelectionRecord.assessment_id == assessment.assessment_id,
                )
                .with_for_update()
            )
            if (
                selection is None
                or selection.protocol_version_key != item.protocol_version_key
                or run.pipeline_version != _EVIDENCE_PIPELINE_VERSION
                or run.feature_schema_version != _EVIDENCE_FEATURE_SCHEMA_VERSION
            ):
                self._cancel_worker_evidence_run(run, "analysis_contract_superseded")
                return None
            provenance = adapted.provenance
            if (
                provenance is None
                or provenance.input_sha256 != item.content_sha256
                or provenance.protocol_version_key != selection.protocol_version_key
                or provenance.pipeline_version != run.pipeline_version
                or provenance.feature_schema_version != run.feature_schema_version
            ):
                raise RepositoryError("evidence_provenance_mismatch")

            evidence = self._persist_adapted_evidence(
                self._worker_scope(run.organization_id),
                assessment.assessment_id,
                transcript,
                selection,
                adapted,
                self._worker_correlation(run.processing_run_id),
                segment_set_id=run.segment_set_id,
                segment_set_sha256=run.segment_set_sha256,
            )
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.SUCCEEDED.value,
                error_code=None,
                evidence_run_id=evidence.id,
                lease_token=None,
                lease_expires_at=None,
                completed_at=self._now(),
                now=self._now(),
            )
            self._audit_worker_run(run, "processing_run.succeeded", ["processing_state"])
            self.session.flush()
            return evidence

    def fail_evidence_processing_run(
        self,
        item: EvidenceWorkItem,
        error_code: str,
        *,
        retryable: bool,
    ) -> ProcessingRunSnapshot:
        with self.session.begin_nested():
            run = self._worker_run(item, check_lease_expiry=False)
            if run is None:
                raise RepositoryError("processing_run_not_found")
            if (
                run.stage != ProcessingRunStage.EVIDENCE_EXTRACTION.value
                or run.state != ProcessingRunState.RUNNING.value
                or run.lease_token != item.lease_token
            ):
                return self._processing_run_snapshot(run)
            now = self._now()
            if run.lease_expires_at is None or _is_expired(run.lease_expires_at, now):
                # A stale worker must not clear or reschedule a lease that may
                # already have been reclaimed by another worker.
                return self._processing_run_snapshot(run)
            if run.cancel_requested_at is not None:
                # A user cancellation may race with extractor failure. Once
                # the request is persisted, a late worker failure must not
                # resurrect the job as queued or make it appear cancellable.
                target_state = ProcessingRunState.CANCELLED.value
                persisted_error_code = _EVIDENCE_USER_CANCEL_CODE
                available_at = run.available_at
            elif error_code in _EVIDENCE_SYSTEM_CANCEL_CODES or error_code == _EVIDENCE_USER_CANCEL_CODE:
                target_state = ProcessingRunState.CANCELLED.value
                persisted_error_code = error_code
                available_at = run.available_at
            elif retryable and run.attempt_count < run.max_attempts:
                target_state = ProcessingRunState.QUEUED.value
                persisted_error_code = error_code
                backoff_index = min(run.attempt_count - 1, len(_EVIDENCE_RETRY_BACKOFF) - 1)
                available_at = now + _EVIDENCE_RETRY_BACKOFF[backoff_index]
            else:
                target_state = ProcessingRunState.FAILED.value
                persisted_error_code = error_code
                available_at = run.available_at
            self._mutate_processing_run(
                run,
                state=target_state,
                error_code=persisted_error_code,
                available_at=available_at,
                lease_token=None,
                lease_expires_at=None,
                now=now,
            )
            action = (
                "processing_run.retry_scheduled"
                if target_state == ProcessingRunState.QUEUED.value
                else "processing_run.cancelled"
                if target_state == ProcessingRunState.CANCELLED.value
                else "processing_run.failed"
            )
            self._audit_worker_run(run, action, ["processing_state"])
            self.session.flush()
            return self._processing_run_snapshot(run)

    def retry_evidence_processing_run(
        self,
        scope: AccessScope,
        run_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> ProcessingRunSnapshot:
        with self.session.begin_nested():
            run_ref = self.session.scalar(
                select(ProcessingRunRecord).where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.processing_run_id == run_id,
                )
            )
            if run_ref is None or run_ref.stage != ProcessingRunStage.EVIDENCE_EXTRACTION.value:
                raise RepositoryError("processing_run_not_found")
            assessment = self._locked_assessment(scope, run_ref.assessment_id or "")
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.processing_run_id == run_id,
                )
                .with_for_update()
            )
            if run is None:
                raise RepositoryError("processing_run_not_found")
            if run.version != expected_version:
                raise RepositoryError("stale_processing_run_version")
            if run.state not in {
                ProcessingRunState.FAILED.value,
                ProcessingRunState.CANCELLED.value,
            }:
                raise RepositoryError("processing_run_not_retryable")
            if run.state == ProcessingRunState.CANCELLED.value and run.error_code != _EVIDENCE_USER_CANCEL_CODE:
                raise RepositoryError("processing_run_not_retryable")
            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.transcript_revision_id == run.transcript_revision_id,
                )
                .with_for_update()
            )
            current_transcript_id = self.session.scalar(
                select(TranscriptRevisionRecord.transcript_revision_id)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == assessment.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .limit(1)
            )
            if (
                transcript is None
                or current_transcript_id != run.transcript_revision_id
                or transcript.review_state != TranscriptReviewState.ATTESTED.value
                or run.pipeline_version != _EVIDENCE_PIPELINE_VERSION
                or run.feature_schema_version != _EVIDENCE_FEATURE_SCHEMA_VERSION
            ):
                raise RepositoryError("processing_run_not_retryable")
            now = self._now()
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.QUEUED.value,
                error_code=None,
                attempt_count=0,
                available_at=now,
                lease_token=None,
                lease_expires_at=None,
                cancel_requested_at=None,
                completed_at=None,
                evidence_run_id=None,
                now=now,
            )
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.retry_requested",
                ["processing_state"],
                correlation_id=correlation_id,
            )
            self.session.flush()
            return self._processing_run_snapshot(run)

    def request_evidence_processing_cancellation(
        self,
        scope: AccessScope,
        run_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> ProcessingRunSnapshot:
        with self.session.begin_nested():
            run_ref = self.session.scalar(
                select(ProcessingRunRecord).where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.processing_run_id == run_id,
                )
            )
            if run_ref is None or run_ref.stage != ProcessingRunStage.EVIDENCE_EXTRACTION.value:
                raise RepositoryError("processing_run_not_found")
            assessment = self._locked_assessment(scope, run_ref.assessment_id or "")
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.processing_run_id == run_id,
                )
                .with_for_update()
            )
            if run is None or run.stage != ProcessingRunStage.EVIDENCE_EXTRACTION.value:
                raise RepositoryError("processing_run_not_found")
            if run.version != expected_version:
                raise RepositoryError("stale_processing_run_version")
            if run.state not in {
                ProcessingRunState.QUEUED.value,
                ProcessingRunState.RUNNING.value,
            }:
                raise RepositoryError("processing_run_not_cancellable")
            now = self._now()
            if run.state == ProcessingRunState.QUEUED.value:
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code=_EVIDENCE_USER_CANCEL_CODE,
                    cancel_requested_at=now,
                    lease_token=None,
                    lease_expires_at=None,
                    now=now,
                )
            else:
                self._mutate_processing_run(
                    run,
                    error_code=_EVIDENCE_USER_CANCEL_CODE,
                    cancel_requested_at=now,
                    now=now,
                )
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.cancel_requested",
                ["processing_state"],
                correlation_id=correlation_id,
            )
            self.session.flush()
            return self._processing_run_snapshot(run)

    def create_transcript_revision(
        self,
        scope: AccessScope,
        command: CreateTranscriptRevision,
        correlation_id: str,
    ) -> TranscriptRevisionSnapshot:
        with self.session.begin_nested():
            assessment = self._locked_assessment(scope, command.assessment_id)
            # Consent withdrawal serializes on the child row. Acquire that
            # same lock before checking consent and mutating transcript state.
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            if assessment.state not in {
                AssessmentState.PROCESSING.value,
                AssessmentState.REVIEW_REQUIRED.value,
            }:
                raise RepositoryError("transcript_not_reviewable")

            latest = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == command.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .with_for_update()
                .limit(1)
            )
            if latest is None:
                if command.expected_revision is not None or command.expected_version is not None:
                    raise RepositoryError("stale_transcript_version")
            elif (
                command.expected_revision != latest.revision
                or command.expected_version != latest.version
            ):
                raise RepositoryError("stale_transcript_version")

            self._cancel_evidence_runs_for_assessment(
                scope,
                assessment.assessment_id,
                "transcript_superseded",
                correlation_id,
            )
            self._mark_evidence_stale_for_assessment(
                scope,
                assessment.assessment_id,
                correlation_id,
            )
            self._supersede_segment_sets_for_assessment(
                scope,
                assessment.assessment_id,
                correlation_id,
            )
            if assessment.state == AssessmentState.PROCESSING.value:
                # The first clinician-visible transcript draft moves the
                # assessment into the explicit review queue. Later revisions
                # remain within that queue and do not create extra assessment
                # transitions.
                self._transition_locked_assessment(
                    scope,
                    assessment,
                    AssessmentState.REVIEW_REQUIRED,
                    assessment.version,
                    correlation_id,
                )
            if latest is not None:
                latest.review_state = TranscriptReviewState.SUPERSEDED.value
                latest.version += 1
                latest.updated_at = _utc_now()
                self._append_audit(
                    scope,
                    "transcript.revision_superseded",
                    "transcript_revision",
                    latest.transcript_revision_id,
                    correlation_id,
                    ["review_state", "version"],
                    target_version=latest.version,
                )
            now = _utc_now()
            record = TranscriptRevisionRecord(
                transcript_revision_id=uuid4().hex,
                organization_id=scope.organization_id,
                assessment_id=command.assessment_id,
                revision=(latest.revision + 1 if latest is not None else 1),
                source=command.source.value,
                review_state=TranscriptReviewState.DRAFT.value,
                content=command.content,
                content_sha256=sha256(command.content.encode("utf-8")).hexdigest(),
                created_by_user_id=scope.user_id,
                attested_by_user_id=None,
                attested_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.session.add(record)
            self._append_audit(
                scope,
                "transcript.revision_created",
                "transcript_revision",
                record.transcript_revision_id,
                correlation_id,
                ["revision", "source", "review_state", "version"],
                target_version=record.version,
            )
            self.session.flush()
            return self._transcript_snapshot(record)

    def get_current_transcript_segment_set(
        self,
        scope: AccessScope,
        assessment_id: str,
    ) -> TranscriptSegmentSetSnapshot | None:
        assessment = self._assessment_record(scope, assessment_id)
        if assessment is None:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        transcript = self.session.scalar(
            select(TranscriptRevisionRecord)
            .where(
                TranscriptRevisionRecord.organization_id == scope.organization_id,
                TranscriptRevisionRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptRevisionRecord.revision))
            .limit(1)
        )
        if transcript is None:
            return None
        record = self.session.scalar(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment_id,
                TranscriptSegmentSetRecord.review_state != TranscriptReviewState.SUPERSEDED.value,
                TranscriptSegmentSetRecord.transcript_revision_id == transcript.transcript_revision_id,
                TranscriptSegmentSetRecord.transcript_content_sha256 == transcript.content_sha256,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
            .limit(1)
        )
        return self._transcript_segment_set_snapshot(record) if record is not None else None

    def get_transcript_segment_replay_target(
        self,
        scope: AccessScope,
        transcript_segment_id: str,
    ) -> tuple[TranscriptSegmentSnapshot, RecordingSnapshot | None] | None:
        segment_record = self.session.scalar(
            select(TranscriptSegmentRecord).where(
                TranscriptSegmentRecord.organization_id == scope.organization_id,
                TranscriptSegmentRecord.transcript_segment_id == transcript_segment_id,
            )
        )
        if segment_record is None:
            return None
        segment_set = self.session.scalar(
            select(TranscriptSegmentSetRecord).where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.transcript_segment_set_id
                == segment_record.transcript_segment_set_id,
            )
        )
        if segment_set is None or segment_set.review_state == TranscriptReviewState.SUPERSEDED.value:
            return None
        try:
            # Replay shares the assessment -> child -> consent lock order used
            # by consent withdrawal and evidence enqueue. The locks remain held
            # until the request transaction commits, including storage signing
            # in the service layer.
            assessment = self._locked_assessment(scope, segment_set.assessment_id)
            self._locked_child(scope, assessment.child_id)
        except RepositoryError:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        segment_set = self.session.scalar(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.transcript_segment_set_id == segment_set.transcript_segment_set_id,
            )
            .with_for_update()
        )
        segment_record = self.session.scalar(
            select(TranscriptSegmentRecord)
            .where(
                TranscriptSegmentRecord.organization_id == scope.organization_id,
                TranscriptSegmentRecord.transcript_segment_id == transcript_segment_id,
            )
            .with_for_update()
        )
        current_segment_set = self.session.scalar(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment.assessment_id,
                TranscriptSegmentSetRecord.review_state != TranscriptReviewState.SUPERSEDED.value,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
            .limit(1)
        )
        if (
            segment_set is None
            or segment_record is None
            or current_segment_set is None
            or current_segment_set.transcript_segment_set_id != segment_set.transcript_segment_set_id
        ):
            return None
        transcript = self.session.scalar(
            select(TranscriptRevisionRecord)
            .where(
                TranscriptRevisionRecord.organization_id == scope.organization_id,
                TranscriptRevisionRecord.assessment_id == segment_set.assessment_id,
            )
            .order_by(desc(TranscriptRevisionRecord.revision))
            .with_for_update()
            .limit(1)
        )
        if (
            transcript is None
            or transcript.transcript_revision_id != segment_set.transcript_revision_id
            or transcript.content_sha256 != segment_set.transcript_content_sha256
        ):
            return None
        segment = self._transcript_segment_snapshot(segment_record)
        recording_snapshot = None
        if segment_set.recording_id is not None:
            recording = self.session.scalar(
                select(RecordingRecord).where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == segment_set.recording_id,
                )
            )
            if (
                recording is not None
                and recording.assessment_id == segment_set.assessment_id
                and recording.upload_state == RecordingUploadState.VERIFIED.value
                and recording.verified_at is not None
                and recording.verified_checksum is not None
            ):
                recording_snapshot = self._recording_snapshot(recording)
        return segment, recording_snapshot

    def _current_attested_segment_set(
        self,
        organization_id: str,
        assessment_id: str,
        transcript: TranscriptRevisionRecord,
        *,
        lock: bool = False,
    ) -> TranscriptSegmentSetRecord | None:
        query = (
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment_id,
                TranscriptSegmentSetRecord.transcript_revision_id
                == transcript.transcript_revision_id,
                TranscriptSegmentSetRecord.transcript_content_sha256 == transcript.content_sha256,
                TranscriptSegmentSetRecord.review_state == TranscriptReviewState.ATTESTED.value,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
            .limit(1)
        )
        if lock:
            query = query.with_for_update()
        record = self.session.scalar(query)
        if record is not None:
            self._transcript_segment_set_snapshot(record)
        return record

    def create_transcript_segment_set(
        self,
        scope: AccessScope,
        command: CreateTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot:
        with self.session.begin_nested():
            # All segment writes use assessment -> child -> transcript ->
            # segment set -> recording lock order.  This is the same order
            # used by transcript writes and prevents consent/recording races.
            assessment = self._locked_assessment(scope, command.assessment_id)
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            self._require_segment_editor_role(scope)
            self._require_segment_editor_assignment(scope, assessment.child_id)
            if assessment.state not in {
                AssessmentState.PROCESSING.value,
                AssessmentState.REVIEW_REQUIRED.value,
            }:
                raise RepositoryError("segment_set_not_reviewable")

            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == command.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .with_for_update()
                .limit(1)
            )
            if transcript is None:
                raise RepositoryError("transcript_not_found")
            if transcript.transcript_revision_id != command.transcript_revision_id:
                raise RepositoryError("segment_transcript_stale")
            if transcript.review_state != TranscriptReviewState.ATTESTED.value:
                raise RepositoryError("transcript_not_reviewable")

            previous = self.session.scalar(
                select(TranscriptSegmentSetRecord)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.assessment_id == command.assessment_id,
                )
                .order_by(desc(TranscriptSegmentSetRecord.revision))
                .with_for_update()
                .limit(1)
            )
            current_previous = self.session.scalar(
                select(TranscriptSegmentSetRecord)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.assessment_id == command.assessment_id,
                    TranscriptSegmentSetRecord.review_state
                    != TranscriptReviewState.SUPERSEDED.value,
                )
                .order_by(desc(TranscriptSegmentSetRecord.revision))
                .with_for_update()
                .limit(1)
            )
            if current_previous is None:
                if command.expected_revision is not None or command.expected_version is not None:
                    raise RepositoryError("stale_segment_set_version")
            elif (
                command.expected_revision != current_previous.revision
                or command.expected_version != current_previous.version
            ):
                raise RepositoryError("stale_segment_set_version")
            if (
                current_previous is not None
                and current_previous.transcript_revision_id != transcript.transcript_revision_id
            ):
                raise RepositoryError("segment_transcript_stale")

            canonical_segments = canonicalize_transcript_segments(
                command.segments,
                client_checksum=command.client_checksum,
            )
            segments_sha256 = compute_transcript_segments_sha256(canonical_segments)
            if current_previous is not None:
                current_previous.review_state = TranscriptReviewState.SUPERSEDED.value
                current_previous.version += 1
                current_previous.updated_at = self._now()
                self._append_audit(
                    scope,
                    "transcript.segment_set_superseded",
                    "transcript_segment_set",
                    current_previous.transcript_segment_set_id,
                    correlation_id,
                    ["review_state", "version"],
                    target_version=current_previous.version,
                )

            recording = None
            if command.recording_id is not None:
                recording = self.session.scalar(
                    select(RecordingRecord)
                    .where(
                        RecordingRecord.organization_id == scope.organization_id,
                        RecordingRecord.recording_id == command.recording_id,
                    )
                    .with_for_update()
                )
                if recording is None or recording.assessment_id != command.assessment_id:
                    raise RepositoryError("recording_not_found")
                if (
                    recording.upload_state != RecordingUploadState.VERIFIED.value
                    or recording.verified_at is None
                    or recording.verified_checksum is None
                ):
                    raise RepositoryError("recording_not_verified")

            now = self._now()
            record = TranscriptSegmentSetRecord(
                transcript_segment_set_id=uuid4().hex,
                organization_id=scope.organization_id,
                assessment_id=command.assessment_id,
                transcript_revision_id=transcript.transcript_revision_id,
                transcript_content_sha256=transcript.content_sha256,
                recording_id=recording.recording_id if recording is not None else None,
                revision=(previous.revision + 1 if previous is not None else 1),
                source=command.source.value,
                review_state=TranscriptReviewState.DRAFT.value,
                segments_sha256=segments_sha256,
                created_by_user_id=scope.user_id,
                attested_by_user_id=None,
                attested_at=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self._cancel_segment_bound_evidence_jobs(
                scope,
                command.assessment_id,
                record.transcript_segment_set_id,
                correlation_id,
            )
            self._mark_segment_bound_evidence_stale_for_assessment(
                scope,
                command.assessment_id,
                record.transcript_segment_set_id,
                correlation_id,
            )
            self.session.add(record)
            # The segment rows have a database FK to this immutable parent,
            # but the SQLAlchemy models intentionally do not expose a mutable
            # relationship. Flush the parent explicitly so PostgreSQL never
            # attempts the child insert first.
            self.session.flush()
            self.session.add_all(
                TranscriptSegmentRecord(
                    transcript_segment_id=uuid4().hex,
                    organization_id=scope.organization_id,
                    transcript_segment_set_id=record.transcript_segment_set_id,
                    ordinal=segment.ordinal,
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                    speaker_role=segment.speaker_role.value,
                    text=segment.text,
                    confidence=segment.confidence,
                    uncertainty_reason=segment.uncertainty_reason.value,
                    created_at=now,
                )
                for segment in canonical_segments
            )
            self._append_audit(
                scope,
                "transcript.segment_set_created",
                "transcript_segment_set",
                record.transcript_segment_set_id,
                correlation_id,
                [
                    "revision",
                    "source",
                    "review_state",
                    "transcript_content_sha256",
                    "segments_sha256",
                    "version",
                ],
                target_version=record.version,
            )
            self.session.flush()
            return self._transcript_segment_set_snapshot(record)

    def attest_transcript_segment_set(
        self,
        scope: AccessScope,
        command: AttestTranscriptSegmentSet,
        correlation_id: str,
    ) -> TranscriptSegmentSetSnapshot:
        with self.session.begin_nested():
            record_ref = self.session.scalar(
                select(TranscriptSegmentSetRecord)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.transcript_segment_set_id
                    == command.transcript_segment_set_id,
                )
            )
            if record_ref is None:
                raise RepositoryError("segment_set_not_found")
            assessment = self._locked_assessment(scope, record_ref.assessment_id)
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            self._require_segment_editor_role(scope)
            self._require_segment_editor_assignment(scope, assessment.child_id)
            transcript = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == assessment.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .with_for_update()
                .limit(1)
            )
            record = self.session.scalar(
                select(TranscriptSegmentSetRecord)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.transcript_segment_set_id
                    == command.transcript_segment_set_id,
                )
                .with_for_update()
            )
            if record is None:
                raise RepositoryError("segment_set_not_found")
            if (
                transcript is None
                or transcript.transcript_revision_id != record.transcript_revision_id
                or transcript.content_sha256 != record.transcript_content_sha256
            ):
                raise RepositoryError("segment_transcript_stale")
            if transcript.review_state != TranscriptReviewState.ATTESTED.value:
                raise RepositoryError("transcript_not_reviewable")
            current_id = self.session.scalar(
                select(TranscriptSegmentSetRecord.transcript_segment_set_id)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.assessment_id == assessment.assessment_id,
                )
                .order_by(desc(TranscriptSegmentSetRecord.revision))
                .limit(1)
            )
            if record.version != command.expected_version:
                raise RepositoryError("stale_segment_set_version")
            if (
                current_id != record.transcript_segment_set_id
                or record.review_state != TranscriptReviewState.DRAFT.value
            ):
                raise RepositoryError("segment_set_not_reviewable")
            if record.recording_id is not None:
                recording = self.session.scalar(
                    select(RecordingRecord)
                    .where(
                        RecordingRecord.organization_id == scope.organization_id,
                        RecordingRecord.recording_id == record.recording_id,
                    )
                    .with_for_update()
                )
                if (
                    recording is None
                    or recording.assessment_id != assessment.assessment_id
                    or recording.upload_state != RecordingUploadState.VERIFIED.value
                    or recording.verified_at is None
                    or recording.verified_checksum is None
                ):
                    raise RepositoryError("recording_not_verified")
            now = self._now()
            record.review_state = TranscriptReviewState.ATTESTED.value
            record.attested_by_user_id = scope.user_id
            record.attested_at = now
            record.version += 1
            record.updated_at = now
            self._append_audit(
                scope,
                "transcript.segment_set_attested",
                "transcript_segment_set",
                record.transcript_segment_set_id,
                correlation_id,
                ["review_state", "attested_at", "version"],
                target_version=record.version,
            )
            self.session.flush()
            return self._transcript_segment_set_snapshot(record)

    def attest_transcript(
        self,
        scope: AccessScope,
        command: AttestTranscript,
        correlation_id: str,
    ) -> TranscriptRevisionSnapshot:
        with self.session.begin_nested():
            record_ref = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.transcript_revision_id == command.transcript_revision_id,
                )
            )
            if record_ref is None:
                raise RepositoryError("transcript_not_found")
            assessment = self._locked_assessment(scope, record_ref.assessment_id)
            self._locked_child(scope, assessment.child_id)
            self._require_current_capture_consent(scope, assessment.child_id)
            record = self.session.scalar(
                select(TranscriptRevisionRecord)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.transcript_revision_id == command.transcript_revision_id,
                )
                .with_for_update()
            )
            if record is None:
                raise RepositoryError("transcript_not_found")
            current = self.session.scalar(
                select(TranscriptRevisionRecord.transcript_revision_id)
                .where(
                    TranscriptRevisionRecord.organization_id == scope.organization_id,
                    TranscriptRevisionRecord.assessment_id == record.assessment_id,
                )
                .order_by(desc(TranscriptRevisionRecord.revision))
                .limit(1)
            )
            if current != record.transcript_revision_id:
                raise RepositoryError("transcript_not_reviewable")
            if record.review_state != TranscriptReviewState.DRAFT.value:
                raise RepositoryError("transcript_not_reviewable")
            if record.version != command.expected_version:
                raise RepositoryError("stale_transcript_version")
            now = _utc_now()
            record.review_state = TranscriptReviewState.ATTESTED.value
            record.attested_by_user_id = scope.user_id
            record.attested_at = now
            record.version += 1
            record.updated_at = now
            self._append_audit(
                scope,
                "transcript.attested",
                "transcript_revision",
                record.transcript_revision_id,
                correlation_id,
                ["review_state", "attested_at", "version"],
                target_version=record.version,
            )
            self.session.flush()
            return self._transcript_snapshot(record)

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

        if command.idempotency_key.startswith(_SYSTEM_PROCESSING_KEY_PREFIX):
            raise RepositoryError("idempotency_conflict")

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
        if run.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value:
            if run.assessment_id is None:
                return None
            assessment = self._assessment_record(scope, run.assessment_id)
            if assessment is None:
                return None
            self._require_current_capture_consent(scope, assessment.child_id)
            return self._processing_run_snapshot(run)
        context = self._recording_with_assessment(scope, run.recording_id)
        if context is None or context[0].recording_id != run.recording_id:
            return None
        self._require_current_capture_consent(scope, context[1].child_id)
        return self._processing_run_snapshot(run)

    def get_current_evidence_processing_run(
        self, scope: AccessScope, assessment_id: str
    ) -> ProcessingRunSnapshot | None:
        """Return the latest job for the assessment's current transcript revision."""

        assessment = self._assessment_record(scope, assessment_id)
        if assessment is None:
            return None
        self._require_current_capture_consent(scope, assessment.child_id)
        current_transcript_id = self.session.scalar(
            select(TranscriptRevisionRecord.transcript_revision_id)
            .where(
                TranscriptRevisionRecord.organization_id == scope.organization_id,
                TranscriptRevisionRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptRevisionRecord.revision))
            .limit(1)
        )
        if current_transcript_id is None:
            return None
        processing_query = select(ProcessingRunRecord).where(
            ProcessingRunRecord.organization_id == scope.organization_id,
            ProcessingRunRecord.assessment_id == assessment_id,
            ProcessingRunRecord.transcript_revision_id == current_transcript_id,
            ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
            ProcessingRunRecord.pipeline_version == _EVIDENCE_PIPELINE_VERSION,
            ProcessingRunRecord.feature_schema_version == _EVIDENCE_FEATURE_SCHEMA_VERSION,
        )
        current_segment_set = self.session.scalar(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment_id,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
            .limit(1)
        )
        if (
            current_segment_set is None
            or current_segment_set.review_state != TranscriptReviewState.ATTESTED.value
        ):
            return None
        processing_query = processing_query.where(
            ProcessingRunRecord.segment_set_id == current_segment_set.transcript_segment_set_id,
            ProcessingRunRecord.segment_set_sha256 == current_segment_set.segments_sha256,
        )
        run = self.session.scalar(
            processing_query
            .order_by(desc(ProcessingRunRecord.created_at), desc(ProcessingRunRecord.processing_run_id))
            .limit(1)
        )
        return self._processing_run_snapshot(run) if run is not None else None

    def mark_recording_deleted_if_consented(
        self,
        scope: AccessScope,
        recording_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> RecordingSnapshot | None:
        return self._tombstone_recording_if_consented(
            scope, recording_id, correlation_id, expected_version=expected_version
        )

    def expire_recording_upload_if_needed(
        self,
        scope: AccessScope,
        recording_id: str,
        expected_version: int,
        correlation_id: str,
    ) -> RecordingSnapshot | None:
        """Persist expiry when a therapist retries an abandoned upload."""

        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, recording_id, lock=True)
            if context is None:
                return None
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if recording.upload_state not in {
                RecordingUploadState.PENDING.value,
                RecordingUploadState.UPLOADING.value,
            } or not _is_expired(recording.expires_at):
                return self._recording_snapshot(recording)
            if recording.version != expected_version:
                raise RepositoryError("upload_verification_failed")
            recording.upload_state = RecordingUploadState.EXPIRED.value
            recording.version += 1
            recording.updated_at = _utc_now()
            upload_run = self.session.scalar(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == recording_id,
                    ProcessingRunRecord.stage == ProcessingRunStage.UPLOAD_VERIFICATION.value,
                    ProcessingRunRecord.state.in_(
                        (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                    ),
                )
                .with_for_update()
            )
            if upload_run is not None:
                self._mutate_processing_run(
                    upload_run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code="upload_intent_expired",
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(upload_run, "processing_run.cancelled", ["processing_state"])
            self._queue_cleanup_run(self._worker_scope(scope.organization_id), recording)
            self._append_audit(
                scope,
                "recording.upload_expired",
                "recording",
                recording.recording_id,
                correlation_id,
                ["upload_state", "version"],
                target_version=recording.version,
            )
            self.session.flush()
            return self._recording_snapshot(recording)

    def complete_cleanup_for_recording(self, scope: AccessScope, recording_id: str) -> None:
        with self.session.begin_nested():
            cleanup_runs = self.session.scalars(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == recording_id,
                    ProcessingRunRecord.stage == ProcessingRunStage.CLEANUP.value,
                    ProcessingRunRecord.state.in_(
                        (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                    ),
                )
                .with_for_update()
            ).all()
            for cleanup_run in cleanup_runs:
                self._mutate_processing_run(
                    cleanup_run,
                    state=ProcessingRunState.SUCCEEDED.value,
                    error_code=None,
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(cleanup_run, "processing_run.succeeded", ["processing_state"])
            self.session.flush()

    def _tombstone_recording_if_consented(
        self,
        scope: AccessScope,
        recording_id: str,
        correlation_id: str,
        *,
        expected_version: int | None = None,
    ) -> RecordingSnapshot | None:
        with self.session.begin_nested():
            context = self._recording_with_assessment(scope, recording_id, lock=True)
            if context is None:
                return None
            recording, assessment = context
            self._require_current_capture_consent(scope, assessment.child_id)
            if assessment.state == AssessmentState.FINALIZED.value:
                raise RepositoryError("evidence_locked")
            if recording.upload_state == RecordingUploadState.FAILED.value:
                self._queue_cleanup_run(scope, recording)
                return self._recording_snapshot(recording)
            result = self.session.execute(
                update(RecordingRecord)
                .where(
                    RecordingRecord.organization_id == scope.organization_id,
                    RecordingRecord.recording_id == recording_id,
                    *(
                        [RecordingRecord.version == expected_version]
                        if expected_version is not None
                        else []
                    ),
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
            active_runs = self.session.scalars(
                select(ProcessingRunRecord)
                .where(
                    ProcessingRunRecord.organization_id == scope.organization_id,
                    ProcessingRunRecord.recording_id == recording_id,
                    ProcessingRunRecord.state.in_(
                        (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                    ),
                )
                .with_for_update()
            ).all()
            for active_run in active_runs:
                self._mutate_processing_run(
                    active_run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code="recording_deleted",
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(active_run, "processing_run.cancelled", ["processing_state"])
            quality = self.session.scalar(
                select(RecordingQualityResultRecord)
                .where(
                    RecordingQualityResultRecord.organization_id == scope.organization_id,
                    RecordingQualityResultRecord.recording_id == recording_id,
                )
                .with_for_update()
            )
            if quality is not None:
                quality.status = RecordingQualityStatus.UNAVAILABLE.value
                quality.measured_duration_seconds = None
                quality.measured_loudness_db = None
                quality.measured_silence_ratio = None
                quality.measured_decodability = None
                quality.unavailable_checks_json = ["recording_deleted"]
                quality.evaluated_at = _utc_now()
                quality.version += 1
                quality.updated_at = _utc_now()
                self._append_audit(
                    scope,
                    "recording.quality_invalidated",
                    "recording_quality_result",
                    quality.recording_quality_result_id,
                    correlation_id,
                    ["quality_status", "version"],
                    target_version=quality.version,
                )
            if assessment.state in {
                AssessmentState.PROCESSING.value,
                AssessmentState.REVIEW_REQUIRED.value,
                AssessmentState.READY_FOR_CLINICIAN.value,
            }:
                assessment.state = AssessmentState.CAPTURING.value
                assessment.version += 1
                assessment.updated_at = _utc_now()
                self._append_audit(
                    scope,
                    "assessment.evidence_invalidated",
                    "assessment",
                    assessment.assessment_id,
                    correlation_id,
                    ["state", "version"],
                    target_version=assessment.version,
                )
            self._queue_cleanup_run(scope, recording)
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
            if command.server_computed_checksum != recording.declared_checksum:
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
                self._mutate_processing_run(
                    upload_run,
                    state=ProcessingRunState.SUCCEEDED.value,
                    error_code=None,
                    lease_token=None,
                    lease_expires_at=None,
                )
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
                self._mutate_processing_run(
                    existing,
                    state=ProcessingRunState.QUEUED.value,
                    error_code=None,
                    available_at=_utc_now(),
                    lease_token=None,
                    lease_expires_at=None,
                )
            return existing
        now = _utc_now()
        run = ProcessingRunRecord(
            processing_run_id=uuid4().hex,
            organization_id=scope.organization_id,
            recording_id=recording.recording_id,
            stage=ProcessingRunStage.QUALITY_ANALYSIS.value,
            state=ProcessingRunState.QUEUED.value,
            idempotency_key=f"{_SYSTEM_PROCESSING_KEY_PREFIX}quality:{recording.recording_id}",
            attempt_count=0,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def _queue_cleanup_run(
        self, scope: AccessScope, recording: RecordingRecord
    ) -> ProcessingRunRecord:
        existing = self.session.scalar(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                ProcessingRunRecord.recording_id == recording.recording_id,
                ProcessingRunRecord.stage == ProcessingRunStage.CLEANUP.value,
            )
            .with_for_update()
        )
        if existing is not None:
            if existing.state in {
                ProcessingRunState.FAILED.value,
                ProcessingRunState.CANCELLED.value,
            }:
                self._mutate_processing_run(
                    existing,
                    state=ProcessingRunState.QUEUED.value,
                    error_code=None,
                    available_at=_utc_now(),
                    lease_token=None,
                    lease_expires_at=None,
                )
            return existing
        now = _utc_now()
        run = ProcessingRunRecord(
            processing_run_id=uuid4().hex,
            organization_id=scope.organization_id,
            recording_id=recording.recording_id,
            stage=ProcessingRunStage.CLEANUP.value,
            state=ProcessingRunState.QUEUED.value,
            idempotency_key=f"{_SYSTEM_PROCESSING_KEY_PREFIX}cleanup:{recording.recording_id}",
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

    def _mark_evidence_stale_for_assessment(
        self,
        scope: AccessScope,
        assessment_id: str,
        correlation_id: str,
    ) -> None:
        runs = self.session.scalars(
            select(EvidenceRunRecord)
            .where(
                EvidenceRunRecord.organization_id == scope.organization_id,
                EvidenceRunRecord.assessment_id == assessment_id,
                EvidenceRunRecord.state != EvidenceState.STALE.value,
            )
            .with_for_update()
        ).all()
        for run in runs:
            run.state = EvidenceState.STALE.value
            run.version += 1
            run.updated_at = _utc_now()
            self._append_audit(
                scope,
                "evidence.run_staled",
                "evidence_run",
                run.evidence_run_id,
                correlation_id,
                ["state", "version"],
                target_version=run.version,
            )

    def _supersede_segment_sets_for_assessment(
        self,
        scope: AccessScope,
        assessment_id: str,
        correlation_id: str,
    ) -> None:
        records = self.session.scalars(
            select(TranscriptSegmentSetRecord)
            .where(
                TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                TranscriptSegmentSetRecord.assessment_id == assessment_id,
                TranscriptSegmentSetRecord.review_state != TranscriptReviewState.SUPERSEDED.value,
            )
            .order_by(desc(TranscriptSegmentSetRecord.revision))
            .with_for_update()
        ).all()
        for record in records:
            record.review_state = TranscriptReviewState.SUPERSEDED.value
            record.version += 1
            record.updated_at = self._now()
            self._append_audit(
                scope,
                "transcript.segment_set_superseded",
                "transcript_segment_set",
                record.transcript_segment_set_id,
                correlation_id,
                ["review_state", "version"],
                target_version=record.version,
            )

    def _persist_adapted_evidence(
        self,
        scope: AccessScope,
        assessment_id: str,
        transcript: TranscriptRevisionRecord,
        selection: AssessmentProtocolSelectionRecord,
        adapted: AdaptedEvidence,
        correlation_id: str,
        *,
        segment_set_id: str | None = None,
        segment_set_sha256: str | None = None,
    ) -> EvidenceRunSnapshot:
        provenance = adapted.provenance
        if provenance is None:
            raise RepositoryError("evidence_provenance_required")
        if transcript.assessment_id != assessment_id:
            raise RepositoryError("transcript_not_found")
        if selection.assessment_id != assessment_id:
            raise RepositoryError("evidence_protocol_mismatch")
        if selection.protocol_version_key != provenance.protocol_version_key:
            raise RepositoryError("evidence_protocol_mismatch")
        if transcript.content_sha256 != provenance.input_sha256:
            raise RepositoryError("stale_evidence_input")
        if (segment_set_id is None) != (segment_set_sha256 is None):
            raise RepositoryError("evidence_segment_provenance_mismatch")
        if segment_set_id is not None:
            segment_set = self.session.scalar(
                select(TranscriptSegmentSetRecord)
                .where(
                    TranscriptSegmentSetRecord.organization_id == scope.organization_id,
                    TranscriptSegmentSetRecord.transcript_segment_set_id == segment_set_id,
                )
                .with_for_update()
            )
            if segment_set is None:
                raise RepositoryError("stale_segment_set_input")
            try:
                self._transcript_segment_set_snapshot(segment_set)
            except RepositoryError as error:
                raise RepositoryError("stale_segment_set_input") from error
            if (
                segment_set.assessment_id != assessment_id
                or segment_set.transcript_revision_id != transcript.transcript_revision_id
                or segment_set.transcript_content_sha256 != transcript.content_sha256
                or segment_set.review_state != TranscriptReviewState.ATTESTED.value
                or segment_set.segments_sha256 != segment_set_sha256
            ):
                raise RepositoryError("stale_segment_set_input")
        if any(feature.provenance != provenance for feature in adapted.features):
            raise RepositoryError("evidence_provenance_mismatch")
        if adapted.state is EvidenceState.COMPLETED and not adapted.features:
            raise RepositoryError("evidence_no_measurements")

        existing = self.session.scalar(
            select(EvidenceRunRecord)
            .where(
                EvidenceRunRecord.organization_id == scope.organization_id,
                EvidenceRunRecord.assessment_id == assessment_id,
                EvidenceRunRecord.transcript_revision_id == transcript.transcript_revision_id,
                EvidenceRunRecord.pipeline_version == provenance.pipeline_version,
                EvidenceRunRecord.feature_schema_version == provenance.feature_schema_version,
            )
            .where(
                or_(
                    segment_set_id is None,
                    EvidenceRunRecord.segment_set_id == segment_set_id,
                ),
                or_(
                    segment_set_sha256 is None,
                    EvidenceRunRecord.segment_set_sha256 == segment_set_sha256,
                ),
            )
            .with_for_update()
        )
        if existing is not None:
            return self._evidence_snapshot(existing)

        generated_at = _as_utc(provenance.analyzed_at)
        profile = build_developmental_profile(
            assessment_id=assessment_id,
            features=adapted.features,
            generated_at=generated_at,
        )
        profile = replace(
            profile,
            state=adapted.state,
            limitations=_merge_texts(profile.limitations, adapted.limitations),
        )
        now = self._now()
        run = EvidenceRunRecord(
            evidence_run_id=uuid4().hex,
            organization_id=scope.organization_id,
            assessment_id=assessment_id,
            transcript_revision_id=transcript.transcript_revision_id,
            segment_set_id=segment_set_id,
            segment_set_sha256=segment_set_sha256,
            state=adapted.state.value,
            input_ref=provenance.input_ref,
            input_sha256=provenance.input_sha256,
            protocol_version_key=provenance.protocol_version_key,
            extractor=provenance.extractor,
            pipeline_version=provenance.pipeline_version,
            feature_schema_version=provenance.feature_schema_version,
            limitations_json=list(profile.limitations),
            generated_at=generated_at,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.session.add(run)
        self.session.flush()
        self.session.add_all(
            EvidenceFeatureRecord(
                evidence_feature_id=uuid4().hex,
                organization_id=scope.organization_id,
                evidence_run_id=run.evidence_run_id,
                feature_key=feature.key,
                value_json=feature.value,
                unit=feature.unit,
                source=feature.source.value,
                state=feature.state.value,
                limitation=feature.limitation,
                version=1,
                created_at=now,
                updated_at=now,
            )
            for feature in profile.features
        )
        self.session.add_all(
            EvidenceDomainProfileRecord(
                domain_profile_id=uuid4().hex,
                organization_id=scope.organization_id,
                evidence_run_id=run.evidence_run_id,
                domain=domain.domain.value,
                status=domain.status.value,
                summary=domain.summary,
                feature_keys_json=list(domain.feature_keys),
                supporting_features_json=list(domain.supporting_features),
                conflicting_features_json=list(domain.conflicting_features),
                limitations_json=list(domain.limitations),
                version=1,
                created_at=now,
                updated_at=now,
            )
            for domain in profile.domains
        )
        self._append_audit(
            scope,
            "evidence.run_created",
            "evidence_run",
            run.evidence_run_id,
            correlation_id,
            ["state", "version"],
            target_version=run.version,
        )
        self.session.flush()
        return self._evidence_snapshot(run)

    def _audit_worker_or_scope_run(
        self,
        scope: AccessScope,
        run: ProcessingRunRecord,
        action: str,
        changed_fields: list[str],
        *,
        correlation_id: str,
    ) -> None:
        self._append_audit(
            scope,
            action,
            "processing_run",
            run.processing_run_id,
            correlation_id,
            changed_fields,
            target_version=run.version,
        )

    def _mutate_processing_run(
        self,
        run: ProcessingRunRecord,
        *,
        now: datetime | None = None,
        **values: object,
    ) -> None:
        changed_at = _as_utc(now or self._now())
        for name, value in values.items():
            setattr(run, name, value)
        run.version = (run.version or 1) + 1
        run.updated_at = changed_at

    def _processing_run_is_claimable(
        self,
        run: ProcessingRunRecord,
        now: datetime,
    ) -> bool:
        if run.state == ProcessingRunState.QUEUED.value:
            return _as_utc(run.available_at) <= now
        return (
            run.state == ProcessingRunState.RUNNING.value
            and run.lease_expires_at is not None
            and _as_utc(run.lease_expires_at) <= now
        )

    def _cancel_worker_evidence_run(self, run: ProcessingRunRecord, error_code: str) -> None:
        now = self._now()
        self._mutate_processing_run(
            run,
            state=ProcessingRunState.CANCELLED.value,
            error_code=error_code,
            lease_token=None,
            lease_expires_at=None,
            now=now,
        )
        self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])

    def _cancel_evidence_runs_for_assessment(
        self,
        scope: AccessScope,
        assessment_id: str,
        error_code: str,
        correlation_id: str,
        *,
        keep_transcript_revision_id: str | None = None,
        keep_segment_set_id: str | None = None,
        keep_segment_set_sha256: str | None = None,
        keep_pipeline_version: str | None = None,
        keep_feature_schema_version: str | None = None,
    ) -> None:
        runs = self.session.scalars(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                ProcessingRunRecord.assessment_id == assessment_id,
                ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                ProcessingRunRecord.state.in_(
                    (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                ),
            )
            .with_for_update()
        ).all()
        for run in runs:
            if (
                keep_transcript_revision_id is not None
                and run.transcript_revision_id == keep_transcript_revision_id
                and run.segment_set_id == keep_segment_set_id
                and run.segment_set_sha256 == keep_segment_set_sha256
                and run.pipeline_version == keep_pipeline_version
                and run.feature_schema_version == keep_feature_schema_version
            ):
                continue
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.CANCELLED.value,
                error_code=error_code,
                lease_token=None,
                lease_expires_at=None,
                now=self._now(),
            )
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.cancelled",
                ["processing_state"],
                correlation_id=correlation_id,
            )

    def _cancel_segment_bound_evidence_jobs(
        self,
        scope: AccessScope,
        assessment_id: str,
        current_segment_set_id: str,
        correlation_id: str,
    ) -> None:
        runs = self.session.scalars(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                ProcessingRunRecord.assessment_id == assessment_id,
                ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                ProcessingRunRecord.segment_set_id.is_not(None),
                ProcessingRunRecord.segment_set_id != current_segment_set_id,
                ProcessingRunRecord.state.in_(
                    (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                ),
            )
            .with_for_update()
        ).all()
        for run in runs:
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.CANCELLED.value,
                error_code="segment_set_superseded",
                lease_token=None,
                lease_expires_at=None,
                now=self._now(),
            )
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.cancelled",
                ["processing_state"],
                correlation_id=correlation_id,
            )

    def _mark_segment_bound_evidence_stale_for_assessment(
        self,
        scope: AccessScope,
        assessment_id: str,
        current_segment_set_id: str,
        correlation_id: str,
    ) -> None:
        runs = self.session.scalars(
            select(EvidenceRunRecord)
            .where(
                EvidenceRunRecord.organization_id == scope.organization_id,
                EvidenceRunRecord.assessment_id == assessment_id,
                EvidenceRunRecord.segment_set_id.is_not(None),
                EvidenceRunRecord.segment_set_id != current_segment_set_id,
                EvidenceRunRecord.state != EvidenceState.STALE.value,
            )
            .with_for_update()
        ).all()
        for run in runs:
            run.state = EvidenceState.STALE.value
            run.version += 1
            run.updated_at = self._now()
            self._append_audit(
                scope,
                "evidence.run_staled",
                "evidence_run",
                run.evidence_run_id,
                correlation_id,
                ["state", "version"],
                target_version=run.version,
            )

    def _cancel_evidence_runs_for_child(
        self,
        scope: AccessScope,
        child_id: str,
        error_code: str,
        correlation_id: str,
    ) -> None:
        runs = self.session.scalars(
            select(ProcessingRunRecord)
            .join(
                AssessmentRecord,
                and_(
                    AssessmentRecord.organization_id == ProcessingRunRecord.organization_id,
                    AssessmentRecord.assessment_id == ProcessingRunRecord.assessment_id,
                ),
            )
            .where(
                ProcessingRunRecord.organization_id == scope.organization_id,
                AssessmentRecord.child_id == child_id,
                ProcessingRunRecord.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value,
                ProcessingRunRecord.state.in_(
                    (ProcessingRunState.QUEUED.value, ProcessingRunState.RUNNING.value)
                ),
            )
            .with_for_update()
        ).all()
        for run in runs:
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.CANCELLED.value,
                error_code=error_code,
                lease_token=None,
                lease_expires_at=None,
                now=self._now(),
            )
            self._audit_worker_or_scope_run(
                scope,
                run,
                "processing_run.cancelled",
                ["processing_state"],
                correlation_id=correlation_id,
            )

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
        return self.active_membership_role(scope) is not None

    def active_membership_role(self, scope: AccessScope) -> str | None:
        """Return the persisted role for the active tenant membership.

        JWT role claims are an authentication hint, not the authorization
        source of truth. Callers must use this value for the request scope so
        a stale privileged claim cannot widen care-team access.
        """

        return self.session.scalar(
            select(OrganizationMembershipRecord.role)
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

    def has_active_membership(self, scope: AccessScope) -> bool:
        """Return the persisted membership state for an authenticated scope."""

        return self._has_active_membership(scope)

    def claim_next_processing_run(self):
        """Claim one durable capture run for the background worker.

        This method intentionally returns an opaque work item rather than a
        therapist-facing snapshot. Consent is checked again at claim time;
        cleanup is the sole stage allowed to continue after withdrawal.
        """

        from app.assessment_v2.worker import CaptureWorkItem

        latest_consent_status = (
            select(ConsentRecord.status)
            .where(
                ConsentRecord.organization_id == AssessmentRecord.organization_id,
                ConsentRecord.child_id == AssessmentRecord.child_id,
                ConsentRecord.purpose == ConsentPurpose.CLINICAL_ASSESSMENT.value,
            )
            .order_by(desc(ConsentRecord.version))
            .limit(1)
            .scalar_subquery()
        )
        for _ in range(100):
            with self.session.begin_nested():
                now = _utc_now()
                capture_query = (
                    select(ProcessingRunRecord)
                    .join(
                        RecordingRecord,
                        and_(
                            RecordingRecord.organization_id == ProcessingRunRecord.organization_id,
                            RecordingRecord.recording_id == ProcessingRunRecord.recording_id,
                        ),
                    )
                    .join(
                        AssessmentRecord,
                        and_(
                            AssessmentRecord.organization_id == RecordingRecord.organization_id,
                            AssessmentRecord.assessment_id == RecordingRecord.assessment_id,
                        ),
                    )
                    .where(
                        or_(
                            and_(
                                ProcessingRunRecord.state == ProcessingRunState.QUEUED.value,
                                ProcessingRunRecord.available_at <= now,
                            ),
                            and_(
                                ProcessingRunRecord.state == ProcessingRunState.RUNNING.value,
                                ProcessingRunRecord.lease_expires_at.is_not(None),
                                ProcessingRunRecord.lease_expires_at <= now,
                            ),
                        ),
                        or_(
                            ProcessingRunRecord.stage != ProcessingRunStage.UPLOAD_VERIFICATION.value,
                            and_(
                                ProcessingRunRecord.stage == ProcessingRunStage.UPLOAD_VERIFICATION.value,
                                or_(
                                    RecordingRecord.upload_state == RecordingUploadState.UPLOADED.value,
                                    RecordingRecord.expires_at <= now,
                                ),
                            ),
                            latest_consent_status.is_(None),
                            latest_consent_status != ConsentStatus.ACTIVE.value,
                        ),
                    )
                )
                if self._worker_organization_id is not None:
                    capture_query = capture_query.where(
                        ProcessingRunRecord.organization_id == self._worker_organization_id
                    )
                run = self.session.scalar(
                    capture_query.order_by(
                        ProcessingRunRecord.available_at,
                        ProcessingRunRecord.created_at,
                    ).with_for_update(skip_locked=True).limit(1)
                )
                if run is None:
                    return None
                context = self._worker_recording_context(run.organization_id, run.recording_id)
                if context is None:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="recording_not_found",
                        lease_token=None,
                        lease_expires_at=None,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue
                recording, assessment = context
                stage = ProcessingRunStage(run.stage)
                if (
                    stage is ProcessingRunStage.UPLOAD_VERIFICATION
                    and recording.upload_state
                    in {
                        RecordingUploadState.PENDING.value,
                        RecordingUploadState.UPLOADING.value,
                    }
                    and _is_expired(recording.expires_at)
                ):
                    recording.upload_state = RecordingUploadState.EXPIRED.value
                    recording.version += 1
                    recording.updated_at = _utc_now()
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="upload_intent_expired",
                        lease_token=None,
                        lease_expires_at=None,
                    )
                    self._queue_cleanup_run(self._worker_scope(run.organization_id), recording)
                    self._append_audit(
                        self._worker_scope(run.organization_id),
                        "recording.upload_expired",
                        "recording",
                        recording.recording_id,
                        f"worker:{run.processing_run_id}",
                        ["upload_state", "version"],
                        target_version=recording.version,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    self.session.flush()
                    continue
                if stage is not ProcessingRunStage.CLEANUP and not self._has_current_capture_consent(
                    run.organization_id, assessment.child_id
                ):
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.CANCELLED.value,
                        error_code="consent_revoked",
                        lease_token=None,
                        lease_expires_at=None,
                    )
                    self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                    continue
                if run.attempt_count >= run.max_attempts:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="retry_limit_exceeded",
                        lease_token=None,
                        lease_expires_at=None,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue
                activity = None
                if stage is not ProcessingRunStage.CLEANUP:
                    activity = self.session.scalar(
                        select(ProtocolActivityRecord).where(
                            ProtocolActivityRecord.protocol_version_key
                            == recording.protocol_version_key,
                            ProtocolActivityRecord.activity_key == recording.activity_key,
                        )
                    )
                    if activity is None:
                        self._mutate_processing_run(
                            run,
                            state=ProcessingRunState.FAILED.value,
                            error_code="recording_activity_invalid",
                            lease_token=None,
                            lease_expires_at=None,
                        )
                        self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                        continue
                if stage is ProcessingRunStage.QUALITY_ANALYSIS and recording.upload_state != RecordingUploadState.VERIFIED.value:
                    self._mutate_processing_run(
                        run,
                        state=ProcessingRunState.FAILED.value,
                        error_code="recording_not_verified",
                        lease_token=None,
                        lease_expires_at=None,
                    )
                    self._audit_worker_run(run, "processing_run.failed", ["processing_state"])
                    continue
                lease_token = uuid4().hex
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.RUNNING.value,
                    attempt_count=run.attempt_count + 1,
                    lease_token=lease_token,
                    lease_expires_at=now + _CAPTURE_LEASE_DURATION,
                    available_at=now,
                    cancel_requested_at=None,
                )
                self._audit_worker_run(run, "processing_run.claimed", ["processing_state"])
                self.session.flush()
                return CaptureWorkItem(
                    run_id=run.processing_run_id,
                    organization_id=run.organization_id,
                    recording_id=recording.recording_id,
                    stage=stage,
                    object_key=recording.object_key,
                    declared_checksum=recording.declared_checksum,
                    declared_content_type=recording.declared_content_type,
                    declared_size_bytes=recording.declared_size_bytes,
                    minimum_duration_seconds=(activity.minimum_duration_seconds if activity else 0),
                    target_duration_seconds=(activity.target_duration_seconds if activity else 0),
                    lease_token=lease_token,
                )
        return None

    def verify_recording_upload_worker(self, item, checksum: str) -> bool:
        with self.session.begin_nested():
            run = self._worker_run(item)
            context = self._worker_recording_context(item.organization_id, item.recording_id)
            if run is None:
                return False
            if context is None:
                raise RepositoryError("recording_not_found")
            recording, assessment = context
            if not self._has_current_capture_consent(item.organization_id, assessment.child_id):
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code="consent_revoked",
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                self.session.flush()
                return False
            if recording.upload_state == RecordingUploadState.VERIFIED.value:
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.SUCCEEDED.value,
                    error_code=None,
                    lease_token=None,
                    lease_expires_at=None,
                    completed_at=_utc_now(),
                )
                self._audit_worker_run(run, "processing_run.succeeded", ["processing_state"])
                return True
            if (
                run.stage != ProcessingRunStage.UPLOAD_VERIFICATION.value
                or run.state != ProcessingRunState.RUNNING.value
                or recording.upload_state != RecordingUploadState.UPLOADED.value
                or checksum != recording.declared_checksum
            ):
                self._append_audit(
                    self._worker_scope(item.organization_id),
                    "processing_run.verification_rejected",
                    "processing_run",
                    run.processing_run_id,
                    self._worker_correlation(run.processing_run_id),
                    [],
                    outcome="failure",
                )
                raise RepositoryError("upload_verification_failed")
            recording.upload_state = RecordingUploadState.VERIFIED.value
            recording.verified_content_type = recording.declared_content_type
            recording.verified_size_bytes = recording.declared_size_bytes
            recording.verified_checksum = checksum
            recording.verified_at = _utc_now()
            recording.version += 1
            recording.updated_at = _utc_now()
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.SUCCEEDED.value,
                error_code=None,
                lease_token=None,
                lease_expires_at=None,
                completed_at=_utc_now(),
            )
            quality_run = self._queue_quality_run(self._worker_scope(item.organization_id), recording)
            self._append_audit(
                self._worker_scope(item.organization_id),
                "recording.upload_verified",
                "recording",
                recording.recording_id,
                self._worker_correlation(run.processing_run_id),
                ["upload_state", "verified_at", "version"],
                target_version=recording.version,
            )
            self._audit_worker_run(run, "processing_run.succeeded", ["processing_state"])
            self._audit_worker_run(quality_run, "processing_run.queued", ["processing_state"])
            self.session.flush()
            return True

    def persist_quality_result(self, item, quality, decision) -> bool:
        with self.session.begin_nested():
            run = self._worker_run(item)
            context = self._worker_recording_context(item.organization_id, item.recording_id)
            if run is None:
                return False
            if context is None:
                raise RepositoryError("recording_not_found")
            recording, assessment = context
            if not self._has_current_capture_consent(item.organization_id, assessment.child_id):
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code="consent_revoked",
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                self.session.flush()
                return False
            if run.stage != ProcessingRunStage.QUALITY_ANALYSIS.value or run.state != ProcessingRunState.RUNNING.value:
                raise RepositoryError("processing_run_not_found")
            if recording.upload_state != RecordingUploadState.VERIFIED.value:
                self._mutate_processing_run(
                    run,
                    state=ProcessingRunState.CANCELLED.value,
                    error_code="recording_not_verified",
                    lease_token=None,
                    lease_expires_at=None,
                )
                self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
                self.session.flush()
                return False
            existing = self.session.scalar(
                select(RecordingQualityResultRecord).where(
                    RecordingQualityResultRecord.organization_id == item.organization_id,
                    RecordingQualityResultRecord.recording_id == item.recording_id,
                )
            )
            values = {
                "status": decision.status,
                "measured_duration_seconds": quality.duration_seconds,
                "measured_loudness_db": quality.loudness_db,
                "measured_silence_ratio": quality.silence_ratio,
                "measured_decodability": quality.decodability,
                "unavailable_checks_json": list(decision.unavailable_checks),
                "provenance": "capture-quality-v1",
                "evaluated_at": _utc_now(),
                "updated_at": _utc_now(),
            }
            if existing is None:
                quality_record = RecordingQualityResultRecord(
                    recording_quality_result_id=uuid4().hex,
                    organization_id=item.organization_id,
                    recording_id=item.recording_id,
                    version=1,
                    created_at=_utc_now(),
                    **values,
                )
                self.session.add(quality_record)
            else:
                quality_record = existing
                for name, value in values.items():
                    setattr(existing, name, value)
                existing.version += 1
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.SUCCEEDED.value,
                error_code=None,
                lease_token=None,
                lease_expires_at=None,
                completed_at=_utc_now(),
            )
            self._append_audit(
                self._worker_scope(item.organization_id),
                "recording.quality_recorded",
                "recording_quality_result",
                quality_record.recording_quality_result_id,
                self._worker_correlation(run.processing_run_id),
                ["quality_status", "version"],
                target_version=quality_record.version,
            )
            self._audit_worker_run(run, "processing_run.succeeded", ["processing_state"])
            self.session.flush()
            return True

    def complete_cleanup(self, item) -> None:
        with self.session.begin_nested():
            run = self._worker_run(item)
            if run is None:
                return
            if run.stage != ProcessingRunStage.CLEANUP.value:
                raise RepositoryError("processing_run_not_found")
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.SUCCEEDED.value,
                error_code=None,
                lease_token=None,
                lease_expires_at=None,
                completed_at=_utc_now(),
            )
            self._audit_worker_run(run, "processing_run.succeeded", ["processing_state"])
            self.session.flush()

    def fail_processing_run(self, item, error_code: str) -> None:
        with self.session.begin_nested():
            run = self._worker_run(item)
            if run is None or run.state != ProcessingRunState.RUNNING.value:
                return
            now = _utc_now()
            self._mutate_processing_run(
                run,
                error_code=error_code,
                state=(
                    ProcessingRunState.FAILED.value
                    if run.attempt_count >= run.max_attempts
                    else ProcessingRunState.QUEUED.value
                ),
                available_at=now,
                lease_token=None,
                lease_expires_at=None,
                now=now,
            )
            self._audit_worker_run(
                run,
                "processing_run.failed" if run.state == ProcessingRunState.FAILED.value else "processing_run.retry_scheduled",
                ["processing_state"],
            )
            self.session.flush()

    def cancel_processing_run(self, item, error_code: str) -> None:
        with self.session.begin_nested():
            run = self._worker_run(item)
            if run is None:
                return
            self._mutate_processing_run(
                run,
                state=ProcessingRunState.CANCELLED.value,
                error_code=error_code,
                lease_token=None,
                lease_expires_at=None,
                now=_utc_now(),
            )
            self._audit_worker_run(run, "processing_run.cancelled", ["processing_state"])
            self.session.flush()

    def _worker_run(
        self, item, *, check_lease_expiry: bool = True
    ) -> ProcessingRunRecord | None:
        run = self.session.scalar(
            select(ProcessingRunRecord)
            .where(
                ProcessingRunRecord.organization_id == item.organization_id,
                ProcessingRunRecord.processing_run_id == item.run_id,
            )
            .with_for_update()
        )
        lease_token = getattr(item, "lease_token", None)
        if (
            run is None
            or not lease_token
            or run.state != ProcessingRunState.RUNNING.value
            or run.lease_token != lease_token
            or run.lease_expires_at is None
            or (
                check_lease_expiry
                and _is_expired(run.lease_expires_at, self._now())
            )
        ):
            return None
        return run

    def _worker_recording_context(
        self, organization_id: str, recording_id: str
    ) -> tuple[RecordingRecord, AssessmentRecord] | None:
        return self.session.execute(
            select(RecordingRecord, AssessmentRecord)
            .join(
                AssessmentRecord,
                and_(
                    AssessmentRecord.organization_id == RecordingRecord.organization_id,
                    AssessmentRecord.assessment_id == RecordingRecord.assessment_id,
                ),
            )
            .where(
                RecordingRecord.organization_id == organization_id,
                RecordingRecord.recording_id == recording_id,
            )
        ).one_or_none()

    def _has_current_capture_consent(self, organization_id: str, child_id: str) -> bool:
        latest = self.session.scalar(
            select(ConsentRecord)
            .where(
                ConsentRecord.organization_id == organization_id,
                ConsentRecord.child_id == child_id,
                ConsentRecord.purpose == ConsentPurpose.CLINICAL_ASSESSMENT.value,
            )
            .order_by(desc(ConsentRecord.version))
            .limit(1)
        )
        return latest is not None and latest.status == ConsentStatus.ACTIVE.value

    def _require_active_membership(self, scope: AccessScope) -> None:
        if not self._has_active_membership(scope):
            raise RepositoryError("inactive_membership")

    def _require_segment_editor_role(self, scope: AccessScope) -> None:
        membership = self.session.scalar(
            select(OrganizationMembershipRecord)
            .where(
                OrganizationMembershipRecord.organization_id == scope.organization_id,
                OrganizationMembershipRecord.user_id == scope.user_id,
            )
            .with_for_update()
        )
        if membership is None or not membership.active:
            raise RepositoryError("inactive_membership")
        if membership.role not in _SEGMENT_EDITOR_MEMBERSHIP_ROLES:
            raise RepositoryError("segment_role_not_permitted")

    def _require_segment_editor_assignment(self, scope: AccessScope, child_id: str) -> None:
        assignment = self.session.scalar(
            select(CareTeamAssignmentRecord.assignment_id)
            .where(
                CareTeamAssignmentRecord.organization_id == scope.organization_id,
                CareTeamAssignmentRecord.child_id == child_id,
                CareTeamAssignmentRecord.user_id == scope.user_id,
                CareTeamAssignmentRecord.active.is_(True),
                CareTeamAssignmentRecord.role.in_(_SEGMENT_EDITOR_ASSIGNMENT_ROLES),
            )
            .with_for_update()
        )
        if assignment is None:
            raise RepositoryError("segment_role_not_permitted")

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
        outcome: str = "success",
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
                outcome=outcome,
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
            created_at=assessment.created_at,
        )

    @staticmethod
    def _transcript_snapshot(record: TranscriptRevisionRecord) -> TranscriptRevisionSnapshot:
        return TranscriptRevisionSnapshot(
            id=record.transcript_revision_id,
            organization_id=record.organization_id,
            assessment_id=record.assessment_id,
            revision=record.revision,
            source=TranscriptSource(record.source),
            review_state=TranscriptReviewState(record.review_state),
            content=record.content,
            content_sha256=record.content_sha256,
            created_by_user_id=record.created_by_user_id,
            created_at=record.created_at,
            attested_by_user_id=record.attested_by_user_id,
            attested_at=record.attested_at,
            version=record.version,
        )

    def _transcript_segment_set_snapshot(
        self,
        record: TranscriptSegmentSetRecord | None,
    ) -> TranscriptSegmentSetSnapshot:
        if record is None:
            raise RepositoryError("segment_set_not_found")
        segment_records = self.session.scalars(
            select(TranscriptSegmentRecord)
            .where(
                TranscriptSegmentRecord.organization_id == record.organization_id,
                TranscriptSegmentRecord.transcript_segment_set_id
                == record.transcript_segment_set_id,
            )
            .order_by(TranscriptSegmentRecord.ordinal)
        ).all()
        snapshots = tuple(self._transcript_segment_snapshot(segment) for segment in segment_records)
        try:
            canonical = canonicalize_transcript_segments(
                (segment.to_segment() for segment in snapshots),
                client_checksum=record.segments_sha256,
            )
        except ValueError as error:
            raise RepositoryError("segment_set_integrity_error") from error
        return TranscriptSegmentSetSnapshot(
            id=record.transcript_segment_set_id,
            organization_id=record.organization_id,
            assessment_id=record.assessment_id,
            transcript_revision_id=record.transcript_revision_id,
            transcript_content_sha256=record.transcript_content_sha256,
            recording_id=record.recording_id,
            revision=record.revision,
            source=TranscriptSource(record.source),
            review_state=TranscriptReviewState(record.review_state),
            segments_sha256=record.segments_sha256,
            segments=snapshots,
            created_by_user_id=record.created_by_user_id,
            created_at=record.created_at,
            attested_by_user_id=record.attested_by_user_id,
            attested_at=record.attested_at,
            version=record.version,
        )

    @staticmethod
    def _transcript_segment_snapshot(
        record: TranscriptSegmentRecord,
    ) -> TranscriptSegmentSnapshot:
        return TranscriptSegmentSnapshot(
            id=record.transcript_segment_id,
            organization_id=record.organization_id,
            segment_set_id=record.transcript_segment_set_id,
            ordinal=record.ordinal,
            start_ms=record.start_ms,
            end_ms=record.end_ms,
            speaker_role=TranscriptSegmentSpeakerRole(record.speaker_role),
            text=record.text,
            confidence=record.confidence,
            uncertainty_reason=TranscriptSegmentUncertaintyReason(record.uncertainty_reason),
            created_at=record.created_at,
        )

    def _evidence_snapshot(self, run: EvidenceRunRecord) -> EvidenceRunSnapshot:
        provenance = EvidenceProvenance(
            input_ref=run.input_ref,
            input_sha256=run.input_sha256,
            protocol_version_key=run.protocol_version_key,
            extractor=run.extractor,
            pipeline_version=run.pipeline_version,
            feature_schema_version=run.feature_schema_version,
            analyzed_at=_as_utc(run.generated_at),
        )
        feature_records = self.session.scalars(
            select(EvidenceFeatureRecord)
            .where(
                EvidenceFeatureRecord.organization_id == run.organization_id,
                EvidenceFeatureRecord.evidence_run_id == run.evidence_run_id,
            )
            .order_by(EvidenceFeatureRecord.feature_key)
        ).all()
        features = tuple(
            MeasuredFeature(
                key=record.feature_key,
                value=record.value_json,
                unit=record.unit,
                source=EvidenceSource(record.source),
                state=EvidenceState(record.state),
                limitation=record.limitation,
                provenance=provenance,
            )
            for record in feature_records
        )
        domain_records = self.session.scalars(
            select(EvidenceDomainProfileRecord)
            .where(
                EvidenceDomainProfileRecord.organization_id == run.organization_id,
                EvidenceDomainProfileRecord.evidence_run_id == run.evidence_run_id,
            )
        ).all()
        domain_order = {domain.value: index for index, domain in enumerate(DevelopmentalDomain)}
        domains = tuple(
            DomainProfile(
                domain=DevelopmentalDomain(record.domain),
                status=DomainProfileStatus(record.status),
                summary=record.summary,
                feature_keys=tuple(_string_values(record.feature_keys_json)),
                supporting_features=tuple(_string_values(record.supporting_features_json)),
                conflicting_features=tuple(_string_values(record.conflicting_features_json)),
                limitations=tuple(_string_values(record.limitations_json)),
            )
            for record in sorted(
                domain_records,
                key=lambda value: domain_order.get(value.domain, len(domain_order)),
            )
        )
        state = EvidenceState(run.state)
        limitations = tuple(_string_values(run.limitations_json))
        if state is EvidenceState.STALE:
            limitations = _merge_texts(
                limitations,
                ("Derived evidence is stale because its reviewed input changed.",),
            )
        profile = DevelopmentalEvidenceProfile(
            assessment_id=run.assessment_id,
            state=state,
            generated_at=_as_utc(run.generated_at),
            features=features,
            domains=domains,
            limitations=limitations,
        )
        return EvidenceRunSnapshot(
            id=run.evidence_run_id,
            organization_id=run.organization_id,
            assessment_id=run.assessment_id,
            transcript_revision_id=run.transcript_revision_id,
            state=state,
            provenance=provenance,
            profile=profile,
            version=run.version,
            segment_set_id=run.segment_set_id,
            segment_set_sha256=run.segment_set_sha256,
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
        evidence_stage = run.stage == ProcessingRunStage.EVIDENCE_EXTRACTION.value
        can_retry = evidence_stage and (
            run.state == ProcessingRunState.FAILED.value
            or (
                run.state == ProcessingRunState.CANCELLED.value
                and run.error_code == _EVIDENCE_USER_CANCEL_CODE
            )
        )
        can_cancel = evidence_stage and run.state in {
            ProcessingRunState.QUEUED.value,
            ProcessingRunState.RUNNING.value,
        } and run.error_code != _EVIDENCE_USER_CANCEL_CODE
        return ProcessingRunSnapshot(
            id=run.processing_run_id,
            organization_id=run.organization_id,
            recording_id=run.recording_id,
            assessment_id=run.assessment_id,
            transcript_revision_id=run.transcript_revision_id,
            segment_set_id=run.segment_set_id,
            segment_set_sha256=run.segment_set_sha256,
            stage=ProcessingRunStage(run.stage),
            state=ProcessingRunState(run.state),
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            available_at=_as_utc(run.available_at),
            error_code=run.error_code,
            result_available=(evidence_stage and run.evidence_run_id is not None),
            can_retry=can_retry,
            can_cancel=can_cancel,
            version=run.version,
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
