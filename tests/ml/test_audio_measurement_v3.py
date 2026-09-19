"""Unit tests for Feature Schema v3a acoustic measurements and quality controls."""

import math
from pathlib import Path
import sys

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.features.acoustic_features import (
    AcousticFeaturesV3a,
    AudioQCRecord,
    QualityStatus,
    compute_audio_qc_metrics,
    compute_pitch_f0_features,
    compute_response_latency_from_turns,
    compute_within_turn_pause_ratio,
    hz_to_semitones,
)


def test_hz_to_semitones_math():
    """Verify semitone conversion relative to 50 Hz reference."""
    # 50 Hz should be 0 semitones
    assert pytest.approx(hz_to_semitones(50.0), abs=1e-4) == 0.0
    # 100 Hz (1 octave above 50 Hz) should be 12 semitones
    assert pytest.approx(hz_to_semitones(100.0), abs=1e-4) == 12.0
    # 200 Hz (2 octaves above 50 Hz) should be 24 semitones
    assert pytest.approx(hz_to_semitones(200.0), abs=1e-4) == 24.0
    # 25 Hz (1 octave below 50 Hz) should be -12 semitones
    assert pytest.approx(hz_to_semitones(25.0), abs=1e-4) == -12.0
    # Invalid frequencies return NaN
    assert math.isnan(hz_to_semitones(0.0))
    assert math.isnan(hz_to_semitones(-10.0))


def test_response_latency_positive_gap():
    """Test standard positive response latency (gap between adult and child)."""
    turns = [
        {"speaker": "INV", "start": 0.0, "end": 2.0},
        {"speaker": "CHI", "start": 2.5, "end": 4.0},   # Latency = +500 ms
        {"speaker": "INV", "start": 5.0, "end": 6.0},
        {"speaker": "CHI", "start": 6.3, "end": 8.0},   # Latency = +300 ms
        {"speaker": "INV", "start": 9.0, "end": 10.0},
        {"speaker": "CHI", "start": 10.4, "end": 12.0}, # Latency = +400 ms
        {"speaker": "INV", "start": 13.0, "end": 14.0},
        {"speaker": "CHI", "start": 14.6, "end": 15.0}, # Latency = +600 ms
        {"speaker": "INV", "start": 16.0, "end": 17.0},
        {"speaker": "CHI", "start": 17.2, "end": 18.0}, # Latency = +200 ms
    ]
    median_lat, iqr_lat, n_pairs, status = compute_response_latency_from_turns(turns)
    assert status == QualityStatus.VALID
    assert n_pairs == 5
    assert pytest.approx(median_lat, abs=1.0) == 400.0
    assert pytest.approx(iqr_lat, abs=1.0) == 200.0


def test_response_latency_zero_and_negative_overlap():
    """Test immediate zero transitions and negative overlaps."""
    turns = [
        {"speaker": "INV", "start": 0.0, "end": 2.0},
        {"speaker": "CHI", "start": 2.0, "end": 3.5},   # Latency = 0 ms (immediate)
        {"speaker": "INV", "start": 4.0, "end": 6.0},
        {"speaker": "CHI", "start": 5.8, "end": 7.5},   # Latency = -200 ms (overlap)
        {"speaker": "INV", "start": 8.0, "end": 10.0},
        {"speaker": "CHI", "start": 10.1, "end": 11.5}, # Latency = +100 ms
        {"speaker": "INV", "start": 12.0, "end": 14.0},
        {"speaker": "CHI", "start": 13.9, "end": 15.0}, # Latency = -100 ms
        {"speaker": "INV", "start": 16.0, "end": 18.0},
        {"speaker": "CHI", "start": 18.2, "end": 19.0}, # Latency = +200 ms
    ]
    median_lat, iqr_lat, n_pairs, status = compute_response_latency_from_turns(turns)
    assert status == QualityStatus.VALID
    assert n_pairs == 5
    # Latencies: [-200, -100, 0, 100, 200] -> median 0, IQR 200.
    assert pytest.approx(median_lat, abs=1.0) == 0.0
    assert pytest.approx(iqr_lat, abs=1.0) == 200.0


