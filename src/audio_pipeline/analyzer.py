"""Unified Audio Session Analyzer providing DSP, acoustic profiling, and speech detection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

from src.audio_pipeline.acoustic_profile import AcousticProfile, compute_acoustic_profile
from src.audio_pipeline.vad import VADConfig, detect_speech_regions, speech_coverage


@dataclass(frozen=True)
class AudioSessionAnalysis:
    """Comprehensive acoustic and speech analysis result for a session recording."""

    audio_path: str
    duration_sec: float
    sample_rate: int
    acoustic_profile: AcousticProfile
    waveform_peaks: list[float]
    speech_regions: list[tuple[float, float]]
    speech_coverage: float


class AudioSessionAnalyzer:
    """Deep interface consolidating audio loading, VAD, acoustic profiling, and waveform DSP."""

    def __init__(self, target_sr: int = 16000) -> None:
        self.target_sr = target_sr

    def load_audio(self, audio_path: str | Path) -> tuple[np.ndarray, int, float]:
        """Load audio with automatic fallback between soundfile and librosa, resampled to target_sr."""
        p = Path(audio_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found at: {p}")

        try:
            import soundfile as sf
            data, sr = sf.read(str(p), dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != self.target_sr:
                import librosa
                data = librosa.resample(data, orig_sr=sr, target_sr=self.target_sr)
                sr = self.target_sr
        except Exception:
            import librosa
            data, sr = librosa.load(str(p), sr=self.target_sr, mono=True)

        duration = float(len(data) / sr) if sr else 0.0
        return data, sr, duration

    def compute_waveform_peaks(
        self,
        audio_path: str | Path,
        num_peaks: int = 200,
        y: np.ndarray | None = None,
        sr: int | None = None,
    ) -> tuple[list[float], float]:
        """Compute downsampled normalized amplitude envelope peaks for waveform rendering."""
        if y is None or sr is None:
            data, sample_rate, duration = self.load_audio(audio_path)
        else:
            data = y
            sample_rate = sr
            duration = float(len(data) / sample_rate) if sample_rate else 0.0

        if len(data) == 0:
            return [], 0.0

        chunk_size = max(1, len(data) // num_peaks)
        peaks: list[float] = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            if len(chunk) > 0:
                rms = float(np.sqrt(np.mean(chunk**2)))
                peaks.append(rms)

        max_peak = max(peaks) if peaks else 1.0
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]

        return peaks, duration

    def compute_profile(
        self,
        audio_path: str | Path,
        utterances: list[Any] | None = None,
        *,
        y: np.ndarray | None = None,
        sr: int | None = None,
    ) -> AcousticProfile:
        """Extract descriptive clinical acoustic profile including F0 median and IQR."""
        return compute_acoustic_profile(
            audio_path,
            utterances=utterances,
            y_audio=y,
            sr_audio=sr or self.target_sr,
        )

    def detect_speech(
        self,
        audio_path: str | Path,
        config: Optional[VADConfig] = None,
        *,
        y: np.ndarray | None = None,
        sr: int | None = None,
    ) -> tuple[list[tuple[float, float]], float]:
        """Detect voiced speech regions and calculate speech coverage percentage."""
        cfg = config or VADConfig()
        regions = detect_speech_regions(str(audio_path), config=cfg)
        if y is not None and sr is not None:
            duration = float(len(y) / sr) if sr else 0.0
        else:
            _, _, duration = self.load_audio(audio_path)
        cov = speech_coverage(regions, duration)
        return regions, cov

    def analyze_session(
        self,
        audio_path: str | Path,
        utterances: list[Any] | None = None,
        num_peaks: int = 200,
        vad_config: Optional[VADConfig] = None,
    ) -> AudioSessionAnalysis:
        """Perform end-to-end DSP analysis on an audio file in a single unified execution pass."""
        p = Path(audio_path).resolve()
        y, sr, duration = self.load_audio(p)
        peaks, _ = self.compute_waveform_peaks(p, num_peaks=num_peaks, y=y, sr=sr)
        profile = self.compute_profile(p, utterances=utterances, y=y, sr=sr)
        regions, coverage = self.detect_speech(p, config=vad_config, y=y, sr=sr)

        return AudioSessionAnalysis(
            audio_path=str(p),
            duration_sec=duration,
            sample_rate=sr,
            acoustic_profile=profile,
            waveform_peaks=peaks,
            speech_regions=regions,
            speech_coverage=coverage,
        )
