"""Unit tests for AudioSessionAnalyzer in src/audio_pipeline/analyzer.py."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from src.audio_pipeline import AudioSessionAnalyzer, AudioSessionAnalysis


def test_audio_session_analyzer_end_to_end(tmp_path: Path):
    """Verify AudioSessionAnalyzer loads audio, computes waveform peaks, speech detection, and acoustic profile."""
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Generate 440 Hz tone with a quiet silence period
    audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    audio[int(sr * 0.8) : int(sr * 1.2)] = 0.0  # 400ms pause
    wav_path = tmp_path / "test_synth.wav"
    sf.write(str(wav_path), audio.astype(np.float32), sr)

    analyzer = AudioSessionAnalyzer(target_sr=16000)

    # 1. Test load_audio
    y, loaded_sr, dur = analyzer.load_audio(wav_path)
    assert loaded_sr == 16000
    assert pytest.approx(dur, 0.05) == 2.0
    assert len(y) == len(audio)

    # 2. Test compute_waveform_peaks
    peaks, peak_dur = analyzer.compute_waveform_peaks(wav_path, num_peaks=50)
    assert len(peaks) > 0
    assert pytest.approx(peak_dur, 0.05) == 2.0
    assert max(peaks) == pytest.approx(1.0, 0.01)

    # 3. Test detect_speech
    regions, coverage = analyzer.detect_speech(wav_path)
    assert isinstance(regions, list)
    assert 0.0 <= coverage <= 1.0

    # 4. Test compute_profile
    profile = analyzer.compute_profile(wav_path)
    assert pytest.approx(profile.duration_sec, 0.05) == 2.0
    assert not np.isnan(profile.f0_median_hz)

    # 5. Test analyze_session (unified single call)
    result = analyzer.analyze_session(wav_path, num_peaks=50)
    assert isinstance(result, AudioSessionAnalysis)
    assert result.duration_sec == pytest.approx(2.0, 0.05)
    assert result.sample_rate == 16000
    assert len(result.waveform_peaks) > 0
    assert result.acoustic_profile.duration_sec == pytest.approx(2.0, 0.05)


def test_audio_session_analyzer_file_not_found():
    """Verify clean error on non-existent audio file."""
    analyzer = AudioSessionAnalyzer()
    with pytest.raises(FileNotFoundError):
        analyzer.load_audio("non_existent_audio_path_xyz.wav")
