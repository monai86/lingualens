import { beforeEach, expect, test, vi } from "vitest";

import {
  createAssessmentV2Client,
  type AssessmentV2Child,
} from "@/services/assessment-v2-client";

beforeEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

test("lists scoped children through the assessment v2 API", async () => {
  const children: AssessmentV2Child[] = [
    {
      id: "child_opaque_01",
      display_code: "LL-0007",
      birth_year: 2021,
      birth_month: 6,
      language_context: { primary: "th", additional: [] },
      version: 1,
    },
  ];
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(children), { status: 200 }),
  );

  const result = await createAssessmentV2Client().listChildren();

  expect(result).toEqual(children);
  expect(fetchSpy).toHaveBeenCalledWith(
    "http://localhost:8000/api/v2/children",
    expect.objectContaining({ cache: "no-store" }),
  );
});

test("creates a consented assessment with an idempotent client request", async () => {
  const assessment = {
    id: "assessment_opaque_01",
    child_id: "child_opaque_01",
    purpose: "initial",
    state: "draft",
    age_months: 36,
    language_context: { primary: "th", additional: [] },
    assigned_clinician_id: "therapist_opaque_01",
    version: 1,
  };
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(assessment), { status: 201 }),
  );

  const result = await createAssessmentV2Client().createAssessment("child_opaque_01", {
    purpose: "initial",
  });

  expect(result).toEqual(assessment);
  expect(fetchSpy).toHaveBeenCalledWith(
    "http://localhost:8000/api/v2/children/child_opaque_01/assessments",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ purpose: "initial" }),
    }),
  );
});
