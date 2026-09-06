"""Small, deterministic media-quality checks for Capture V2.

These checks describe whether an audio artifact is usable for research capture.
They do not infer speech, speakers, developmental status, or diagnosis.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Any


_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)
_SILENCE_DURATION = re.compile(r"silence_duration:\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


class MediaProbeError(RuntimeError):
    """The media was present but a quality check could not decode it."""


class MediaProbeUnavailable(RuntimeError):
    """The runtime does not have a required media tool."""


@dataclass(frozen=True, slots=True)
class MediaQuality:
    duration_seconds: float | None
    loudness_db: float | None
    silence_ratio: float | None
    decodability: float | None
    unavailable_checks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QualityDecision:
    status: str
    unavailable_checks: tuple[str, ...]


Runner = Callable[..., Any]


class SubprocessMediaProbe:
    """Run a fixed ffprobe/ffmpeg command set with an injectable runner."""

    def __init__(self, *, runner: Runner | None = None, timeout_seconds: float = 30.0) -> None:
        self._runner = runner or self._run
        self._timeout_seconds = timeout_seconds

    def probe(self, media_path: Path) -> MediaQuality:
        ffprobe_result = self._invoke(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(media_path),
            ]
        )
        if ffprobe_result.returncode != 0:
            raise MediaProbeError("media could not be decoded")
        try:
            payload = json.loads(ffprobe_result.stdout)
            duration = float(payload["format"]["duration"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MediaProbeError("media duration could not be measured") from exc
        if duration <= 0:
            raise MediaProbeError("media duration is not positive")

        unavailable: list[str] = []
        loudness: float | None = None
        silence_ratio: float | None = None
        try:
            volume_result = self._invoke(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(media_path),
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-",
                ]
            )
        except MediaProbeUnavailable:
            unavailable.append("loudness")
            volume_result = None
        if volume_result is not None:
            if volume_result.returncode != 0:
                raise MediaProbeError("media loudness could not be measured")
            match = _MEAN_VOLUME.search(volume_result.stderr or volume_result.stdout)
            if match is None:
                unavailable.append("loudness")
            else:
                loudness = float(match.group(1))

        try:
            silence_result = self._invoke(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(media_path),
                    "-af",
                    "silencedetect=noise=-40dB:d=0.5",
                    "-f",
                    "null",
                    "-",
                ]
            )
        except MediaProbeUnavailable:
            unavailable.append("silence_ratio")
            silence_result = None
        if silence_result is not None:
            if silence_result.returncode != 0:
                raise MediaProbeError("media silence could not be measured")
            silence_seconds = sum(
                float(value) for value in _SILENCE_DURATION.findall(silence_result.stderr or "")
            )
            silence_ratio = min(1.0, max(0.0, silence_seconds / duration))

        return MediaQuality(
            duration_seconds=duration,
            loudness_db=loudness,
            silence_ratio=silence_ratio,
            decodability=1.0,
            unavailable_checks=tuple(dict.fromkeys(unavailable)),
        )

    def _invoke(self, command: list[str]) -> Any:
        try:
            return self._runner(command, timeout=self._timeout_seconds)
        except FileNotFoundError as exc:
            raise MediaProbeUnavailable("media tools are unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise MediaProbeError("media quality check timed out") from exc
        except OSError as exc:
            raise MediaProbeError("media quality check failed") from exc

    @staticmethod
    def _run(command: list[str], *, timeout: float) -> Any:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )


def evaluate_quality(
    quality: MediaQuality,
    *,
    minimum_duration_seconds: int,
    target_duration_seconds: int,
) -> QualityDecision:
    """Map observable media measurements to a non-diagnostic capture status."""

    del target_duration_seconds  # Target is guidance; minimum is the capture gate.
    unavailable = list(quality.unavailable_checks)
    if quality.decodability is None:
        unavailable.append("decodability")
    if quality.duration_seconds is None:
        unavailable.append("duration")
    if quality.duration_seconds is None or quality.decodability is None:
        return QualityDecision("unavailable", tuple(dict.fromkeys(unavailable)))
    if quality.decodability < 1.0:
        return QualityDecision("unavailable", tuple(dict.fromkeys(unavailable)))
    if unavailable:
        return QualityDecision("unavailable", tuple(dict.fromkeys(unavailable)))
    if quality.duration_seconds < minimum_duration_seconds:
        return QualityDecision("needs_additional_sample", ())
    if quality.loudness_db is not None and quality.loudness_db < -50.0:
        return QualityDecision("needs_additional_sample", ())
    if quality.silence_ratio is not None and quality.silence_ratio > 0.80:
        return QualityDecision("needs_additional_sample", ())
    return QualityDecision("usable", ())
