from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from datetime import datetime
from typing import Iterable

from app.assessment_v2.domain.models import (
    TranscriptSegmentSpeakerRole,
    TranscriptSegmentUncertaintyReason,
    TranscriptReviewState,
    TranscriptSource,
)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    ordinal: int
    start_ms: int
    end_ms: int
    speaker_role: TranscriptSegmentSpeakerRole
    text: str
    confidence: float | None = None
    uncertainty_reason: TranscriptSegmentUncertaintyReason = (
        TranscriptSegmentUncertaintyReason.NONE
    )

    def __post_init__(self) -> None:
        if self.ordinal < 1:
            raise ValueError("ordinal must be positive")
        if self.start_ms < 0:
            raise ValueError("start_ms must be non-negative")
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        if not isinstance(self.speaker_role, TranscriptSegmentSpeakerRole):
            raise ValueError("speaker_role must be a supported transcript segment role")
        if not isinstance(self.uncertainty_reason, TranscriptSegmentUncertaintyReason):
            raise ValueError("uncertainty_reason must be a supported transcript segment reason")
        if not isinstance(self.text, str) or not self.text.strip() or any(
            char in self.text for char in "\r\n"
        ):
            raise ValueError("text must be a non-empty value without newlines")
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
                raise ValueError("confidence must be between 0 and 1")
            if not 0 <= self.confidence <= 1:
                raise ValueError("confidence must be between 0 and 1")

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "speaker_role": self.speaker_role.value,
            "text": self.text,
            "confidence": self.confidence,
            "uncertainty_reason": self.uncertainty_reason.value,
        }


@dataclass(frozen=True, slots=True)
class TranscriptSegmentSnapshot:
    id: str
    organization_id: str
    segment_set_id: str
    ordinal: int
    start_ms: int
    end_ms: int
    speaker_role: TranscriptSegmentSpeakerRole
    text: str
    confidence: float | None
    uncertainty_reason: TranscriptSegmentUncertaintyReason
    created_at: datetime

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.id, "transcript segment id"),
            (self.organization_id, "organization id"),
            (self.segment_set_id, "transcript segment set id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty value")
        # Reuse the canonical segment validation so database rows cannot cross
        # the API boundary with a shape the checksum contract would reject.
        self.to_segment()

    def to_segment(self) -> TranscriptSegment:
        return TranscriptSegment(
            ordinal=self.ordinal,
            start_ms=self.start_ms,
            end_ms=self.end_ms,
            speaker_role=self.speaker_role,
            text=self.text,
            confidence=self.confidence,
            uncertainty_reason=self.uncertainty_reason,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "ordinal": self.ordinal,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "speaker_role": self.speaker_role.value,
            "text": self.text,
            "confidence": self.confidence,
            "uncertainty_reason": self.uncertainty_reason.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SegmentAudioReplayGrant:
    segment_id: str
    start_ms: int
    end_ms: int
    available: bool
    url: str | None
    expires_at: datetime | None
    expires_in_seconds: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, str) or not self.segment_id.strip():
            raise ValueError("segment_id must be a non-empty value")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("replay offsets must be non-negative and ordered")
        if self.available:
            if (
                not isinstance(self.url, str)
                or not self.url
                or self.expires_at is None
                or self.expires_in_seconds is None
                or self.expires_in_seconds < 1
            ):
                raise ValueError("available replay requires a signed URL and expiry")
        elif self.url is not None or self.expires_at is not None or self.expires_in_seconds is not None:
            raise ValueError("unavailable replay cannot expose a signed grant")


@dataclass(frozen=True, slots=True)
class TranscriptSegmentSetSnapshot:
    id: str
    organization_id: str
    assessment_id: str
    transcript_revision_id: str
    transcript_content_sha256: str
    recording_id: str | None
    revision: int
    source: TranscriptSource
    review_state: TranscriptReviewState
    segments_sha256: str
    segments: tuple[TranscriptSegmentSnapshot, ...]
    created_by_user_id: str
    created_at: datetime
    attested_by_user_id: str | None
    attested_at: datetime | None
    version: int

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.id, "transcript segment set id"),
            (self.organization_id, "organization id"),
            (self.assessment_id, "assessment id"),
            (self.transcript_revision_id, "transcript revision id"),
            (self.created_by_user_id, "created by user id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty value")
        if len(self.transcript_content_sha256) != 64 or len(self.segments_sha256) != 64:
            raise ValueError("segment set checksums must be 64-character SHA-256 digests")
        if self.revision < 1 or self.version < 1:
            raise ValueError("segment set revision and version must be positive")
        if not isinstance(self.segments, tuple) or not self.segments:
            raise ValueError("segment set must contain segments")
        if not all(isinstance(segment, TranscriptSegmentSnapshot) for segment in self.segments):
            raise ValueError("segment set must contain transcript segment snapshots")
        if (self.attested_by_user_id is None) != (self.attested_at is None):
            raise ValueError("attestation actor and timestamp must be provided together")
        if self.review_state is TranscriptReviewState.ATTESTED and self.attested_by_user_id is None:
            raise ValueError("attested segment set requires attestation metadata")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "assessment_id": self.assessment_id,
            "transcript_revision_id": self.transcript_revision_id,
            "transcript_content_sha256": self.transcript_content_sha256,
            "recording_id": self.recording_id,
            "revision": self.revision,
            "source": self.source.value,
            "review_state": self.review_state.value,
            "segments_sha256": self.segments_sha256,
            "segments": [segment.to_dict() for segment in self.segments],
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat(),
            "attested_by_user_id": self.attested_by_user_id,
            "attested_at": self.attested_at.isoformat() if self.attested_at else None,
            "version": self.version,
        }


def _canonical_json(segments: tuple[TranscriptSegment, ...]) -> bytes:
    return json.dumps(
        [segment.to_canonical_dict() for segment in segments],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validated_segments(segments: Iterable[TranscriptSegment]) -> tuple[TranscriptSegment, ...]:
    canonical = tuple(segments)
    if not canonical:
        raise ValueError("segments must not be empty")

    expected_ordinals = list(range(1, len(canonical) + 1))
    actual_ordinals = [segment.ordinal for segment in canonical]
    if actual_ordinals != expected_ordinals:
        if len(actual_ordinals) != len(set(actual_ordinals)):
            raise ValueError("segment ordinals must be unique")
        raise ValueError("segment ordinals must be contiguous")

    for previous, current in zip(canonical, canonical[1:]):
        if current.start_ms < previous.start_ms:
            raise ValueError("segment start_ms must be non-decreasing")
    return canonical


def compute_transcript_segments_sha256(segments: Iterable[TranscriptSegment]) -> str:
    canonical = _validated_segments(segments)
    return hashlib.sha256(_canonical_json(canonical)).hexdigest()


def canonicalize_transcript_segments(
    segments: Iterable[TranscriptSegment],
    *,
    client_checksum: str | None = None,
) -> tuple[TranscriptSegment, ...]:
    canonical = _validated_segments(segments)
    computed_checksum = hashlib.sha256(_canonical_json(canonical)).hexdigest()
    if client_checksum is not None and client_checksum != computed_checksum:
        raise ValueError("client checksum does not match the server-computed checksum")
    return canonical
