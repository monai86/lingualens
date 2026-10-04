"use client";

import React, { useState, useEffect } from "react";
import { Gauge, Radio, Clock, ShieldCheck } from "lucide-react";
import { WaveformMinimap } from "./waveform-minimap";
import { WaveformDetailCanvas, type WaveformSegment } from "./waveform-detail-canvas";

export interface DualViewWaveformProps {
  currentTimeMs: number;
  durationMs: number;
  segments: WaveformSegment[];
  peaks?: Int8Array | null;
  snrDb?: number;
  diarizationConfidence?: number;
  responseLatencyMs?: number;
  showPitch?: boolean;
  onSeek?: (timeMs: number) => void;
  onSegmentBoundaryChange?: (segmentId: string, startMs: number, endMs: number) => void;
  className?: string;
}

export function DualViewWaveform({
  currentTimeMs,
  durationMs,
  segments,
  peaks,
  snrDb,
  diarizationConfidence,
  responseLatencyMs,
  showPitch = false,
  onSeek,
  onSegmentBoundaryChange,
  className = "",
}: DualViewWaveformProps) {
  // Zoom window duration (e.g. 20 seconds = 20,000 ms)
  const DETAIL_WINDOW_MS = 20000;

  // Viewport window state
  const [viewportStartMs, setViewportStartMs] = useState(0);
  const [viewportEndMs, setViewportEndMs] = useState(Math.min(durationMs || DETAIL_WINDOW_MS, DETAIL_WINDOW_MS));

  // Automatically keep viewport centered around currentTimeMs when playing outside window
  useEffect(() => {
    if (currentTimeMs < viewportStartMs || currentTimeMs > viewportEndMs) {
      const half = DETAIL_WINDOW_MS / 2;
      let start = Math.max(0, currentTimeMs - half);
      let end = start + DETAIL_WINDOW_MS;
      if (durationMs > 0 && end > durationMs) {
        end = durationMs;
        start = Math.max(0, durationMs - DETAIL_WINDOW_MS);
      }
      setViewportStartMs(start);
      setViewportEndMs(end);
    }
  }, [currentTimeMs, viewportStartMs, viewportEndMs, durationMs]);

  const handleViewportChange = (newStart: number, newEnd: number) => {
    setViewportStartMs(newStart);
    setViewportEndMs(newEnd);
  };

  return (
    <div
      className={`flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/90 p-3 text-slate-100 shadow-xl ${className}`}
      data-testid="dual-view-waveform"
    >
      {/* Top Header Bar: Track Legends & Quality KPIs */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2 text-xs">
        {/* Track Legends */}
        <div className="flex items-center gap-3">
          <span className="font-semibold text-slate-300">Tracks:</span>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-blue-500 ring-2 ring-blue-500/30" />
            <span className="font-medium text-blue-300">CHI (Child)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-500/30" />
            <span className="font-medium text-emerald-300">INV (Clinician)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-purple-500 ring-2 ring-purple-500/30" />
            <span className="font-medium text-purple-300">OTH / Parent</span>
          </div>
        </div>

        {/* Quality Indicators */}
        <div className="flex items-center gap-3 font-mono">
          {typeof snrDb === "number" && (
            <div
              className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-slate-300"
              title="Signal-to-Noise Ratio (Clean audio > 15 dB)"
            >
              <Radio size={12} className="text-sky-400" />
              <span>SNR: {snrDb.toFixed(1)} dB</span>
            </div>
          )}

          {typeof diarizationConfidence === "number" && (
            <div
              className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-slate-300"
              title="Diarization Alignment Confidence"
            >
              <ShieldCheck size={12} className="text-emerald-400" />
              <span>Diarization: {diarizationConfidence.toFixed(1)}%</span>
            </div>
          )}

          {typeof responseLatencyMs === "number" && (
            <div
              className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-slate-300"
              title="Clinician-to-Child Turn-taking Latency"
            >
              <Clock size={12} className="text-amber-400" />
              <span>Latency: {Math.round(responseLatencyMs)} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Mini-map Full Overview */}
      <div className="relative">
        <WaveformMinimap
          durationMs={durationMs}
          currentTimeMs={currentTimeMs}
          viewportStartMs={viewportStartMs}
          viewportEndMs={viewportEndMs}
          peaks={peaks}
          onViewportChange={handleViewportChange}
          onSeek={onSeek}
        />
      </div>

      {/* High-Resolution Detail Canvas */}
      <div className="relative">
        <WaveformDetailCanvas
          currentTimeMs={currentTimeMs}
          viewportStartMs={viewportStartMs}
          viewportEndMs={viewportEndMs}
          segments={segments}
          peaks={peaks}
          showPitch={showPitch}
          onSeek={onSeek}
          onSegmentBoundaryChange={onSegmentBoundaryChange}
        />
      </div>
    </div>
  );
}
