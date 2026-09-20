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
    segment_set_id: "segment_set_opaque_01",
    segment_set_sha256: "b".repeat(64),
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
    .mockResolvedValueOnce(new Response(JSON.stringify({
      processing_run: {
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
      },
    }), { status: 202 }));
  const client = createAssessmentV2Client();

  await expect(client.getTranscript("assessment_opaque_01")).resolves.toEqual(transcript);
  await expect(client.createTranscriptRevision("assessment_opaque_01", {
    source: "asr_draft",
    content: "*CHI: hello .\n",
    expected_revision: 1,
    expected_version: 1,
  })).resolves.toEqual(transcript);
  await expect(client.attestTranscript("transcript_revision_opaque_01", 1)).resolves.toMatchObject({ review_state: "attested" });
  await expect(client.queueEvidence("assessment_opaque_01")).resolves.toMatchObject({
    processing_run: { id: "processing_run_opaque_01", state: "queued" },
  });

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

test("loads, revises, attests, and replays transcript segments through FastAPI", async () => {
  const segmentSet = {
    id: "segment_set_opaque_01",
    assessment_id: "assessment_opaque_01",
    transcript_revision_id: "transcript_revision_opaque_01",
    transcript_content_sha256: "a".repeat(64),
    recording_id: "recording_opaque_01",
    revision: 1,
    source: "asr_draft",
    review_state: "draft",
    segments_sha256: "b".repeat(64),
    segments: [{
      id: "segment_opaque_01",
      ordinal: 1,
      start_ms: 0,
      end_ms: 1200,
      speaker_role: "child" as const,
      text: "hello .",
      confidence: 0.91,
      uncertainty_reason: "none" as const,
      created_at: "2026-09-07T08:00:00Z",
    }],
    created_at: "2026-09-07T08:00:00Z",
    attested_at: null,
    version: 1,
  };
  const replay = {
    segment_id: "segment_opaque_01",
    start_ms: 0,
    end_ms: 1200,
    available: true,
    url: "https://signed.example/replay",
    expires_at: "2026-09-07T08:05:00Z",
    expires_in_seconds: 300,
  };
  const fetchSpy = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(segmentSet), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...segmentSet, revision: 2, version: 1 }), { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...segmentSet, review_state: "attested", version: 2 }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(replay), { status: 200 }));
  const client = createAssessmentV2Client();

  await expect(client.getCurrentTranscriptSegmentSet("assessment_opaque_01")).resolves.toEqual(segmentSet);
  await expect(client.createTranscriptSegmentSet("assessment_opaque_01", {
      transcript_revision_id: "transcript_revision_opaque_01",
      source: "asr_draft",
      segments: segmentSet.segments.map(({ id: _id, created_at: _createdAt, ...segment }) => segment),
    recording_id: "recording_opaque_01",
    expected_revision: 1,
    expected_version: 1,
  })).resolves.toMatchObject({ revision: 2 });
  await expect(client.attestTranscriptSegmentSet("segment_set_opaque_01", 1)).resolves.toMatchObject({
    review_state: "attested",
  });
  await expect(client.createSegmentReplayGrant("segment_opaque_01")).resolves.toEqual(replay);

  expect(fetchSpy).toHaveBeenNthCalledWith(
    1,
    "http://localhost:8000/api/v2/assessments/assessment_opaque_01/transcript-segment-set",
    expect.objectContaining({ cache: "no-store" }),
  );
  expect(fetchSpy).toHaveBeenNthCalledWith(
    2,
    "http://localhost:8000/api/v2/assessments/assessment_opaque_01/transcript-segment-sets",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        transcript_revision_id: "transcript_revision_opaque_01",
        source: "asr_draft",
        segments: segmentSet.segments.map(({ id: _id, created_at: _createdAt, ...segment }) => segment),
        recording_id: "recording_opaque_01",
        expected_revision: 1,
        expected_version: 1,
      }),
    }),
  );
  expect(fetchSpy).toHaveBeenNthCalledWith(
    3,
    "http://localhost:8000/api/v2/transcript-segment-sets/segment_set_opaque_01/attest",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ expected_version: 1 }) }),
  );
  expect(fetchSpy).toHaveBeenNthCalledWith(
    4,
    "http://localhost:8000/api/v2/transcript-segments/segment_opaque_01/audio-replay-grant",
    expect.objectContaining({ method: "POST" }),
  );
});