def test_response_latency_insufficient_pairs_returns_nan_not_zero():
    """Verify that fewer than min_pairs returns NaN and INSUFFICIENT_DATA, never 0.0."""
    turns = [
        {"speaker": "INV", "start": 0.0, "end": 2.0},
        {"speaker": "CHI", "start": 2.5, "end": 4.0},   # Only 1 pair
    ]
    median_lat, iqr_lat, n_pairs, status = compute_response_latency_from_turns(turns, min_pairs=3)
    assert status == QualityStatus.INSUFFICIENT_DATA
    assert n_pairs == 1
    assert math.isnan(median_lat)
    assert math.isnan(iqr_lat)


def test_response_latency_iqr_requires_five_pairs_and_rejects_extreme_overlap():
    """The grouped latency result requires five pairs and a -2 s minimum."""
    turns = [
        {"speaker": "INV", "start": 0.0, "end": 5.0},
        {"speaker": "CHI", "start": 1.0, "end": 2.0},  # -4000 ms: invalid
        {"speaker": "INV", "start": 10.0, "end": 11.0},
        {"speaker": "CHI", "start": 11.2, "end": 12.0},
        {"speaker": "INV", "start": 20.0, "end": 21.0},
        {"speaker": "CHI", "start": 21.3, "end": 22.0},
        {"speaker": "INV", "start": 30.0, "end": 31.0},
        {"speaker": "CHI", "start": 31.4, "end": 32.0},
    ]

    median_lat, iqr_lat, n_pairs, status = compute_response_latency_from_turns(turns)

    assert n_pairs == 3
    assert math.isnan(median_lat)
    assert math.isnan(iqr_lat)
    assert status == QualityStatus.INSUFFICIENT_DATA


def test_response_latency_rejects_missing_or_nonfinite_boundaries():
    turns = []
    for index in range(5):
        turns.extend(
            [
                {"speaker": "INV", "start": float(index * 10)},
                {"speaker": "CHI", "start": float(index * 10 + 4.2), "end": float(index * 10 + 5)},
            ]
        )
    turns.extend(
        [
            {"speaker": "INV", "start": 60.0, "end": float("nan")},
            {"speaker": "CHI", "start": 61.0, "end": 62.0},
        ]
    )

    median_lat, iqr_lat, n_pairs, status = compute_response_latency_from_turns(turns)

    assert n_pairs == 0
    assert math.isnan(median_lat)
    assert math.isnan(iqr_lat)
    assert status == QualityStatus.INSUFFICIENT_DATA


def test_pitch_f0_features_valid():
    """Test semitone pitch variability on simulated voiced speech."""
    sr = 16000
    hop_sec = 0.01
    duration_sec = 5.0
    n_frames = int(duration_sec / hop_sec)

    # Simulated pitch varying smoothly around 200 Hz (Child pitch)
    time = np.linspace(0, duration_sec, n_frames)
    f0_series = 200.0 + 30.0 * np.sin(2 * np.pi * 1.5 * time) # 170 Hz to 230 Hz
    voiced_mask = np.ones(n_frames, dtype=bool)

    f0_sd, f0_range, valid_frac, voiced_sec, status = compute_pitch_f0_features(
        f0_series, voiced_mask, total_child_duration_sec=duration_sec, hop_sec=hop_sec
    )

    assert status == QualityStatus.VALID
    assert valid_frac == 1.0
    assert pytest.approx(voiced_sec, abs=0.1) == 5.0
    assert f0_sd > 0.5 and f0_sd < 5.0 # Plausible semitone SD
    assert f0_range > 1.0 and f0_range < 10.0


def test_pitch_f0_features_low_voiced_coverage():
    """Test pitch extractor when voiced coverage is below threshold."""
    hop_sec = 0.01
    duration_sec = 10.0
    n_frames = int(duration_sec / hop_sec)

    f0_series = np.full(n_frames, 200.0)
    voiced_mask = np.zeros(n_frames, dtype=bool)
    voiced_mask[:20] = True # Only 20 frames = 0.20 sec (< 1.0s required)

    f0_sd, f0_range, valid_frac, voiced_sec, status = compute_pitch_f0_features(
        f0_series, voiced_mask, total_child_duration_sec=duration_sec, min_voiced_sec=1.0, hop_sec=hop_sec
    )

    assert status == QualityStatus.LOW_VOICED_COVERAGE
    assert math.isnan(f0_sd)
    assert math.isnan(f0_range)
    assert voiced_sec == 0.20


