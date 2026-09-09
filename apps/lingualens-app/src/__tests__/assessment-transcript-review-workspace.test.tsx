import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import {
  AssessmentTranscriptReviewWorkspace,
  type AssessmentTranscriptReviewClient,
} from "@/features/assessment-v2/components/assessment-transcript-review-workspace";
import type { AssessmentV2ProcessingRun } from "@/services/assessment-v2-client";

function transcript(overrides: Partial<Awaited<ReturnType<AssessmentTranscriptReviewClient["getTranscript"]>>> = {}) {
  return {
    id: "transcript_revision_opaque_01",
    assessment_id: "assessment_opaque_01",
    revision: 1,
    source: "asr_draft" as const,
    review_state: "draft" as const,
    content: "*CHI: hello .\n",
    content_sha256: "a".repeat(64),
    created_at: "2026-09-07T08:00:00Z",
    attested_at: null,
    version: 1,
    ...overrides,
  };
}

function missingProcessingRun(): Error & { status: number; body: string } {
  return Object.assign(new Error("not found"), {
    status: 404,
    body: JSON.stringify({ error: { code: "processing_run_not_found" } }),
  });
}

function processingRun(overrides: Partial<AssessmentV2ProcessingRun> = {}): AssessmentV2ProcessingRun {
  return {
    id: "processing_run_opaque_01",
    stage: "evidence_extraction",
    state: "queued",
    attempt_count: 0,
    max_attempts: 3,
    available_at: "2026-09-07T08:02:00Z",
    error_code: null,
    result_available: false,
    can_retry: false,
    can_cancel: true,
    version: 1,
    ...overrides,
  };
}

function processingClient(): Pick<
  AssessmentTranscriptReviewClient,
  "queueEvidence" | "getCurrentEvidenceProcessingRun" | "getProcessingRun" | "retryProcessingRun" | "cancelProcessingRun"
> {
  return {
    queueEvidence: vi.fn().mockResolvedValue({ processing_run: processingRun() }),
    getCurrentEvidenceProcessingRun: vi.fn().mockRejectedValue(missingProcessingRun()),
    getProcessingRun: vi.fn().mockResolvedValue(processingRun()),
    retryProcessingRun: vi.fn().mockResolvedValue(processingRun()),
    cancelProcessingRun: vi.fn().mockResolvedValue(processingRun({
      state: "cancelled",
      error_code: "cancel_requested",
      can_cancel: false,
      can_retry: true,
      version: 2,
    })),
  };
}

test("loads a draft, saves a new revision, and requires explicit attestation", async () => {
  const saved = transcript({
    id: "transcript_revision_opaque_02",
    revision: 2,
    content: "*CHI: hello there .\n",
  });
  const attested = transcript({
    ...saved,
    review_state: "attested",
    version: 2,
    attested_at: "2026-09-07T08:03:00Z",
  });
  const client: AssessmentTranscriptReviewClient = {
    getTranscript: vi.fn().mockResolvedValue(transcript()),
    createTranscriptRevision: vi.fn().mockResolvedValue(saved),
    attestTranscript: vi.fn().mockResolvedValue(attested),
    ...processingClient(),
  };

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  const editor = await screen.findByRole("textbox", { name: "เนื้อหา transcript" });
  expect(editor).toHaveValue("*CHI: hello .\n");
  expect(screen.getByRole("status")).toHaveTextContent("สถานะ: รอตรวจสอบ");

  fireEvent.change(editor, { target: { value: "*CHI: hello there .\n" } });
  fireEvent.click(screen.getByRole("button", { name: "บันทึกฉบับร่าง" }));

  await waitFor(() => expect(client.createTranscriptRevision).toHaveBeenCalledWith(
    "assessment_opaque_01",
    {
      source: "asr_draft",
      content: "*CHI: hello there .\n",
      expected_revision: 1,
      expected_version: 1,
    },
  ));
  expect(screen.getByRole("button", { name: "รับรอง transcript" })).toBeDisabled();

  fireEvent.click(screen.getByRole("checkbox", { name: /ฉันได้ตรวจสอบ/ }));
  fireEvent.click(screen.getByRole("button", { name: "รับรอง transcript" }));

  await waitFor(() => expect(client.attestTranscript).toHaveBeenCalledWith(
    "transcript_revision_opaque_02",
    1,
  ));
  expect(await screen.findByText("รับรองแล้ว")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "สร้างหลักฐานเชิงพรรณนา" }));
  await waitFor(() => expect(client.queueEvidence).toHaveBeenCalledWith("assessment_opaque_01"));
  expect(await screen.findByText("บันทึกงานแล้ว กำลังรอประมวลผล")).toBeInTheDocument();
});

