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

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
});

test("processing assessment can create its first transcript draft and continue review", async ({ page }) => {
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
  await page.route(`**/api/v2/assessments/${assessmentId}/transcript`, async (route) => {
    if (!transcriptExists) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "transcript_not_found" } }),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(transcript) });
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

  await page.goto(`/assessments/${assessmentId}/transcript`);
  await expect(page.getByRole("heading", { name: "สร้าง transcript ฉบับแรก" })).toBeVisible();

  await page.getByRole("textbox", { name: "เนื้อหา transcript" }).fill(transcript.content);
  await page.getByRole("button", { name: "สร้างฉบับร่าง" }).click();

  await expect(page.getByRole("heading", { name: "ทบทวน transcript" })).toBeVisible();
  await expect(page.getByText("สถานะ: รอตรวจสอบ")).toBeVisible();
});
