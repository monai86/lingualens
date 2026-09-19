import { expect, test } from "@playwright/test";

const assessmentId = "assessment_opaque_01";
const transcript = {
  id: "transcript_revision_opaque_01",
  assessment_id: assessmentId,
  revision: 1,
  source: "asr_draft",
  review_state: "draft",
  content: "@UTF8\n@Begin\n*CHI: hello .\n@End\n",
  content_sha256: "a".repeat(64),
  created_at: "2026-09-07T08:00:00Z",
  attested_at: null,
  version: 1,
};
const attestedTranscript = {
  ...transcript,
  review_state: "attested",
  attested_at: "2026-09-07T08:03:00Z",
  version: 2,
};
const segmentSet = {
  id: "segment_set_opaque_01",
  assessment_id: assessmentId,
  transcript_revision_id: transcript.id,
  transcript_content_sha256: "a".repeat(64),
  recording_id: null,
  revision: 1,
  source: "asr_draft",
  review_state: "draft",
  segments_sha256: "b".repeat(64),
  segments: [{
    id: "segment_opaque_01",
    ordinal: 1,
    start_ms: 0,
    end_ms: 1200,
    speaker_role: "child",
    text: "hello .",
    confidence: 0.91,
    uncertainty_reason: "none",
    created_at: "2026-09-07T08:03:00Z",
  }],
  created_at: "2026-09-07T08:03:00Z",
  attested_at: null,
  version: 1,
};
const attestedSegmentSet = {
  ...segmentSet,
  review_state: "attested",
  attested_at: "2026-09-07T08:04:00Z",
  version: 2,
};
const processingRun = {
  id: "processing_run_opaque_01",
  stage: "evidence_extraction",
  state: "queued",
  attempt_count: 0,
  max_attempts: 3,
  available_at: "2026-09-07T08:04:00Z",
  error_code: null,
  result_available: false,
  can_retry: false,
  can_cancel: true,
  version: 1,
};
const evidenceProfile = {
  evidence_run_id: "evidence_run_opaque_01",
  assessment_id: assessmentId,
  transcript_revision_id: transcript.id,
  segment_set_id: attestedSegmentSet.id,
  segment_set_sha256: attestedSegmentSet.segments_sha256,
  state: "completed",
  generated_at: "2026-09-07T08:05:00Z",
  provenance: {
    input_ref: "transcript_input_opaque_01",
    input_sha256: "a".repeat(64),
    protocol_version_key: "thai_guided_language_sample:v0",
    extractor: "reviewed-transcript-adapter",
    pipeline_version: "reviewed-transcript-descriptors-v1",
    feature_schema_version: "descriptive-transcript-features-v1",
    analyzed_at: "2026-09-07T08:05:00Z",
  },
  features: [],
  domains: [{
    domain: "expressive_language",
    status: "descriptive_only",
    summary: "มีข้อมูลเชิงพรรณนาในช่องภาษาแสดงออก",
    feature_keys: [],
    supporting_features: [],
    conflicting_features: [],
    limitations: [],
  }],
  limitations: [],
  not_diagnostic: true,
  decision_support_only: true,
  version: 1,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
});

