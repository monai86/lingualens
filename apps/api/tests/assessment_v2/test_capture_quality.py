from __future__ import annotations

from pathlib import Path

import pytest

from app.assessment_v2.quality import (
    MediaProbeError,
    MediaProbeUnavailable,
    MediaQuality,
    QualityDecision,
    SubprocessMediaProbe,
    evaluate_quality,
)


def test_evaluate_quality_accepts_a_decodable_sample_with_research_thresholds() -> None:
    decision = evaluate_quality(
        MediaQuality(
            duration_seconds=135.0,
            loudness_db=-24.0,
            silence_ratio=0.12,
            decodability=1.0,
            unavailable_checks=(),
        ),
        minimum_duration_seconds=120,
        target_duration_seconds=180,
    )

    assert decision == QualityDecision(status="usable", unavailable_checks=())


@pytest.mark.parametrize(
    "quality",
    [
        MediaQuality(90.0, -24.0, 0.1, 1.0, ()),
        MediaQuality(135.0, -60.0, 0.1, 1.0, ()),
        MediaQuality(135.0, -24.0, 0.85, 1.0, ()),
    ],
)
def test_evaluate_quality_requests_an_additional_sample_for_observable_quality_problems(
    quality: MediaQuality,
) -> None:
    decision = evaluate_quality(quality, minimum_duration_seconds=120, target_duration_seconds=180)

    assert decision.status == "needs_additional_sample"


def test_evaluate_quality_preserves_unavailable_checks_without_fabricating_values() -> None:
    decision = evaluate_quality(
        MediaQuality(None, None, None, None, ("loudness", "silence_ratio")),
        minimum_duration_seconds=120,
        target_duration_seconds=180,
    )

    assert decision.status == "unavailable"
    assert decision.unavailable_checks == (
        "loudness",
        "silence_ratio",
        "decodability",
        "duration",
    )


def test_subprocess_probe_parses_only_bounded_commands() -> None:
    calls: list[list[str]] = []

    class Completed:
        def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def runner(command: list[str], *, timeout: float) -> Completed:
        del timeout
        calls.append(command)
        if command[0] == "ffprobe":
            return Completed('{"format":{"duration":"135.25"}}')
        if "volumedetect" in " ".join(command):
            return Completed("", "mean_volume: -24.0 dB\n")
        if "silencedetect" in " ".join(command):
            return Completed("", "silence_duration: 10.0\n")
        raise AssertionError(command)

    result = SubprocessMediaProbe(runner=runner).probe(Path("/tmp/opaque-media"))

    assert result.duration_seconds == 135.25
    assert result.loudness_db == -24.0
    assert result.silence_ratio == pytest.approx(10.0 / 135.25)
    assert result.decodability == 1.0
    ffmpeg_commands = [command for command in calls if command[0] == "ffmpeg"]
    assert ffmpeg_commands
    assert all(command[command.index("-v") + 1] == "info" for command in ffmpeg_commands)
    assert all("/tmp/opaque-media" in command for command in calls)
    assert all(";" not in part and "&&" not in part for command in calls for part in command)


def test_subprocess_probe_distinguishes_unavailable_tool_from_undecodable_media() -> None:
    def unavailable(_command: list[str], *, timeout: float):
        del timeout
        raise FileNotFoundError("ffprobe")

    with pytest.raises(MediaProbeUnavailable):
        SubprocessMediaProbe(runner=unavailable).probe(Path("/tmp/opaque-media"))

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "invalid media"

    with pytest.raises(MediaProbeError):
        SubprocessMediaProbe(runner=lambda _command, *, timeout: Failed()).probe(
            Path("/tmp/opaque-media")
        )
