"use client";

import { useCallback, useEffect, useState } from "react";

import {
  AssessmentV2Client,
  type AssessmentV2TranscriptRevision,
  type AssessmentV2TranscriptSource,
} from "@/services/assessment-v2-client";
import { AssessmentProcessingStatus } from "@/features/assessment-v2/components/assessment-processing-status";

export type AssessmentTranscriptReviewClient = Pick<
  AssessmentV2Client,
  | "getTranscript"
  | "createTranscriptRevision"
  | "attestTranscript"
  | "queueEvidence"
  | "getCurrentEvidenceProcessingRun"
  | "getProcessingRun"
  | "retryProcessingRun"
  | "cancelProcessingRun"
>;

type AssessmentTranscriptReviewWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentTranscriptReviewClient;
};

const defaultClient = new AssessmentV2Client();

export function AssessmentTranscriptReviewWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentTranscriptReviewWorkspaceProps) {
  const [transcript, setTranscript] = useState<AssessmentV2TranscriptRevision | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [attestationConfirmed, setAttestationConfirmed] = useState(false);

  const loadTranscript = useCallback(async () => {
    setLoading(true);
    setError(null);
    setActionError(null);
    try {
      const current = await client.getTranscript(assessmentId);
      setTranscript(current);
      setDraftContent(current.content);
      setAttestationConfirmed(false);
    } catch (error) {
      setTranscript(null);
      setDraftContent("");
      setError(isMissingTranscriptError(error) ? null : "ไม่สามารถโหลด transcript ได้");
      setAttestationConfirmed(false);
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadTranscript();
  }, [loadTranscript]);

  async function saveDraft() {
    if (busy || !draftContent.trim() || (transcript && draftContent === transcript.content)) return;

    setBusy(true);
    setActionError(null);
    try {
      const saved = await client.createTranscriptRevision(assessmentId, {
        source: transcript?.source ?? "asr_draft",
        content: draftContent,
        expected_revision: transcript?.revision ?? null,
        expected_version: transcript?.version ?? null,
      });
      setTranscript(saved);
      setDraftContent(saved.content);
      setAttestationConfirmed(false);
    } catch {
      setActionError("ยังบันทึก transcript ฉบับร่างไม่ได้ กรุณาตรวจสถานะ assessment แล้วลองใหม่");
    } finally {
      setBusy(false);
    }
  }

  async function attestTranscript() {
    if (!transcript || busy || transcript.review_state !== "draft" || draftContent !== transcript.content || !attestationConfirmed) return;

    setBusy(true);
    setActionError(null);
    try {
      const attested = await client.attestTranscript(transcript.id, transcript.version);
      setTranscript(attested);
      setDraftContent(attested.content);
      setAttestationConfirmed(false);
    } catch {
      setActionError("ยังรับรอง transcript ไม่ได้ ฉบับนี้อาจถูกแก้ไขไปแล้ว กรุณาโหลดข้อมูลใหม่");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="workspace-panel p-6" aria-busy="true">
        <p>กำลังโหลด transcript…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="workspace-panel p-6" role="alert">
        <h1 className="text-xl font-semibold">ไม่สามารถโหลด transcript ได้</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          ระบบยังอ่าน transcript จาก FastAPI ไม่ได้ จึงยังไม่เปิดให้ตรวจหรือรับรองข้อมูลในเบราว์เซอร์
        </p>
        <button
          type="button"
          className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white"
          onClick={() => void loadTranscript()}
        >
          ลองใหม่
        </button>
      </section>
    );
  }

  if (!transcript) {
    return (
      <section className="space-y-5">
        <header>
          <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 5 จาก 5</p>
          <h1 className="mt-1 text-2xl font-semibold">สร้าง transcript ฉบับแรก</h1>
          <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
            ระบบยังไม่มีฉบับร่างจากการถอดเสียง ให้ตรวจสอบหรือวางข้อความจาก FastAPI ก่อนรับรอง
          </p>
        </header>
        <section className="workspace-panel p-5" aria-labelledby="first-transcript-editor-heading">
          <h2 id="first-transcript-editor-heading" className="text-lg font-semibold">ฉบับร่างจากการถอดเสียง</h2>
          <label className="sr-only" htmlFor="assessment-transcript-content">เนื้อหา transcript</label>
          <textarea
            id="assessment-transcript-content"
            aria-label="เนื้อหา transcript"
            value={draftContent}
            onChange={(event) => setDraftContent(event.target.value)}
            disabled={busy}
            rows={14}
            className="mt-4 min-h-72 w-full rounded-lg border border-[color:var(--color-border)] bg-white p-4 font-mono text-sm leading-7 outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:bg-[color:var(--color-surface-muted)]"
          />
          <button
            type="button"
            disabled={busy || !draftContent.trim()}
            onClick={() => void saveDraft()}
            className="mt-4 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "กำลังบันทึก…" : "สร้างฉบับร่าง"}
          </button>
        </section>
        {actionError ? <p className="text-sm text-red-700" role="alert">{actionError}</p> : null}
      </section>
    );
  }

  const isDirty = draftContent !== transcript.content;
  const isDraft = transcript.review_state === "draft";
  const canAttest = isDraft && !isDirty && attestationConfirmed && !busy;

  return (
    <section className="space-y-5">
      <header>
        <p className="text-sm font-semibold text-[color:var(--color-primary)]">ขั้นตอนที่ 5 จาก 5</p>
        <h1 className="mt-1 text-2xl font-semibold">ทบทวน transcript</h1>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          ตรวจแก้ข้อความและ speaker label ให้เรียบร้อยก่อนรับรอง ข้อมูลที่ยังไม่รับรองจะไม่ถูกนำไปสร้างหลักฐาน
        </p>
      </header>

      <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-semibold">สถานะ: {transcriptStateLabel(transcript.review_state)}</p>
          <span className="text-sm">revision {transcript.revision} · version {transcript.version}</span>
        </div>
        <p className="mt-1 text-sm">แหล่งที่มา: {transcriptSourceLabel(transcript.source)} · การรับรองเป็นความรับผิดชอบของนักบำบัด</p>
      </div>

      <section className="workspace-panel p-5" aria-labelledby="transcript-editor-heading">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="transcript-editor-heading" className="text-lg font-semibold">ข้อความ transcript</h2>
            <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">แก้ไขได้โดยตรง ระบบจะเก็บ revision ใหม่เมื่อกดบันทึก</p>
          </div>
          {isDirty ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">มีการแก้ไขที่ยังไม่บันทึก</span> : null}
        </div>
        <label className="sr-only" htmlFor="assessment-transcript-content">เนื้อหา transcript</label>
        <textarea
          id="assessment-transcript-content"
          aria-label="เนื้อหา transcript"
          value={draftContent}
          onChange={(event) => setDraftContent(event.target.value)}
          disabled={busy}
          rows={14}
          className="mt-4 min-h-72 w-full rounded-lg border border-[color:var(--color-border)] bg-white p-4 font-mono text-sm leading-7 outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:bg-[color:var(--color-surface-muted)]"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={busy || !isDirty || !draftContent.trim()}
            onClick={() => void saveDraft()}
            className="rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "กำลังบันทึก…" : "บันทึกฉบับร่าง"}
          </button>
          <span className="text-xs text-[color:var(--color-text-muted)]">SHA-256: {transcript.content_sha256.slice(0, 12)}…</span>
        </div>
      </section>

      {isDraft ? (
        <section className="workspace-panel p-5" aria-labelledby="transcript-attestation-heading">
          <h2 id="transcript-attestation-heading" className="text-lg font-semibold">รับรองฉบับที่ตรวจแล้ว</h2>
          <label className="mt-3 flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              checked={attestationConfirmed}
              onChange={(event) => setAttestationConfirmed(event.target.checked)}
              disabled={busy || isDirty}
              className="mt-1 h-4 w-4"
            />
            <span>ฉันได้ตรวจสอบข้อความและ speaker label แล้ว และยืนยันว่า transcript ฉบับนี้พร้อมให้ระบบประมวลผลเชิงพรรณนา</span>
          </label>
          {isDirty ? <p className="mt-3 text-sm text-amber-800">บันทึกฉบับร่างก่อนจึงจะรับรองได้</p> : null}
          <button
            type="button"
            disabled={!canAttest}
            onClick={() => void attestTranscript()}
            className="mt-4 rounded-lg border border-[color:var(--color-border-strong)] px-4 py-2 text-sm font-semibold text-[color:var(--color-text-strong)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "กำลังรับรอง…" : "รับรอง transcript"}
          </button>
        </section>
      ) : null}

      {transcript.review_state === "attested" ? (
        <section className="rounded-xl border border-emerald-300 bg-emerald-50 p-5 text-emerald-950" role="status">
          <p className="font-semibold">รับรองแล้ว</p>
          <p className="mt-1 text-sm">ระบบสามารถใช้ revision นี้เป็น input ของ evidence worker ได้</p>
          <div className="mt-4">
            <AssessmentProcessingStatus
              assessmentId={assessmentId}
              client={client}
              canQueue={!isDirty}
            />
          </div>
          {isDirty ? <p className="mt-3 text-sm text-amber-800">บันทึกฉบับร่างก่อนสร้างหลักฐาน</p> : null}
        </section>
      ) : null}

      {actionError ? <p className="text-sm text-red-700" role="alert">{actionError}</p> : null}
    </section>
  );
}

function transcriptStateLabel(value: AssessmentV2TranscriptRevision["review_state"]): string {
  const labels: Record<AssessmentV2TranscriptRevision["review_state"], string> = {
    draft: "รอตรวจสอบ",
    attested: "รับรองแล้ว",
    superseded: "ถูกแทนที่",
  };
  return labels[value];
}

function transcriptSourceLabel(value: AssessmentV2TranscriptSource): string {
  const labels: Record<AssessmentV2TranscriptSource, string> = {
    manual: "กรอกโดยนักบำบัด",
    asr_draft: "ร่างจากการถอดเสียง",
    imported: "นำเข้า",
  };
  return labels[value];
}

function isMissingTranscriptError(error: unknown): boolean {
  return typeof error === "object"
    && error !== null
    && "status" in error
    && (error as { status?: unknown }).status === 404
    && errorCode(error) === "transcript_not_found";
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
