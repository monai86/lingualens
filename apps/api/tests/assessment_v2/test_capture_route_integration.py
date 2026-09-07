from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    CareTeamAssignmentRecord,
    ChildRecord,
    ConsentRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    ProtocolActivityRecord,
    ProtocolVersionRecord,
    RecordingRecord,
    AssessmentProtocolSelectionRecord,
    AssessmentRecord,
    UserProfileRecord,
)
from app.assessment_v2.dependencies import get_assessment_session, get_capture_storage
from app.assessment_v2.domain.models import (
    AssessmentPurpose,
    AssessmentState,
    ConsentPurpose,
    RecordingUploadState,
)
from app.assessment_v2.protocols import PROTOCOL_CATALOG
from app.assessment_v2.storage import SignedUploadGrant
from app.core.security import CurrentUser, get_current_user
from app.main import app


UTC = timezone.utc


@pytest.fixture
def real_capture_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AssessmentBase.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    principal = CurrentUser(
        user_id="route_therapist_01",
        organization_id="route_org_01",
        role="therapist",
        display_name="Synthetic Therapist",
    )
    now = datetime.now(UTC)
    protocol = PROTOCOL_CATALOG[0]
    try:
        session.add(
            OrganizationRecord(
                organization_id=principal.organization_id,
                display_label="Synthetic Organization",
                active=True,
            )
        )
        session.add(UserProfileRecord(user_id=principal.user_id, display_label=principal.display_name))
        session.add(
            OrganizationMembershipRecord(
                membership_id="route_membership_01",
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                role=principal.role,
                active=True,
            )
        )
        session.add(
            ProtocolVersionRecord(
                protocol_version_key=protocol.protocol_version_key,
                primary_language=protocol.primary_language,
                minimum_age_months=protocol.minimum_age_months,
                maximum_age_months=protocol.maximum_age_months,
                supported_purposes=",".join(purpose.value for purpose in protocol.supported_purposes),
            )
        )
        session.add_all(
            ProtocolActivityRecord(
                protocol_version_key=protocol.protocol_version_key,
                activity_key=activity.activity_key,
                required=activity.required,
                target_duration_seconds=activity.target_duration_seconds,
                minimum_duration_seconds=activity.minimum_duration_seconds,
                sort_order=sort_order,
            )
            for sort_order, activity in enumerate(protocol.activities, start=1)
        )
        child_id = "route_child_01"
        assessment_id = "route_assessment_01"
        recording_id = "route_recording_01"
        session.add(
            ChildRecord(
                child_id=child_id,
                organization_id=principal.organization_id,
                display_code="LL-ROUTE-01",
                birth_year=2021,
                birth_month=6,
                language_context='{"additional":[],"primary":"th"}',
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CareTeamAssignmentRecord(
                assignment_id="route_assignment_01",
                organization_id=principal.organization_id,
                child_id=child_id,
                user_id=principal.user_id,
                role="assigned_clinician",
                active=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            ConsentRecord(
                consent_record_id="route_consent_01",
                organization_id=principal.organization_id,
                child_id=child_id,
                purpose=ConsentPurpose.CLINICAL_ASSESSMENT.value,
                scope_version="clinical-v1",
                status="active",
                recorded_by_user_id=principal.user_id,
                version=1,
                granted_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AssessmentRecord(
                assessment_id=assessment_id,
                organization_id=principal.organization_id,
                child_id=child_id,
                purpose=AssessmentPurpose.INITIAL.value,
                state=AssessmentState.CAPTURING.value,
                age_months=36,
                language_context='{"additional":[],"primary":"th"}',
                assigned_clinician_id=principal.user_id,
                version=3,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AssessmentProtocolSelectionRecord(
                assessment_protocol_selection_id="route_selection_01",
                organization_id=principal.organization_id,
                assessment_id=assessment_id,
                protocol_version_key=protocol.protocol_version_key,
                selected_by_user_id=principal.user_id,
                selected_at=now,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            RecordingRecord(
                recording_id=recording_id,
                organization_id=principal.organization_id,
                assessment_id=assessment_id,
                protocol_version_key=protocol.protocol_version_key,
                activity_key="free_play",
                declared_content_type="audio/webm",
                declared_size_bytes=456,
                declared_checksum="sha256:0123456789abcdef0123456789abcdef",
                object_key="capture/0123456789abcdef0123456789abcdef",
                upload_state=RecordingUploadState.PENDING.value,
                expires_at=now + timedelta(hours=1),
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

        def override_session() -> Iterator[Session]:
            yield session

        class _Storage:
            def create_signed_upload_grant(
                self, object_key: str, content_type: str, declared_size_bytes: int
            ) -> SignedUploadGrant:
                return SignedUploadGrant(
                    tus_endpoint="https://storage.invalid/upload",
                    headers={"x-signature": "opaque"},
                    upload_metadata={"objectName": object_key},
                    bucket="capture-private",
                    object_key=object_key,
                    expires_at=now + timedelta(minutes=30),
                    expires_in_seconds=1800,
                    chunk_size_bytes=1024,
                    upload_length_bytes=declared_size_bytes,
                    content_type=content_type,
                    upsert=False,
                    url="https://storage.invalid/object/upload/sign/capture-private/token",
                )

        app.dependency_overrides[get_current_user] = lambda: principal
        app.dependency_overrides[get_assessment_session] = override_session
        app.dependency_overrides[get_capture_storage] = _Storage
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        AssessmentBase.metadata.drop_all(engine)
        engine.dispose()


def test_real_dependency_stack_upload_intent_returns_safe_metadata(
    real_capture_client: TestClient,
) -> None:
    response = real_capture_client.post(
        "/api/v2/recordings/route_recording_01/upload-intent"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recording"]["upload_state"] == "uploading"
    assert body["upload"]["url"].startswith("https://storage.invalid/")
    assert "bucket" not in body["upload"]
    assert "object_key" not in body["upload"]
    assert "upload_metadata" not in body["upload"]
    assert "Upload-Metadata" not in response.text
    assert "capture/" not in response.text
    assert "declared_checksum" not in body["recording"]
    assert "sha256:0123456789abcdef0123456789abcdef" not in response.text


def test_real_dependency_stack_lists_child_consents_for_workflow_gate(
    real_capture_client: TestClient,
) -> None:
    response = real_capture_client.get("/api/v2/children/route_child_01/consents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert {
        "id": body[0]["id"],
        "child_id": body[0]["child_id"],
        "purpose": body[0]["purpose"],
        "scope_version": body[0]["scope_version"],
        "status": body[0]["status"],
        "withdrawn_at": body[0]["withdrawn_at"],
        "version": body[0]["version"],
    } == {
        "id": "route_consent_01",
        "child_id": "route_child_01",
        "purpose": "clinical_assessment",
        "scope_version": "clinical-v1",
        "status": "active",
        "withdrawn_at": None,
        "version": 1,
    }
    assert body[0]["granted_at"]
