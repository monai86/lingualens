import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  AssessmentClinicalReviewWorkspace,
  type AssessmentClinicalReviewClient,
} from "@/features/assessment-v2/components/assessment-clinical-review-workspace";
import type { AssessmentV2ClinicalReview, AssessmentV2Report } from "@/services/assessment-v2-client";

function mockClinicalReview(unreviewedCount = 1): AssessmentV2ClinicalReview {
  return {
    review_id: "rev_test_001",
    assessment_id: "asmt_test_001",
    organization_id: "org_alpha",
    clinician_id: "clinician_001",
    cues_evaluated: true,
    cues_policy_version: "cues-v2.0",
    attention_cues: [
      {
        cue_id: "cue_001",
        cue_type: "lexical_diversity_low",
        title: "ความหลากหลายของคลังคำศัพท์ต่ำกว่าเกณฑ์สังเกต",
        description: "ค่า TTR อยู่ในระดับที่ควรสังเกตเพิ่มเติมในการทำกิจกรรมการเล่นร่วมกัน",
        severity_level: "moderate",
        policy_version: "cues-v2.0",
        evidence_run_id: "ev_run_001",
        feature_key: "type_token_ratio",
        status: unreviewedCount === 0 ? "acknowledged" : "unreviewed",
        clinician_action: unreviewedCount === 0 ? "acknowledged" : "unreviewed",
        clinician_rationale: unreviewedCount === 0 ? "Confirmed during session" : null,
        reviewed_at: unreviewedCount === 0 ? "2026-09-12T10:00:00Z" : null,
        reviewed_by: unreviewedCount === 0 ? "clinician_001" : null,
      },
    ],
    disposition_type: "monitoring_recommended",
    disposition_notes: "Initial clinical notes",
    clinical_summary: "Child demonstrates emerging expressive skills.",
    follow_up_plan: {
      target_window_weeks: 4,
      recommended_activities: ["interactive play"],
      caregiver_guidance: "Encourage conversational turns.",
    },
    unreviewed_cues_count: unreviewedCount,
    can_finalize: unreviewedCount === 0,
    version: 1,
    created_at: "2026-09-12T09:00:00Z",
    updated_at: "2026-09-12T09:00:00Z",
  };
}