test("processing assessment can review a transcript and follow durable evidence processing", async ({ page }) => {
  await page.route("**/api/v1/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mock_mode: true,
        auth_mode: "mock",
        model_version: "v2-mock",
        feature_schema: "lingualens-app.1",
        guideline_mapping: "review-support-only",
        user_roles: ["therapist"],
        data_retention: "local demo data only",
        consent_policy: "visible per case",
        capabilities: {
          cases: "available",
          audio_upload: "experimental",
          transcription: "experimental",
          transcript_qa: "available",
          feature_extraction: "available",
          ai_review: "disabled",
          report_drafting: "disabled",
          pdf_export: "unavailable",
        },
        pipeline_settings: {
          audio_processing: "experimental_async",
          job_queue_mode: "memory",
          repository_mode: "memory",
          storage_mode: "local_private",
        },
      }),
    });
  });

  let transcriptExists = false;
  let segmentSetAttested = false;
  await page.route(`**/api/v2/assessments/${assessmentId}/transcript`, async (route) => {
    if (!transcriptExists) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "transcript_not_found" } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(transcriptExists ? attestedTranscript : transcript),
    });
  });
  await page.route(`**/api/v2/assessments/${assessmentId}/transcript-revisions`, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toMatchObject({
      source: "asr_draft",
      expected_revision: null,
      expected_version: null,
    });
    transcriptExists = true;
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(transcript) });
  });
  await page.route(`**/api/v2/transcript-revisions/${transcript.id}/attest`, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ expected_version: 1 });
    transcriptExists = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(attestedTranscript) });
  });
  await page.route(`**/api/v2/assessments/${assessmentId}/transcript-segment-set`, async (route) => {
    expect(route.request().method()).toBe("GET");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(segmentSetAttested ? attestedSegmentSet : segmentSet),
    });
  });
  await page.route(`**/api/v2/assessments/${assessmentId}/transcript-segment-sets`, async (route) => {
    expect(route.request().method()).toBe("POST");
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ ...segmentSet, revision: 2 }) });
  });
  await page.route(`**/api/v2/transcript-segment-sets/${segmentSet.id}/attest`, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ expected_version: 1 });
    segmentSetAttested = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(attestedSegmentSet) });
  });
  await page.route(`**/api/v2/transcript-segments/${segmentSet.segments[0].id}/audio-replay-grant`, async (route) => {
    expect(route.request().method()).toBe("POST");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        segment_id: segmentSet.segments[0].id,
        start_ms: 0,
        end_ms: 1200,
        available: false,
        url: null,
        expires_at: null,
        expires_in_seconds: null,
      }),
    });
  });

  let currentRun: typeof processingRun | null = null;
  let allowSuccess = false;
  await page.route(`**/api/v2/assessments/${assessmentId}/evidence-processing-run`, async (route) => {
    if (!currentRun) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "processing_run_not_found" } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ processing_run: allowSuccess ? { ...processingRun, state: "running", attempt_count: 1, version: 2 } : currentRun }),
    });
  });
  await page.route(`**/api/v2/assessments/${assessmentId}/evidence-runs`, async (route) => {
    expect(route.request().method()).toBe("POST");
    currentRun = processingRun;
    await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ processing_run: currentRun }) });
  });
  await page.route(`**/api/v2/processing-runs/${processingRun.id}`, async (route) => {
    expect(route.request().method()).toBe("GET");
    const result = allowSuccess
      ? { ...processingRun, state: "succeeded", attempt_count: 1, result_available: true, can_cancel: false, version: 3 }
      : { ...processingRun, state: "running", attempt_count: 1, version: 2 };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
  });
  await page.route(`**/api/v2/assessments/${assessmentId}/evidence`, async (route) => {
    expect(route.request().method()).toBe("GET");
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(evidenceProfile) });
  });

  await page.goto(`/assessments/${assessmentId}/transcript`);
  await expect(page.getByRole("heading", { name: "สร้าง transcript ฉบับแรก" })).toBeVisible();

  await page.getByRole("textbox", { name: "เนื้อหา transcript" }).fill(transcript.content);
  await page.getByRole("button", { name: "สร้างฉบับร่าง" }).click();

  await expect(page.getByRole("heading", { name: "ตรวจ transcript ก่อนสร้าง segment" })).toBeVisible();
  await page.getByRole("checkbox", { name: /ฉันได้ตรวจสอบข้อความ/ }).check();
  await page.getByRole("button", { name: "รับรอง transcript" }).click();
  await expect(page.getByText("รับรองแล้ว", { exact: true })).toBeVisible();

  await expect(page.getByRole("heading", { name: "ทบทวน transcript รายช่วง" })).toBeVisible();
  await expect(page.getByRole("article").getByText("hello .", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "เล่นเสียงช่วงที่ 1" }).click();
  await expect(page.getByText(/เสียงของช่วงนี้ยังไม่พร้อมใช้งาน/)).toBeVisible();
  await page.getByRole("checkbox", { name: /ฉันได้ตรวจสอบทุกช่วง/ }).check();
  await page.getByRole("button", { name: "รับรอง segment revision" }).click();
  await expect(page.getByText("รับรอง segment revision แล้ว", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "สร้างหลักฐานเชิงพรรณนา" }).click();
  await expect(page.getByText("บันทึกงานแล้ว กำลังรอประมวลผล")).toBeVisible();
  await page.waitForTimeout(2_200);
  await expect(page.getByText("กำลังประมวลผล")).toBeVisible();

  allowSuccess = true;
  await page.reload();
  await expect(page.getByText("กำลังประมวลผล")).toBeVisible();
  await page.waitForTimeout(2_200);
  await expect(page.getByRole("link", { name: "เปิดผลหลักฐาน" })).toBeVisible();
  await expect(page.evaluate(() => Object.keys(localStorage))).resolves.toEqual([]);

  await page.getByRole("link", { name: "เปิดผลหลักฐาน" }).click();
  await expect(page.getByRole("heading", { name: "โปรไฟล์พัฒนาการเชิงพรรณนา" })).toBeVisible();
  await expect(page.getByText("มีข้อมูลเชิงพรรณนาในช่องภาษาแสดงออก")).toBeVisible();
});
