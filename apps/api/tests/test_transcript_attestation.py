import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import Transcript, Utterance


client = TestClient(app)

HEADERS = {
    "x-mock-user-id": "therapist-demo",
    "x-mock-role": "therapist",
    "x-organization-id": "pilot_org_001",
}


@pytest.fixture
def repo_with_transcript():
    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="trans_demo_001",
        session_id=session.session_id,
        case_id=session.case_id,
        source="manual",
        version=3,
        raw_text="*CHI: รถ สี แดง\n*INV: ใช่แล้ว",
        utterances=[
            Utterance(utterance_id="u1", speaker="CHI", text="รถ สี แดง", start_ms=1000, end_ms=2500),
            Utterance(utterance_id="u2", speaker="INV", text="ใช่แล้ว", start_ms=2800, end_ms=3500),
        ],
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    app.dependency_overrides[get_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_repository, None)


def test_transcript_update_optimistic_concurrency_conflict(repo_with_transcript):
    # Base version is 3; sending base_version=2 must result in 409 Conflict
    payload = {
        "base_version": 2,
        "lines": [
            {"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2500, "text": "รถ สี แดง"}
        ],
        "review_status": "IN_REVIEW",
    }
    response = client.put(
        "/api/v1/sessions/session_demo_001/transcript",
        json=payload,
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert "conflict" in response.json()["detail"].lower()


def test_transcript_update_sets_downstream_stale_and_increments_version(repo_with_transcript):
    # Sending matching base_version=3
    payload = {
        "base_version": 3,
        "lines": [
            {"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2600, "text": "รถ สี แดง คัน ใหญ่"},
            {"line_id": "L2", "speaker": "INV", "start_ms": 2800, "end_ms": 3500, "text": "ใช่แล้ว"},
        ],
        "review_status": "IN_REVIEW",
    }
    response = client.put(
        "/api/v1/sessions/session_demo_001/transcript",
        json=payload,
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 4
    # Check that session flags findings as stale
    assert repo_with_transcript.sessions["session_demo_001"].findings_stale is True
