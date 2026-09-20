import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  AssessmentReportWorkspace,
  type AssessmentReportClient,
} from "@/features/assessment-v2/components/assessment-report-workspace";
import type { AssessmentV2Report, AssessmentV2ReportLineageItem } from "@/services/assessment-v2-client";

function mockDraftReport(isReady = true): AssessmentV2Report {
  return {
    report_id: "rep_test_draft_01",
    assessment_id: "asmt_test_001",
    organization_id: "org_alpha",
    status: "draft",
    signer_id: null,
    signer_name: null,
    signer_role: null,
    amends_report_id: null,
    amendment_sequence: 0,
    report_title: "รายงานการประเมินพัฒนาการทางภาษาและการสื่อสาร",
    markdown_content: "# รายงานการประเมิน\n\n- ผลการประเมิน: อยู่ในเกณฑ์ปกติ",
    clinical_summary: "เด็กสามารถสื่อสารและเข้าใจคำสั่งได้ตามเกณฑ์",
    disposition_type: "within_normal_expectations",
    disposition_notes: "ไม่มีข้อกังวลเพิ่มเติม",
    follow_up_plan: null,
    snapshot_data: null,
    snapshot_sha256: null,
    signed_at: null,
    amendment_reason: null,
    readiness: {
      is_ready: isReady,
      blockers: isReady ? [] : ["ยังมีข้อสังเกตที่ยังไม่ได้รับการตรวจทาน (1 unreviewed cues)"],
    },
    version: 1,
    created_at: "2026-09-12T10:00:00Z",
    updated_at: "2026-09-12T10:00:00Z",
  };
}

function mockSignedReport(): AssessmentV2Report {
  return {
    report_id: "rep_test_signed_01",
    assessment_id: "asmt_test_001",
    organization_id: "org_alpha",
    status: "signed_off",
    signer_id: "therapist_001",
    signer_name: "ดร. สมชาย รักดี",
    signer_role: "assigned_clinician",
    amends_report_id: null,
    amendment_sequence: 0,
    report_title: "รายงานการประเมินพัฒนาการทางภาษาและการสื่อสาร",
    markdown_content: "# รายงานการประเมินฉบับสมบูรณ์",
    clinical_summary: "เด็กสามารถสื่อสารและเข้าใจคำสั่งได้ตามเกณฑ์",
    disposition_type: "within_normal_expectations",
    disposition_notes: "ไม่มีข้อกังวลเพิ่มเติม",
    follow_up_plan: null,
    snapshot_data: { test: "snapshot" },
    snapshot_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    signed_at: "2026-09-12T11:00:00Z",
    amendment_reason: null,
    readiness: { is_ready: true, blockers: [] },
    version: 2,
    created_at: "2026-09-12T10:00:00Z",
    updated_at: "2026-09-12T11:00:00Z",
  };
}

function mockLineage(): AssessmentV2ReportLineageItem[] {
  return [
    {
      report_id: "rep_test_signed_01",
      amendment_sequence: 0,
      status: "signed_off",
      signed_at: "2026-09-12T11:00:00Z",
      signer_id: "therapist_001",
      snapshot_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      amendment_reason: null,
      created_at: "2026-09-12T10:00:00Z",
    },
  ];
}

