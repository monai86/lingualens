"use client";

import React from "react";
import { Play, Pause, Repeat, Activity, Volume2 } from "lucide-react";

export interface AudioScrubberBarProps {
  isPlaying: boolean;
  currentTimeMs: number;
  durationMs: number;
  speed: number;
  isLooping: boolean;
  showPitch: boolean;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
  onToggleLoop: () => void;
  onTogglePitch: () => void;
  onSeek?: (timeMs: number) => void;
}

export function formatTimecode(ms: number): string {
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  const millis = Math.floor(ms % 1000);
  const pad = (n: number, z = 2) => String(n).padStart(z, "0");
  return `${pad(minutes)}:${pad(seconds)}.${pad(millis, 3)}`;
}

export function AudioScrubberBar({
  isPlaying,
  currentTimeMs,
  durationMs,
  speed,
  isLooping,
  showPitch,
  onPlayPause,
  onSpeedChange,
  onToggleLoop,
  onTogglePitch,
  onSeek,
}: AudioScrubberBarProps) {
  const speeds = [0.75, 1.0, 1.25];
  const progressPercent = durationMs > 0 ? Math.min(100, Math.max(0, (currentTimeMs / durationMs) * 100)) : 0;

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onSeek) {
      const targetMs = (Number(e.target.value) / 100) * durationMs;
      onSeek(targetMs);
    }
  };

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-900 px-4 py-2.5 text-white shadow-md dark:border-slate-800"
      data-testid="audio-scrubber-bar"
    >
      {/* Play/Pause & Times */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onPlayPause}
          aria-label={isPlaying ? "Pause" : "Play"}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white transition hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} className="translate-x-0.5" />}
        </button>

        <div className="font-mono text-sm tracking-tight text-slate-200">
          <span className="font-semibold text-white">{formatTimecode(currentTimeMs)}</span>
          <span className="text-slate-400"> / </span>
          <span className="text-slate-400">{formatTimecode(durationMs)}</span>
        </div>
      </div>

      {/* Scrubber slider */}
      <div className="flex min-w-[200px] flex-1 items-center px-2">
        <input
          type="range"
          min="0"
          max="100"
          step="0.01"
          value={progressPercent}
          onChange={handleScrubberChange}
          aria-label="Audio scrubber"
          className="h-1.5 w-full cursor-pointer appearance-none rounded-lg bg-slate-700 accent-blue-500 transition hover:bg-slate-600 focus:outline-none"
        />
      </div>

      {/* Speed, Loop & Pitch Controls */}
      <div className="flex items-center gap-2">
        <div className="flex rounded-md bg-slate-800 p-0.5" role="group" aria-label="Playback speed">
          {speeds.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSpeedChange(s)}
              className={`rounded px-2 py-1 text-xs font-semibold transition ${
                speed === s
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              {s.toFixed(2).replace(/\.?0+$/, "")}x
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onToggleLoop}
          aria-label="Loop"
          className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition ${
            isLooping
              ? "bg-emerald-600 text-white"
              : "bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white"
          }`}
        >
          <Repeat size={14} />
          <span>Loop</span>
        </button>

        <button
          type="button"
          onClick={onTogglePitch}
          aria-label="F0 Pitch"
          className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition ${
            showPitch
              ? "bg-amber-600 text-white"
              : "bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white"
          }`}
        >
          <Activity size={14} />
          <span>F0 Pitch</span>
        </button>
      </div>
    </div>
  );
}
