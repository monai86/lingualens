from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentProtocolSelectionRecord,
    AssessmentRecord,
    CareTeamAssignmentRecord,
    ChildRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingRecord,
    UserProfileRecord,
)
from app.assessment_v2.db.session import (
    assessment_session_for,
    get_assessment_engine,
    get_assessment_session_factory,
)
from app.core.security import CurrentUser


def test_sqlite_assessment_session_enforces_capture_tenant_foreign_keys() -> None:
    with TemporaryDirectory(prefix="lingualens-assessment-v2-fk-") as temp_dir:
        database_path = Path(temp_dir) / "assessment-v2.db"
        database_url = f"sqlite:///{database_path}"
        engine = get_assessment_engine(database_url)
        AssessmentBase.metadata.create_all(engine)
        now = datetime.now(timezone.utc)

        try:
            with engine.connect() as connection:
                assert connection.scalar(text("PRAGMA foreign_keys")) == 1

            with Session(engine, expire_on_commit=False) as session:
                session.add_all(
                    [
                        OrganizationRecord(
                            organization_id="org_alpha",
                            display_label="Synthetic Alpha",
                        ),
                        OrganizationRecord(
                            organization_id="org_beta",
                            display_label="Synthetic Beta",
                        ),
                    ]
                )
                session.flush()
                session.add(UserProfileRecord(user_id="user_alpha", display_label="Synthetic User"))
                session.flush()
                session.add(
                    OrganizationMembershipRecord(
                        membership_id=uuid4().hex,
                        organization_id="org_alpha",
                        user_id="user_alpha",
                        role="therapist",
                    )
                )
                session.flush()
                session.add(
                    ChildRecord(
                        child_id="child_alpha",
                        organization_id="org_alpha",
                        display_code="LL-ALPHA",
                        birth_month=6,
                        birth_year=2021,
                        language_context='{"additional":[],"primary":"th"}',
                    )
                )
                session.flush()
                session.add(
                    CareTeamAssignmentRecord(
                        assignment_id=uuid4().hex,
                        organization_id="org_alpha",
                        child_id="child_alpha",
                        user_id="user_alpha",
                        role="assigned_clinician",
                    )
                )
                session.flush()
                session.add(
                    AssessmentRecord(
                        assessment_id="assessment_alpha",
                        organization_id="org_alpha",
                        child_id="child_alpha",
                        purpose="initial",
                        state="draft",
                        age_months=36,
                        language_context='{"additional":[],"primary":"th"}',
                        assigned_clinician_id="user_alpha",
                    )
                )
                session.flush()
                session.add(
                    ProtocolVersionRecord(
                        protocol_version_key="thai_guided_language_sample:v0",
                        primary_language="th",
                        minimum_age_months=18,
                        maximum_age_months=72,
                        supported_purposes="initial,developmental_follow_up,post_intervention_follow_up,additional_evidence",
                    )
                )
                session.flush()
                session.add(
                    ProtocolActivityRecord(
                        protocol_version_key="thai_guided_language_sample:v0",
                        activity_key="free_play",
                        required=True,
                        target_duration_seconds=180,
                        minimum_duration_seconds=120,
                        sort_order=1,
                    )
                )
                session.flush()
                session.add(
                    AssessmentProtocolSelectionRecord(
                        organization_id="org_alpha",
                        assessment_id="assessment_alpha",
                        protocol_version_key="thai_guided_language_sample:v0",
                        selected_by_user_id="user_alpha",
                    )
                )
                session.commit()

            with pytest.raises(IntegrityError):
                with assessment_session_for(
                    CurrentUser(
                        user_id="user_beta",
                        organization_id="org_beta",
                        role="therapist",
                        display_name="Synthetic User",
                    ),
                    database_url,
                ) as session:
                    session.add(
                        RecordingRecord(
                            recording_id=uuid4().hex,
                            organization_id="org_beta",
                            assessment_id="assessment_alpha",
                            protocol_version_key="thai_guided_language_sample:v0",
                            activity_key="free_play",
                            declared_content_type="audio/wav",
                            declared_size_bytes=1,
                            declared_checksum="a" * 64,
                            object_key="opaque-object-key",
                            expires_at=now,
                        )
                    )
                    session.flush()
        finally:
            AssessmentBase.metadata.drop_all(engine)
            engine.dispose()
            get_assessment_session_factory.cache_clear()
            get_assessment_engine.cache_clear()
