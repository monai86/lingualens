import { expect, test } from "@playwright/test";

const childId = "child_synth_01";
const currentAssessmentId = "asmt_visit_3";

const childHistory = [
  {
    assessment_id: "asmt_visit_1",
    created_at: "2026-03-01T10:00:00Z",
    purpose: "initial",
    state: "finalized",
    age_months: 36,
    protocol_version_key: "thai_guided_language_sample:v0",
    language: "th-TH",
    evidence_run_id: "run_visit_1",
    is_comparable: true,
  },
  {
    assessment_id: "asmt_visit_2",
    created_at: "2026-06-01T10:00:00Z",
    purpose: "developmental_follow_up",
    state: "finalized",
    age_months: 39,
    protocol_version_key: "elicitation_protocol_v1", // Incompatible protocol!
    language: "th-TH",
    evidence_run_id: "run_visit_2",
    is_comparable: true,
  },
  {
    assessment_id: currentAssessmentId,
    created_at: "2026-09-12T10:00:00Z",
    purpose: "developmental_follow_up",
    state: "finalized",
    age_months: 42,
    protocol_version_key: "thai_guided_language_sample:v0",
    language: "th-TH",
    evidence_run_id: "run_visit_3",
    is_comparable: true,
  },
];

const incompatibleComparison = {
  comparison_id: "comp_incompatible_01",
  baseline_assessment_id: "asmt_visit_2",
  current_assessment_id: currentAssessmentId,
  baseline_evidence_run_id: "run_visit_2",
  current_evidence_run_id: "run_visit_3",
  baseline_evidence_sha256: "a".repeat(64),
  current_evidence_sha256: "b".repeat(64),
  policy_version: "longitudinal_v1",
  status: "not_comparable",
  is_stale: false,
  created_at: "2026-09-12T11:00:00Z",
  features: [
    {
      feature_key: "mlu_words",
      unit: "morphemes_per_utterance",
      status: "not_comparable",
      incompatibility_reasons: ["protocol_incompatible"],
      baseline_value: 2.2,
      current_value: 3.2,
      absolute_delta: null,
      percent_change: null,
      percent_change_limitation: null,
      numerical_trend: "indeterminate",
      clinical_interpretation: "indeterminate",
    },
  ],
};

const compatibleComparison = {
  comparison_id: "comp_compatible_01",
  baseline_assessment_id: "asmt_visit_1",
  current_assessment_id: currentAssessmentId,
  baseline_evidence_run_id: "run_visit_1",
  current_evidence_run_id: "run_visit_3",
  baseline_evidence_sha256: "a".repeat(64),
  current_evidence_sha256: "b".repeat(64),
  policy_version: "longitudinal_v1",
  status: "compatible",
  is_stale: false,
  created_at: "2026-09-12T11:00:00Z",
  features: [
    {
      feature_key: "mlu_words",
      unit: "morphemes_per_utterance",
      status: "compatible",
      incompatibility_reasons: [],
      baseline_value: 2.5,
      current_value: 3.5,
      absolute_delta: 1.0,
      percent_change: 40.0,
      percent_change_limitation: null,
      numerical_trend: "increased",
      clinical_interpretation: "indeterminate",
    },
    {
      feature_key: "consonant_inventory_size",
      unit: "count",
      status: "compatible",
      incompatibility_reasons: [],
      baseline_value: 0.0,
      current_value: 5.0,
      absolute_delta: 5.0,
      percent_change: null,
      percent_change_limitation: "zero_baseline",
      numerical_trend: "increased",
      clinical_interpretation: "indeterminate",
    },
  ],
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

test.describe("Longitudinal Comparison Browser Scenario (Slices B1-B3)", () => {
  test("exercises synthetic 3-visit scenario where Visit 2 is incompatible and Visit 1 is compatible", async ({
    page,
  }) => {
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

    // Intercept v2 API routes
    await page.route(`**/api/v2/children/${childId}/assessments/history`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(childHistory),
      });
    });

    await page.route(`**/api/v2/assessments/${currentAssessmentId}/comparisons`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else if (route.request().method() === "POST") {
        const postData = JSON.parse(route.request().postData() || "{}");
        if (postData.baseline_assessment_id === "asmt_visit_2") {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify(incompatibleComparison),
          });
        } else {
          await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify(compatibleComparison),
          });
        }
      }
    });

    // Navigate to history page
    await page.goto(`/assessments/${currentAssessmentId}/history?childId=${childId}`);

    // Wait for the workspace to load
    await expect(page.getByLabel(/เลือกการประเมินพื้นฐาน/)).toBeVisible();

    // 1. Select Visit 2 (incompatible protocol)
    await page.getByLabel(/เลือกการประเมินพื้นฐาน/).selectOption("asmt_visit_2");
    await page.getByRole("button", { name: "เปรียบเทียบ" }).click();

    // Verify H14-Incompatible callout
    await expect(page.getByText("H14-Incompatible")).toBeVisible();
    await expect(page.getByText("protocol_incompatible")).toBeVisible();
    await expect(
      page.getByText("Comparisons are not permitted across differing protocol structures")
    ).toBeVisible();

    // 2. Select Visit 1 (compatible baseline)
    await page.getByLabel(/เลือกการประเมินพื้นฐาน/).selectOption("asmt_visit_1");
    await page.getByRole("button", { name: "เปรียบเทียบ" }).click();

    // Verify H14-Compatible results table
    await expect(page.getByText("H14-Compatible")).toBeVisible();
    await expect(page.getByText("mlu_words")).toBeVisible();
    await expect(page.getByText("+1.00")).toBeVisible();
    await expect(page.getByText("+40.0%")).toBeVisible();

    // Verify zero_baseline limitation
    await expect(page.getByText("consonant_inventory_size")).toBeVisible();
    await expect(page.getByText("N/A (zero_baseline)")).toBeVisible();

    // Verify clinical safety: indeterminate interpretations only
    const indeterminateBadges = page.getByText("indeterminate");
    await expect(indeterminateBadges.first()).toBeVisible();
    await expect(page.getByText("improved")).not.toBeVisible();
    await expect(page.getByText("stable")).not.toBeVisible();
  });
});
