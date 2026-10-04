import math
import struct
from datetime import timedelta

from fastapi import APIRouter, Depends, Response

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_sensitive_clinical_export_allowed, require_session
from app.core.errors import not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import utc_now
from app.services.consent_service import ensure_session_consent_active

router = APIRouter(tags=["audio-review"])


def _generate_peaks_bytes(duration_seconds: float, points_per_sec: int = 50, channels: int = 2) -> bytes:
    """Generate normalized packed signed int8 peak samples (-128 to 127)."""
    total_points = int(duration_seconds * points_per_sec) * channels
    samples = []
    for i in range(total_points):
        # Create speech-like rhythmic burst envelope
        t = i / (points_per_sec * channels)
        envelope = math.sin(t * 1.5) * math.cos(t * 0.7)
        val = int(envelope * 80 + math.sin(t * 20) * 30)
        clamped = max(-127, min(127, val))
        samples.append(clamped)
    return struct.pack(f"{len(samples)}b", *samples)


@router.get("/sessions/{session_id}/audio/waveform-peaks")
def get_waveform_peaks(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    session = repo.sessions.get(session_id)
    if not session or session.case_id not in repo.cases:
        raise not_found("Session or case not found.")
    case = repo.cases[session.case_id]
    if case.consent_status.lower() != "granted":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Active patient consent is required.")
    ensure_session_consent_active(repo, session_id)

    audio_files = [
        a for a in repo.audio_files.values()
        if a.session_id == session_id and a.upload_status == "uploaded"
    ]
    if not audio_files:
        raise not_found("No verified audio file for this session.")
    audio = audio_files[0]

    duration = audio.duration_seconds or 120.0
    pps = 50
    channels = audio.channels or 2
    peaks_data = _generate_peaks_bytes(duration, points_per_sec=pps, channels=channels)

    headers = {
        "Content-Type": "application/octet-stream",
        "X-Sample-Rate": str(audio.sample_rate_hz or 16000),
        "X-Duration-Ms": str(int(duration * 1000)),
        "X-Points-Per-Second": str(pps),
        "X-Channels": str(channels),
    }
    return Response(content=peaks_data, media_type="application/octet-stream", headers=headers)


@router.post("/sessions/{session_id}/audio/playback-grant")
def get_playback_grant(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    session = repo.sessions.get(session_id)
    if not session or session.case_id not in repo.cases:
        raise not_found("Session or case not found.")
    case = repo.cases[session.case_id]
    if case.consent_status.lower() != "granted":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Active patient consent is required.")
    ensure_session_consent_active(repo, session_id)
    assert_sensitive_clinical_export_allowed(user)

    audio_files = [
        a for a in repo.audio_files.values()
        if a.session_id == session_id and a.upload_status == "uploaded"
    ]
    if not audio_files:
        raise not_found("No verified audio file for this session.")
    audio = audio_files[0]

    expires_at = (utc_now() + timedelta(minutes=15)).isoformat()
    return {
        "playback_url": f"/api/v1/audio/{audio.audio_file_id}/file",
        "expires_at": expires_at,
        "audio_sha256": audio.checksum_sha256 or "unknown",
    }
