"use client";

import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { AlertCircle, CheckCircle2, RotateCcw, Volume2, ShieldAlert } from "lucide-react";
import { AudioScrubberBar } from "./audio-scrubber-bar";
import { DualViewWaveform } from "./dual-view-waveform";
import { UtteranceReviewList, type ReviewLine } from "./utterance-review-list";
import { useKeyboardReview } from "./use-keyboard-review";
import type { TranscriptLine } from "@/lib/workflow";

export interface AudioReviewWorkbenchProps {
  lines: TranscriptLine[];
  onLinesChange: (lines: TranscriptLine[]) => void;
  audioUrl?: string;
  sessionId?: string;
  isAttested?: boolean;
  onAttest?: () => void;
  onSaveDraft?: () => void;
  isBusy?: boolean;
  findingsStale?: boolean;
  className?: string;
}

export function AudioReviewWorkbench({
  lines,
  onLinesChange,
  audioUrl,
  sessionId,
  isAttested = false,
  onAttest,
  onSaveDraft,
  isBusy = false,
  findingsStale = false,
  className = "",
}: AudioReviewWorkbenchProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(60000);
  const [speed, setSpeed] = useState(1.0);
  const [isLooping, setIsLooping] = useState(false);
  const [showPitch, setShowPitch] = useState(false);
  const [activeLineId, setActiveLineId] = useState<string>(lines[0]?.lineId || "");
  const [peaks, setPeaks] = useState<Int8Array | null>(null);

  // Fetch binary peaks if sessionId is present
  useEffect(() => {
    if (!sessionId) return;
    let isSubscribed = true;

    async function loadPeaks() {
      try {
        const res = await fetch(`/api/v1/sessions/${sessionId}/audio/waveform-peaks`);
        if (res.ok && isSubscribed) {
          const buffer = await res.arrayBuffer();
          setPeaks(new Int8Array(buffer));
        }
      } catch {
        // Fallback gracefully without binary peaks
      }
    }
    loadPeaks();
    return () => {
      isSubscribed = false;
    };
  }, [sessionId]);

  // Sync duration from lines if audio element duration is not available
  useEffect(() => {
    if (lines.length > 0) {
      const maxEnd = Math.max(...lines.map((l) => l.endMs || 0));
      if (maxEnd > 0) {
        setDurationMs((prev) => Math.max(prev, maxEnd));
      }
    }
  }, [lines]);

  // Audio element event listeners
  const handleTimeUpdate = () => {
    if (audioRef.current) {
      const ms = audioRef.current.currentTime * 1000;
      setCurrentTimeMs(ms);

      // Check loop boundary if looping active line
      if (isLooping && activeLineId) {
        const active = lines.find((l) => l.lineId === activeLineId);
        if (active && typeof active.endMs === "number" && ms >= active.endMs) {
          audioRef.current.currentTime = (active.startMs || 0) / 1000;
          return;
        }
      }

      // Automatically sync activeLineId based on playback time
      const currentLine = lines.find(
        (l) => typeof l.startMs === "number" && typeof l.endMs === "number" && ms >= l.startMs && ms <= l.endMs
      );
      if (currentLine && currentLine.lineId !== activeLineId) {
        setActiveLineId(currentLine.lineId);
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current && Number.isFinite(audioRef.current.duration)) {
      setDurationMs(audioRef.current.duration * 1000);
    }
  };

  const handlePlayPause = useCallback(() => {
    if (!audioRef.current) {
      setIsPlaying((prev) => !prev);
      return;
    }
    if (audioRef.current.paused) {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    } else {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const handleSeek = useCallback((timeMs: number) => {
    setCurrentTimeMs(timeMs);
    if (audioRef.current) {
      audioRef.current.currentTime = timeMs / 1000;
    }
  }, []);

  const handleSpeedChange = useCallback((newSpeed: number) => {
    setSpeed(newSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = newSpeed;
    }
  }, []);

  const handleToggleLoop = useCallback(() => {
    setIsLooping((prev) => !prev);
  }, []);

  const handleTogglePitch = useCallback(() => {
    setShowPitch((prev) => !prev);
  }, []);

  const handleReplayActive = useCallback(() => {
    const active = lines.find((l) => l.lineId === activeLineId);
    if (active && typeof active.startMs === "number") {
      handleSeek(active.startMs);
      if (audioRef.current && audioRef.current.paused) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    }
  }, [lines, activeLineId, handleSeek]);

  const handlePlayUtterance = useCallback(
    (startMs: number, _endMs?: number) => {
      handleSeek(startMs);
      if (audioRef.current) {
        audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    },
    [handleSeek]
  );

  const handleAssignSpeaker = useCallback(
    (newSpeaker: "CHI" | "INV" | "MOT" | "FAT") => {
      const idx = lines.findIndex((l) => l.lineId === activeLineId);
      if (idx !== -1) {
        const updated = [...lines];
        updated[idx] = { ...updated[idx], speaker: newSpeaker };
        onLinesChange(updated);
      }
    },
    [lines, activeLineId, onLinesChange]
  );

  const handleAdvanceLine = useCallback(() => {
    const idx = lines.findIndex((l) => l.lineId === activeLineId);
    if (idx !== -1 && idx < lines.length - 1) {
      setActiveLineId(lines[idx + 1].lineId);
      const nextStart = lines[idx + 1].startMs;
      if (typeof nextStart === "number") {
        handleSeek(nextStart);
      }
    }
  }, [lines, activeLineId, handleSeek]);

  // Hook for transcriptionist keyboard hotkeys
  useKeyboardReview({
    onPlayPause: handlePlayPause,
    onReplayActive: handleReplayActive,
    onToggleLoop: handleToggleLoop,
    onAssignSpeaker: handleAssignSpeaker,
    onAdvanceLine: handleAdvanceLine,
    isEnabled: true,
  });

  // Calculate live conversational cues from current lines
  const { childTalkRatio, avgLatencyMs, turnsCount } = useMemo(() => {
    let chiMs = 0;
    let invMs = 0;
    let turns = 0;
    let latencies: number[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const dur = Math.max(0, (line.endMs || 0) - (line.startMs || 0));
      const spk = line.speaker.toUpperCase().replace("*", "");

      if (spk === "CHI") chiMs += dur;
      else if (spk === "INV") invMs += dur;

      if (i > 0) {
        const prev = lines[i - 1];
        const prevSpk = prev.speaker.toUpperCase().replace("*", "");
        if (spk !== prevSpk) turns++;

        if (prevSpk === "INV" && spk === "CHI" && typeof line.startMs === "number" && typeof prev.endMs === "number") {
          const gap = line.startMs - prev.endMs;
          if (gap >= 0 && gap <= 5000) {
            latencies.push(gap);
          }
        }
      }
    }

    const totalMs = chiMs + invMs;
    const ratio = totalMs > 0 ? (chiMs / totalMs) * 100 : 35;
    const avgLat = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 450;

    return { childTalkRatio: ratio, avgLatencyMs: avgLat, turnsCount: turns };
  }, [lines]);

  // Convert lines to waveform segments
  const segments = useMemo(() => {
    return lines.map((l) => ({
      id: l.lineId,
      speaker: l.speaker,
      startMs: l.startMs || 0,
      endMs: l.endMs || (l.startMs || 0) + 1500,
      text: l.text,
    }));
  }, [lines]);

  const handleLineChange = (index: number, updatedLine: ReviewLine) => {
    const updated = [...lines];
    updated[index] = {
      ...updated[index],
      ...updatedLine,
    };
    onLinesChange(updated);
  };

  const handleSegmentBoundaryChange = (segmentId: string, startMs: number, endMs: number) => {
    const idx = lines.findIndex((l) => l.lineId === segmentId);
    if (idx !== -1) {
      const updated = [...lines];
      updated[idx] = {
        ...updated[idx],
        startMs,
        endMs,
      };
      onLinesChange(updated);
    }
  };

  return (
    <div className={`space-y-4 ${className}`} data-testid="audio-review-workbench">
      {/* Hidden Native Audio Element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          aria-label="Workspace audio playback"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
        />
      )}

      {/* Rule 9 Downstream Invalidation Banner */}
      {findingsStale && (
        <div
          role="status"
          className="flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3.5 text-amber-900 shadow-sm dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <AlertCircle size={20} className="flex-shrink-0 text-amber-600 dark:text-amber-400" />
          <div className="flex-1 text-sm font-medium">
            Downstream language-sample features and report draft are currently out of sync with edited transcript lines.
            Re-run feature extraction or attest transcript to refresh.
          </div>
        </div>
      )}

      {/* Waveform Scrubber Control Header */}
      <AudioScrubberBar
        isPlaying={isPlaying}
        currentTimeMs={currentTimeMs}
        durationMs={durationMs}
        speed={speed}
        isLooping={isLooping}
        showPitch={showPitch}
        onPlayPause={handlePlayPause}
        onSpeedChange={handleSpeedChange}
        onToggleLoop={handleToggleLoop}
        onTogglePitch={handleTogglePitch}
        onSeek={handleSeek}
      />

      {/* Dual-View Waveform: Mini-map + Detail Canvas */}
      <DualViewWaveform
        currentTimeMs={currentTimeMs}
        durationMs={durationMs}
        segments={segments}
        peaks={peaks}
        snrDb={21.8}
        diarizationConfidence={89.2}
        responseLatencyMs={avgLatencyMs}
        showPitch={showPitch}
        onSeek={handleSeek}
        onSegmentBoundaryChange={handleSegmentBoundaryChange}
      />

      {/* Live Acoustic & Conversational Summary Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300">
        <div className="flex items-center gap-4">
          <span>
            <strong className="text-slate-900 dark:text-slate-100">Child Talk Time:</strong>{" "}
            {childTalkRatio.toFixed(1)}%
          </span>
          <span>
            <strong className="text-slate-900 dark:text-slate-100">Conversational Turns:</strong>{" "}
            {turnsCount}
          </span>
          <span>
            <strong className="text-slate-900 dark:text-slate-100">Mean Turn Latency:</strong>{" "}
            {Math.round(avgLatencyMs)} ms
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500">
            Shortcuts: <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-[10px] dark:bg-slate-800">Space</kbd> Play · <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-[10px] dark:bg-slate-800">⌘1</kbd> CHI · <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-[10px] dark:bg-slate-800">⌘2</kbd> INV · <kbd className="rounded bg-slate-200 px-1 py-0.5 font-mono text-[10px] dark:bg-slate-800">⌘L</kbd> Loop
          </span>
        </div>
      </div>

      {/* Utterance List */}
      <UtteranceReviewList
        lines={lines}
        activeLineId={activeLineId}
        onSelectLine={(id) => {
          setActiveLineId(id);
          const line = lines.find((l) => l.lineId === id);
          if (line && typeof line.startMs === "number") {
            handleSeek(line.startMs);
          }
        }}
        onLineChange={handleLineChange}
        onPlayUtterance={handlePlayUtterance}
        className="max-h-[480px]"
      />
    </div>
  );
}
