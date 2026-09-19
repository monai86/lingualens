"use client";

import { useRef } from "react";

import type {
  AssessmentV2TranscriptSegment,
  AssessmentV2TranscriptSegmentReplayGrant,
  AssessmentV2TranscriptSegmentSet,
  AssessmentV2TranscriptSegmentSpeakerRole,
  AssessmentV2TranscriptSegmentUncertaintyReason,
} from "@/services/assessment-v2-client";

export type SegmentDraft = Omit<AssessmentV2TranscriptSegment, "id" | "created_at"> & { id: string };

export function TranscriptDraftPanel({
  content,
  busy,
  error,
  onChange,
  onSave,
  onAttest,
  attestationConfirmed = false,
  onAttestationChange,
  createMode = false,
}: {
  content: string;
  busy: boolean;
  error: string | null;
  onChange: (value: string) => void;
  onSave: () => void;
  onAttest?: () => void;
  attestationConfirmed?: boolean;
  onAttestationChange?: (value: boolean) => void;
  createMode?: boolean;
}) {
  return (
    <section className="space-y-5">
      <header><p className="text-sm font-semibold text-[color:var(--color-accent)]">ขั้นตอนที่ 5 จาก 5</p><h1 className="mt-1 text-2xl font-semibold">{createMode ? "สร้าง transcript ฉบับแรก" : "ตรวจ transcript ก่อนสร้าง segment"}</h1><p className="mt-2 text-sm text-[color:var(--color-text-muted)]">ตรวจข้อความต้นฉบับและรับรองก่อนให้ระบบผูก segment กับ revision ที่แน่นอน</p></header>
      <section className="workspace-panel p-5" aria-labelledby="transcript-prerequisite-heading"><h2 id="transcript-prerequisite-heading" className="text-lg font-semibold">ข้อความ transcript</h2><textarea aria-label="เนื้อหา transcript" value={content} onChange={(event) => onChange(event.target.value)} disabled={busy} rows={12} className={`${fieldClass} mt-4 min-h-64 font-mono leading-7`} /><button type="button" className={primaryButtonClass} disabled={busy || !content.trim()} onClick={onSave}>{busy ? "กำลังบันทึก…" : createMode ? "สร้างฉบับร่าง" : "บันทึกฉบับร่าง"}</button></section>
      {onAttest ? <section className="workspace-panel p-5"><h2 className="text-lg font-semibold">รับรอง transcript</h2><label className="mt-3 flex min-h-11 items-start gap-3 text-sm"><input type="checkbox" checked={attestationConfirmed} onChange={(event) => onAttestationChange?.(event.target.checked)} disabled={busy} className="mt-1 h-4 w-4" /><span>ฉันได้ตรวจสอบข้อความและยืนยันว่า transcript พร้อมให้ระบบสร้าง segment</span></label><button type="button" className={secondaryButtonClass} disabled={busy || !attestationConfirmed} onClick={onAttest}>รับรอง transcript</button></section> : null}
      {error ? <p className="text-sm text-red-800" role="alert">{error}</p> : null}
    </section>
  );
}

export function SegmentAudioPlayer({ grant, ordinal }: { grant: AssessmentV2TranscriptSegmentReplayGrant; ordinal: number }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  function boundPlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.currentTime < grant.start_ms / 1000) audio.currentTime = grant.start_ms / 1000;
    if (audio.currentTime >= grant.end_ms / 1000) {
      audio.pause();
      audio.currentTime = grant.start_ms / 1000;
    }
  }
  return <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3"><p className="text-xs font-semibold text-emerald-900">เสียงช่วงที่ {ordinal} พร้อมเล่น · ลิงก์ชั่วคราว {grant.expires_in_seconds ?? 0} วินาที</p><audio ref={audioRef} role="audio" aria-label={`เสียงช่วงที่ ${ordinal}`} controls preload="metadata" src={grant.url ?? undefined} onLoadedMetadata={boundPlayback} onTimeUpdate={boundPlayback} className="mt-2 w-full" /></div>;
}

