"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Calendar, Activity } from "lucide-react";

export interface LongitudinalSessionItem {
  sessionId: string;
  date: string;
  mluWords?: number;
  ttr?: number;
  turnTakingCount?: number;
  echolaliaCount?: number;
  politeParticleCount?: number;
  f0MedianHz?: number;
  notes?: string;
}

export interface LongitudinalTrendCardProps {
  sessions: LongitudinalSessionItem[];
  title?: string;
  description?: string;
}

function computeDelta(curr?: number, prev?: number): { val: number; text: string; direction: "up" | "down" | "flat" } | null {
  if (curr == null || prev == null) return null;
  const delta = Number((curr - prev).toFixed(2));
  if (delta > 0) return { val: delta, text: `+${delta}`, direction: "up" };
  if (delta < 0) return { val: delta, text: `${delta}`, direction: "down" };
  return { val: 0, text: "0.0", direction: "flat" };
}

export function LongitudinalTrendCard({
  sessions,
  title = "Longitudinal Developmental Trajectory / พัฒนาการข้ามเซสชัน",
  description = "Descriptive linguistic trajectory across consecutive reviewed sessions.",
}: LongitudinalTrendCardProps) {
  if (!sessions || sessions.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 text-center text-sm text-slate-500 shadow-sm">
        No longitudinal session data recorded for this case yet.
      </div>
    );
  }

  // Calculate trajectory across first and latest sessions if at least 2 sessions
  const firstSession = sessions[0];
  const latestSession = sessions[sessions.length - 1];
  const mluDelta = sessions.length > 1 ? computeDelta(latestSession.mluWords, firstSession.mluWords) : null;
  const turnDelta = sessions.length > 1 ? computeDelta(latestSession.turnTakingCount, firstSession.turnTakingCount) : null;
  const echoDelta = sessions.length > 1 ? computeDelta(latestSession.echolaliaCount, firstSession.echolaliaCount) : null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4" data-testid="longitudinal-trend-card">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-teal-600" />
            {title}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        </div>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200 self-start sm:self-auto">
          {sessions.length} Recorded Sessions
        </span>
      </div>

      {/* Trajectory Highlights (when 2+ sessions exist) */}
      {sessions.length > 1 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {mluDelta && (
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="text-xs text-slate-500 font-medium">MLU-w Trajectory (Sentence Length)</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-lg font-bold text-slate-900">{latestSession.mluWords?.toFixed(2)}</span>
                <span className="text-xs text-slate-500">คำ/ประโยค</span>
                <span
                  className={`inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded ${
                    mluDelta.direction === "up"
                      ? "bg-emerald-100 text-emerald-800"
                      : mluDelta.direction === "down"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {mluDelta.direction === "up" && <TrendingUp className="w-3 h-3 mr-0.5" />}
                  {mluDelta.direction === "down" && <TrendingDown className="w-3 h-3 mr-0.5" />}
                  {mluDelta.direction === "flat" && <Minus className="w-3 h-3 mr-0.5" />}
                  {mluDelta.text}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1">From {firstSession.mluWords?.toFixed(2)} in initial session</div>
            </div>
          )}

          {turnDelta && (
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="text-xs text-slate-500 font-medium">Turn-Taking (Social Reciprocity)</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-lg font-bold text-slate-900">{latestSession.turnTakingCount}</span>
                <span className="text-xs text-slate-500">รอบ</span>
                <span
                  className={`inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded ${
                    turnDelta.direction === "up"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {turnDelta.direction === "up" && <TrendingUp className="w-3 h-3 mr-0.5" />}
                  {turnDelta.text}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1">From {firstSession.turnTakingCount} in initial session</div>
            </div>
          )}

          {echoDelta && (
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <div className="text-xs text-slate-500 font-medium">Echolalia (Verbatim Repetition)</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-lg font-bold text-slate-900">{latestSession.echolaliaCount}</span>
                <span className="text-xs text-slate-500">ครั้ง</span>
                <span
                  className={`inline-flex items-center text-xs font-semibold px-1.5 py-0.5 rounded ${
                    echoDelta.direction === "down"
                      ? "bg-emerald-100 text-emerald-800"
                      : echoDelta.direction === "up"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {echoDelta.direction === "down" && <TrendingDown className="w-3 h-3 mr-0.5" />}
                  {echoDelta.direction === "up" && <TrendingUp className="w-3 h-3 mr-0.5" />}
                  {echoDelta.text}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-1">From {firstSession.echolaliaCount} in initial session</div>
            </div>
          )}
        </div>
      )}

      {/* Trajectory Table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
              <th className="py-2.5 px-3">Date / วันที่</th>
              <th className="py-2.5 px-3">Session ID</th>
              <th className="py-2.5 px-3 text-right">MLU-w (Words)</th>
              <th className="py-2.5 px-3 text-right">TTR (Diversity)</th>
              <th className="py-2.5 px-3 text-right">Turn-Taking</th>
              <th className="py-2.5 px-3 text-right">Polite (คำสุภาพ)</th>
              <th className="py-2.5 px-3 text-right">Echolalia</th>
              <th className="py-2.5 px-3 text-right">Pitch F0 (Hz)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sessions.map((s, idx) => (
              <tr key={s.sessionId} className={idx === sessions.length - 1 ? "bg-teal-50/40 font-medium" : "hover:bg-slate-50/60"}>
                <td className="py-2.5 px-3 whitespace-nowrap text-slate-900 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  {s.date}
                  {idx === sessions.length - 1 && (
                    <span className="ml-1 text-[10px] font-bold text-teal-700 bg-teal-100/70 px-1.5 py-0.2 rounded">
                      Current
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 font-mono text-slate-600">{s.sessionId}</td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.mluWords != null ? s.mluWords.toFixed(2) : "-"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.ttr != null ? `${(s.ttr * 100).toFixed(0)}%` : "-"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.turnTakingCount != null ? s.turnTakingCount : "-"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.politeParticleCount != null ? s.politeParticleCount : "-"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.echolaliaCount != null ? s.echolaliaCount : "-"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-slate-900">
                  {s.f0MedianHz != null ? s.f0MedianHz : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900">
        <strong>⚠️ Clinical Note:</strong> Longitudinal trajectories illustrate observed descriptive speech patterns across clinical sessions. They are not automated prognostic predictions and must be interpreted by a certified speech-language pathologist in holistic context.
      </div>
    </div>
  );
}
