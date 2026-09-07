import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { AssessmentCaptureWorkspace } from "@/features/assessment-v2/components/assessment-capture-workspace";

vi.mock("@/components/browser-audio-recorder", () => ({
  BrowserAudioRecorder: ({ onRecordingReady }: { onRecordingReady?: (blob: Blob, metadata: { recordingStatus: "stopped"; durationSeconds: number; mimeType: string; createdAt: string; hasUnsavedRecording: boolean }) => void }) => (
    <button
      type="button"
      onClick={() => onRecordingReady?.(
        new Blob(["hello"], { type: "audio/webm" }),
        {
          recordingStatus: "stopped",
          durationSeconds: 5,
          mimeType: "audio/webm",
          createdAt: "2026-09-07T08:00:00Z",
          hasUnsavedRecording: true,
        },
      )}
    >
      จำลองอัดเสียงเสร็จ
    </button>
  ),
}));

beforeEach(() => {
  vi.restoreAllMocks();
});

test("requires explicit consent confirmation before creating an assessment", async () => {
  const client = {
    listChildren: vi.fn().mockResolvedValue([
      {
        id: "child_opaque_01",
        display_code: "LL-0007",
        birth_year: 2021,
        birth_month: 6,
        language_context: { primary: "th", additional: [] },
        version: 1,
      },
    ]),
    getChild: vi.fn().mockResolvedValue({
      id: "child_opaque_01",
      display_code: "LL-0007",
      birth_year: 2021,
      birth_month: 6,
      language_context: { primary: "th", additional: [] },
      version: 1,
    }),
    listConsents: vi.fn().mockResolvedValue([]),
    listAssessments: vi.fn().mockResolvedValue([]),
    createConsent: vi.fn().mockResolvedValue({
      id: "consent_opaque_01",
      child_id: "child_opaque_01",
      purpose: "clinical_assessment",
      scope_version: "clinical-v1",
      status: "active",
      granted_at: "2026-09-07T08:00:00Z",
      withdrawn_at: null,
      version: 1,
    }),
    createAssessment: vi.fn().mockResolvedValue({
      id: "assessment_opaque_01",
      child_id: "child_opaque_01",
      purpose: "initial",
      state: "draft",
      age_months: 36,
      language_context: { primary: "th", additional: [] },
      assigned_clinician_id: "therapist_opaque_01",
      version: 1,
    }),
    selectProtocol: vi.fn().mockResolvedValue({
      assessment_id: "assessment_opaque_01",
      state: "ready_for_capture",
      protocol: {
        protocol_version_key: "thai_guided_language_sample:v0",
        selected_at: "2026-09-07T08:00:00Z",
        version: 1,
      },
      activities: [
        {
          activity_code: "free_play",
          required: true,
          target_duration_seconds: 180,
          minimum_duration_seconds: 120,
        },
      ],
      recordings: [],
      progress: {
        required_activities_total: 1,
        required_activities_verified: 0,
        required_activities_usable: 0,
      },
    }),
    startCapture: vi.fn(),
    createRecording: vi.fn(),
    createUploadIntent: vi.fn(),
    completeUpload: vi.fn(),
    getCapture: vi.fn(),
    getRecordingQuality: vi.fn(),
    completeCapture: vi.fn(),
  };

  render(<AssessmentCaptureWorkspace client={client} />);

  fireEvent.click(await screen.findByRole("button", { name: "เลือก LL-0007" }));

  expect(await screen.findByText("ยังไม่มี consent สำหรับการประเมิน" )).toBeInTheDocument();
  const startButton = screen.getByRole("button", { name: "บันทึก consent และเริ่มการประเมิน" });
  expect(startButton).toBeDisabled();
  expect(client.createAssessment).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("checkbox", { name: "ยืนยันว่าได้รับ consent แล้ว" }));
  expect(startButton).toBeEnabled();
  fireEvent.click(startButton);

  expect(await screen.findByRole("heading", { name: "พร้อมบันทึกเสียง" })).toBeInTheDocument();
  expect(screen.getByText("เล่นอิสระ" )).toBeInTheDocument();
  expect(client.createConsent).toHaveBeenCalledWith("child_opaque_01", {
    purpose: "clinical_assessment",
    scope_version: "clinical-v1",
    status: "active",
  });
  expect(client.createAssessment).toHaveBeenCalledWith("child_opaque_01", { purpose: "initial" });
  expect(client.selectProtocol).toHaveBeenCalledWith("assessment_opaque_01");
});

