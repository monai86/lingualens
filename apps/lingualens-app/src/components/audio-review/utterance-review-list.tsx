"use client";

import React, { useRef, useEffect } from "react";
import { Play, Sparkles, CheckCircle2 } from "lucide-react";
import { formatTimecode } from "./audio-scrubber-bar";

export interface ReviewLine {
  lineId: string;
  speaker: string;
  text: string;
  startMs?: number;
  endMs?: number;
  clinicalTag?: string;
  verified?: boolean;
}

export interface UtteranceReviewListProps {
  lines: ReviewLine[];
  activeLineId?: string;
  onSelectLine?: (lineId: string) => void;
  onLineChange: (index: number, updatedLine: ReviewLine) => void;
  onPlayUtterance?: (startMs: number, endMs?: number) => void;
  className?: string;
}

export function UtteranceReviewList({
  lines,
  activeLineId,
  onSelectLine,
  onLineChange,
  onPlayUtterance,
  className = "",
}: UtteranceReviewListProps) {
  const activeRowRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll active row into view when activeLineId changes
  useEffect(() => {
    if (activeRowRef.current && typeof activeRowRef.current.scrollIntoView === "function") {
      activeRowRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activeLineId]);

  const handleSpeakerChange = (index: number, newSpeaker: string) => {
    const targetLine = lines[index];
    if (!targetLine) return;
    onLineChange(index, {
      ...targetLine,
      speaker: newSpeaker,
    });
  };

  const handleTextChange = (index: number, newText: string) => {
    const targetLine = lines[index];
    if (!targetLine) return;
    onLineChange(index, {
      ...targetLine,
      text: newText,
    });
  };

  return (
    <div
      className={`flex flex-col gap-2 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-950 ${className}`}
      data-testid="utterance-review-list"
    >
      {lines.length === 0 ? (
        <div className="py-8 text-center text-sm text-slate-500">
          No utterances recorded for this session.
        </div>
      ) : (
        lines.map((line, index) => {
          const isActive = line.lineId === activeLineId;
          const speakerUpper = line.speaker.toUpperCase().replace("*", "");
          const isChi = speakerUpper === "CHI";
          const isInv = speakerUpper === "INV";

          return (
            <div
              key={line.lineId || index}
              ref={isActive ? activeRowRef : null}
              onClick={() => onSelectLine?.(line.lineId)}
              className={`group flex flex-wrap items-center gap-2.5 rounded-md px-3 py-2 transition ${
                isActive
                  ? "bg-blue-50/80 ring-1 ring-blue-400 dark:bg-blue-950/40 dark:ring-blue-600"
                  : "hover:bg-slate-50 dark:hover:bg-slate-900/50"
              }`}
            >
              {/* Play Utterance Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (typeof line.startMs === "number") {
                    onPlayUtterance?.(line.startMs, line.endMs);
                  }
                }}
                disabled={typeof line.startMs !== "number"}
                aria-label={`Play line ${index + 1}`}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600 transition hover:bg-blue-600 hover:text-white disabled:opacity-30 dark:bg-slate-800 dark:text-slate-300"
              >
                <Play size={13} className="translate-x-0.5" />
              </button>

              {/* Timecode Badge */}
              <div className="w-24 flex-shrink-0 font-mono text-xs text-slate-400 dark:text-slate-500">
                {typeof line.startMs === "number" && typeof line.endMs === "number" ? (
                  <span>
                    {formatTimecode(line.startMs).slice(3)} - {formatTimecode(line.endMs).slice(3)}
                  </span>
                ) : (
                  <span>--:--</span>
                )}
              </div>

              {/* Speaker Selector */}
              <div className="flex-shrink-0">
                <select
                  value={line.speaker.replace("*", "")}
                  onChange={(e) => handleSpeakerChange(index, e.target.value)}
                  className={`h-7 rounded border text-xs font-semibold px-2 py-0.5 transition ${
                    isChi
                      ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300"
                      : isInv
                      ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                      : "border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-700 dark:bg-purple-950 dark:text-purple-300"
                  }`}
                  aria-label="Speaker Role"
                >
                  <option value="CHI">CHI (Child)</option>
                  <option value="INV">INV (Clinician)</option>
                  <option value="MOT">MOT (Mother)</option>
                  <option value="FAT">FAT (Father)</option>
                  <option value="OTH">OTH (Other)</option>
                </select>
              </div>

              {/* Editable Thai Utterance Text Input */}
              <div className="min-w-[180px] flex-1">
                <input
                  type="text"
                  value={line.text}
                  onChange={(e) => handleTextChange(index, e.target.value)}
                  className="w-full rounded border border-transparent bg-transparent px-2 py-1 text-sm text-slate-800 transition focus:border-slate-300 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 dark:text-slate-100 dark:focus:border-slate-700 dark:focus:bg-slate-900"
                  placeholder="Enter Thai speech transcription..."
                />
              </div>

              {/* Clinical Cue Tag Badges */}
              {line.clinicalTag && (
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {line.clinicalTag.toLowerCase().includes("echolalia") && (
                    <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-950/70 dark:text-amber-300">
                      <Sparkles size={11} />
                      Echolalia
                    </span>
                  )}
                  {line.clinicalTag.toLowerCase().includes("pronoun") && (
                    <span className="flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300">
                      Pronoun Reversal
                    </span>
                  )}
                </div>
              )}

              {/* Verified Status Indicator */}
              {line.verified && (
                <div
                  className="flex-shrink-0 text-emerald-600 dark:text-emerald-400"
                  title="Verified by clinician"
                >
                  <CheckCircle2 size={16} />
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
