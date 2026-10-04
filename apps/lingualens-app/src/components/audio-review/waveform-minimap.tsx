"use client";

import React, { useRef, useEffect, useCallback } from "react";

export interface WaveformMinimapProps {
  durationMs: number;
  currentTimeMs: number;
  viewportStartMs: number;
  viewportEndMs: number;
  peaks?: Int8Array | null;
  onViewportChange?: (startMs: number, endMs: number) => void;
  onSeek?: (timeMs: number) => void;
  className?: string;
}

export function WaveformMinimap({
  durationMs,
  currentTimeMs,
  viewportStartMs,
  viewportEndMs,
  peaks,
  onViewportChange,
  onSeek,
  className = "",
}: WaveformMinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef(false);

  // Draw full-duration overview waveform
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext("2d");
    } catch {
      return;
    }
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const midY = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = "#0f172a"; // Slate-900
    ctx.fillRect(0, 0, width, height);

    // Draw peaks if available, else synthetic fallback envelope
    if (peaks && peaks.length > 0) {
      const numPoints = peaks.length;
      const step = numPoints / width;

      ctx.fillStyle = "#38bdf8"; // Sky-400
      ctx.beginPath();
      for (let x = 0; x < width; x++) {
        const peakIdx = Math.floor(x * step);
        const val = Math.abs(peaks[peakIdx] || 0) / 128.0;
        const barHeight = Math.max(1, val * (height / 2 - 2));
        ctx.fillRect(x, midY - barHeight, 1, barHeight * 2);
      }
    } else {
      // Default placeholder baseline
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();
    }

    if (durationMs > 0) {
      // Viewport window overlay
      const startX = (viewportStartMs / durationMs) * width;
      const endX = (viewportEndMs / durationMs) * width;
      const vpWidth = Math.max(8, endX - startX);

      // Shaded non-active areas
      ctx.fillStyle = "rgba(15, 23, 42, 0.65)";
      ctx.fillRect(0, 0, startX, height);
      ctx.fillRect(endX, 0, width - endX, height);

      // Viewport highlight box
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(startX, 0.5, vpWidth, height - 1);
      ctx.fillStyle = "rgba(56, 189, 248, 0.12)";
      ctx.fillRect(startX, 1, vpWidth, height - 2);

      // Playhead line
      const playheadX = (currentTimeMs / durationMs) * width;
      ctx.strokeStyle = "#f43f5e"; // Rose-500
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();
    }
  }, [durationMs, currentTimeMs, viewportStartMs, viewportEndMs, peaks]);

  useEffect(() => {
    draw();
  }, [draw]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current || durationMs <= 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickRatio = Math.max(0, Math.min(1, clickX / rect.width));
    const targetMs = clickRatio * durationMs;

    isDraggingRef.current = true;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    if (onSeek) onSeek(targetMs);

    // Center viewport on click
    if (onViewportChange) {
      const windowDuration = Math.max(10000, viewportEndMs - viewportStartMs);
      const halfWindow = windowDuration / 2;
      let newStart = targetMs - halfWindow;
      let newEnd = targetMs + halfWindow;
      if (newStart < 0) {
        newStart = 0;
        newEnd = Math.min(durationMs, windowDuration);
      } else if (newEnd > durationMs) {
        newEnd = durationMs;
        newStart = Math.max(0, durationMs - windowDuration);
      }
      onViewportChange(newStart, newEnd);
    }
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDraggingRef.current || !containerRef.current || durationMs <= 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickRatio = Math.max(0, Math.min(1, clickX / rect.width));
    const targetMs = clickRatio * durationMs;
    if (onSeek) onSeek(targetMs);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    isDraggingRef.current = false;
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // Ignore pointer capture release error if already released
    }
  };

  return (
    <div
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className={`relative h-12 w-full cursor-crosshair overflow-hidden rounded-md border border-slate-700 bg-slate-900 select-none ${className}`}
      data-testid="waveform-minimap"
      role="region"
      aria-label="Overview waveform minimap"
    >
      <canvas
        ref={canvasRef}
        width={800}
        height={48}
        className="h-full w-full block"
      />
    </div>
  );
}
