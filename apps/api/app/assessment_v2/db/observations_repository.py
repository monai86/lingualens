"""Repository for managing assessment v2 observations and instrument administrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session


def _ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

from app.assessment_v2.db.models import (
    AssessmentInstrumentItemRecord,
    AssessmentInstrumentRecord,
    AssessmentObservationRecord,
    AssessmentRecord,
    CareTeamAssignmentRecord,
    OrganizationMembershipRecord,
)
from app.assessment_v2.domain.instruments import (
    InstrumentAdministration,
    InstrumentItemResponse,
    InstrumentRespondentType,
)
from app.assessment_v2.domain.observations import (
    ObservationCategory,
    ObservationRecordValue,
    ObservationSource,
)


class ObservationsRepository:
    """Handles tenant-safe storage, validation, and retrieval of observations and instruments."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _assert_editor_permission(
        self,
        *,
        organization_id: str,
        assessment_id: str,
        actor_user_id: str,
    ) -> AssessmentRecord:
        """Enforce organization membership and editor care-team assignment."""
        # Check active membership
        membership = self._session.scalar(
            select(OrganizationMembershipRecord).where(
                OrganizationMembershipRecord.organization_id == organization_id,
                OrganizationMembershipRecord.user_id == actor_user_id,
                OrganizationMembershipRecord.active.is_(True),
            )
        )
        if membership is None:
            raise PermissionError(f"User {actor_user_id} is not an active member of {organization_id}")

        # Check assessment exists
        assessment = self._session.scalar(
            select(AssessmentRecord).where(
                AssessmentRecord.organization_id == organization_id,
                AssessmentRecord.assessment_id == assessment_id,
            )
        )
        if assessment is None:
            raise ValueError(f"Assessment {assessment_id} not found in organization {organization_id}")

        # Check care team role
        care_team = self._session.scalar(
            select(CareTeamAssignmentRecord).where(
                CareTeamAssignmentRecord.organization_id == organization_id,
                CareTeamAssignmentRecord.child_id == assessment.child_id,
                CareTeamAssignmentRecord.user_id == actor_user_id,
                CareTeamAssignmentRecord.active.is_(True),
            )
        )
        if care_team is None or care_team.role not in {"assigned_clinician", "supervisor"}:
            raise PermissionError(
                f"User {actor_user_id} lacks editor-capable care-team role for child {assessment.child_id}"
            )

        return assessment

    def create_observation(
        self,
        observation: ObservationRecordValue,
        *,
        actor_user_id: str,
    ) -> ObservationRecordValue:
        """Persist a new observation or amendment."""
        self._assert_editor_permission(
            organization_id=observation.organization_id,
            assessment_id=observation.assessment_id,
            actor_user_id=actor_user_id,
        )

        if observation.is_amendment:
            # Verify ancestor observation exists
            parent = self._session.scalar(
                select(AssessmentObservationRecord).where(
                    AssessmentObservationRecord.organization_id == observation.organization_id,
                    AssessmentObservationRecord.assessment_id == observation.assessment_id,
                    AssessmentObservationRecord.observation_id == observation.amends_observation_id,
                )
            )
            if parent is None:
                raise ValueError(
                    f"Amended observation {observation.amends_observation_id} does not exist in assessment"
                )

        record = AssessmentObservationRecord(
            observation_id=observation.observation_id,
            organization_id=observation.organization_id,
            assessment_id=observation.assessment_id,
            category=observation.category.value,
            source=observation.source.value,
            observer_name=observation.observer_name,
            observer_role=observation.observer_role,
            observed_at=observation.observed_at,
            activity_context=observation.activity_context,
            notes=observation.notes,
            structured_flags_json=list(observation.structured_flags),
            is_amendment=observation.is_amendment,
            amends_observation_id=observation.amends_observation_id,
            version=observation.version,
            created_at=observation.created_at,
        )
        self._session.add(record)
        self._session.commit()
        return observation

    def list_observations(
        self,
        *,
        organization_id: str,
        assessment_id: str,
    ) -> list[ObservationRecordValue]:
        """List all observations for an assessment ordered by created_at."""
        records = self._session.scalars(
            select(AssessmentObservationRecord)
            .where(
                AssessmentObservationRecord.organization_id == organization_id,
                AssessmentObservationRecord.assessment_id == assessment_id,
            )
            .order_by(AssessmentObservationRecord.created_at.asc())
        ).all()

        return [
            ObservationRecordValue(
                observation_id=rec.observation_id,
                organization_id=rec.organization_id,
                assessment_id=rec.assessment_id,
                category=ObservationCategory(rec.category),
                source=ObservationSource(rec.source),
                observer_name=rec.observer_name,
                observer_role=rec.observer_role,
                observed_at=_ensure_utc(rec.observed_at),
                activity_context=rec.activity_context,
                notes=rec.notes,
                structured_flags=tuple(rec.structured_flags_json),
                is_amendment=rec.is_amendment,
                amends_observation_id=rec.amends_observation_id,
                version=rec.version,
                created_at=_ensure_utc(rec.created_at),
            )
            for rec in records
        ]

    def create_instrument_administration(
        self,
        administration: InstrumentAdministration,
        *,
        actor_user_id: str,
    ) -> InstrumentAdministration:
        """Persist a generic instrument administration and individual item responses."""
        self._assert_editor_permission(
            organization_id=administration.organization_id,
            assessment_id=administration.assessment_id,
            actor_user_id=actor_user_id,
        )

        admin_rec = AssessmentInstrumentRecord(
            administration_id=administration.administration_id,
            organization_id=administration.organization_id,
            assessment_id=administration.assessment_id,
            instrument_name=administration.instrument_name,
            instrument_version=administration.instrument_version,
            respondent_type=administration.respondent_type.value,
            administered_by_user_id=administration.administered_by_user_id,
            administered_at=administration.administered_at,
            licensing_verified=administration.licensing_verified,
            summary_scores_json=dict(administration.summary_scores),
            version=1,
            created_at=administration.created_at,
        )
        self._session.add(admin_rec)
        self._session.flush()

        for item in administration.items:
            item_rec = AssessmentInstrumentItemRecord(
                item_id=uuid4().hex,
                organization_id=administration.organization_id,
                administration_id=administration.administration_id,
                item_key=item.item_key,
                prompt_label=item.prompt_label,
                response_value=str(item.response_value),
                score=item.score,
                notes=item.notes,
                created_at=administration.created_at,
            )
            self._session.add(item_rec)

        self._session.commit()
        return administration

    def list_instrument_administrations(
        self,
        *,
        organization_id: str,
        assessment_id: str,
    ) -> list[InstrumentAdministration]:
        """List instrument administrations and item responses for an assessment."""
        admin_records = self._session.scalars(
            select(AssessmentInstrumentRecord)
            .where(
                AssessmentInstrumentRecord.organization_id == organization_id,
                AssessmentInstrumentRecord.assessment_id == assessment_id,
            )
            .order_by(AssessmentInstrumentRecord.administered_at.asc())
        ).all()

        results: list[InstrumentAdministration] = []
        for admin_rec in admin_records:
            item_records = self._session.scalars(
                select(AssessmentInstrumentItemRecord)
                .where(
                    AssessmentInstrumentItemRecord.organization_id == organization_id,
                    AssessmentInstrumentItemRecord.administration_id == admin_rec.administration_id,
                )
                .order_by(AssessmentInstrumentItemRecord.item_key.asc())
            ).all()

            items = tuple(
                InstrumentItemResponse(
                    item_key=it.item_key,
                    prompt_label=it.prompt_label,
                    response_value=it.response_value,
                    score=it.score,
                    notes=it.notes,
                )
                for it in item_records
            )

            results.append(
                InstrumentAdministration(
                    administration_id=admin_rec.administration_id,
                    organization_id=admin_rec.organization_id,
                    assessment_id=admin_rec.assessment_id,
                    instrument_name=admin_rec.instrument_name,
                    instrument_version=admin_rec.instrument_version,
                    respondent_type=InstrumentRespondentType(admin_rec.respondent_type),
                    administered_by_user_id=admin_rec.administered_by_user_id,
                    administered_at=_ensure_utc(admin_rec.administered_at),
                    licensing_verified=admin_rec.licensing_verified,
                    summary_scores=dict(admin_rec.summary_scores_json),
                    items=items,
                    created_at=_ensure_utc(admin_rec.created_at),
                )
            )

        return results
