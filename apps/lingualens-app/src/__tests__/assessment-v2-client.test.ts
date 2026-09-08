import { beforeEach, expect, test, vi } from "vitest";

import {
  createAssessmentV2Client,
  type AssessmentV2Child,
} from "@/services/assessment-v2-client";
import { deriveAssessmentApiBase } from "@/lib/api";

beforeEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

test("derives the v2 API from the legacy /api base used by the local launcher", () => {
  expect(deriveAssessmentApiBase("http://localhost:8000/api")).toBe("http://localhost:8000/api/v2");
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

test("loads the assessment evidence profile from FastAPI", async () => {
  const evidence = {
    evidence_run_id: "evidence_run_opaque_01",
    assessment_id: "assessment_opaque_01",
    transcript_revision_id: "transcript_revision_opaque_01",
    state: "completed",
    generated_at: "2026-09-07T08:02:00Z",
    provenance: {
      input_ref: "transcript_input_opaque_01",
      input_sha256: "a".repeat(64),
      protocol_version_key: "thai_guided_language_sample:v0",
      extractor: "reviewed-transcript-adapter",
      pipeline_version: "reviewed-transcript-descriptors-v1",
      feature_schema_version: "descriptive-transcript-features-v1",
      analyzed_at: "2026-09-07T08:02:00Z",
    },
    features: [],
    domains: [],
    limitations: [],
    not_diagnostic: true,
    decision_support_only: true,
    version: 1,
  };
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(evidence), { status: 200 }),
  );

  const result = await createAssessmentV2Client().getEvidence("assessment_opaque_01");

  expect(result).toEqual(evidence);
  expect(fetchSpy).toHaveBeenCalledWith(
    "http://localhost:8000/api/v2/assessments/assessment_opaque_01/evidence",
    expect.objectContaining({ cache: "no-store" }),
  );
});

test("loads and mutates reviewed transcript revisions through FastAPI", async () => {
  const transcript = {
    id: "transcript_revision_opaque_01",
    assessment_id: "assessment_opaque_01",
    revision: 1,
    source: "asr_draft",
    review_state: "draft",
    content: "*CHI: hello .\n",
    content_sha256: "a".repeat(64),
    created_at: "2026-09-07T08:00:00Z",
    attested_at: null,
    version: 1,
  };
  const fetchSpy = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(transcript), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(transcript), { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...transcript, review_state: "attested", version: 2 }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ evidence_run_id: "evidence_run_opaque_01" }), { status: 201 }));
  const client = createAssessmentV2Client();

  await expect(client.getTranscript("assessment_opaque_01")).resolves.toEqual(transcript);
  await expect(client.createTranscriptRevision("assessment_opaque_01", {
    source: "asr_draft",
    content: "*CHI: hello .\n",
    expected_revision: 1,
    expected_version: 1,
  })).resolves.toEqual(transcript);
  await expect(client.attestTranscript("transcript_revision_opaque_01", 1)).resolves.toMatchObject({ review_state: "attested" });
  await expect(client.createEvidence("assessment_opaque_01")).resolves.toEqual({ evidence_run_id: "evidence_run_opaque_01" });

  expect(fetchSpy).toHaveBeenNthCalledWith(
    2,
    "http://localhost:8000/api/v2/assessments/assessment_opaque_01/transcript-revisions",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        source: "asr_draft",
        content: "*CHI: hello .\n",
        expected_revision: 1,
        expected_version: 1,
      }),
    }),
  );
  expect(fetchSpy).toHaveBeenNthCalledWith(
    3,
    "http://localhost:8000/api/v2/transcript-revisions/transcript_revision_opaque_01/attest",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ expected_version: 1 }) }),
  );
  expect(fetchSpy).toHaveBeenNthCalledWith(
    4,
    "http://localhost:8000/api/v2/assessments/assessment_opaque_01/evidence-runs",
    expect.objectContaining({ method: "POST" }),
  );
});