describe("AssessmentClinicalReviewWorkspace", () => {
  it("renders attention cues and clinical safety notice", async () => {
    const client: AssessmentClinicalReviewClient = {
      getClinicalReview: vi.fn().mockResolvedValue(mockClinicalReview(1)),
      reviewAttentionCue: vi.fn(),
      updateClinicalDisposition: vi.fn(),
      createReportDraft: vi.fn(),
    };

    render(<AssessmentClinicalReviewWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("การตรวจทานข้อสังเกตและความเห็นของนักบำบัด")).toBeInTheDocument();
    });

    // Verify non-overclaiming safety boundary notice
    expect(screen.getByLabelText("Clinical safety boundary notice")).toBeInTheDocument();
    expect(
      screen.getByText(/ไม่มีการทำนายอัตราความน่าจะเป็นของภาวะออทิซึม/)
    ).toBeInTheDocument();

    // Verify cue is rendered
    expect(screen.getByText("ความหลากหลายของคลังคำศัพท์ต่ำกว่าเกณฑ์สังเกต")).toBeInTheDocument();
    expect(screen.getByText("1 ข้อ")).toBeInTheDocument();
  });

  it("handles cue acknowledgement", async () => {
    const updatedReview = mockClinicalReview(0);
    const client: AssessmentClinicalReviewClient = {
      getClinicalReview: vi.fn().mockResolvedValue(mockClinicalReview(1)),
      reviewAttentionCue: vi.fn().mockResolvedValue(updatedReview),
      updateClinicalDisposition: vi.fn(),
      createReportDraft: vi.fn(),
    };

    render(<AssessmentClinicalReviewWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("รับทราบ (Acknowledge)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("รับทราบ (Acknowledge)"));

    await waitFor(() => {
      expect(client.reviewAttentionCue).toHaveBeenCalledWith("asmt_test_001", "cue_001", {
        action: "acknowledged",
        rationale: undefined,
        expected_version: 1,
      });
    });

    expect(await screen.findByText("บันทึกการพิจารณาข้อสังเกตเรียบร้อยแล้ว")).toBeInTheDocument();
  });

  it("handles cue disagreement with required rationale", async () => {
    const updatedReview = {
      ...mockClinicalReview(0),
      attention_cues: [
        {
          ...mockClinicalReview(0).attention_cues[0],
          status: "disagreed" as const,
          clinician_action: "disagreed" as const,
          clinician_rationale: "Child was shy today.",
        },
      ],
    };
    const client: AssessmentClinicalReviewClient = {
      getClinicalReview: vi.fn().mockResolvedValue(mockClinicalReview(1)),
      reviewAttentionCue: vi.fn().mockResolvedValue(updatedReview),
      updateClinicalDisposition: vi.fn(),
      createReportDraft: vi.fn(),
    };

    render(<AssessmentClinicalReviewWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("ไม่เห็นด้วย (Disagree)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ไม่เห็นด้วย (Disagree)"));

    // Rationale textarea should appear
    const rationaleInput = screen.getByPlaceholderText(/กรุณาระบุเหตุผลการไม่เห็นด้วย/);
    fireEvent.change(rationaleInput, { target: { value: "Child was shy today." } });

    fireEvent.click(screen.getByText("ยืนยันเหตุผล"));

    await waitFor(() => {
      expect(client.reviewAttentionCue).toHaveBeenCalledWith("asmt_test_001", "cue_001", {
        action: "disagreed",
        rationale: "Child was shy today.",
        expected_version: 1,
      });
    });
  });

  it("handles updating clinical disposition and follow-up plan", async () => {
    const client: AssessmentClinicalReviewClient = {
      getClinicalReview: vi.fn().mockResolvedValue(mockClinicalReview(0)),
      reviewAttentionCue: vi.fn(),
      updateClinicalDisposition: vi.fn().mockResolvedValue({
        ...mockClinicalReview(0),
        disposition_notes: "Updated notes",
      }),
      createReportDraft: vi.fn(),
    };

    render(<AssessmentClinicalReviewWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("บันทึกความเห็นและแผนติดตาม (Save Disposition)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("บันทึกความเห็นและแผนติดตาม (Save Disposition)"));

    await waitFor(() => {
      expect(client.updateClinicalDisposition).toHaveBeenCalled();
    });
    expect(await screen.findByText("บันทึกความเห็นทางคลินิกและแผนการติดตามสำเร็จ")).toBeInTheDocument();
  });

  it("triggers report draft creation when review is ready", async () => {
    const mockReport: AssessmentV2Report = {
      report_id: "rep_draft_001",
      assessment_id: "asmt_test_001",
      organization_id: "org_alpha",
      status: "draft",
      signer_id: null,
      signer_name: null,
      signer_role: null,
      amends_report_id: null,
      amendment_sequence: 0,
      report_title: "Draft Report",
      markdown_content: "# Draft",
      clinical_summary: "Summary",
      disposition_type: "monitoring_recommended",
      disposition_notes: "Notes",
      follow_up_plan: null,
      snapshot_data: null,
      snapshot_sha256: null,
      signed_at: null,
      amendment_reason: null,
      readiness: { is_ready: true, blockers: [] },
      version: 1,
      created_at: "2026-09-12T10:00:00Z",
      updated_at: "2026-09-12T10:00:00Z",
    };

    const client: AssessmentClinicalReviewClient = {
      getClinicalReview: vi.fn().mockResolvedValue(mockClinicalReview(0)),
      reviewAttentionCue: vi.fn(),
      updateClinicalDisposition: vi.fn(),
      createReportDraft: vi.fn().mockResolvedValue(mockReport),
    };

    render(<AssessmentClinicalReviewWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("สร้างร่างรายงาน (Create Draft)")).toBeEnabled();
    });

    fireEvent.click(screen.getByText("สร้างร่างรายงาน (Create Draft)"));

    await waitFor(() => {
      expect(client.createReportDraft).toHaveBeenCalledWith("asmt_test_001");
    });
    expect(await screen.findByText(/สร้างร่างรายงานรหัส rep_draft_001 สำเร็จ/)).toBeInTheDocument();
  });
});
