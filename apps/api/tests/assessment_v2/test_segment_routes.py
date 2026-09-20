from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.assessment_v2.dependencies import get_assessment_service
from app.assessment_v2.domain.models import (
    TranscriptReviewState,
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptSource,
)
from app.assessment_v2.domain.segments import (
    SegmentAudioReplayGrant,
    TranscriptSegmentSetSnapshot,
    TranscriptSegmentSnapshot,
)
from app.assessment_v2.schemas import (
    TranscriptSegmentCreateRequest,
    TranscriptSegmentReplayGrantResponse,
    TranscriptSegmentSetCreateRequest,
)
from app.main import app


def segment_set() -> TranscriptSegmentSetSnapshot:
    created_at = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)
    return TranscriptSegmentSetSnapshot(
        id="segment_set_opaque_01",
        organization_id="org_opaque_01",
        assessment_id="assessment_opaque_01",
        transcript_revision_id="transcript_revision_opaque_01",
        transcript_content_sha256="a" * 64,
        recording_id="recording_opaque_01",
        revision=1,
        source=TranscriptSource.MANUAL,
        review_state=TranscriptReviewState.DRAFT,
        segments_sha256="b" * 64,
        segments=(
            TranscriptSegmentSnapshot(
                id="segment_opaque_01",
                organization_id="org_opaque_01",
                segment_set_id="segment_set_opaque_01",
                ordinal=1,
                start_ms=0,
                end_ms=900,
                speaker_role=TranscriptSegmentSpeakerRole.CHILD,
                text="hello",
                confidence=0.9,
                uncertainty_reason=TranscriptSegmentUncertaintyReason.NONE,
                created_at=created_at,
            ),
            TranscriptSegmentSnapshot(
                id="segment_opaque_02",
                organization_id="org_opaque_01",
                segment_set_id="segment_set_opaque_01",
                ordinal=2,
                start_ms=900,
                end_ms=1_700,
                speaker_role=TranscriptSegmentSpeakerRole.THERAPIST,
                text="tell me more",
                confidence=None,
                uncertainty_reason=TranscriptSegmentUncertaintyReason.LOW_ASR_CONFIDENCE,
                created_at=created_at,
            ),
        ),
        created_by_user_id="therapist_opaque_01",
        created_at=created_at,
        attested_by_user_id=None,
        attested_at=None,
        version=1,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    class FakeService:
        def __init__(self) -> None:
            self.current = segment_set()
            self.created = None
            self.attested = None
            self.replay = SegmentAudioReplayGrant(
                segment_id="segment_opaque_01",
                start_ms=0,
                end_ms=900,
                available=True,
                url="https://project-ref.supabase.co/storage/v1/object/sign/capture-private/token?token=opaque",
                expires_at=datetime(2026, 9, 9, 8, 5, tzinfo=timezone.utc),
                expires_in_seconds=300,
            )

        def get_current_transcript_segment_set(self, assessment_id: str):
            assert assessment_id == "assessment_opaque_01"
            return self.current

        def create_transcript_segment_set(self, assessment_id, command, correlation_id):
            self.created = (assessment_id, command, correlation_id)
            return self.current

        def attest_transcript_segment_set(self, segment_set_id, command, correlation_id):
            self.attested = (segment_set_id, command, correlation_id)
            return replace(
                self.current,
                review_state=TranscriptReviewState.ATTESTED,
                attested_by_user_id="therapist_opaque_01",
                attested_at=datetime(2026, 9, 9, 8, 1, tzinfo=timezone.utc),
                version=2,
            )

        def create_transcript_segment_audio_replay_grant(self, segment_id: str):
            assert segment_id == "segment_opaque_01"
            return self.replay

    service = FakeService()
    app.dependency_overrides[get_assessment_service] = lambda: service
    try:
        value = TestClient(app)
        value.fake_service = service  # type: ignore[attr-defined]
        yield value
    finally:
        app.dependency_overrides.clear()


def _segment_payload() -> dict[str, object]:
    return {
        "ordinal": 1,
        "start_ms": 0,
        "end_ms": 900,
        "speaker_role": "child",
        "text": "hello",
        "confidence": 0.9,
        "uncertainty_reason": "none",
    }


def test_segment_request_schemas_are_strict_and_validate_ranges() -> None:
    request = TranscriptSegmentSetCreateRequest(
        transcript_revision_id="transcript_revision_opaque_01",
        source="manual",
        segments=[_segment_payload()],
    )
    assert request.segments[0].speaker_role is TranscriptSegmentSpeakerRole.CHILD

    with pytest.raises(ValidationError):
        TranscriptSegmentCreateRequest(
            **{**_segment_payload(), "end_ms": 0},
        )
    with pytest.raises(ValidationError):
        TranscriptSegmentSetCreateRequest(
            transcript_revision_id="transcript_revision_opaque_01",
            source="manual",
            segments=[],
        )
    with pytest.raises(ValidationError):
        TranscriptSegmentSetCreateRequest(
            transcript_revision_id="transcript_revision_opaque_01",
            source="manual",
            segments=[_segment_payload()],
            expected_revision=1,
        )
    with pytest.raises(ValidationError):
        TranscriptSegmentSetCreateRequest(
            transcript_revision_id="transcript_revision_opaque_01",
            source="manual",
            segments=[{**_segment_payload(), "child_name": "unsafe"}],
        )


def test_get_segment_set_route_returns_ordered_segment_ids_and_safe_fields(client: TestClient) -> None:
    response = client.get("/api/v2/assessments/assessment_opaque_01/transcript-segment-set")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "segment_set_opaque_01"
    assert [segment["id"] for segment in body["segments"]] == [
        "segment_opaque_01",
        "segment_opaque_02",
    ]
    assert body["segments"][1]["uncertainty_reason"] == "low_asr_confidence"
    assert "organization_id" not in body
    assert "object_key" not in body


def test_create_segment_set_route_builds_domain_command_and_returns_created(client: TestClient) -> None:
    response = client.post(
        "/api/v2/assessments/assessment_opaque_01/transcript-segment-sets",
        json={
            "transcript_revision_id": "transcript_revision_opaque_01",
            "source": "manual",
            "segments": [_segment_payload()],
            "expected_revision": 1,
            "expected_version": 1,
            "client_checksum": "b" * 64,
        },
    )

    assert response.status_code == 201
    service = client.fake_service  # type: ignore[attr-defined]
    assert service.created[0] == "assessment_opaque_01"
    assert service.created[1].segments[0].speaker_role is TranscriptSegmentSpeakerRole.CHILD
    assert service.created[1].expected_version == 1
    assert service.created[1].client_checksum == "b" * 64


@pytest.mark.parametrize(
    "segments",
    (
        [
            {**_segment_payload(), "ordinal": 1},
            {**_segment_payload(), "ordinal": 1, "start_ms": 900, "end_ms": 1_700},
        ],
        [{**_segment_payload(), "text": "hello\nworld"}],
    ),
)
def test_create_segment_set_route_rejects_invalid_segment_payloads(
    client: TestClient,
    segments: list[dict[str, object]],
) -> None:
    response = client.post(
        "/api/v2/assessments/assessment_opaque_01/transcript-segment-sets",
        json={
            "transcript_revision_id": "transcript_revision_opaque_01",
            "source": "manual",
            "segments": segments,
        },
    )

    assert response.status_code == 422
    assert client.fake_service.created is None  # type: ignore[attr-defined]


def test_attest_segment_set_route_requires_matching_path_identifier(client: TestClient) -> None:
    response = client.post(
        "/api/v2/transcript-segment-sets/segment_set_opaque_01/attest",
        json={"expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json()["review_state"] == "attested"
    service = client.fake_service  # type: ignore[attr-defined]
    assert service.attested[0] == "segment_set_opaque_01"
    assert service.attested[1].expected_version == 1


def test_segment_replay_route_returns_bounded_private_grant(client: TestClient) -> None:
    response = client.post(
        "/api/v2/transcript-segments/segment_opaque_01/audio-replay-grant"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["segment_id"] == "segment_opaque_01"
    assert body["start_ms"] == 0
    assert body["end_ms"] == 900
    assert body["available"] is True
    assert body["url"].startswith("https://")
    assert "object_key" not in body


def test_replay_response_schema_can_explicitly_report_unavailable_audio() -> None:
    response = TranscriptSegmentReplayGrantResponse(
        segment_id="segment_opaque_01",
        start_ms=0,
        end_ms=900,
        available=False,
        url=None,
        expires_at=None,
        expires_in_seconds=None,
    )

    assert response.available is False
    assert response.url is None