test("shows an unavailable state when the child list cannot be loaded", async () => {
  const client = {
    listChildren: vi.fn().mockRejectedValue(new Error("network")),
    getChild: vi.fn(),
    listConsents: vi.fn(),
    listAssessments: vi.fn(),
    createConsent: vi.fn(),
    createAssessment: vi.fn(),
    selectProtocol: vi.fn(),
    startCapture: vi.fn(),
    createRecording: vi.fn(),
    createUploadIntent: vi.fn(),
    completeUpload: vi.fn(),
    getCapture: vi.fn(),
    getRecordingQuality: vi.fn(),
    completeCapture: vi.fn(),
  };

  render(<AssessmentCaptureWorkspace client={client} />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("ไม่สามารถโหลดรายการเด็กได้"));
  expect(screen.getByRole("button", { name: "ลองใหม่" })).toBeInTheDocument();
});

test("uploads a completed activity recording and shows the server handoff state", async () => {
  const client = {
    listChildren: vi.fn().mockResolvedValue([
      {
        id: "child_opaque_01",
        display_code: "LL-0007",
        birth_year: 2021,
        birth_month: 6,
        language_context: { primary: "th", additional: [] },
        version: 1,
      },
    ]),
    getChild: vi.fn().mockResolvedValue({
      id: "child_opaque_01",
      display_code: "LL-0007",
      birth_year: 2021,
      birth_month: 6,
      language_context: { primary: "th", additional: [] },
      version: 1,
    }),
    listConsents: vi.fn().mockResolvedValue([{
      id: "consent_opaque_01",
      child_id: "child_opaque_01",
      purpose: "clinical_assessment",
      scope_version: "clinical-v1",
      status: "active",
      granted_at: "2026-09-07T08:00:00Z",
      withdrawn_at: null,
      version: 1,
    }]),
    listAssessments: vi.fn().mockResolvedValue([]),
    createConsent: vi.fn(),
    createAssessment: vi.fn().mockResolvedValue({
      id: "assessment_opaque_01",
      child_id: "child_opaque_01",
      purpose: "initial",
      state: "draft",
      age_months: 36,
      language_context: { primary: "th", additional: [] },
      assigned_clinician_id: "therapist_opaque_01",
      version: 1,
    }),
    selectProtocol: vi.fn().mockResolvedValue({
      assessment_id: "assessment_opaque_01",
      state: "ready_for_capture",
      protocol: {
        protocol_version_key: "thai_guided_language_sample:v0",
        selected_at: "2026-09-07T08:00:00Z",
        version: 1,
      },
      activities: [{
        activity_code: "free_play",
        required: true,
        target_duration_seconds: 180,
        minimum_duration_seconds: 120,
      }],
      recordings: [],
      progress: {
        required_activities_total: 1,
        required_activities_verified: 0,
        required_activities_usable: 0,
      },
    }),
    startCapture: vi.fn().mockResolvedValue({
      assessment_id: "assessment_opaque_01",
      state: "capturing",
      version: 2,
    }),
    createRecording: vi.fn().mockResolvedValue({
      recording: {
        id: "recording_opaque_01",
        activity_code: "free_play",
        content_type: "audio/webm",
        size_bytes: 5,
        upload_state: "pending",
        expires_at: "2026-09-07T09:00:00Z",
        verified_at: null,
        version: 1,
      },
      processing_run: {
        id: "run_opaque_01",
        stage: "upload_verification",
        state: "queued",
        attempt_count: 0,
        error_code: null,
      },
    }),
    createUploadIntent: vi.fn().mockResolvedValue({
      recording: {
        id: "recording_opaque_01",
        activity_code: "free_play",
        content_type: "audio/webm",
        size_bytes: 5,
        upload_state: "uploading",
        expires_at: "2026-09-07T09:00:00Z",
        verified_at: null,
        version: 2,
      },
      upload: {
        url: "https://storage.example.test/signed-upload",
        expires_at: "2026-09-07T09:00:00Z",
        expires_in_seconds: 900,
        chunk_size_bytes: 5,
        upload_length_bytes: 5,
        content_type: "audio/webm",
        upsert: false,
      },
    }),
    completeUpload: vi.fn().mockResolvedValue({
      recording: {
        id: "recording_opaque_01",
        activity_code: "free_play",
        content_type: "audio/webm",
        size_bytes: 5,
        upload_state: "uploaded",
        expires_at: "2026-09-07T09:00:00Z",
        verified_at: null,
        version: 3,
      },
      processing_run: {
        id: "run_opaque_01",
        stage: "upload_verification",
        state: "queued",
        attempt_count: 0,
        error_code: null,
      },
    }),
    getCapture: vi.fn().mockResolvedValue({
      assessment_id: "assessment_opaque_01",
      state: "capturing",
      protocol: {
        protocol_version_key: "thai_guided_language_sample:v0",
        selected_at: "2026-09-07T08:00:00Z",
        version: 1,
      },
      activities: [{
        activity_code: "free_play",
        required: true,
        target_duration_seconds: 180,
        minimum_duration_seconds: 120,
      }],
      recordings: [{
        id: "recording_opaque_01",
        activity_code: "free_play",
        content_type: "audio/webm",
        size_bytes: 5,
        upload_state: "verified",
        expires_at: "2026-09-07T09:00:00Z",
        verified_at: "2026-09-07T08:02:00Z",
        version: 4,
      }],
      progress: {
        required_activities_total: 1,
        required_activities_verified: 1,
        required_activities_usable: 0,
      },
    }),
    getRecordingQuality: vi.fn().mockResolvedValue({
      status: "needs_additional_sample",
      evaluated_at: "2026-09-07T08:03:00Z",
      version: 1,
    }),
    completeCapture: vi.fn(),
  };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 200 })));

  render(<AssessmentCaptureWorkspace client={client} />);
  fireEvent.click(await screen.findByRole("button", { name: "เลือก LL-0007" }));
  fireEvent.click(await screen.findByRole("button", { name: "เริ่มการประเมิน" }));
  fireEvent.click(await screen.findByRole("button", { name: "เริ่มบันทึกเสียง" }));

  fireEvent.click(await screen.findByRole("button", { name: "จำลองอัดเสียงเสร็จ" }));
  fireEvent.click(screen.getByRole("button", { name: "อัปโหลดตัวอย่างเสียง" }));

  expect(await screen.findByRole("status")).toHaveTextContent("อัปโหลดแล้ว รอตรวจสอบคุณภาพ");
  expect(client.createRecording).toHaveBeenCalledWith(
    "assessment_opaque_01",
    "free_play",
    expect.objectContaining({
      content_type: "audio/webm",
      size_bytes: 5,
      checksum: "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    }),
    expect.stringMatching(/^capture-/),
  );
  expect(client.completeUpload).toHaveBeenCalledWith("recording_opaque_01");
  expect(await screen.findByText("ตัวอย่างนี้ยังต้องเก็บเพิ่มเติม")).toBeInTheDocument();
});