describe("AssessmentReportWorkspace", () => {
  it("renders draft report with server readiness banner and editable fields", async () => {
    const client: AssessmentReportClient = {
      getCurrentReport: vi.fn().mockResolvedValue(mockDraftReport(true)),
      getReport: vi.fn(),
      updateReportDraft: vi.fn(),
      signOffReport: vi.fn(),
      createReportAmendment: vi.fn(),
      getReportLineage: vi.fn().mockResolvedValue([]),
      getReportExportPdfUrl: vi.fn().mockReturnValue("/api/v2/export/pdf"),
    };

    render(<AssessmentReportWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("รายงานการประเมินและการลงนามรับรอง")).toBeInTheDocument();
    });

    expect(screen.getByText("ร่างรายงาน (Draft)")).toBeInTheDocument();
    expect(screen.getByText("✓ เซิร์ฟเวอร์พร้อมสำหรับการลงนาม (Server Readiness Passed)")).toBeInTheDocument();
    expect(screen.getByDisplayValue("รายงานการประเมินพัฒนาการทางภาษาและการสื่อสาร")).toBeInTheDocument();
  });

  it("displays blockers when server readiness fails", async () => {
    const client: AssessmentReportClient = {
      getCurrentReport: vi.fn().mockResolvedValue(mockDraftReport(false)),
      getReport: vi.fn(),
      updateReportDraft: vi.fn(),
      signOffReport: vi.fn(),
      createReportAmendment: vi.fn(),
      getReportLineage: vi.fn().mockResolvedValue([]),
      getReportExportPdfUrl: vi.fn().mockReturnValue("/api/v2/export/pdf"),
    };

    render(<AssessmentReportWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("⚠ เงื่อนไขความพร้อมสำหรับการลงนามยังไม่ครบ (Sign-off Blocked)")).toBeInTheDocument();
    });

    expect(screen.getByText(/ยังมีข้อสังเกตที่ยังไม่ได้รับการตรวจทาน/)).toBeInTheDocument();
    expect(screen.queryByText("ลงนามรับรองรายงาน (Sign-off Report)")).not.toBeInTheDocument();
  });

  it("handles updating report draft", async () => {
    const draft = mockDraftReport(true);
    const client: AssessmentReportClient = {
      getCurrentReport: vi.fn().mockResolvedValue(draft),
      getReport: vi.fn(),
      updateReportDraft: vi.fn().mockResolvedValue({
        ...draft,
        report_title: "ชื่อรายงานที่แก้ไขใหม่",
      }),
      signOffReport: vi.fn(),
      createReportAmendment: vi.fn(),
      getReportLineage: vi.fn().mockResolvedValue([]),
      getReportExportPdfUrl: vi.fn().mockReturnValue("/api/v2/export/pdf"),
    };

    render(<AssessmentReportWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("บันทึกการแก้ไขร่างรายงาน (Save Draft)")).toBeInTheDocument();
    });

    const titleInput = screen.getByLabelText("ชื่อรายงาน (Report Title):");
    fireEvent.change(titleInput, { target: { value: "ชื่อรายงานที่แก้ไขใหม่" } });

    fireEvent.click(screen.getByText("บันทึกการแก้ไขร่างรายงาน (Save Draft)"));

    await waitFor(() => {
      expect(client.updateReportDraft).toHaveBeenCalledWith("asmt_test_001", "rep_test_draft_01", {
        report_title: "ชื่อรายงานที่แก้ไขใหม่",
        clinical_summary: "เด็กสามารถสื่อสารและเข้าใจคำสั่งได้ตามเกณฑ์",
        markdown_content: "# รายงานการประเมิน\n\n- ผลการประเมิน: อยู่ในเกณฑ์ปกติ",
        expected_version: 1,
      });
    });

    expect(await screen.findByText("บันทึกร่างรายงานเรียบร้อยแล้ว")).toBeInTheDocument();
  });

  it("handles signing off report with modal confirmation", async () => {
    const draft = mockDraftReport(true);
    const signed = mockSignedReport();
    const client: AssessmentReportClient = {
      getCurrentReport: vi.fn().mockResolvedValue(draft),
      getReport: vi.fn(),
      updateReportDraft: vi.fn(),
      signOffReport: vi.fn().mockResolvedValue(signed),
      createReportAmendment: vi.fn(),
      getReportLineage: vi.fn().mockResolvedValue(mockLineage()),
      getReportExportPdfUrl: vi.fn().mockReturnValue("/api/v2/export/pdf"),
    };

    render(<AssessmentReportWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("ลงนามรับรองรายงาน (Sign-off Report)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ลงนามรับรองรายงาน (Sign-off Report)"));

    // Modal should be open
    expect(screen.getByText("ยืนยันการลงนามรับรองรายงาน (Sign-off Confirmation)")).toBeInTheDocument();

    fireEvent.click(screen.getByText("ยืนยันการลงนามรับรอง"));

    await waitFor(() => {
      expect(client.signOffReport).toHaveBeenCalledWith("asmt_test_001", "rep_test_draft_01", {
        expected_version: 1,
      });
    });

    // Should transition to signed view
    expect(await screen.findByText("ข้อมูลการลงนามรับรอง (Immutable Signed Snapshot)")).toBeInTheDocument();
    expect(screen.getByText(/ดร. สมชาย รักดี/)).toBeInTheDocument();
    expect(screen.getByText(/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/)).toBeInTheDocument();
    expect(screen.getByText("ดาวน์โหลด PDF ภาษาไทย 📄")).toBeInTheDocument();
  });

  it("handles creating an amendment from signed report", async () => {
    const signed = mockSignedReport();
    const amendmentDraft: AssessmentV2Report = {
      ...signed,
      report_id: "rep_amend_draft_02",
      status: "draft",
      signer_id: null,
      signer_name: null,
      signed_at: null,
      snapshot_data: null,
      snapshot_sha256: null,
      amends_report_id: "rep_test_signed_01",
      amendment_sequence: 1,
      amendment_reason: "เพิ่มผลการสังเกตเพิ่มเติม",
      version: 1,
    };

    const client: AssessmentReportClient = {
      getCurrentReport: vi.fn().mockResolvedValue(signed),
      getReport: vi.fn(),
      updateReportDraft: vi.fn(),
      signOffReport: vi.fn(),
      createReportAmendment: vi.fn().mockResolvedValue(amendmentDraft),
      getReportLineage: vi.fn().mockResolvedValue(mockLineage()),
      getReportExportPdfUrl: vi.fn().mockReturnValue("/api/v2/export/pdf"),
    };

    render(<AssessmentReportWorkspace assessmentId="asmt_test_001" client={client} />);

    await waitFor(() => {
      expect(screen.getByText("แก้ไขเพิ่มเติม (Amend Report) ✏️")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("แก้ไขเพิ่มเติม (Amend Report) ✏️"));

    // Modal appears
    expect(screen.getByText("สร้างฉบับแก้ไขเพิ่มเติม (Create Report Amendment)")).toBeInTheDocument();

    const reasonInput = screen.getByLabelText("ระบุเหตุผลในการแก้ไข (Amendment Reason):");
    fireEvent.change(reasonInput, { target: { value: "เพิ่มผลการสังเกตเพิ่มเติม" } });

    fireEvent.click(screen.getByText("สร้างร่างฉบับแก้ไข"));

    await waitFor(() => {
      expect(client.createReportAmendment).toHaveBeenCalledWith(
        "asmt_test_001",
        "rep_test_signed_01",
        {
          amendment_reason: "เพิ่มผลการสังเกตเพิ่มเติม",
          expected_version: 2,
        }
      );
    });

    expect(await screen.findByText(/สร้างฉบับแก้ไขเพิ่มเติม \(ลำดับที่ 1\) สำเร็จ/)).toBeInTheDocument();
  });
});
