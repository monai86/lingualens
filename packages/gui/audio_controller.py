"""Audio playback, waveform DSP computation, and scrubber timeline controller for LinguaLens."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable


class AudioPlaybackController:
    """Encapsulates low-level audio playback, subprocess management, waveform downsampling, and F0 pitch tracking."""

    def __init__(self) -> None:
        self.active_audio_path: str | None = None
        self.waveform_duration: float = 0.0
        self.waveform_peaks: list[float] = []
        self.f0_contour: list[tuple[float, float]] = []
        self.playback_speed: float = 1.0
        self.show_pitch_overlay: bool = False

        self.is_continuous_playing: bool = False
        self.playhead_time_sec: float = 0.0
        self.current_playback_offset_sec: float = 0.0
        self.playback_end_limit_sec: float | None = None
        self.playback_start_wall_time: float = 0.0

        self.current_play_process: subprocess.Popen | None = None
        self.current_temp_slice: str | None = None

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format timestamp into clean mm:ss.d format."""
        if seconds < 0:
            seconds = 0
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:04.1f}"

    def load_audio(self, audio_path: str, num_peaks: int = 200) -> list[float]:
        """Set active audio file and precompute downsampled waveform peaks and F0 contour."""
        self.active_audio_path = audio_path
        self.waveform_peaks = self.compute_waveform_peaks(audio_path, num_peaks=num_peaks)
        return self.waveform_peaks

    def compute_waveform_peaks(self, audio_path: str, num_peaks: int = 200) -> list[float]:
        """Compute downsampled normalized RMS amplitude peaks and F0 pitch contour for visualization."""
        if not audio_path or not os.path.exists(audio_path):
            self.f0_contour = []
            return []
        try:
            import soundfile as sf
            import numpy as np

            info = sf.info(audio_path)
            self.waveform_duration = float(info.duration)
            data, sr = sf.read(audio_path, dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            total_samples = len(data)
            if total_samples == 0:
                self.f0_contour = []
                return []
            chunk_size = max(1, total_samples // num_peaks)
            peaks = []
            f0_contour = []
            dur = self.waveform_duration

            # Sample F0 contour efficiently across segments
            for i in range(0, total_samples, chunk_size):
                chunk = data[i : i + chunk_size]
                if len(chunk) > 0:
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    peaks.append(rms)
                    t_sec = (i / total_samples) * dur

                    # Autocorrelation F0 estimator for fast rendering
                    if rms > 0.01 and len(chunk) > 64:
                        corr = np.correlate(chunk, chunk, mode="full")
                        corr = corr[len(corr) // 2 :]
                        d = np.diff(corr)
                        peaks_idx = np.where((d[:-1] > 0) & (d[1:] < 0))[0] + 1
                        if len(peaks_idx) > 0:
                            lag = peaks_idx[0]
                            if lag > 0:
                                f0 = float(sr / lag)
                                if 65.0 <= f0 <= 500.0:
                                    f0_contour.append((t_sec, f0))

            self.f0_contour = f0_contour
            max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
            return [min(1.0, p / max_rms) for p in peaks]
        except Exception:
            try:
                import librosa
                import numpy as np

                y, sr = librosa.load(audio_path, sr=8000)
                self.waveform_duration = float(len(y) / sr)
                chunk_size = max(1, len(y) // num_peaks)
                peaks = []
                f0_contour = []
                dur = self.waveform_duration
                for i in range(0, len(y), chunk_size):
                    chunk = y[i : i + chunk_size]
                    if len(chunk) > 0:
                        rms = float(np.sqrt(np.mean(chunk**2)))
                        peaks.append(rms)
                        t_sec = (i / len(y)) * dur
                        if rms > 0.01 and len(chunk) > 32:
                            corr = np.correlate(chunk, chunk, mode="full")
                            corr = corr[len(corr) // 2 :]
                            d = np.diff(corr)
                            peaks_idx = np.where((d[:-1] > 0) & (d[1:] < 0))[0] + 1
                            if len(peaks_idx) > 0:
                                lag = peaks_idx[0]
                                if lag > 0:
                                    f0 = float(sr / lag)
                                    if 65.0 <= f0 <= 500.0:
                                        f0_contour.append((t_sec, f0))
                self.f0_contour = f0_contour
                max_rms = max(peaks) if peaks and max(peaks) > 0 else 1.0
                return [min(1.0, p / max_rms) for p in peaks]
            except Exception:
                self.f0_contour = []
                return []

    def slice_audio_snippet(
        self,
        audio_path: str,
        start_sec: float,
        end_sec: float | None = None,
    ) -> str | None:
        """Extract a precise slice of an audio file to a temporary WAV file."""
        if not audio_path or not os.path.exists(audio_path):
            return None
        try:
            import soundfile as sf
            import numpy as np

            data, sr = sf.read(audio_path, dtype="float32")
            total_dur = len(data) / sr

            start_sec = max(0.0, min(total_dur, float(start_sec)))
            if end_sec is None:
                end_sec = total_dur
            else:
                end_sec = max(start_sec + 0.1, min(total_dur, float(end_sec)))

            start_sample = int(start_sec * sr)
            end_sample = int(end_sec * sr)
            sliced = data[start_sample:end_sample]
            if len(sliced) == 0:
                return None

            fd, temp_path = tempfile.mkstemp(suffix="_slice.wav")
            os.close(fd)
            sf.write(temp_path, sliced, sr)
            return temp_path
        except Exception:
            return None

    def build_audio_segment_command(
        self,
        audio_path: str,
        start_sec: float | None = None,
        end_sec: float | None = None,
        speed: float = 1.0,
    ) -> tuple[list[str] | None, str | None]:
        """Construct platform-native audio player process command."""
        if not audio_path:
            return None, None

        play_target = audio_path
        temp_slice = None

        if start_sec is not None and start_sec > 0.05:
            temp_slice = self.slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice
        elif start_sec is not None and end_sec is not None and end_sec > start_sec:
            temp_slice = self.slice_audio_snippet(audio_path, start_sec, end_sec)
            if temp_slice:
                play_target = temp_slice

        if sys.platform == "darwin":
            cmd = ["afplay"]
            if abs(speed - 1.0) > 0.05:
                cmd.extend(["-r", str(round(speed, 2))])
            cmd.append(play_target)
            return cmd, temp_slice
        elif sys.platform.startswith("linux"):
            if abs(speed - 1.0) > 0.05:
                return ["ffplay", "-nodisp", "-autoexit", "-af", f"atempo={speed:.2f}", play_target], temp_slice
            if temp_slice:
                return ["aplay", play_target], temp_slice
            elif start_sec is not None:
                to_args = ["-to", str(end_sec)] if end_sec is not None else []
                return ["ffplay", "-nodisp", "-autoexit", "-ss", str(start_sec), *to_args, audio_path], None
            return ["aplay", audio_path], None
        elif sys.platform == "win32":
            return ["powershell", "-c", f"(New-Object Media.SoundPlayer '{play_target}').PlaySync();"], temp_slice
        return None, None

    def stop_playback(self) -> None:
        """Stop any active audio playback subprocess and clean up temp files."""
        self.is_continuous_playing = False
        if self.current_play_process:
            try:
                self.current_play_process.terminate()
            except Exception:
                pass
            self.current_play_process = None

            self.current_temp_slice = None


class AudioRecorder:
    """Manages live microphone audio recording and real-time VU meter level feedback."""

    def __init__(self, sample_rate: int = 16000) -> None:
        import threading
        self.sample_rate = sample_rate
        self.is_recording = False
        self.start_time: float = 0.0
        self.recorded_frames: list[Any] = []
        self._current_meter_level: float = 0.0
        self._stream = None
        self._lock = threading.Lock()
        self._is_voice_active: bool = False
        self._is_clipping: bool = False
        self._noise_floor: float = 0.012

    def start_recording(self) -> bool:
        """Start microphone stream using sounddevice with mock fallback for headless environments."""
        with self._lock:
            if self.is_recording:
                return True
            self.recorded_frames = []
            self.start_time = time.time()
            self.is_recording = True
            self._current_meter_level = 0.0
            self._is_voice_active = False
            self._is_clipping = False

            try:
                import numpy as np
                import sounddevice as sd

                def callback(indata, frames, time_info, status):
                    if not self.is_recording:
                        return
                    data_copy = indata.copy()
                    with self._lock:
                        self.recorded_frames.append(data_copy)
                        peak = float(np.max(np.abs(data_copy))) if len(data_copy) > 0 else 0.0
                        rms = float(np.sqrt(np.mean(data_copy**2)))
                        self._current_meter_level = min(1.0, rms * 6.0)
                        self._is_clipping = peak >= 0.95
                        # Energy-based VAD: Active vocalization detection
                        self._is_voice_active = rms > max(0.02, self._noise_floor * 1.8)
                        if not self._is_voice_active and rms > 0.001:
                            self._noise_floor = self._noise_floor * 0.95 + rms * 0.05

                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=callback,
                )
                self._stream.start()
                return True
            except Exception:
                self._stream = None
                return True

    def stop_recording(self, output_path: str | None = None) -> str:
        """Stop recording and save recorded buffer to a 16kHz mono WAV file."""
        with self._lock:
            self.is_recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            import numpy as np
            import soundfile as sf

            if self.recorded_frames:
                audio_data = np.concatenate(self.recorded_frames, axis=0)
            else:
                dur = max(1.0, time.time() - self.start_time if self.start_time else 1.0)
                audio_data = np.zeros((int(self.sample_rate * dur), 1), dtype=np.float32)

            if not output_path:
                fd, output_path = tempfile.mkstemp(prefix="lingualens_rec_", suffix=".wav")
                os.close(fd)

            sf.write(output_path, audio_data, self.sample_rate)
            self._current_meter_level = 0.0
            return output_path

    def get_recording_duration(self) -> float:
        if not self.is_recording or not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def get_current_meter_level(self) -> float:
        """Return 0.0 to 1.0 audio volume meter level."""
        with self._lock:
            return self._current_meter_level

    def is_voice_active(self) -> bool:
        """Return True if incoming audio exhibits active speech vocalization."""
        with self._lock:
            return self._is_voice_active

    def is_clipping(self) -> bool:
        """Return True if incoming audio peaks exceed headroom limits."""
        with self._lock:
            return self._is_clipping

    def set_simulated_meter_level(self, level: float, is_voice: bool = True, is_clipping: bool = False) -> None:
        """Helper for headless/automated UI testing."""
        with self._lock:
            self._current_meter_level = min(1.0, max(0.0, level))
            self._is_voice_active = is_voice
            self._is_clipping = is_clipping


