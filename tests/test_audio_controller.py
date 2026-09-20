"""Unit tests for AudioPlaybackController and AudioRecorder."""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from packages.gui.audio_controller import AudioPlaybackController, AudioRecorder


def test_audio_playback_controller_time_format():
    assert AudioPlaybackController.format_time(0.0) == "00:00.0"
    assert AudioPlaybackController.format_time(65.4) == "01:05.4"
    assert AudioPlaybackController.format_time(125.0) == "02:05.0"


def test_audio_playback_controller_peaks(tmp_path: Path):
    sr = 16000
    dur = 1.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wav = 0.5 * np.sin(2 * np.pi * 300 * t)
    wav_path = tmp_path / "ctrl_test.wav"
    sf.write(str(wav_path), wav.astype(np.float32), sr)

    ctrl = AudioPlaybackController()
    peaks = ctrl.compute_waveform_peaks(str(wav_path), num_peaks=20)
    assert len(peaks) > 0
    assert ctrl.waveform_duration == pytest.approx(1.0, 0.05)


def test_audio_recorder_lifecycle(tmp_path: Path):
    rec = AudioRecorder(sample_rate=16000)
    assert not rec.is_recording
    assert rec.get_recording_duration() == 0.0

    # Start
    res = rec.start_recording()
    assert res is True
    assert rec.is_recording

    # Stop & save
    out_wav = tmp_path / "rec_output.wav"
    saved = rec.stop_recording(output_path=str(out_wav))
    assert not rec.is_recording
    assert os.path.exists(saved)

    info = sf.info(saved)
    assert info.samplerate == 16000
    assert info.channels == 1
