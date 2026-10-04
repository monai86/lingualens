"use client";

import React, { useRef, useEffect, useCallback, useState } from "react";

export interface WaveformSegment {
  id: string;
  speaker: string;
  startMs: number;
  endMs: number;
  text?: string;
}

export interface WaveformDetailCanvasProps {
  currentTimeMs: number;
  viewportStartMs: number;
  viewportEndMs: number;
  segments: WaveformSegment[];
  peaks?: Int8Array | null;
  showPitch?: boolean;
  onSeek?: (timeMs: number) => void;
  onSegmentBoundaryChange?: (segmentId: string, startMs: number, endMs: number) => void;
  className?: string;
}

interface DragState {
  segmentId: string;
  edge: "start" | "end";
  initialMs: number;
}

export function WaveformDetailCanvas({
  currentTimeMs,
  viewportStartMs,
  viewportEndMs,
  segments,
  peaks,
  showPitch = false,
  onSeek,
  onSegmentBoundaryChange,
  className = "",
}: WaveformDetailCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [activeDrag, setActiveDrag] = useState<DragState | null>(null);

  const durationInWindow = Math.max(1000, viewportEndMs - viewportStartMs);

  const getSpeakerColor = (speaker: string) => {
    const s = speaker.toUpperCase();
    if (s === "CHI" || s === "*CHI") {
      return { fill: "rgba(59, 130, 246, 0.25)", border: "#3b82f6", text: "#93c5fd" };
    }
    if (s === "INV" || s === "*INV") {
      return { fill: "rgba(16, 185, 129, 0.25)", border: "#10b981", text: "#6ee7b7" };
    }
    return { fill: "rgba(168, 85, 247, 0.25)", border: "#a855f7", text: "#d8b4fe" };
  };

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

    // Dark background
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines (1 second intervals)
    const secStepMs = 1000;
    const firstSec = Math.ceil(viewportStartMs / secStepMs) * secStepMs;
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    ctx.font = "10px monospace";
    ctx.fillStyle = "#64748b";

    for (let t = firstSec; t <= viewportEndMs; t += secStepMs) {
      const x = ((t - viewportStartMs) / durationInWindow) * width;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();

      const secVal = (t / 1000).toFixed(1);
      ctx.fillText(`${secVal}s`, x + 3, 12);
    }

    // Draw baseline
    ctx.strokeStyle = "#1e293b";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, midY);
    ctx.lineTo(width, midY);
    ctx.stroke();

    // Draw multi-track utterance segment bands
    segments.forEach((seg) => {
      // Check if segment overlaps current viewport
      if (seg.endMs < viewportStartMs || seg.startMs > viewportEndMs) return;

      const segStartX = Math.max(0, ((seg.startMs - viewportStartMs) / durationInWindow) * width);
      const segEndX = Math.min(width, ((seg.endMs - viewportStartMs) / durationInWindow) * width);
      const segWidth = Math.max(4, segEndX - segStartX);

      const color = getSpeakerColor(seg.speaker);

      // Segment fill & border
      ctx.fillStyle = color.fill;
      ctx.fillRect(segStartX, 16, segWidth, height - 20);

      ctx.strokeStyle = color.border;
      ctx.lineWidth = 2;
      ctx.strokeRect(segStartX, 16, segWidth, height - 20);

      // Label & speaker badge
      ctx.font = "bold 11px system-ui, sans-serif";
      ctx.fillStyle = color.text;
      ctx.fillText(`${seg.speaker}: ${seg.text || ""}`, segStartX + 6, 32);

      // Draw boundary drag handles
      ctx.fillStyle = color.border;
      // Start handle
      ctx.fillRect(segStartX - 3, midY - 14, 6, 28);
      // End handle
      ctx.fillRect(segEndX - 3, midY - 14, 6, 28);
    });

    // Draw pitch contour overlay if enabled
    if (showPitch) {
      ctx.strokeStyle = "#f59e0b"; // Amber-500
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 2]);
      ctx.beginPath();
      for (let x = 0; x < width; x += 4) {
        const timeAtX = viewportStartMs + (x / width) * durationInWindow;
        // Synthesize gentle pitch curve modulated with speech boundaries
        const pitchNorm = Math.sin(timeAtX / 400) * 0.25 + 0.5;
        const pitchY = height * 0.7 - pitchNorm * 40;
        if (x === 0) ctx.moveTo(x, pitchY);
        else ctx.lineTo(x, pitchY);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw playhead cursor
    if (currentTimeMs >= viewportStartMs && currentTimeMs <= viewportEndMs) {
      const playheadX = ((currentTimeMs - viewportStartMs) / durationInWindow) * width;
      ctx.strokeStyle = "#f43f5e"; // Rose-500
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();

      // Playhead top cap triangle
      ctx.fillStyle = "#f43f5e";
      ctx.beginPath();
      ctx.moveTo(playheadX - 6, 0);
      ctx.lineTo(playheadX + 6, 0);
      ctx.lineTo(playheadX, 10);
      ctx.fill();
    }
  }, [
    currentTimeMs,
    viewportStartMs,
    viewportEndMs,
    durationInWindow,
    segments,
    showPitch,
  ]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Pointer event handlers for boundary dragging or seeking
  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickMs = viewportStartMs + (clickX / rect.width) * durationInWindow;

    // Check if clicked near an utterance boundary (handle within 8px)
    const thresholdMs = (8 / rect.width) * durationInWindow;
    for (const seg of segments) {
      if (Math.abs(seg.startMs - clickMs) <= thresholdMs) {
        setActiveDrag({ segmentId: seg.id, edge: "start", initialMs: seg.startMs });
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        return;
      }
      if (Math.abs(seg.endMs - clickMs) <= thresholdMs) {
        setActiveDrag({ segmentId: seg.id, edge: "end", initialMs: seg.endMs });
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        return;
      }
    }

    // Otherwise, seek to position
    if (onSeek) {
      onSeek(Math.max(0, clickMs));
    }
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!activeDrag || !containerRef.current || !onSegmentBoundaryChange) return;

    const rect = containerRef.current.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    let newMs = viewportStartMs + (currentX / rect.width) * durationInWindow;

    // Smart VAD boundary snapping (quantize to nearest 50ms)
    newMs = Math.round(newMs / 50) * 50;

    const seg = segments.find((s) => s.id === activeDrag.segmentId);
    if (!seg) return;

    const MIN_DURATION = 150; // Minimum utterance duration in ms
    if (activeDrag.edge === "start") {
      const clampedStart = Math.min(newMs, seg.endMs - MIN_DURATION);
      onSegmentBoundaryChange(seg.id, Math.max(0, clampedStart), seg.endMs);
    } else {
      const clampedEnd = Math.max(newMs, seg.startMs + MIN_DURATION);
      onSegmentBoundaryChange(seg.id, seg.startMs, clampedEnd);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (activeDrag) {
      setActiveDrag(null);
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // ignore
      }
    }
  };

  return (
    <div
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className={`relative h-44 w-full cursor-crosshair overflow-hidden rounded-md border border-slate-800 bg-slate-950 select-none ${className}`}
      data-testid="waveform-detail-canvas"
      role="region"
      aria-label="High-resolution waveform detail canvas"
    >
      <canvas
        ref={canvasRef}
        width={1000}
        height={176}
        className="h-full w-full block"
      />
    </div>
  );
}