export function toDraftSegments(segments: AssessmentV2TranscriptSegment[]): SegmentDraft[] {
  return segments.map(({ id, created_at: _createdAt, ...segment }) => ({ id, ...segment }));
}

export function toSegmentPayload(segment: SegmentDraft) {
  return {
    ordinal: segment.ordinal,
    start_ms: segment.start_ms,
    end_ms: segment.end_ms,
    speaker_role: segment.speaker_role,
    text: segment.text,
    confidence: segment.confidence,
    uncertainty_reason: segment.uncertainty_reason,
  };
}

export function sameSegmentValues(left: SegmentDraft[], right: AssessmentV2TranscriptSegment[]): boolean {
  if (left.length !== right.length) return false;
  return left.every((segment, index) => {
    const saved = right[index];
    const savedDraft = saved ? toDraftSegments([saved])[0] : null;
    if (!savedDraft) return false;
    return JSON.stringify(toSegmentPayload(segment)) === JSON.stringify(toSegmentPayload(savedDraft));
  });
}

export function isErrorCode(error: unknown, expected: string): boolean {
  return errorCode(error) === expected;
}

export function isStaleError(error: unknown): boolean {
  return ["stale_segment_set_version", "segment_transcript_stale", "stale_transcript_version"].includes(errorCode(error) ?? "");
}

function errorCode(error: unknown): string | null {
  if (typeof error !== "object" || error === null || !("body" in error)) return null;
  const body = (error as { body?: unknown }).body;
  if (typeof body !== "string") return null;
  try {
    const parsed = JSON.parse(body) as { error?: { code?: unknown } };
    return typeof parsed.error?.code === "string" ? parsed.error.code : null;
  } catch {
    return null;
  }
}

export function formatTime(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function speakerLabel(value: AssessmentV2TranscriptSegmentSpeakerRole): string {
  return { child: "เด็ก", therapist: "นักบำบัด", caregiver: "ผู้ดูแล", unknown: "ยังไม่ทราบ" }[value];
}

export function uncertaintyLabel(value: AssessmentV2TranscriptSegmentUncertaintyReason): string {
  return {
    none: "ไม่มี",
    low_asr_confidence: "ถอดเสียงไม่มั่นใจ",
    unintelligible_audio: "ฟังไม่ชัด",
    speaker_uncertain: "ผู้พูดยังไม่แน่ใจ",
    timestamp_uncertain: "เวลายังไม่แน่ใจ",
    manual_review: "ต้องตรวจด้วยคน",
  }[value];
}

export function segmentStateLabel(value: AssessmentV2TranscriptSegmentSet["review_state"]): string {
  return { draft: "รอตรวจสอบ", attested: "รับรองแล้ว", superseded: "ถูกแทนที่" }[value];
}

export const labelClass = "block text-sm font-semibold text-[color:var(--color-text-strong)]";
export const fieldClass = "mt-2 min-h-11 w-full rounded-lg border border-[color:var(--color-border-strong)] bg-white px-3 py-2 text-sm outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:bg-[color:var(--color-surface-muted)]";
export const primaryButtonClass = "mt-4 inline-flex min-h-11 items-center justify-center rounded-lg bg-[color:var(--color-accent-strong)] px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-[color:var(--color-accent)] focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50";
export const secondaryButtonClass = "mt-4 inline-flex min-h-11 items-center justify-center rounded-lg border border-[color:var(--color-border-strong)] bg-white px-4 py-2 text-sm font-semibold text-[color:var(--color-text-strong)] outline-none hover:bg-[color:var(--color-surface-muted)] focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50";
export const activeFilterButtonClass = "mt-4 inline-flex min-h-11 items-center justify-center rounded-lg border border-[color:var(--color-accent-strong)] bg-[color:var(--color-accent-soft)] px-4 py-2 text-sm font-semibold text-[color:var(--color-accent-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";