test("only completes an assessment after the required recording is usable", async () => {
  const child = {
    id: "child_opaque_01",
    display_code: "LL-0007",
    birth_year: 2021,
    birth_month: 6,
    language_context: { primary: "th", additional: [] },
    version: 1,
  };
  const capture = {
    assessment_id: "assessment_opaque_01",
    state: "capturing" as const,
    protocol: {
      protocol_version_key: "thai_guided_language_sample:v0",
      selected_at: "2026-09-07T08:00:00Z",
      version: 1,
    },
    activities: [{
      activity_code: "free_play",
      required: true,
      target_duration_seconds: 180,
      minimum_duration_seconds: 120,
    }],
    recordings: [{
      id: "recording_opaque_01",
      activity_code: "free_play",
      content_type: "audio/webm",
      size_bytes: 5,
      upload_state: "verified" as const,
      expires_at: "2026-09-07T09:00:00Z",
      verified_at: "2026-09-07T08:02:00Z",
      version: 4,
    }],
    progress: {
      required_activities_total: 1,
      required_activities_verified: 1,
      required_activities_usable: 1,
    },
  };
  const client = {
    listChildren: vi.fn().mockResolvedValue([child]),
    getChild: vi.fn().mockResolvedValue(child),
    listConsents: vi.fn().mockResolvedValue([{
      id: "consent_opaque_01",
      child_id: child.id,
      purpose: "clinical_assessment",
      scope_version: "clinical-v1",
      status: "active",
      granted_at: "2026-09-07T08:00:00Z",
      withdrawn_at: null,
      version: 1,
    }]),
    listAssessments: vi.fn().mockResolvedValue([]),
    createConsent: vi.fn(),
    createAssessment: vi.fn().mockResolvedValue({
      id: "assessment_opaque_01",
      child_id: child.id,
      purpose: "initial",
      state: "draft",
      age_months: 36,
      language_context: child.language_context,
      assigned_clinician_id: "therapist_opaque_01",
      version: 1,
    }),
    selectProtocol: vi.fn().mockResolvedValue({ ...capture, state: "ready_for_capture", recordings: [], progress: { ...capture.progress, required_activities_verified: 0, required_activities_usable: 0 } }),
    startCapture: vi.fn().mockResolvedValue({ assessment_id: capture.assessment_id, state: "capturing", version: 2 }),
    createRecording: vi.fn().mockResolvedValue({
      recording: { ...capture.recordings[0], upload_state: "pending", version: 1 },
      processing_run: { id: "run_opaque_01", stage: "upload_verification", state: "queued", attempt_count: 0, error_code: null },
    }),
    createUploadIntent: vi.fn().mockResolvedValue({
      recording: { ...capture.recordings[0], upload_state: "uploading", version: 2 },
      upload: { url: "https://storage.example.test/signed-upload", expires_at: "2026-09-07T09:00:00Z", expires_in_seconds: 900, chunk_size_bytes: 5, upload_length_bytes: 5, content_type: "audio/webm", upsert: false },
    }),
    completeUpload: vi.fn().mockResolvedValue({
      recording: { ...capture.recordings[0], upload_state: "uploaded", verified_at: null, version: 3 },
      processing_run: { id: "run_opaque_01", stage: "upload_verification", state: "queued", attempt_count: 0, error_code: null },
    }),
    getCapture: vi.fn().mockResolvedValue(capture),
    getRecordingQuality: vi.fn().mockResolvedValue({ status: "usable", evaluated_at: "2026-09-07T08:03:00Z", version: 1 }),
    completeCapture: vi.fn().mockResolvedValue({
      id: capture.assessment_id,
      child_id: child.id,
      purpose: "initial",
      state: "processing",
      age_months: 36,
      language_context: child.language_context,
      assigned_clinician_id: "therapist_opaque_01",
      version: 5,
    }),
  };
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 200 })));

  render(<AssessmentCaptureWorkspace client={client} />);
  fireEvent.click(await screen.findByRole("button", { name: "เลือก LL-0007" }));
  fireEvent.click(await screen.findByRole("button", { name: "เริ่มการประเมิน" }));
  fireEvent.click(await screen.findByRole("button", { name: "เริ่มบันทึกเสียง" }));
  fireEvent.click(await screen.findByRole("button", { name: "จำลองอัดเสียงเสร็จ" }));
  fireEvent.click(screen.getByRole("button", { name: "อัปโหลดตัวอย่างเสียง" }));

  fireEvent.click(await screen.findByRole("button", { name: "ส่ง assessment เข้า processing" }));

  expect(await screen.findByRole("heading", { name: "ส่งข้อมูลครบแล้ว" })).toBeInTheDocument();
  expect(client.completeCapture).toHaveBeenCalledWith("assessment_opaque_01");
});

