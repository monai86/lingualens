"""Prospective research helpers for Acoustic & Timing Schema v3a.

This module implements deterministic, quality-aware acoustic and conversational timing
measurements for pediatric speech-language research.

Principles:
1. Deterministic, mathematically defined implementations.
2. Coupled measurement quality indicators and explicit quality statuses.
3. No silent zero imputation: insufficient evidence outputs NaN + INSUFFICIENT_DATA status.
4. No product/API integration or clinical-readiness claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Union

import numpy as np


class QualityStatus(str, Enum):
    """Quality status enum for acoustic measurements."""
    VALID = "VALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    LOW_VOICED_COVERAGE = "LOW_VOICED_COVERAGE"
    LOW_ALIGNMENT_COVERAGE = "LOW_ALIGNMENT_COVERAGE"
    DIARIZATION_UNCERTAIN = "DIARIZATION_UNCERTAIN"
    UNSUPPORTED_AUDIO = "UNSUPPORTED_AUDIO"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class AudioQCRecord:
    """Continuous audio quality control metrics."""
    duration_seconds: float
    sample_rate_hz: int
    channel_count: int
    clipping_fraction: float
    silence_fraction: float
    speech_fraction: float
    estimated_snr_db: float
    valid_child_speech_sec: float
    valid_adult_speech_sec: float
    overlap_fraction: float
    qc_status: QualityStatus

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["qc_status"] = self.qc_status.value
        return d


@dataclass(frozen=True)
class AcousticFeaturesV3a:
    """Feature Schema v3a output vector."""
    # Response latency (Dyadic timing)
    response_latency_median_ms: float
    response_latency_iqr_ms: float
    response_latency_n_pairs: int
    response_latency_quality_status: QualityStatus

    # Pitch & Prosody (Child-intrinsic)
    pitch_f0_sd_semitones: float
    pitch_range_90_10_semitones: float
    pitch_valid_fraction: float
    voiced_duration_seconds: float
    pitch_quality_status: QualityStatus

    # Within-turn pause (Child-intrinsic)
    pause_duration_ratio: float
    pause_quality_status: QualityStatus

    # Audio QC
    audio_qc: Optional[AudioQCRecord] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["response_latency_quality_status"] = self.response_latency_quality_status.value
        d["pitch_quality_status"] = self.pitch_quality_status.value
        d["pause_quality_status"] = self.pause_quality_status.value
        if self.audio_qc:
            d["audio_qc"] = self.audio_qc.to_dict()
        return d


def hz_to_semitones(f0_hz: Union[float, np.ndarray], ref_hz: float = 50.0) -> Union[float, np.ndarray]:
    """Convert fundamental frequency in Hz to semitones relative to a base reference (default 50 Hz)."""
    if isinstance(f0_hz, (int, float)):
        if f0_hz <= 0 or not math.isfinite(f0_hz):
            return float("nan")
        return 12.0 * math.log2(f0_hz / ref_hz)
    
    arr = np.asarray(f0_hz, dtype=float)
    out = np.full_like(arr, np.nan)
    valid = (arr > 0) & np.isfinite(arr)
    out[valid] = 12.0 * np.log2(arr[valid] / ref_hz)
    return out


def compute_response_latency_from_turns(
    turns: List[dict[str, Any]],
    max_gap_ms: float = 10000.0,
    min_pairs: int = 5,
    time_unit: Literal["seconds", "milliseconds"] = "seconds",
) -> Tuple[float, float, int, QualityStatus]:
    """Compute adult->child response latency metrics from timed speaker turns.
    
    Parameters
    ----------
    turns : list of dict
        List of turn dicts containing 'speaker' (str), 'start' (float sec or ms),
        and 'end' (float sec or ms).
    max_gap_ms : float
        Upper bound (in ms) above which an adult->child transition is treated as
        an interaction pause rather than a conversational response (default 10,000 ms).
    min_pairs : int
        Minimum valid transitions required for the grouped median/IQR result.
    time_unit : {"seconds", "milliseconds"}
        Explicit unit for all turn timestamps. Mixed units are unsupported.
        
    Returns
    -------
    median_latency_ms, iqr_latency_ms, n_pairs, quality_status
    """
    if not turns or len(turns) < 2:
        return float("nan"), float("nan"), 0, QualityStatus.INSUFFICIENT_DATA

    if time_unit not in {"seconds", "milliseconds"}:
        raise ValueError("time_unit must be 'seconds' or 'milliseconds'")
    scale_to_ms = 1000.0 if time_unit == "seconds" else 1.0

    latencies: List[float] = []

    for curr, nxt in zip(turns, turns[1:]):

        curr_spk = str(curr.get("speaker", "")).upper()
        nxt_spk = str(nxt.get("speaker", "")).upper()

        # Check for adult -> child transition
        is_adult = curr_spk in {"ADULT", "INV", "MOT", "FAT", "EXP", "EXAMINER", "THERAPIST", "TEA", "SPEAKER_01"}
        is_child = nxt_spk in {"CHILD", "CHI", "TARGET_CHILD", "SPEAKER_00"}

        if is_adult and is_child:
            try:
                curr_start = float(curr["start"])
                curr_end = float(curr["end"])
                next_start = float(nxt["start"])
                next_end = float(nxt["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if not all(math.isfinite(value) for value in (curr_start, curr_end, next_start, next_end)):
                continue
            if curr_end < curr_start or next_end < next_start:
                continue

            adult_offset = curr_end * scale_to_ms
            child_onset = next_start * scale_to_ms
            
            lat_ms = child_onset - adult_offset
            # Exclude long non-interactive pauses
            if -2000.0 <= lat_ms <= max_gap_ms:
                latencies.append(lat_ms)

    n_pairs = len(latencies)
    if n_pairs < min_pairs:
        return float("nan"), float("nan"), n_pairs, QualityStatus.INSUFFICIENT_DATA

    lat_arr = np.array(latencies, dtype=float)
    median_lat = float(np.median(lat_arr))
    q75, q25 = np.percentile(lat_arr, [75, 25])
    iqr_lat = float(q75 - q25)

    return round(median_lat, 2), round(iqr_lat, 2), n_pairs, QualityStatus.VALID


def compute_pitch_f0_features(
    f0_hz_series: np.ndarray,
    voiced_mask: np.ndarray,
    total_child_duration_sec: float,
    min_voiced_sec: float = 1.0,
    min_voiced_fraction: float = 0.30,
    hop_sec: float = 0.01,
) -> Tuple[float, float, float, float, QualityStatus]:
    """Compute semitone-normalized pitch variability and range on voiced child speech.
    
    Parameters
    ----------
    f0_hz_series : np.ndarray
        Array of fundamental frequencies (in Hz).
    voiced_mask : np.ndarray
        Boolean mask indicating reliable voiced frames.
    total_child_duration_sec : float
        Total duration (in seconds) of child speech examined.
    min_voiced_sec : float
        Minimum cumulative voiced duration required for reliable pitch stats.
    min_voiced_fraction : float
        Minimum voiced fraction required.
    hop_sec : float
        Frame hop time in seconds (e.g. 10 ms = 0.01).
        
    Returns
    -------
    f0_sd_semitones, f0_range_90_10_semitones, valid_fraction, voiced_duration_sec, quality_status
    """
    if len(f0_hz_series) == 0 or total_child_duration_sec <= 0:
        return float("nan"), float("nan"), 0.0, 0.0, QualityStatus.INSUFFICIENT_DATA

    voiced_f0 = f0_hz_series[voiced_mask & np.isfinite(f0_hz_series) & (f0_hz_series > 40.0) & (f0_hz_series < 800.0)]
    n_voiced_frames = len(voiced_f0)
    voiced_duration_sec = n_voiced_frames * hop_sec
    total_frames = max(1, len(f0_hz_series))
    valid_fraction = min(1.0, n_voiced_frames / total_frames)

    if voiced_duration_sec < min_voiced_sec or valid_fraction < min_voiced_fraction:
        return float("nan"), float("nan"), round(valid_fraction, 4), round(voiced_duration_sec, 2), QualityStatus.LOW_VOICED_COVERAGE

    # Convert voiced F0 Hz to semitones
    st_series = hz_to_semitones(voiced_f0, ref_hz=50.0)
    st_series = st_series[np.isfinite(st_series)]

    if len(st_series) < 10:
        return float("nan"), float("nan"), round(valid_fraction, 4), round(voiced_duration_sec, 2), QualityStatus.LOW_VOICED_COVERAGE

    f0_sd = float(np.std(st_series))
    p90, p10 = np.percentile(st_series, [90, 10])
    f0_range = float(p90 - p10)

    return round(f0_sd, 3), round(f0_range, 3), round(valid_fraction, 4), round(voiced_duration_sec, 2), QualityStatus.VALID


def compute_within_turn_pause_ratio(
    child_speech_segments: List[Tuple[float, float]],
    child_turn_bounds: List[Tuple[float, float]],
    min_pause_ms: float = 200.0,
    min_child_speech_sec: float = 3.0,
) -> Tuple[float, QualityStatus]:
    """Compute ratio of within-child-turn silence to total child speaking time.
    
    Parameters
    ----------
    child_speech_segments : list of (start_sec, end_sec)
        VAD-detected speech regions within child utterances.
    child_turn_bounds : list of (turn_start_sec, turn_end_sec)
        Overall boundaries of child turns.
    min_pause_ms : float
        Minimum silence duration in ms to count as an internal planning pause.
    min_child_speech_sec : float
        Minimum total child speech duration required.
        
    Returns
    -------
    pause_duration_ratio, quality_status
    """
    if not child_turn_bounds:
        return float("nan"), QualityStatus.INSUFFICIENT_DATA

    min_pause_sec = min_pause_ms / 1000.0
    internal_pause_sec = 0.0
    total_child_speech_sec = 0.0

    for turn_start, turn_end in child_turn_bounds:
        # Find all speech segments strictly inside this turn
        segs_in_turn = [
            (max(turn_start, s), min(turn_end, e))
            for s, e in child_speech_segments
            if s < turn_end and e > turn_start
        ]
        segs_in_turn = sorted(segs_in_turn, key=lambda x: x[0])
        merged: list[tuple[float, float]] = []
        for start, end in segs_in_turn:
            if end <= start:
                continue
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        total_child_speech_sec += sum(end - start for start, end in merged)
        for i in range(len(merged) - 1):
            gap = merged[i + 1][0] - merged[i][1]
            if gap >= min_pause_sec:
                internal_pause_sec += gap

    if total_child_speech_sec < min_child_speech_sec:
        return float("nan"), QualityStatus.INSUFFICIENT_DATA

    pause_ratio = min(1.0, max(0.0, internal_pause_sec / total_child_speech_sec))
    return round(pause_ratio, 4), QualityStatus.VALID


def compute_audio_qc_metrics(
    y_audio: np.ndarray,
    sr: int,
    child_speech_sec: float = 0.0,
    adult_speech_sec: float = 0.0,
    overlap_speech_sec: float = 0.0,
) -> AudioQCRecord:
    """Compute continuous objective audio quality control metrics."""
    duration = float(len(y_audio) / sr) if sr > 0 else 0.0
    if duration <= 0 or len(y_audio) == 0:
        return AudioQCRecord(
            duration_seconds=0.0,
            sample_rate_hz=sr,
            channel_count=1,
            clipping_fraction=0.0,
            silence_fraction=1.0,
            speech_fraction=0.0,
            estimated_snr_db=0.0,
            valid_child_speech_sec=0.0,
            valid_adult_speech_sec=0.0,
            overlap_fraction=0.0,
            qc_status=QualityStatus.UNSUPPORTED_AUDIO,
        )

    # Clipping detection: sample >= 0.999 of max scale
    clipping_count = np.sum(np.abs(y_audio) >= 0.999)
    clipping_fraction = float(clipping_count / len(y_audio))

    # Energy-based SNR estimation via frame RMS
    frame_len = int(0.032 * sr)
    hop_len = int(0.016 * sr)
    
    if len(y_audio) >= frame_len:
        num_frames = (len(y_audio) - frame_len) // hop_len + 1
        frames = np.lib.stride_tricks.as_strided(
            y_audio,
            shape=(num_frames, frame_len),
            strides=(y_audio.strides[0] * hop_len, y_audio.strides[0]),
        )
        rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
        
        # 10th percentile as noise floor, 90th as signal level
        p10 = float(np.percentile(rms, 10))
        p90 = float(np.percentile(rms, 90))
        noise_floor = max(1e-6, p10)
        signal_level = max(noise_floor, p90)
        estimated_snr_db = float(20.0 * np.log10(signal_level / noise_floor))

        silence_mask = rms < (noise_floor * 2.0)
        silence_fraction = float(np.mean(silence_mask))
        speech_fraction = float(1.0 - silence_fraction)
    else:
        estimated_snr_db = 0.0
        silence_fraction = 0.0
        speech_fraction = 1.0

    overlap_fraction = float(overlap_speech_sec / duration) if duration > 0 else 0.0

    qc_status = QualityStatus.VALID if (sr >= 16000 and duration >= 5.0) else QualityStatus.UNSUPPORTED_AUDIO

    return AudioQCRecord(
        duration_seconds=round(duration, 3),
        sample_rate_hz=sr,
        channel_count=1,
        clipping_fraction=round(clipping_fraction, 6),
        silence_fraction=round(silence_fraction, 4),
        speech_fraction=round(speech_fraction, 4),
        estimated_snr_db=round(estimated_snr_db, 2),
        valid_child_speech_sec=round(child_speech_sec, 2),
        valid_adult_speech_sec=round(adult_speech_sec, 2),
        overlap_fraction=round(overlap_fraction, 4),
        qc_status=qc_status,
    )