test("does not hide transcript API failures and offers retry", async () => {
  const getTranscript = vi.fn().mockRejectedValue(new Error("network"));
  const client: AssessmentTranscriptReviewClient = {
    getTranscript,
    createTranscriptRevision: vi.fn(),
    attestTranscript: vi.fn(),
    ...processingClient(),
  };

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("ไม่สามารถโหลด transcript ได้"));
  expect(screen.getByRole("button", { name: "ลองใหม่" })).toBeInTheDocument();
  expect(getTranscript).toHaveBeenCalledWith("assessment_opaque_01");
});

test("starts the first transcript draft when the processing assessment has no revision yet", async () => {
  const client: AssessmentTranscriptReviewClient = {
    getTranscript: vi.fn().mockRejectedValue(Object.assign(new Error("not found"), {
      status: 404,
      body: JSON.stringify({ error: { code: "transcript_not_found" } }),
    })),
    createTranscriptRevision: vi.fn().mockResolvedValue(transcript({ source: "asr_draft" })),
    attestTranscript: vi.fn(),
    ...processingClient(),
  };

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  const editor = await screen.findByRole("textbox", { name: "เนื้อหา transcript" });
  fireEvent.change(editor, { target: { value: "@UTF8\n@Begin\n*CHI: hello .\n@End\n" } });
  fireEvent.click(screen.getByRole("button", { name: "สร้างฉบับร่าง" }));

  await waitFor(() => expect(client.createTranscriptRevision).toHaveBeenCalledWith(
    "assessment_opaque_01",
    {
      source: "asr_draft",
      content: "@UTF8\n@Begin\n*CHI: hello .\n@End\n",
      expected_revision: null,
      expected_version: null,
    },
  ));
});

test("does not hide an assessment 404 as an empty transcript draft", async () => {
  const client: AssessmentTranscriptReviewClient = {
    getTranscript: vi.fn().mockRejectedValue(Object.assign(new Error("not found"), {
      status: 404,
      body: JSON.stringify({ error: { code: "assessment_not_found" } }),
    })),
    createTranscriptRevision: vi.fn(),
    attestTranscript: vi.fn(),
    ...processingClient(),
  };

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("ไม่สามารถโหลด transcript ได้"));
  expect(screen.queryByRole("textbox", { name: "เนื้อหา transcript" })).not.toBeInTheDocument();
});

test("does not generate evidence while an attested transcript has unsaved edits", async () => {
  const client: AssessmentTranscriptReviewClient = {
    getTranscript: vi.fn().mockResolvedValue(transcript({
      review_state: "attested",
      version: 2,
      attested_at: "2026-09-07T08:03:00Z",
    })),
    createTranscriptRevision: vi.fn(),
    attestTranscript: vi.fn(),
    ...processingClient(),
  };

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  const editor = await screen.findByRole("textbox", { name: "เนื้อหา transcript" });
  fireEvent.change(editor, { target: { value: "*CHI: unsaved content .\n" } });

  const evidenceButton = screen.getByRole("button", { name: "สร้างหลักฐานเชิงพรรณนา" });
  expect(evidenceButton).toBeDisabled();
  expect(screen.getByText("บันทึกฉบับร่างก่อนสร้างหลักฐาน")).toBeInTheDocument();
  expect(client.queueEvidence).not.toHaveBeenCalled();
});

test("shows evidence extraction failure instead of fabricating a local result", async () => {
  const client: AssessmentTranscriptReviewClient = {
    getTranscript: vi.fn().mockResolvedValue(transcript({ review_state: "attested", version: 2, attested_at: "2026-09-07T08:03:00Z" })),
    createTranscriptRevision: vi.fn(),
    attestTranscript: vi.fn(),
    ...processingClient(),
  };
  client.queueEvidence = vi.fn().mockRejectedValue(new Error("worker unavailable"));

  render(<AssessmentTranscriptReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  fireEvent.click(await screen.findByRole("button", { name: "สร้างหลักฐานเชิงพรรณนา" }));

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("ยังอ่านสถานะการประมวลผลไม่ได้"));
  expect(client.queueEvidence).toHaveBeenCalledWith("assessment_opaque_01");
  expect(screen.queryByText(/ASD|probability|ความน่าจะเป็น/i)).not.toBeInTheDocument();
});
