import { render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import {
  AssessmentEvidenceWorkspace,
  type AssessmentEvidenceClient,
} from "@/features/assessment-v2/components/assessment-evidence-workspace";

function evidenceProfile(state: "completed" | "stale" = "completed") {
  return {
    evidence_run_id: "evidence_run_opaque_01",
    assessment_id: "assessment_opaque_01",
    transcript_revision_id: "transcript_revision_opaque_01",
    state,
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
    features: [
      {
        key: "child_token_count",
        value: 12,
        unit: "tokens",
        source: "reviewed_transcript",
        state: "completed",
        limitation: "Descriptive measurement only.",
        provenance: {
          input_ref: "transcript_input_opaque_01",
          input_sha256: "a".repeat(64),
          protocol_version_key: "thai_guided_language_sample:v0",
          extractor: "reviewed-transcript-adapter",
          pipeline_version: "reviewed-transcript-descriptors-v1",
          feature_schema_version: "descriptive-transcript-features-v1",
          analyzed_at: "2026-09-07T08:02:00Z",
        },
      },
    ],
    domains: [
      {
        domain: "expressive_language",
        status: "descriptive_only",
        summary: "มีข้อมูลเชิงพรรณนาในช่องภาษาแสดงออก",
        feature_keys: ["child_token_count"],
        supporting_features: ["child_token_count"],
        conflicting_features: [],
        limitations: ["ยังไม่มี reference band ที่เข้ากันได้"],
      },
    ],
    limitations: ["ผลนี้เป็น decision support เท่านั้น"],
    not_diagnostic: true,
    decision_support_only: true,
    version: 1,
  };
}

function clientFor(value: ReturnType<typeof evidenceProfile>): AssessmentEvidenceClient {
  return { getEvidence: vi.fn().mockResolvedValue(value) };
}

test("renders domain evidence and provenance without diagnostic language", async () => {
  render(
    <AssessmentEvidenceWorkspace
      assessmentId="assessment_opaque_01"
      client={clientFor(evidenceProfile())}
    />,
  );

  expect(await screen.findByRole("heading", { name: "โปรไฟล์พัฒนาการเชิงพรรณนา" })).toBeInTheDocument();
  expect(screen.getByText("ภาษาแสดงออก")).toBeInTheDocument();
  expect(screen.getByText("มีข้อมูลเชิงพรรณนาในช่องภาษาแสดงออก")).toBeInTheDocument();
  expect(screen.getByText("12 tokens")).toBeInTheDocument();
  expect(screen.getByText("ผลนี้เป็น decision support เท่านั้น")).toBeInTheDocument();
  expect(screen.queryByText(/ASD.*%|probability/i)).not.toBeInTheDocument();
});

test("makes stale evidence visible and tells therapist the input changed", async () => {
  render(
    <AssessmentEvidenceWorkspace
      assessmentId="assessment_opaque_01"
      client={clientFor(evidenceProfile("stale"))}
    />,
  );

  expect(await screen.findByRole("alert")).toHaveTextContent("ข้อมูลเดิมไม่เป็นปัจจุบัน");
  expect(screen.getByText(/ต้องทบทวน transcript หรือประมวลผลใหม่/)).toBeInTheDocument();
});

test("keeps API failure visible and offers a retry", async () => {
  const getEvidence = vi.fn().mockRejectedValue(new Error("network"));
  render(
    <AssessmentEvidenceWorkspace
      assessmentId="assessment_opaque_01"
      client={{ getEvidence }}
    />,
  );

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("ไม่สามารถโหลดผลหลักฐานได้"));
  expect(screen.getByRole("button", { name: "ลองใหม่" })).toBeInTheDocument();
  expect(getEvidence).toHaveBeenCalledWith("assessment_opaque_01");
});