def test_pitch_f0_default_requires_thirty_percent_voiced_coverage():
    """The implementation default must match the v3a public 30% threshold."""
    f0_series = np.full(500, 200.0)
    voiced_mask = np.zeros(500, dtype=bool)
    voiced_mask[:125] = True  # 1.25 s but only 25% of child frames

    f0_sd, f0_range, valid_frac, voiced_sec, status = compute_pitch_f0_features(
        f0_series,
        voiced_mask,
        total_child_duration_sec=5.0,
    )

    assert status == QualityStatus.LOW_VOICED_COVERAGE
    assert math.isnan(f0_sd)
    assert math.isnan(f0_range)
    assert valid_frac == 0.25
    assert voiced_sec == 1.25


def test_within_turn_pause_ratio():
    """Test pause ratio within child turn boundaries."""
    # Child turn is from 0.0 to 10.0s (Total = 10.0s)
    # Child speech bursts: [0.0 - 3.0], [3.5 - 6.5], [7.0 - 10.0]
    # Internal pauses >= 200ms: [3.0 - 3.5] (0.5s) and [6.5 - 7.0] (0.5s) -> Total = 1.0s pause
    child_turn_bounds = [(0.0, 10.0)]
    child_speech_segments = [(0.0, 3.0), (3.5, 6.5), (7.0, 10.0)]

    pause_ratio, status = compute_within_turn_pause_ratio(
        child_speech_segments, child_turn_bounds, min_pause_ms=200.0, min_child_speech_sec=3.0
    )

    assert status == QualityStatus.VALID
    # 1.0s pause / 9.0s detected child speech = 0.1111
    assert pytest.approx(pause_ratio, abs=1e-4) == 0.1111


def test_within_turn_pause_ratio_insufficient_data():
    """Test pause ratio when total child speech is too short."""
    child_turn_bounds = [(0.0, 1.5)] # 1.5s < 3.0s threshold
    child_speech_segments = [(0.0, 1.5)]

    pause_ratio, status = compute_within_turn_pause_ratio(
        child_speech_segments, child_turn_bounds, min_child_speech_sec=3.0
    )

    assert status == QualityStatus.INSUFFICIENT_DATA
    assert math.isnan(pause_ratio)


def test_compute_audio_qc_metrics_synthetic():
    """Test continuous audio QC metrics on synthetic sine wave audio."""
    sr = 16000
    duration = 10.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Sine wave with amplitude 0.5 (no clipping)
    y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    qc = compute_audio_qc_metrics(y, sr=sr, child_speech_sec=4.0, adult_speech_sec=5.0, overlap_speech_sec=0.5)

    assert qc.qc_status == QualityStatus.VALID
    assert qc.sample_rate_hz == 16000
    assert pytest.approx(qc.duration_seconds, abs=0.01) == 10.0
    assert qc.clipping_fraction == 0.0
    assert qc.valid_child_speech_sec == 4.0
    assert qc.valid_adult_speech_sec == 5.0
    assert qc.overlap_fraction == 0.05
    assert qc.estimated_snr_db > 0.0


def test_acoustic_features_v3a_serialization():
    """Verify dataclass serialization to dict."""
    feat = AcousticFeaturesV3a(
        response_latency_median_ms=450.0,
        response_latency_iqr_ms=180.0,
        response_latency_n_pairs=12,
        response_latency_quality_status=QualityStatus.VALID,
        pitch_f0_sd_semitones=2.45,
        pitch_range_90_10_semitones=6.80,
        pitch_valid_fraction=0.85,
        voiced_duration_seconds=14.2,
        pitch_quality_status=QualityStatus.VALID,
        pause_duration_ratio=0.125,
        pause_quality_status=QualityStatus.VALID,
    )
    d = feat.to_dict()
    assert d["response_latency_median_ms"] == 450.0
    assert d["response_latency_quality_status"] == "VALID"
    assert d["pitch_f0_sd_semitones"] == 2.45
    assert d["pitch_quality_status"] == "VALID"
    assert d["pause_duration_ratio"] == 0.125
