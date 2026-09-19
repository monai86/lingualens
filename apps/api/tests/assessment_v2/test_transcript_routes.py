from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    TranscriptReviewState,
    TranscriptSource,
    TranscriptRevisionSnapshot,
)
from app.assessment_v2.evidence import (
    EvidenceProvenance,
    EvidenceRunSnapshot,
    EvidenceSource,
    EvidenceState,
    MeasuredFeature,
    build_developmental_profile,
)
from app.main import app


def revision() -> TranscriptRevisionSnapshot:
    return TranscriptRevisionSnapshot(
        id="transcript_revision_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.DRAFT,
        content="@UTF8\n@Begin\n*CHI: hello .\n@End\n",
        content_sha256="a" * 64,
        created_by_user_id="therapist_opaque_01",
        created_at=datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc),
        attested_by_user_id=None,
        attested_at=None,
        version=1,
    )


def evidence_run() -> EvidenceRunSnapshot:
    provenance = EvidenceProvenance(
        input_ref="transcript_input_opaque_01",
        input_sha256="a" * 64,
        protocol_version_key="thai_guided_language_sample:v0",
        extractor="reviewed-transcript-adapter",
        pipeline_version="reviewed-transcript-descriptors-v1",
        feature_schema_version="descriptive-transcript-features-v1",
        analyzed_at=datetime(2026, 9, 7, 8, 2, tzinfo=timezone.utc),
    )
    feature = MeasuredFeature(
        key="child_token_count",
        value=12,
        unit="tokens",
        source=EvidenceSource.REVIEWED_TRANSCRIPT,
        state=EvidenceState.COMPLETED,
        limitation="Descriptive measurement only.",
        provenance=provenance,
    )
    profile = build_developmental_profile(
        assessment_id="assessment_opaque_01",
        features=[feature],
        generated_at=provenance.analyzed_at,
    )
    return EvidenceRunSnapshot(
        id="evidence_run_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        transcript_revision_id="transcript_revision_opaque_01",
        state=EvidenceState.COMPLETED,
        provenance=provenance,
        profile=profile,
        version=1,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    class FakeService:
        def __init__(self) -> None:
            self.created = None
            self.attested = None

        def get_current_transcript(self, assessment_id: str):
            assert assessment_id == "assessment_opaque_01"
            return revision()

        def get_current_evidence(self, assessment_id: str):
            assert assessment_id == "assessment_opaque_01"
            return evidence_run()

        def create_transcript_revision(self, assessment_id, command, correlation_id):
            self.created = (assessment_id, command, correlation_id)
            return revision()

        def attest_transcript(self, transcript_revision_id, command, correlation_id):
            self.attested = (transcript_revision_id, command, correlation_id)
            value = revision()
            return replace(
                value,
                review_state=TranscriptReviewState.ATTESTED,
                attested_by_user_id="therapist_opaque_01",
                attested_at=datetime(2026, 9, 7, 8, 1, tzinfo=timezone.utc),
                version=2,
            )

    service = FakeService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        value = TestClient(app)
        value.fake_service = service  # type: ignore[attr-defined]
        yield value
    finally:
        app.dependency_overrides.clear()


def test_get_transcript_route_returns_review_state_and_checksum(client: TestClient) -> None:
    response = client.get("/api/v2/assessments/assessment_opaque_01/transcript")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "transcript_revision_opaque_01"
    assert body["review_state"] == "draft"
    assert body["content_sha256"] == "a" * 64
    assert body["content"] == "@UTF8\n@Begin\n*CHI: hello .\n@End\n"


def test_get_evidence_route_returns_profile_without_diagnostic_fields(client: TestClient) -> None:
    response = client.get("/api/v2/assessments/assessment_opaque_01/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "completed"
    assert body["features"][0]["key"] == "child_token_count"
    assert body["features"][0]["provenance"]["input_sha256"] == "a" * 64
    assert body["not_diagnostic"] is True
    assert body["decision_support_only"] is True
    assert "diagnosis" not in body
    assert "asd_probability" not in body
    assert "probability" not in body


def test_create_transcript_revision_route_uses_explicit_source(client: TestClient) -> None:
    response = client.post(
        "/api/v2/assessments/assessment_opaque_01/transcript-revisions",
        json={
            "source": "manual",
            "content": "@UTF8\n@Begin\n*CHI: hello .\n@End\n",
            "expected_revision": 1,
            "expected_version": 1,
        },
    )

    assert response.status_code == 201
    service = client.fake_service  # type: ignore[attr-defined]
    assert service.created[0] == "assessment_opaque_01"
    assert service.created[1].source is TranscriptSource.MANUAL
    assert service.created[1].expected_revision == 1
    assert service.created[1].expected_version == 1


def test_create_transcript_revision_route_allows_first_draft_without_current_revision(client: TestClient) -> None:
    response = client.post(
        "/api/v2/assessments/assessment_opaque_01/transcript-revisions",
        json={
            "source": "asr_draft",
            "content": "@UTF8\n@Begin\n*CHI: hello .\n@End\n",
            "expected_revision": None,
            "expected_version": None,
        },
    )

    assert response.status_code == 201


def test_attest_transcript_route_requires_expected_version(client: TestClient) -> None:
    response = client.post(
        "/api/v2/transcript-revisions/transcript_revision_opaque_01/attest",
        json={"expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json()["review_state"] == "attested"
    service = client.fake_service  # type: ignore[attr-defined]
    assert service.attested[0] == "transcript_revision_opaque_01"
    assert service.attested[1].expected_version == 1
