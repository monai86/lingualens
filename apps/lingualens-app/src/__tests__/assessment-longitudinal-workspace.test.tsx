import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  AssessmentLongitudinalWorkspace,
  type AssessmentLongitudinalClient,
} from "@/features/assessment-v2/components/assessment-longitudinal-workspace";
import type {
  AssessmentV2ChildHistoryItem,
  AssessmentV2Comparison,
} from "@/services/assessment-v2-client";

function mockHistory(): AssessmentV2ChildHistoryItem[] {
  return [
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
      assessment_id: "asmt_visit_3",
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
}

function mockIncompatibleComparison(): AssessmentV2Comparison {
  return {
    comparison_id: "comp_incompatible_01",
    baseline_assessment_id: "asmt_visit_2",
    current_assessment_id: "asmt_visit_3",
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
}

function mockCompatibleComparison(isStale = false): AssessmentV2Comparison {
  return {
    comparison_id: "comp_compatible_01",
    baseline_assessment_id: "asmt_visit_1",
    current_assessment_id: "asmt_visit_3",
    baseline_evidence_run_id: "run_visit_1",
    current_evidence_run_id: "run_visit_3",
    baseline_evidence_sha256: "a".repeat(64),
    current_evidence_sha256: "b".repeat(64),
    policy_version: "longitudinal_v1",
    status: "compatible",
    is_stale: isStale,
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
}

describe("AssessmentLongitudinalWorkspace", () => {
  it("renders H14-NoHistory when child has no previous visits", async () => {
    const client: AssessmentLongitudinalClient = {
      getChildAssessmentHistory: vi.fn().mockResolvedValue([
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
      ]),
      getComparisons: vi.fn().mockResolvedValue([]),
      createComparison: vi.fn(),
      getComparison: vi.fn(),
    };

    render(
      <AssessmentLongitudinalWorkspace
        assessmentId="asmt_visit_1"
        childId="child_01"
        client={client}
      />
    );

    await waitFor(() => {
      expect(
        screen.getByText(/This is the child's initial recorded assessment/i)
      ).toBeInTheDocument();
    });
  });

  it("renders synthetic 3-visit scenario where Visit 2 is incompatible and Visit 1 is compatible", async () => {
    const client: AssessmentLongitudinalClient = {
      getChildAssessmentHistory: vi.fn().mockResolvedValue(mockHistory()),
      getComparisons: vi.fn().mockResolvedValue([]),
      createComparison: vi.fn().mockImplementation((_asmtId, baselineId) => {
        if (baselineId === "asmt_visit_2") {
          return Promise.resolve(mockIncompatibleComparison());
        }
        return Promise.resolve(mockCompatibleComparison());
      }),
      getComparison: vi.fn(),
    };

    render(
      <AssessmentLongitudinalWorkspace
        assessmentId="asmt_visit_3"
        childId="child_01"
        client={client}
      />
    );

    // Wait for dropdown to populate
    await waitFor(() => {
      expect(screen.getByLabelText(/เลือกการประเมินพื้นฐาน/i)).toBeInTheDocument();
    });

    // 1. Select Visit 2 (incompatible protocol)
    fireEvent.change(screen.getByLabelText(/เลือกการประเมินพื้นฐาน/i), {
      target: { value: "asmt_visit_2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /เปรียบเทียบ/i }));

    await waitFor(() => {
      expect(screen.getByText(/H14-Incompatible/i)).toBeInTheDocument();
      expect(
        screen.getByText(/protocol_incompatible/i)
      ).toBeInTheDocument();
    });

    // 2. Select Visit 1 (compatible)
    fireEvent.change(screen.getByLabelText(/เลือกการประเมินพื้นฐาน/i), {
      target: { value: "asmt_visit_1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /เปรียบเทียบ/i }));

    await waitFor(() => {
      expect(screen.getByText(/H14-Compatible/i)).toBeInTheDocument();
      expect(screen.getByText("mlu_words")).toBeInTheDocument();
      expect(screen.getByText("+1.00")).toBeInTheDocument();
      expect(screen.getByText("+40.0%")).toBeInTheDocument();

      // Zero baseline handling: shows zero_baseline limitation
      expect(screen.getByText("consonant_inventory_size")).toBeInTheDocument();
      expect(screen.getByText(/zero_baseline/i)).toBeInTheDocument();

      // Mandatory Safety Check: clinical interpretation must be indeterminate!
      const interpretations = screen.getAllByText("indeterminate");
      expect(interpretations.length).toBeGreaterThan(0);
      expect(screen.queryByText(/improved/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/stable/i)).not.toBeInTheDocument();
    });
  });

  it("displays stale warning badge when comparison is_stale is true", async () => {
    const client: AssessmentLongitudinalClient = {
      getChildAssessmentHistory: vi.fn().mockResolvedValue(mockHistory()),
      getComparisons: vi.fn().mockResolvedValue([mockCompatibleComparison(true)]),
      createComparison: vi.fn(),
      getComparison: vi.fn(),
    };

    render(
      <AssessmentLongitudinalWorkspace
        assessmentId="asmt_visit_3"
        childId="child_01"
        client={client}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/ข้อมูลต้นทางมีการอัปเดตใหม่/i)).toBeInTheDocument();
    });
  });
});
