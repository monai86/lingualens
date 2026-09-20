import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import {
  AssessmentProcessingStatus,
  type AssessmentProcessingStatusClient,
} from "@/features/assessment-v2/components/assessment-processing-status";
import type { AssessmentV2ProcessingRun } from "@/services/assessment-v2-client";

const run = (overrides: Partial<AssessmentV2ProcessingRun> = {}): AssessmentV2ProcessingRun => ({
  id: "processing_run_opaque_01",
  stage: "evidence_extraction",
  state: "queued",
  attempt_count: 0,
  max_attempts: 3,
  available_at: "2026-09-08T12:00:00Z",
  error_code: null,
  result_available: false,
  can_retry: false,
  can_cancel: true,
  version: 1,
  ...overrides,
});

function missingRunError(): Error & { status: number; body: string } {
  return Object.assign(new Error("missing"), {
    status: 404,
    body: JSON.stringify({ error: { code: "processing_run_not_found" } }),
  });
}

function unavailableError(): Error & { status: number; body: string } {
  return Object.assign(new Error("unavailable"), {
    status: 503,
    body: JSON.stringify({ error: { code: "persistence_error" } }),
  });
}

function clientFor(overrides: Partial<AssessmentProcessingStatusClient> = {}): AssessmentProcessingStatusClient {
  return {
    queueEvidence: vi.fn().mockResolvedValue({ processing_run: run() }),
    getCurrentEvidenceProcessingRun: vi.fn().mockRejectedValue(missingRunError()),
    getProcessingRun: vi.fn().mockResolvedValue(run()),
    retryProcessingRun: vi.fn().mockResolvedValue(run()),
    cancelProcessingRun: vi.fn().mockResolvedValue(run({ state: "cancelled", error_code: "cancel_requested", can_cancel: false, can_retry: true, version: 2 })),
    ...overrides,
  };
}

async function settle(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

test("queues once, keeps the server run id, and polls it after the initial response", async () => {
  const queued = run();
  const running = run({ state: "running", attempt_count: 1, version: 2 });
  const client = clientFor({
    queueEvidence: vi.fn().mockResolvedValue({ processing_run: queued }),
    getProcessingRun: vi.fn().mockResolvedValue(running),
  });

  render(<AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={client} />);

  await settle();
  const createButton = screen.getByRole("button", { name: "สร้างหลักฐานเชิงพรรณนา" });
  fireEvent.click(createButton);

  expect(client.queueEvidence).toHaveBeenCalledTimes(1);
  await settle();
  expect(screen.getByText("บันทึกงานแล้ว กำลังรอประมวลผล")).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(2_000);
  });

  await settle();
  expect(client.getProcessingRun).toHaveBeenCalledWith(queued.id);
  expect(screen.getByText(/ครั้งที่ 1/)).toBeInTheDocument();
  expect(window.localStorage.length).toBe(0);
  expect(window.sessionStorage.length).toBe(0);
});

test("shows running cancellation only when the backend permits it", async () => {
  const running = run({ state: "running", attempt_count: 2, can_cancel: true, version: 4 });
  const client = clientFor({
    getCurrentEvidenceProcessingRun: vi.fn().mockResolvedValue({ processing_run: running }),
  });

  render(<AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={client} />);

  await settle();
  const cancel = screen.getByRole("button", { name: "หยุดการประมวลผล" });
  fireEvent.click(cancel);

  await settle();
  expect(client.cancelProcessingRun).toHaveBeenCalledWith(running.id, 4);
  expect(screen.getByText("ยกเลิกแล้ว")).toBeInTheDocument();
});

test("acknowledges a persisted cancellation request while the worker settles", async () => {
  const running = run({ state: "running", attempt_count: 2, can_cancel: true, version: 4 });
  const requested = run({
    state: "running",
    error_code: "cancel_requested",
    can_cancel: false,
    version: 5,
  });
  const client = clientFor({
    getCurrentEvidenceProcessingRun: vi.fn().mockResolvedValue({ processing_run: running }),
    cancelProcessingRun: vi.fn().mockResolvedValue(requested),
  });

  render(<AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={client} />);

  await settle();
  fireEvent.click(screen.getByRole("button", { name: "หยุดการประมวลผล" }));

  await settle();
  expect(screen.getByText("รับคำขอหยุดแล้ว")).toBeInTheDocument();
  expect(screen.getByText(/worker กำลังปิดงาน/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "หยุดการประมวลผล" })).not.toBeInTheDocument();
});

test("shows safe failure recovery and sends the backend version on retry", async () => {
  const failed = run({ state: "failed", error_code: "evidence_processing_failed", can_retry: true, can_cancel: false, version: 7 });
  const retried = run({ version: 8 });
  const client = clientFor({
    getCurrentEvidenceProcessingRun: vi.fn().mockResolvedValue({ processing_run: failed }),
    retryProcessingRun: vi.fn().mockResolvedValue(retried),
  });

  render(<AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={client} />);

  await settle();
  expect(screen.getByText("ประมวลผลไม่สำเร็จ")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "ลองประมวลผลใหม่" }));

  await settle();
  expect(client.retryProcessingRun).toHaveBeenCalledWith(failed.id, 7);
  expect(screen.getByText("บันทึกงานแล้ว กำลังรอประมวลผล")).toBeInTheDocument();
});

test("does not offer restart for a system-cancelled run and never turns an outage into success", async () => {
  const systemCancelled = run({
    state: "cancelled",
    error_code: "consent_revoked",
    can_retry: false,
    can_cancel: false,
    version: 3,
  });
  const cancelledClient = clientFor({
    getCurrentEvidenceProcessingRun: vi.fn().mockResolvedValue({ processing_run: systemCancelled }),
  });
  const { unmount } = render(
    <AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={cancelledClient} />,
  );

  await settle();
  expect(screen.getByText("การประมวลผลถูกยกเลิกตามเงื่อนไขของข้อมูล")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "เริ่มประมวลผลใหม่" })).not.toBeInTheDocument();
  unmount();

  const outageClient = clientFor({ getCurrentEvidenceProcessingRun: vi.fn().mockRejectedValue(unavailableError()) });
  render(<AssessmentProcessingStatus assessmentId="assessment_opaque_01" client={outageClient} />);

  await settle();
  expect(screen.getByRole("alert")).toHaveTextContent("ยังอ่านสถานะการประมวลผลไม่ได้");
  expect(outageClient.queueEvidence).not.toHaveBeenCalled();
  expect(screen.queryByText("พร้อมอ่าน")).not.toBeInTheDocument();
});
