import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import {
  AssessmentSegmentReviewWorkspace,
  type AssessmentSegmentReviewClient,
} from "@/features/assessment-v2/components/assessment-segment-review-workspace";
import type {
  AssessmentV2ProcessingRun,
  AssessmentV2TranscriptSegmentSet,
  AssessmentV2TranscriptRevision,
} from "@/services/assessment-v2-client";

function transcript(overrides: Partial<AssessmentV2TranscriptRevision> = {}): AssessmentV2TranscriptRevision {
  return {
    id: "transcript_revision_opaque_01",
    assessment_id: "assessment_opaque_01",
    revision: 1,
    source: "asr_draft",
    review_state: "attested",
    content: "*CHI: hello .\n*MOT: hi .\n",
    content_sha256: "a".repeat(64),
    created_at: "2026-09-07T08:00:00Z",
    attested_at: "2026-09-07T08:01:00Z",
    version: 2,
    ...overrides,
  };
}

function segmentSet(overrides: Partial<AssessmentV2TranscriptSegmentSet> = {}): AssessmentV2TranscriptSegmentSet {
  return {
    id: "segment_set_opaque_01",
    assessment_id: "assessment_opaque_01",
    transcript_revision_id: "transcript_revision_opaque_01",
    transcript_content_sha256: "a".repeat(64),
    recording_id: "recording_opaque_01",
    revision: 1,
    source: "asr_draft",
    review_state: "draft",
    segments_sha256: "b".repeat(64),
    segments: [
      {
        id: "segment_opaque_01",
        ordinal: 1,
        start_ms: 0,
        end_ms: 1200,
        speaker_role: "child",
        text: "hello .",
        confidence: 0.91,
        uncertainty_reason: "none",
        created_at: "2026-09-07T08:00:00Z",
      },
      {
        id: "segment_opaque_02",
        ordinal: 2,
        start_ms: 1200,
        end_ms: 2600,
        speaker_role: "unknown",
        text: "hi .",
        confidence: 0.42,
        uncertainty_reason: "speaker_uncertain",
        created_at: "2026-09-07T08:00:00Z",
      },
    ],
    created_at: "2026-09-07T08:00:00Z",
    attested_at: null,
    version: 1,
    ...overrides,
  };
}

function processingRun(): AssessmentV2ProcessingRun {
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
  };
}

function missingProcessingRun(): Error & { status: number; body: string } {
  return Object.assign(new Error("not found"), {
    status: 404,
    body: JSON.stringify({ error: { code: "processing_run_not_found" } }),
  });
}

function clientOverrides(overrides: Partial<AssessmentSegmentReviewClient> = {}): AssessmentSegmentReviewClient {
  return {
    ...overrides,
    getTranscript: overrides.getTranscript ?? vi.fn().mockResolvedValue(transcript()),
    createTranscriptRevision: overrides.createTranscriptRevision ?? vi.fn().mockResolvedValue(transcript()),
    attestTranscript: overrides.attestTranscript ?? vi.fn().mockResolvedValue(transcript({ review_state: "attested" })),
    getCurrentTranscriptSegmentSet: overrides.getCurrentTranscriptSegmentSet ?? vi.fn().mockResolvedValue(segmentSet()),
    createTranscriptSegmentSet: overrides.createTranscriptSegmentSet ?? vi.fn().mockResolvedValue(segmentSet({
      id: "segment_set_opaque_02",
      revision: 2,
    })),
    attestTranscriptSegmentSet: overrides.attestTranscriptSegmentSet ?? vi.fn().mockResolvedValue(segmentSet({
      review_state: "attested",
      version: 2,
      attested_at: "2026-09-07T08:03:00Z",
    })),
    createSegmentReplayGrant: overrides.createSegmentReplayGrant ?? vi.fn().mockResolvedValue({
      segment_id: "segment_opaque_01",
      start_ms: 0,
      end_ms: 1200,
      available: true,
      url: "https://signed.example/replay",
      expires_at: "2026-09-07T08:05:00Z",
      expires_in_seconds: 300,
    }),
    queueEvidence: overrides.queueEvidence ?? vi.fn().mockResolvedValue({ processing_run: processingRun() }),
    getCurrentEvidenceProcessingRun: overrides.getCurrentEvidenceProcessingRun ?? vi.fn().mockRejectedValue(missingProcessingRun()),
    getProcessingRun: overrides.getProcessingRun ?? vi.fn().mockResolvedValue(processingRun()),
    retryProcessingRun: overrides.retryProcessingRun ?? vi.fn().mockResolvedValue(processingRun()),
    cancelProcessingRun: overrides.cancelProcessingRun ?? vi.fn().mockResolvedValue(processingRun()),
  };
}

