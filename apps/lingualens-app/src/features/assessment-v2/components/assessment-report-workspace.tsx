"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AssessmentV2Client,
  type AssessmentV2Report,
  type AssessmentV2ReportLineageItem,
} from "@/services/assessment-v2-client";

export type AssessmentReportClient = Pick<
  AssessmentV2Client,
  | "getCurrentReport"
  | "getReport"
  | "updateReportDraft"
  | "signOffReport"
  | "createReportAmendment"
  | "getReportLineage"
  | "getReportExportPdfUrl"
>;

type AssessmentReportWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentReportClient;
};

const defaultClient = new AssessmentV2Client();

export function AssessmentReportWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentReportWorkspaceProps) {
  const [report, setReport] = useState<AssessmentV2Report | null>(null);
  const [lineage, setLineage] = useState<AssessmentV2ReportLineageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [amending, setAmending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form states for draft edit
  const [reportTitle, setReportTitle] = useState("");
  const [clinicalSummary, setClinicalSummary] = useState("");
  const [markdownContent, setMarkdownContent] = useState("");

  // Modals
  const [showSignModal, setShowSignModal] = useState(false);
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendmentReason, setAmendmentReason] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rep = await client.getCurrentReport(assessmentId);
      setReport(rep);
      setReportTitle(rep.report_title);
      setClinicalSummary(rep.clinical_summary);
      setMarkdownContent(rep.markdown_content);

      if (rep.report_id) {
        try {
          const lin = await client.getReportLineage(assessmentId, rep.report_id);
          setLineage(lin);
        } catch {
          // Lineage might be empty for new drafts
        }
      }
    } catch (err: unknown) {
      setError("ยังไม่มีร่างรายงานสำหรับรอบการประเมินนี้ กรุณาทำการตรวจทานข้อสังเกตและสร้างร่างก่อน");
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSaveDraft = async () => {
    if (!report) return;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await client.updateReportDraft(assessmentId, report.report_id, {
        report_title: reportTitle.trim(),
        clinical_summary: clinicalSummary.trim(),
        markdown_content: markdownContent,
        expected_version: report.version,
      });
      setReport(updated);
      setSuccessMessage("บันทึกร่างรายงานเรียบร้อยแล้ว");
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการบันทึกร่างรายงาน (อาจมีการแก้ไขจากเซสชันอื่นหรือรายงานถูกลงนามแล้ว)");
    } finally {
      setSaving(false);
    }
  };

  const handleSignOff = async () => {
    if (!report) return;
    setSigning(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const signed = await client.signOffReport(assessmentId, report.report_id, {
        expected_version: report.version,
      });
      setReport(signed);
      setShowSignModal(false);
      setSuccessMessage("ลงนามรับรองรายงานเรียบร้อยแล้ว รายงานถูกบันทึกเป็น Snapshot ถาวร");
      // Reload lineage
      const lin = await client.getReportLineage(assessmentId, signed.report_id);
      setLineage(lin);
    } catch (err: unknown) {
      setError("ไม่สามารถลงนามรับรองรายงานได้ กรุณาตรวจสอบเงื่อนไขความพร้อมของเซิร์ฟเวอร์");
    } finally {
      setSigning(false);
    }
  };

  const handleCreateAmendment = async () => {
    if (!report || !amendmentReason.trim()) return;
    setAmending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const newDraft = await client.createReportAmendment(assessmentId, report.report_id, {
        amendment_reason: amendmentReason.trim(),
        expected_version: report.version,
      });
      setReport(newDraft);
      setReportTitle(newDraft.report_title);
      setClinicalSummary(newDraft.clinical_summary);
      setMarkdownContent(newDraft.markdown_content);
      setShowAmendModal(false);
      setAmendmentReason("");
      setSuccessMessage(`สร้างฉบับแก้ไขเพิ่มเติม (ลำดับที่ ${newDraft.amendment_sequence}) สำเร็จ`);
      const lin = await client.getReportLineage(assessmentId, newDraft.report_id);
      setLineage(lin);
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการสร้างฉบับแก้ไขเพิ่มเติม");
    } finally {
      setAmending(false);
    }
  };

  if (loading) {
    return (
      <section
        className="workspace-panel rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        aria-busy="true"
      >
        <div className="flex items-center space-x-3 text-slate-500">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium">กำลังโหลดข้อมูลรายงานทางคลินิก…</p>
        </div>
      </section>
    );
  }

  if (!report) {
    return (
      <section className="workspace-panel rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="text-center">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            ยังไม่พบร่างรายงาน (No Report Draft Available)
          </h3>
          <p className="mt-2 text-xs text-slate-500">
            กรุณาไปที่หน้าการตรวจทานทางคลินิก (Clinical Review) เพื่อตรวจทานข้อสังเกตและสร้างร่างรายงานฉบับแรก
          </p>
          <div className="mt-4">
            <Link
              href={`/assessments/${encodeURIComponent(assessmentId)}/review`}
              className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              ← ไปยังหน้าตรวจทานข้อสังเกต (Clinical Review)
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const isDraft = report.status === "draft";
  const isSigned = report.status === "signed_off" || report.status === "amended";
  const isReady = report.readiness.is_ready;

  return (
    <section className="workspace-panel space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* Header & Status */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold uppercase text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
              Clinical Report (Slice C2)
            </span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              รายงานการประเมินและการลงนามรับรอง
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Report ID: <span className="font-mono">{report.report_id}</span> | สถานะ:{" "}
            <span
              className={`font-bold ${
                report.status === "signed_off"
                  ? "text-emerald-600"
                  : report.status === "draft"
                  ? "text-amber-600"
                  : "text-slate-600"
              }`}
            >
              {report.status === "signed_off"
                ? "ลงนามรับรองแล้ว (Signed-off)"
                : report.status === "draft"
                ? "ร่างรายงาน (Draft)"
                : report.status}
            </span>{" "}
            {report.amendment_sequence > 0 && `(ฉบับแก้ไขที่ ${report.amendment_sequence})`}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            href={`/assessments/${encodeURIComponent(assessmentId)}/review`}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            ← หน้าตรวจทานข้อสังเกต
          </Link>
          {isSigned && (
            <a
              href={client.getReportExportPdfUrl(assessmentId, report.report_id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500"
            >
              ดาวน์โหลด PDF ภาษาไทย 📄
            </a>
          )}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg bg-rose-50 p-4 text-xs font-medium text-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
        >
          {error}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="rounded-lg bg-emerald-50 p-4 text-xs font-medium text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
        >
          {successMessage}
        </div>
      )}

      {/* Server-Side Readiness Banner */}
      {isDraft && (
        <div
          className={`rounded-lg border p-4 text-xs ${
            isReady
              ? "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200"
              : "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-bold">
                {isReady
                  ? "✓ เซิร์ฟเวอร์พร้อมสำหรับการลงนาม (Server Readiness Passed)"
                  : "⚠ เงื่อนไขความพร้อมสำหรับการลงนามยังไม่ครบ (Sign-off Blocked)"}
              </span>
            </div>
            {isReady && (
              <button
                type="button"
                onClick={() => setShowSignModal(true)}
                className="inline-flex items-center rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500"
              >
                ลงนามรับรองรายงาน (Sign-off Report)
              </button>
            )}
          </div>

          {!isReady && report.readiness.blockers.length > 0 && (
            <ul className="mt-2 list-inside list-disc space-y-1 text-[11px] text-amber-800 dark:text-amber-300">
              {report.readiness.blockers.map((b, idx) => (
                <li key={idx}>{b}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Signed Snapshot Metadata Card */}
      {isSigned && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 text-xs dark:border-emerald-900/60 dark:bg-emerald-950/20">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="font-bold text-emerald-900 dark:text-emerald-200">
                ข้อมูลการลงนามรับรอง (Immutable Signed Snapshot)
              </span>
              <p className="mt-1 text-slate-700 dark:text-slate-300">
                ผู้ลงนาม: <strong>{report.signer_name || report.signer_id}</strong> (
                {report.signer_role || "assigned_clinician"}) | เวลาที่ลงนาม:{" "}
                {report.signed_at ? new Date(report.signed_at).toLocaleString() : "—"}
              </p>
              <p className="mt-1 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                SHA-256 Hash: {report.snapshot_sha256}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowAmendModal(true)}
              className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              แก้ไขเพิ่มเติม (Amend Report) ✏️
            </button>
          </div>
        </div>
      )}

      {/* Draft Content Form / Preview */}
      <div className="space-y-4">
        <div>
          <label htmlFor="report-title-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            ชื่อรายงาน (Report Title):
          </label>
          <input
            id="report-title-input"
            type="text"
            disabled={!isDraft}
            value={reportTitle}
            onChange={(e) => setReportTitle(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-900"
          />
        </div>

        <div>
          <label htmlFor="clinical-summary-text" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            บทสรุปทางคลินิก (Clinical Summary):
          </label>
          <textarea
            id="clinical-summary-text"
            rows={3}
            disabled={!isDraft}
            value={clinicalSummary}
            onChange={(e) => setClinicalSummary(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-900"
          />
        </div>

        <div>
          <label htmlFor="markdown-content-text" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            เนื้อหารายงาน Markdown (Markdown Content):
          </label>
          <textarea
            id="markdown-content-text"
            rows={12}
            disabled={!isDraft}
            value={markdownContent}
            onChange={(e) => setMarkdownContent(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 font-mono p-3 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:disabled:bg-slate-900"
          />
        </div>

        {isDraft && (
          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => void handleSaveDraft()}
              disabled={saving}
              className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {saving ? "กำลังบันทึก…" : "บันทึกการแก้ไขร่างรายงาน (Save Draft)"}
            </button>
          </div>
        )}
      </div>

      {/* Amendment Lineage Section */}
      {lineage.length > 0 && (
        <div className="space-y-3 border-t border-slate-100 pt-4 dark:border-slate-800">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            ประวัติการแก้ไขและสายวิวัฒนาการรายงาน (Amendment Lineage)
          </h3>

          <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-xs dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
            {lineage.map((item) => (
              <div key={item.report_id} className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-900 dark:text-white">
                      ฉบับที่ {item.amendment_sequence === 0 ? "ตั้งต้น (Original)" : `แก้ไข ${item.amendment_sequence}`}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        item.status === "signed_off"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : item.status === "amended"
                          ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    {item.signed_at ? new Date(item.signed_at).toLocaleString() : "ยังไม่ลงนาม"}
                  </span>
                </div>

                {item.amendment_reason && (
                  <p className="mt-1 text-slate-600 dark:text-slate-300">
                    <span className="font-semibold">เหตุผลการแก้ไข: </span>
                    {item.amendment_reason}
                  </p>
                )}

                {item.snapshot_sha256 && (
                  <p className="mt-1 font-mono text-[10px] text-slate-500">
                    SHA-256: {item.snapshot_sha256.slice(0, 24)}…
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sign-off Confirmation Modal */}
      {showSignModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="sign-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <h3 id="sign-modal-title" className="text-base font-bold text-slate-900 dark:text-white">
              ยืนยันการลงนามรับรองรายงาน (Sign-off Confirmation)
            </h3>
            <div className="mt-3 text-xs text-slate-600 dark:text-slate-300 space-y-2">
              <p>
                การลงนามรับรองจะบันทึก Snapshot รายงานอย่างถาวร (Immutable Snapshot) พร้อมสร้าง Deterministic SHA-256
                Hash ซึ่งไม่สามารถเปลี่ยนแปลงได้
              </p>
              <p className="font-medium text-amber-800 dark:text-amber-300">
                หากจำเป็นต้องปรับปรุงข้อความในอนาคต จะต้องดำเนินการผ่านกระบวนการออกฉบับแก้ไขเพิ่มเติม (Amendment Lineage)
                เท่านั้น
              </p>
            </div>
            <div className="mt-5 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowSignModal(false)}
                className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={signing}
                onClick={() => void handleSignOff()}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-50"
              >
                {signing ? "กำลังลงนาม…" : "ยืนยันการลงนามรับรอง"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Amendment Modal */}
      {showAmendModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="amend-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <h3 id="amend-modal-title" className="text-base font-bold text-slate-900 dark:text-white">
              สร้างฉบับแก้ไขเพิ่มเติม (Create Report Amendment)
            </h3>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
              การแก้ไขเพิ่มเติมจะคัดลอกเนื้อหาเดิมไปเป็นร่างใหม่ (Draft) และคง Snapshot ฉบับเดิมไว้ในประวัติ
            </p>
            <div className="mt-3">
              <label htmlFor="amend-reason-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                ระบุเหตุผลในการแก้ไข (Amendment Reason):
              </label>
              <textarea
                id="amend-reason-input"
                rows={3}
                value={amendmentReason}
                onChange={(e) => setAmendmentReason(e.target.value)}
                placeholder="เช่น ปรับปรุงข้อความตามหลักฐานเพิ่มเติมจากการสังเกตในห้องตรวจ..."
                className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
            <div className="mt-5 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAmendModal(false)}
                className="rounded-lg px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400"
              >
                ยกเลิก
              </button>
              <button
                type="button"
                disabled={!amendmentReason.trim() || amending}
                onClick={() => void handleCreateAmendment()}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
              >
                {amending ? "กำลังดำเนินการ…" : "สร้างร่างฉบับแก้ไข"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
