"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import {
  AssessmentV2Client,
  type AssessmentV2EvidenceProcessing,
  type AssessmentV2ProcessingRun,
} from "@/services/assessment-v2-client";

export type AssessmentProcessingStatusClient = Pick<
  AssessmentV2Client,
  | "queueEvidence"
  | "getCurrentEvidenceProcessingRun"
  | "getProcessingRun"
  | "retryProcessingRun"
  | "cancelProcessingRun"
>;

type AssessmentProcessingStatusProps = {
  assessmentId: string;
  client?: AssessmentProcessingStatusClient;
  onEvidenceReady?: () => void | Promise<void>;
  canQueue?: boolean;
};

const defaultClient = new AssessmentV2Client();
const INITIAL_POLL_DELAY_MS = 2_000;
const MAX_POLL_DELAY_MS = 15_000;

export function AssessmentProcessingStatus({
  assessmentId,
  client = defaultClient,
  onEvidenceReady,
  canQueue = true,
}: AssessmentProcessingStatusProps) {
  const [run, setRun] = useState<AssessmentV2ProcessingRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hidden, setHidden] = useState(false);
  const [pollDelayMs, setPollDelayMs] = useState(INITIAL_POLL_DELAY_MS);
  const [pollTick, setPollTick] = useState(0);
  const notifiedRunId = useRef<string | null>(null);

  const notifyEvidenceReady = useCallback(
    (candidate: AssessmentV2ProcessingRun) => {
      if (!candidate.result_available || candidate.state !== "succeeded" || notifiedRunId.current === candidate.id) {
        return;
      }
      notifiedRunId.current = candidate.id;
      void onEvidenceReady?.();
    },
    [onEvidenceReady],
  );

  const loadCurrentRun = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.getCurrentEvidenceProcessingRun(assessmentId);
      setRun(response.processing_run);
      setPollDelayMs(INITIAL_POLL_DELAY_MS);
      notifyEvidenceReady(response.processing_run);
    } catch (requestError) {
      if (isMissingProcessingRunError(requestError)) {
        setRun(null);
      } else {
        setRun(null);
        setError(safeProcessingError(requestError));
      }
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client, notifyEvidenceReady]);

  const pollRun = useCallback(
    async (runId: string) => {
      try {
        const current = await client.getProcessingRun(runId);
        setRun(current);
        setError(null);
        setPollDelayMs(INITIAL_POLL_DELAY_MS);
        notifyEvidenceReady(current);
      } catch (requestError) {
        setError(safeProcessingError(requestError));
        setPollDelayMs((current) => Math.min(MAX_POLL_DELAY_MS, current * 2));
      } finally {
        setPollTick((current) => current + 1);
      }
    },
    [client, notifyEvidenceReady],
  );

  useEffect(() => {
    notifiedRunId.current = null;
    void loadCurrentRun();
  }, [loadCurrentRun]);

  useEffect(() => {
    const onVisibilityChange = () => {
      const isHidden = document.visibilityState === "hidden";
      setHidden(isHidden);
      if (!isHidden) {
        setPollDelayMs(INITIAL_POLL_DELAY_MS);
        setPollTick((current) => current + 1);
        void loadCurrentRun();
      }
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [loadCurrentRun]);

  useEffect(() => {
    if (hidden || !run || !isActiveProcessingState(run.state)) return;

    const timer = window.setTimeout(() => {
      void pollRun(run.id);
    }, pollDelayMs);
    return () => window.clearTimeout(timer);
  }, [hidden, pollDelayMs, pollRun, pollTick, run]);

  async function queueEvidence() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const response: AssessmentV2EvidenceProcessing = await client.queueEvidence(assessmentId);
      setRun(response.processing_run);
      setPollDelayMs(INITIAL_POLL_DELAY_MS);
      setPollTick((current) => current + 1);
    } catch (requestError) {
      setError(safeActionError(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function retryProcessing() {
    if (busy || !run || !run.can_retry) return;
    setBusy(true);
    setError(null);
    try {
      const current = await client.retryProcessingRun(run.id, run.version);
      setRun(current);
      setPollDelayMs(INITIAL_POLL_DELAY_MS);
      setPollTick((value) => value + 1);
    } catch (requestError) {
      setError(safeActionError(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function cancelProcessing() {
    if (busy || !run || !run.can_cancel) return;
    setBusy(true);
    setError(null);
    try {
      const current = await client.cancelProcessingRun(run.id, run.version);
      setRun(current);
    } catch (requestError) {
      setError(safeActionError(requestError));
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status" aria-live="polite" aria-busy="true">
        <p className="font-semibold">กำลังอ่านสถานะการประมวลผล…</p>
      </section>
    );
  }

  const status = run ? processingStatusCopy(run) : null;

  return (
    <section className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status" aria-live="polite">
      {error ? <p className="mb-3 text-sm text-red-800" role="alert">{error}</p> : null}
      {!run ? (
        <>
          <p className="font-semibold">ยังไม่มีงานประมวลผลหลักฐาน</p>
          <p className="mt-1 text-sm">เมื่อกดเริ่ม ระบบจะส่ง transcript ที่รับรองแล้วให้ FastAPI ประมวลผลเชิงพรรณนา</p>
          <button
            type="button"
            className="mt-4 min-h-11 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy || !canQueue}
            onClick={() => void queueEvidence()}
          >
            {busy ? "กำลังบันทึกงาน…" : "สร้างหลักฐานเชิงพรรณนา"}
          </button>
        </>
      ) : (
        <>
          <p className="font-semibold">{status?.title}</p>
          <p className="mt-1 text-sm">{status?.description}</p>
          {isActiveProcessingState(run.state) ? (
            <p className="mt-2 text-sm">ครั้งที่ {run.attempt_count} จาก {run.max_attempts}</p>
          ) : null}
          {run.state === "failed" && run.can_retry ? (
            <button
              type="button"
              className="mt-4 min-h-11 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={busy}
              onClick={() => void retryProcessing()}
            >
              {busy ? "กำลังเริ่มใหม่…" : "ลองประมวลผลใหม่"}
            </button>
          ) : null}
          {run.state === "cancelled" && run.can_retry ? (
            <button
              type="button"
              className="mt-4 min-h-11 rounded-lg bg-[color:var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              disabled={busy}
              onClick={() => void retryProcessing()}
            >
              {busy ? "กำลังเริ่มใหม่…" : "เริ่มประมวลผลใหม่"}
            </button>
          ) : null}
          {run.can_cancel ? (
            <button
              type="button"
              className="ml-2 mt-4 min-h-11 rounded-lg border border-sky-800 px-4 py-2 text-sm font-semibold text-sky-950 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={busy}
              onClick={() => void cancelProcessing()}
            >
              {busy ? "กำลังหยุด…" : "หยุดการประมวลผล"}
            </button>
          ) : null}
          {run.state === "succeeded" && run.result_available ? (
            <Link
              href={`/assessments/${encodeURIComponent(assessmentId)}/evidence`}
              className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-sky-800 px-4 py-2 text-sm font-semibold text-sky-950"
            >
              เปิดผลหลักฐาน
            </Link>
          ) : null}
          {run.state === "cancelled" && !run.can_retry ? (
            <Link
              href={`/assessments/${encodeURIComponent(assessmentId)}/transcript`}
              className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-sky-800 px-4 py-2 text-sm font-semibold text-sky-950"
            >
              กลับไปตรวจ transcript
            </Link>
          ) : null}
        </>
      )}
    </section>
  );
}

function isActiveProcessingState(value: AssessmentV2ProcessingRun["state"]): boolean {
  return value === "queued" || value === "running";
}

function processingStatusCopy(run: AssessmentV2ProcessingRun): { title: string; description: string } {
  if (run.error_code === "cancel_requested" && run.state === "running") {
    return {
      title: "รับคำขอหยุดแล้ว",
      description: "ระบบบันทึกคำขอหยุดแล้ว และ worker กำลังปิดงานอย่างปลอดภัย",
    };
  }
  if (run.state === "queued") {
    return {
      title: "บันทึกงานแล้ว กำลังรอประมวลผล",
      description: "ระบบเก็บงานไว้ในคิวของ FastAPI แล้ว หน้านี้จะติดตามสถานะให้อัตโนมัติ",
    };
  }
  if (run.state === "running") {
    return {
      title: "กำลังประมวลผล",
      description: "ระบบกำลังสกัดฟีเจอร์จาก transcript ที่รับรองแล้ว",
    };
  }
  if (run.state === "succeeded") {
    return {
      title: "พร้อมอ่าน",
      description: "มีผลหลักฐานเชิงพรรณนาจาก backend แล้ว โปรดอ่านร่วมกับข้อมูลทางคลินิกอื่น",
    };
  }
  if (run.state === "failed") {
    return {
      title: "ประมวลผลไม่สำเร็จ",
      description: run.can_retry ? "ระบบยังคงเก็บ transcript เดิมไว้ คุณสามารถสั่งให้ประมวลผลใหม่ได้" : "ระบบเก็บสถานะความผิดพลาดไว้เพื่อการตรวจสอบ",
    };
  }
  if (run.error_code === "cancel_requested") {
    return {
      title: "ยกเลิกแล้ว",
      description: run.can_retry ? "ระบบยังเก็บ transcript เดิมไว้ และคุณสามารถเริ่มประมวลผลใหม่ได้" : "ระบบหยุดงานตามคำขอแล้ว",
    };
  }
  return {
    title: "การประมวลผลถูกยกเลิกตามเงื่อนไขของข้อมูล",
    description: "ระบบจะไม่ใช้ผลจากงานนี้ต่อ โปรดกลับไปตรวจ transcript หรือ consent ตามข้อความที่แสดง",
  };
}

function isMissingProcessingRunError(error: unknown): boolean {
  return statusOf(error) === 404 && errorCodeOf(error) === "processing_run_not_found";
}

function safeProcessingError(error: unknown): string {
  const code = errorCodeOf(error);
  if (code === "consent_revoked") return "ไม่สามารถประมวลผลต่อได้ เพราะ consent ไม่อยู่ในสถานะใช้งาน";
  if (code === "transcript_not_attested") return "ต้องรับรอง transcript ก่อนเริ่มประมวลผล";
  if (code === "transcript_superseded") return "มี transcript ฉบับใหม่กว่าแล้ว กรุณากลับไปตรวจฉบับปัจจุบัน";
  return "ยังอ่านสถานะการประมวลผลไม่ได้ กรุณาลองใหม่เมื่อเชื่อมต่อ FastAPI ได้";
}

function safeActionError(error: unknown): string {
  const code = errorCodeOf(error);
  if (code === "stale_processing_run_version") return "สถานะงานเปลี่ยนไปแล้ว กรุณาโหลดหน้านี้ใหม่";
  if (code === "processing_run_not_retryable") return "งานนี้ยังเริ่มใหม่ไม่ได้จากสถานะปัจจุบัน";
  if (code === "processing_run_not_cancellable") return "งานนี้หยุดไม่ได้จากสถานะปัจจุบัน";
  return safeProcessingError(error);
}

function statusOf(error: unknown): number | null {
  if (typeof error !== "object" || error === null || !("status" in error)) return null;
  const value = (error as { status?: unknown }).status;
  return typeof value === "number" ? value : null;
}

function errorCodeOf(error: unknown): string | null {
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
