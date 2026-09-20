import { beforeEach, describe, expect, it, vi } from "vitest";

import { uploadAssessmentRecording } from "@/features/assessment-v2/lib/assessment-recording-upload";

const recording = {
  id: "recording_opaque_01",
  activity_code: "free_play",
  content_type: "audio/webm",
  size_bytes: 5,
  upload_state: "pending" as const,
  expires_at: "2026-09-07T09:00:00Z",
  verified_at: null,
  version: 1,
};

const processingRun = {
  id: "run_opaque_01",
  stage: "upload_verification" as const,
  state: "queued" as const,
  attempt_count: 0,
  error_code: null,
};

const uploadIntent = {
  recording,
  upload: {
    url: "https://storage.example.test/signed-upload",
    expires_at: "2026-09-07T09:00:00Z",
    expires_in_seconds: 900,
    chunk_size_bytes: 5,
    upload_length_bytes: 5,
    content_type: "audio/webm",
    upsert: false,
  },
};

describe("uploadAssessmentRecording", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("hashes the blob, creates an idempotent intent, uploads privately, and completes it", async () => {
    const client = {
      createRecording: vi.fn().mockResolvedValue({ recording, processing_run: processingRun }),
      createUploadIntent: vi.fn().mockResolvedValue(uploadIntent),
      completeUpload: vi.fn().mockResolvedValue({ recording: { ...recording, upload_state: "uploaded" }, processing_run: processingRun }),
    };
    const upload = vi.fn().mockResolvedValue(undefined);
    const blob = new Blob(["hello"], { type: "audio/webm" });

    const result = await uploadAssessmentRecording({
      client,
      assessmentId: "assessment_opaque_01",
      activityCode: "free_play",
      blob,
      idempotencyKey: "capture-key-01",
      upload,
    });

    expect(client.createRecording).toHaveBeenCalledWith(
      "assessment_opaque_01",
      "free_play",
      {
        content_type: "audio/webm",
        size_bytes: 5,
        checksum: "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
      },
      "capture-key-01",
    );
    expect(client.createUploadIntent).toHaveBeenCalledWith("recording_opaque_01");
    expect(upload).toHaveBeenCalledWith(uploadIntent.upload.url, blob);
    expect(client.completeUpload).toHaveBeenCalledWith("recording_opaque_01");
    expect(result).toEqual({
      recording: { ...recording, upload_state: "uploaded" },
      processing_run: processingRun,
      checksum: "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    });
  });

  it("does not mark the recording complete when the signed upload fails", async () => {
    const client = {
      createRecording: vi.fn().mockResolvedValue({ recording, processing_run: processingRun }),
      createUploadIntent: vi.fn().mockResolvedValue(uploadIntent),
      completeUpload: vi.fn(),
    };
    const upload = vi.fn().mockRejectedValue(new Error("network"));

    await expect(uploadAssessmentRecording({
      client,
      assessmentId: "assessment_opaque_01",
      activityCode: "free_play",
      blob: new Blob(["hello"], { type: "audio/webm" }),
      idempotencyKey: "capture-key-01",
      upload,
    })).rejects.toThrow("network");

    expect(client.completeUpload).not.toHaveBeenCalled();
  });
});