test("resumes a previous ready assessment without creating a duplicate", async () => {
  const child = {
    id: "child_opaque_01",
    display_code: "LL-0007",
    birth_year: 2021,
    birth_month: 6,
    language_context: { primary: "th", additional: [] },
    version: 1,
  };
  const previousAssessment = {
    id: "assessment_previous_01",
    child_id: child.id,
    purpose: "developmental_follow_up" as const,
    state: "ready_for_capture" as const,
    age_months: 36,
    language_context: child.language_context,
    assigned_clinician_id: "therapist_opaque_01",
    version: 2,
  };
  const previousCapture = {
    assessment_id: previousAssessment.id,
    state: "ready_for_capture" as const,
    protocol: {
      protocol_version_key: "thai_guided_language_sample:v0",
      selected_at: "2026-09-07T08:00:00Z",
      version: 1,
    },
    activities: [{
      activity_code: "free_play",
      required: true,
      target_duration_seconds: 180,
      minimum_duration_seconds: 120,
    }],
    recordings: [],
    progress: {
      required_activities_total: 1,
      required_activities_verified: 0,
      required_activities_usable: 0,
    },
  };
  const client = {
    listChildren: vi.fn().mockResolvedValue([child]),
    getChild: vi.fn().mockResolvedValue(child),
    listConsents: vi.fn().mockResolvedValue([{
      id: "consent_opaque_01",
      child_id: child.id,
      purpose: "clinical_assessment",
      scope_version: "clinical-v1",
      status: "active",
      granted_at: "2026-09-07T08:00:00Z",
      withdrawn_at: null,
      version: 1,
    }]),
    listAssessments: vi.fn().mockResolvedValue([previousAssessment]),
    createConsent: vi.fn(),
    createAssessment: vi.fn(),
    selectProtocol: vi.fn(),
    startCapture: vi.fn(),
    createRecording: vi.fn(),
    createUploadIntent: vi.fn(),
    completeUpload: vi.fn(),
    getCapture: vi.fn().mockResolvedValue(previousCapture),
    getRecordingQuality: vi.fn(),
    completeCapture: vi.fn(),
  };

  render(<AssessmentCaptureWorkspace client={client} />);
  fireEvent.click(await screen.findByRole("button", { name: "เลือก LL-0007" }));

  fireEvent.click(await screen.findByRole("button", { name: "ดำเนินการต่อ" }));

  expect(await screen.findByRole("heading", { name: "พร้อมบันทึกเสียง" })).toBeInTheDocument();
  expect(client.getCapture).toHaveBeenCalledWith("assessment_previous_01");
  expect(client.createAssessment).not.toHaveBeenCalled();
  expect(client.selectProtocol).not.toHaveBeenCalled();
});
