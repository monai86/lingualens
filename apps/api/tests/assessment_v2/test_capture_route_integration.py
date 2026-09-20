from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from hashlib import sha256

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
    AccessScope,
    AssessmentPurpose,
    AssessmentState,
    AttestTranscript,
    ConsentPurpose,
    CreateTranscriptRevision,
    RecordingUploadState,
    TranscriptSource,
)
from app.assessment_v2.db.repositories import AssessmentRepository
from app.assessment_v2.evidence import (
    EvidenceProvenance,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
)
from app.assessment_v2.evidence_adapter import AdaptedEvidence
from app.assessment_v2.evidence_worker import EvidenceProcessingWorker
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
        client = TestClient(app)
        client.assessment_session = session  # type: ignore[attr-defined]
        yield client
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


def test_real_dependency_stack_persists_and_attests_reviewed_transcript(
    real_capture_client: TestClient,
) -> None:
    session = real_capture_client.assessment_session  # type: ignore[attr-defined]
    assessment = session.get(AssessmentRecord, "route_assessment_01")
    assert assessment is not None
    assessment.state = AssessmentState.PROCESSING.value
    session.flush()

    content = "@UTF8\n@Begin\n*CHI: hello .\n@End\n"
    created = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/transcript-revisions",
        json={"source": "manual", "content": content},
    )

    assert created.status_code == 201
    created_body = created.json()
    assert created_body["review_state"] == "draft"
    assert created_body["content"] == content
    assert created_body["content_sha256"] == sha256(content.encode("utf-8")).hexdigest()

    current = real_capture_client.get(
        "/api/v2/assessments/route_assessment_01/transcript"
    )
    assert current.status_code == 200
    assert current.json()["id"] == created_body["id"]

    attested = real_capture_client.post(
        f"/api/v2/transcript-revisions/{created_body['id']}/attest",
        json={"expected_version": 1},
    )
    assert attested.status_code == 200
    assert attested.json()["review_state"] == "attested"
    assert attested.json()["version"] == 2

    stale = real_capture_client.post(
        f"/api/v2/transcript-revisions/{created_body['id']}/attest",
        json={"expected_version": 1},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "transcript_not_reviewable"


def test_real_dependency_stack_reads_persisted_evidence_profile(
    real_capture_client: TestClient,
) -> None:
    session = real_capture_client.assessment_session  # type: ignore[attr-defined]
    assessment = session.get(AssessmentRecord, "route_assessment_01")
    assert assessment is not None
    assessment.state = AssessmentState.PROCESSING.value
    session.flush()

    repo = AssessmentRepository(session)
    scope = AccessScope(
        user_id="route_therapist_01",
        organization_id="route_org_01",
        role="therapist",
    )
    content = "@UTF8\n@Begin\n*CHI: hello .\n@End\n"
    transcript = repo.create_transcript_revision(
        scope,
        CreateTranscriptRevision(
            assessment_id="route_assessment_01",
            content=content,
            source=TranscriptSource.MANUAL,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    repo.attest_transcript(
        scope,
        AttestTranscript(transcript_revision_id=transcript.id, expected_version=1),
        correlation_id="0123456789abcdef0123456789abcdef",
    )
    provenance = EvidenceProvenance(
        input_ref="transcript_input_opaque_01",
        input_sha256=transcript.content_sha256,
        protocol_version_key="thai_guided_language_sample:v0",
        extractor="reviewed-transcript-adapter",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 7, 8, 2, tzinfo=UTC),
    )
    repo.create_evidence_run(
        scope,
        "route_assessment_01",
        transcript.id,
        AdaptedEvidence(
            state=EvidenceState.COMPLETED,
            features=(
                MeasuredFeature(
                    key="child_token_count",
                    value=12,
                    unit="tokens",
                    source=EvidenceSource.REVIEWED_TRANSCRIPT,
                    state=EvidenceState.COMPLETED,
                    limitation="Descriptive measurement only.",
                    provenance=provenance,
                ),
            ),
            limitations=("No compatible reference band was applied.",),
            provenance=provenance,
        ),
        correlation_id="0123456789abcdef0123456789abcdef",
    )

    response = real_capture_client.get("/api/v2/assessments/route_assessment_01/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "completed"
    assert body["features"][0]["key"] == "child_token_count"
    assert body["features"][0]["value"] == 12
    assert body["domains"]
    assert body["not_diagnostic"] is True
    assert "content" not in body
    assert "diagnosis" not in body
    assert "asd_probability" not in body


def test_real_dependency_stack_runs_reviewed_transcript_worker_after_attestation(
    real_capture_client: TestClient,
) -> None:
    session = real_capture_client.assessment_session  # type: ignore[attr-defined]
    assessment = session.get(AssessmentRecord, "route_assessment_01")
    assert assessment is not None
    assessment.state = AssessmentState.PROCESSING.value
    session.flush()

    content = (
        "@UTF8\n@Begin\n"
        "*INV: do you see the red car ?\n"
        "*CHI: red car .\n"
        "*INV: what color ?\n"
        "*CHI: red .\n"
        "*INV: say more .\n"
        "*CHI: red car .\n"
        "@End\n"
    )
    created = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/transcript-revisions",
        json={"source": "asr_draft", "content": content},
    )
    assert created.status_code == 201
    revision = created.json()

    attested = real_capture_client.post(
        f"/api/v2/transcript-revisions/{revision['id']}/attest",
        json={"expected_version": revision["version"]},
    )
    assert attested.status_code == 200

    segment_set = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/transcript-segment-sets",
        json={
            "transcript_revision_id": revision["id"],
            "source": "manual",
            "segments": [
                {
                    "ordinal": 1,
                    "start_ms": 0,
                    "end_ms": 1200,
                    "speaker_role": "child",
                    "text": "red car .",
                    "confidence": 0.98,
                    "uncertainty_reason": "none",
                }
            ],
        },
    )
    assert segment_set.status_code == 201
    segment_attested = real_capture_client.post(
        f"/api/v2/transcript-segment-sets/{segment_set.json()['id']}/attest",
        json={"expected_version": segment_set.json()["version"]},
    )
    assert segment_attested.status_code == 200

    evidence = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/evidence-runs"
    )

    assert evidence.status_code == 202
    body = evidence.json()
    assert body["processing_run"]["state"] == "queued"
    assert body["processing_run"]["result_available"] is False
    processing_run_id = body["processing_run"]["id"]

    worker_result = EvidenceProcessingWorker(AssessmentRepository(session)).run_once()

    assert worker_result.status == "evidence_recorded"
    assert worker_result.run_id == processing_run_id
    completed = real_capture_client.get(f"/api/v2/processing-runs/{processing_run_id}")
    assert completed.status_code == 200
    assert completed.json()["state"] == "succeeded"
    assert completed.json()["result_available"] is True

    evidence_profile = real_capture_client.get(
        "/api/v2/assessments/route_assessment_01/evidence"
    )
    assert evidence_profile.status_code == 200
    body = evidence_profile.json()
    feature_values = {feature["key"]: feature["value"] for feature in body["features"]}
    assert feature_values["child_utterance_count"] == 1
    assert feature_values["child_token_count"] == 2
    assert body["not_diagnostic"] is True
    assert body["decision_support_only"] is True
    assert body["segment_set_id"] == segment_set.json()["id"]
    assert body["segment_set_sha256"] == segment_set.json()["segments_sha256"]
    assert body["provenance"]["input_ref"] == f"transcript-segment-set:{segment_set.json()['id']}"
    assert content not in evidence.text
    assert content not in evidence_profile.text


def test_real_dependency_stack_blocks_worker_for_unattested_transcript(
    real_capture_client: TestClient,
) -> None:
    session = real_capture_client.assessment_session  # type: ignore[attr-defined]
    assessment = session.get(AssessmentRecord, "route_assessment_01")
    assert assessment is not None
    assessment.state = AssessmentState.PROCESSING.value
    session.flush()

    created = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/transcript-revisions",
        json={"source": "manual", "content": "@Begin\n*CHI: hello .\n@End\n"},
    )
    assert created.status_code == 201

    evidence = real_capture_client.post(
        "/api/v2/assessments/route_assessment_01/evidence-runs"
    )

    assert evidence.status_code == 409
    assert evidence.json()["error"]["code"] == "transcript_not_reviewable"
