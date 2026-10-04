import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata


client = TestClient(app)

HEADERS = {
    "x-mock-user-id": "therapist-demo",
    "x-mock-role": "therapist",
    "x-organization-id": "pilot_org_001",
}


@pytest.fixture
def repo_with_audio():
    repo = MockRepository()
    # Add verified audio file to session_demo_001
    audio = AudioFileMetadata(
        audio_file_id="audio_demo_001",
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="sample.wav",
        content_type="audio/wav",
        size_bytes=10240,
        storage_mode="local_private",
        object_key="pilot_org_001/case_demo_001/session_demo_001/audio_demo_001.wav",
        upload_status="uploaded",
        duration_seconds=120.0,
        sample_rate_hz=16000,
        channels=2,
        checksum_sha256="4a7d1ed414474e4033ac29ccb8653d9b",
    )
    repo.audio_files[audio.audio_file_id] = audio
    app.dependency_overrides[get_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_repository, None)


def test_waveform_peaks_returns_binary_stream(repo_with_audio):
    response = client.get(
        "/api/v1/sessions/session_demo_001/audio/waveform-peaks",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "x-points-per-second" in response.headers
    assert "x-duration-ms" in response.headers
    assert "x-channels" in response.headers
    assert len(response.content) > 0


def test_playback_grant_requires_consent_and_returns_signed_url(repo_with_audio):
    response = client.post(
        "/api/v1/sessions/session_demo_001/audio/playback-grant",
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "playback_url" in data
    assert "expires_at" in data
    assert "audio_sha256" in data
    assert data["audio_sha256"] == "4a7d1ed414474e4033ac29ccb8653d9b"


def test_playback_grant_rejects_revoked_consent(repo_with_audio):
    # Revoke consent for the case
    repo_with_audio.cases["case_demo_001"].consent_status = "revoked"
    response = client.post(
        "/api/v1/sessions/session_demo_001/audio/playback-grant",
        headers=HEADERS,
    )
    assert response.status_code == 403