test("shows the full segment timeline, uncertain-only filter, focused edit, and revision attestation", async () => {
  const client = clientOverrides();

  render(<AssessmentSegmentReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  expect(await screen.findByRole("heading", { name: "ทบทวน transcript รายช่วง" })).toBeInTheDocument();
  expect(screen.getByText("รับรองแล้ว", { exact: true })).toBeInTheDocument();
  expect(screen.getAllByText("hello .").length).toBeGreaterThan(0);
  expect(screen.getAllByText("hi .").length).toBeGreaterThan(0);
  expect(screen.getByText(/2\s*ช่วง/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "แสดงเฉพาะช่วงที่ไม่แน่ใจ" }));
  expect(screen.queryByText("hello .")).not.toBeInTheDocument();
  expect(screen.getAllByText("hi .").length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "แก้ไขช่วงที่ 2" }));
  fireEvent.change(screen.getByRole("textbox", { name: "ข้อความช่วงที่ 2" }), {
    target: { value: "hi there ." },
  });
  fireEvent.change(screen.getByRole("combobox", { name: "บทบาทผู้พูดช่วงที่ 2" }), {
    target: { value: "caregiver" },
  });
  fireEvent.click(screen.getByRole("button", { name: "บันทึก revision ใหม่" }));

  await waitFor(() => expect(client.createTranscriptSegmentSet).toHaveBeenCalledWith(
    "assessment_opaque_01",
    expect.objectContaining({
      transcript_revision_id: "transcript_revision_opaque_01",
      expected_revision: 1,
      expected_version: 1,
      segments: expect.arrayContaining([
        expect.objectContaining({
          ordinal: 2,
          text: "hi there .",
          speaker_role: "caregiver",
        }),
      ]),
    }),
  ));

  fireEvent.click(screen.getByRole("checkbox", { name: /ฉันได้ตรวจสอบทุกช่วง/ }));
  fireEvent.click(screen.getByRole("button", { name: "รับรอง segment revision" }));

  await waitFor(() => expect(client.attestTranscriptSegmentSet).toHaveBeenCalledWith(
    "segment_set_opaque_02",
    1,
  ));
  expect((await screen.findAllByText(/รับรอง segment revision แล้ว/)).length).toBeGreaterThan(0);
});

test("requests a signed replay grant and states when audio is unavailable", async () => {
  const client = clientOverrides({
    createSegmentReplayGrant: vi.fn()
      .mockResolvedValueOnce({
        segment_id: "segment_opaque_01",
        start_ms: 0,
        end_ms: 1200,
        available: true,
        url: "https://signed.example/replay",
        expires_at: "2026-09-07T08:05:00Z",
        expires_in_seconds: 300,
      })
      .mockResolvedValueOnce({
        segment_id: "segment_opaque_02",
        start_ms: 1200,
        end_ms: 2600,
        available: false,
        url: null,
        expires_at: null,
        expires_in_seconds: null,
      }),
  });

  render(<AssessmentSegmentReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);
  await screen.findByRole("heading", { name: "ทบทวน transcript รายช่วง" });

  fireEvent.click(screen.getByRole("button", { name: "เล่นเสียงช่วงที่ 1" }));
  expect(await screen.findByRole("audio")).toHaveAttribute("src", "https://signed.example/replay");
  await waitFor(() => expect(client.createSegmentReplayGrant).toHaveBeenCalledTimes(1));

  fireEvent.click(screen.getByRole("button", { name: "เล่นเสียงช่วงที่ 2" }));
  await waitFor(() => expect(client.createSegmentReplayGrant).toHaveBeenCalledTimes(2));
  expect(await screen.findByText(/เสียงของช่วงนี้ยังไม่พร้อมใช้งาน/)).toBeInTheDocument();
});

test("exposes a stale revision conflict with a safe reload action", async () => {
  const staleError = Object.assign(new Error("stale"), {
    status: 409,
    body: JSON.stringify({ error: { code: "stale_segment_set_version" } }),
  });
  const getCurrentTranscriptSegmentSet = vi.fn()
    .mockResolvedValueOnce(segmentSet())
    .mockResolvedValueOnce(segmentSet({ id: "segment_set_opaque_03", revision: 3 }));
  const client = clientOverrides({
    getCurrentTranscriptSegmentSet,
    createTranscriptSegmentSet: vi.fn().mockRejectedValue(staleError),
  });

  render(<AssessmentSegmentReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);
  await screen.findByRole("heading", { name: "ทบทวน transcript รายช่วง" });
  fireEvent.click(screen.getByRole("button", { name: "แก้ไขช่วงที่ 1" }));
  fireEvent.change(screen.getByRole("textbox", { name: "ข้อความช่วงที่ 1" }), {
    target: { value: "hello revised ." },
  });
  fireEvent.click(screen.getByRole("button", { name: "บันทึก revision ใหม่" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("ข้อมูล segment เปลี่ยนแปลงแล้ว");
  fireEvent.click(screen.getByRole("button", { name: "โหลด revision ล่าสุด" }));
  await waitFor(() => expect(getCurrentTranscriptSegmentSet).toHaveBeenCalledTimes(2));
  expect(await screen.findByText(/segment_set_opaque_03/)).toBeInTheDocument();
});

test("keeps transcript attestation as the prerequisite when no segment set exists", async () => {
  const draft = transcript({ review_state: "draft", attested_at: null, version: 1 });
  const attested = transcript({ review_state: "attested", attested_at: "2026-09-07T08:02:00Z", version: 2 });
  const missingSegmentSet = Object.assign(new Error("missing segments"), {
    status: 404,
    body: JSON.stringify({ error: { code: "segment_set_not_found" } }),
  });
  const client = clientOverrides({
    getTranscript: vi.fn().mockResolvedValueOnce(draft).mockResolvedValueOnce(attested),
    getCurrentTranscriptSegmentSet: vi.fn().mockRejectedValue(missingSegmentSet),
    attestTranscript: vi.fn().mockResolvedValue(attested),
  });

  render(<AssessmentSegmentReviewWorkspace assessmentId="assessment_opaque_01" client={client} />);

  expect(await screen.findByRole("heading", { name: "รับรอง transcript" })).toBeInTheDocument();
  const attestButton = screen.getByRole("button", { name: "รับรอง transcript" });
  expect(attestButton).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox", { name: /ยืนยันว่า transcript พร้อม/ }));
  fireEvent.click(attestButton);
  await waitFor(() => expect(client.attestTranscript).toHaveBeenCalledWith(
    "transcript_revision_opaque_01",
    1,
  ));
});
