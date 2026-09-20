"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AssessmentV2Client,
  type AssessmentV2ClinicalReview,
  type AssessmentV2AttentionCue,
  type AssessmentV2CueStatus,
  type AssessmentV2ClinicalDispositionType,
  type AssessmentV2FollowUpPlan,
} from "@/services/assessment-v2-client";

export type AssessmentClinicalReviewClient = Pick<
  AssessmentV2Client,
  "getClinicalReview" | "reviewAttentionCue" | "updateClinicalDisposition" | "createReportDraft"
>;

type AssessmentClinicalReviewWorkspaceProps = {
  assessmentId: string;
  client?: AssessmentClinicalReviewClient;
};

const defaultClient = new AssessmentV2Client();

const DISPOSITION_LABELS: Record<AssessmentV2ClinicalDispositionType, { labelTh: string; labelEn: string }> = {
  within_normal_expectations: {
    labelTh: "อยู่ในเกณฑ์ปกติเหมาะสมตามวัย",
    labelEn: "Within Normal Developmental Expectations",
  },
  monitoring_recommended: {
    labelTh: "แนะนำติดตามพัฒนาการเป็นระยะ",
    labelEn: "Developmental Monitoring Recommended",
  },
  targeted_intervention_recommended: {
    labelTh: "แนะนำการส่งเสริมกระตุ้นพัฒนาการเฉพาะด้าน",
    labelEn: "Targeted Speech-Language Intervention Recommended",
  },
  comprehensive_multidisciplinary_evaluation_recommended: {
    labelTh: "แนะนำส่งต่อเพื่อการประเมินแบบสหวิชาชีพรอบด้าน",
    labelEn: "Comprehensive Multidisciplinary Evaluation Recommended",
  },
  inconclusive_further_evidence_needed: {
    labelTh: "ยังสรุปผลไม่ได้ จำเป็นต้องรวบรวมหลักฐานเพิ่มเติม",
    labelEn: "Inconclusive / Further Evidence Needed",
  },
};

const SEVERITY_BADGES: Record<AssessmentV2AttentionCue["severity_level"], { bg: string; text: string }> = {
  info: { bg: "bg-blue-100 dark:bg-blue-950/60", text: "text-blue-800 dark:text-blue-300" },
  moderate: { bg: "bg-amber-100 dark:bg-amber-950/60", text: "text-amber-800 dark:text-amber-300" },
  significant: { bg: "bg-rose-100 dark:bg-rose-950/60", text: "text-rose-800 dark:text-rose-300" },
};

export function AssessmentClinicalReviewWorkspace({
  assessmentId,
  client = defaultClient,
}: AssessmentClinicalReviewWorkspaceProps) {
  const [review, setReview] = useState<AssessmentV2ClinicalReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoadingCueId, setActionLoadingCueId] = useState<string | null>(null);
  const [savingDisposition, setSavingDisposition] = useState(false);
  const [creatingDraft, setCreatingDraft] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Cue review rationale input states
  const [activeCueAction, setActiveCueAction] = useState<{
    cueId: string;
    action: AssessmentV2CueStatus;
  } | null>(null);
  const [rationaleText, setRationaleText] = useState("");

  // Disposition form states
  const [selectedDisposition, setSelectedDisposition] = useState<AssessmentV2ClinicalDispositionType>(
    "monitoring_recommended"
  );
  const [dispositionNotes, setDispositionNotes] = useState("");
  const [clinicalSummary, setClinicalSummary] = useState("");
  const [followUpWeeks, setFollowUpWeeks] = useState(4);
  const [followUpActivities, setFollowUpActivities] = useState("interactive play, turn-taking routines");
  const [caregiverGuidance, setCaregiverGuidance] = useState("Encourage joint attention and natural conversational turns during daily routines.");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await client.getClinicalReview(assessmentId);
      setReview(data);
      if (data.disposition_type) {
        setSelectedDisposition(data.disposition_type);
      }
      if (data.disposition_notes) {
        setDispositionNotes(data.disposition_notes);
      }
      if (data.clinical_summary) {
        setClinicalSummary(data.clinical_summary);
      }
      if (data.follow_up_plan) {
        setFollowUpWeeks(data.follow_up_plan.target_window_weeks);
        setFollowUpActivities(data.follow_up_plan.recommended_activities.join(", "));
        setCaregiverGuidance(data.follow_up_plan.caregiver_guidance);
      }
    } catch (err: unknown) {
      setError("ไม่สามารถโหลดข้อมูลการตรวจทานทางคลินิกได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setLoading(false);
    }
  }, [assessmentId, client]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCueActionSubmit = async (cueId: string, action: AssessmentV2CueStatus, rationale?: string) => {
    if (!review) return;
    setActionLoadingCueId(cueId);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await client.reviewAttentionCue(assessmentId, cueId, {
        action,
        rationale: rationale?.trim() || undefined,
        expected_version: review.version,
      });
      setReview(updated);
      setActiveCueAction(null);
      setRationaleText("");
      setSuccessMessage("บันทึกการพิจารณาข้อสังเกตเรียบร้อยแล้ว");
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการบันทึกการพิจารณาข้อสังเกต กรุณาตรวจสอบและลองใหม่");
    } finally {
      setActionLoadingCueId(null);
    }
  };

  const handleSaveDisposition = async () => {
    if (!review) return;
    setSavingDisposition(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const followUp: AssessmentV2FollowUpPlan = {
        target_window_weeks: Number(followUpWeeks) || 4,
        recommended_activities: followUpActivities
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        caregiver_guidance: caregiverGuidance.trim(),
      };
      const updated = await client.updateClinicalDisposition(assessmentId, {
        disposition_type: selectedDisposition,
        disposition_notes: dispositionNotes.trim(),
        clinical_summary: clinicalSummary.trim(),
        follow_up_plan: followUp,
        expected_version: review.version,
      });
      setReview(updated);
      setSuccessMessage("บันทึกความเห็นทางคลินิกและแผนการติดตามสำเร็จ");
    } catch (err: unknown) {
      setError("เกิดข้อผิดพลาดในการบันทึกความเห็นทางคลินิก กรุณาตรวจสอบและลองใหม่");
    } finally {
      setSavingDisposition(false);
    }
  };

  const handleCreateDraft = async () => {
    setCreatingDraft(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const report = await client.createReportDraft(assessmentId);
      setSuccessMessage(`สร้างร่างรายงานรหัส ${report.report_id} สำเร็จ`);
    } catch (err: unknown) {
      setError("ไม่สามารถสร้างร่างรายงานได้ ตรวจสอบว่าได้พิจารณาข้อสังเกตครบทุกข้อและระบุผลการประเมินแล้ว");
    } finally {
      setCreatingDraft(false);
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
          <p className="text-sm font-medium">กำลังโหลดข้อมูลการตรวจทานและข้อสังเกตทางคลินิก…</p>
        </div>
      </section>
    );
  }

  const unreviewedCount = review?.unreviewed_cues_count ?? 0;
  const canFinalize = review?.can_finalize ?? false;

  return (
    <section className="workspace-panel space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* Header & Clinical Safety Notice */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold uppercase text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
              Clinical Review (Slice C1)
            </span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              การตรวจทานข้อสังเกตและความเห็นของนักบำบัด
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Non-exclusive attention cues referenced to policy version {review?.cues_policy_version || "cues-v2.0"}.
            Clinician acknowledgement or rationale required.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href={`/assessments/${encodeURIComponent(assessmentId)}/report`}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            ไปยังหน้ารายงาน (Report Workspace) →
          </Link>
        </div>
      </div>

      {/* Safety Notice Banner */}
      <div
        role="note"
        aria-label="Clinical safety boundary notice"
        className="rounded-lg border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
      >
        <p className="font-bold">ข้อกำหนดความปลอดภัยทางคลินิก (Clinical Safety Boundary):</p>
        <p className="mt-1">
          ระบบคำนวณข้อสังเกตเพื่อช่วยสนับสนุนการพิจารณาเท่านั้น (Decision Support Only)
          โดย<strong>ไม่มีการทำนายอัตราความน่าจะเป็นของภาวะออทิซึม (ASD) หรือระดับเปอร์เซ็นต์ความล่าช้า</strong>
          และข้อสังเกตที่คำนวณได้จะ<strong>ไม่ถูกนำเข้าสู่ข้อสรุปของรายงานโดยอัตโนมัติ</strong>จนกว่านักบำบัดจะตรวจทานและบันทึกความเห็น
        </p>
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

      {/* Status Bar */}
      <div className="flex items-center justify-between rounded-lg bg-slate-50 p-4 border border-slate-200 text-xs dark:bg-slate-800/60 dark:border-slate-700">
        <div className="flex items-center space-x-4">
          <div>
            <span className="text-slate-500">ข้อสังเกตที่รอตรวจทาน:</span>{" "}
            <span
              className={`font-bold ${
                unreviewedCount === 0 ? "text-emerald-600" : "text-amber-600 font-extrabold"
              }`}
            >
              {unreviewedCount} ข้อ
            </span>
          </div>
          <div>
            <span className="text-slate-500">สถานะความพร้อม:</span>{" "}
            <span
              className={`font-bold ${
                canFinalize ? "text-emerald-600" : "text-slate-600 dark:text-slate-400"
              }`}
            >
              {canFinalize ? "พร้อมสรุปรายงาน (Ready for Report)" : "ต้องตรวจทานให้ครบทุกข้อ (Incomplete)"}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void handleCreateDraft()}
          disabled={!canFinalize || creatingDraft}
          className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
        >
          {creatingDraft ? "กำลังสร้างร่าง…" : "สร้างร่างรายงาน (Create Draft)"}
        </button>
      </div>

      {/* Attention Cues Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          ข้อสังเกตเพื่อการพิจารณา (Attention Cues)
        </h3>

        {(!review?.attention_cues || review.attention_cues.length === 0) ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900">
            ไม่พบข้อสังเกตที่ต้องพิจารณาเป็นพิเศษสำหรับชุดหลักฐานนี้
          </div>
        ) : (
          <div className="space-y-3">
            {review.attention_cues.map((cue) => {
              const badge = SEVERITY_BADGES[cue.severity_level];
              const isBusy = actionLoadingCueId === cue.cue_id;
              const isEditingRationale = activeCueAction?.cueId === cue.cue_id;

              return (
                <div
                  key={cue.cue_id}
                  className="rounded-lg border border-slate-200 bg-white p-4 text-xs shadow-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${badge.bg} ${badge.text}`}
                      >
                        {cue.severity_level}
                      </span>
                      <h4 className="font-bold text-slate-900 dark:text-white">{cue.title}</h4>
                      {cue.feature_key && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                          {cue.feature_key}
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-slate-500">สถานะ: </span>
                      <span
                        className={`font-semibold ${
                          cue.status === "unreviewed"
                            ? "text-amber-600"
                            : cue.status === "acknowledged"
                            ? "text-emerald-600"
                            : cue.status === "disagreed"
                            ? "text-rose-600"
                            : "text-blue-600"
                        }`}
                      >
                        {cue.status}
                      </span>
                    </div>
                  </div>

                  <p className="mt-2 text-slate-700 dark:text-slate-300">{cue.description}</p>

                  {cue.clinician_rationale && (
                    <div className="mt-2 rounded bg-slate-50 p-2 text-slate-700 dark:bg-slate-800/80 dark:text-slate-300">
                      <span className="font-semibold text-slate-900 dark:text-white">เหตุผลของนักบำบัด: </span>
                      {cue.clinician_rationale}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => void handleCueActionSubmit(cue.cue_id, "acknowledged")}
                      className={`rounded px-2.5 py-1 text-xs font-medium ${
                        cue.status === "acknowledged"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-bold"
                          : "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {isBusy && activeCueAction?.action === "acknowledged" ? "กำลังบันทึก…" : "รับทราบ (Acknowledge)"}
                    </button>

                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        setActiveCueAction({ cueId: cue.cue_id, action: "disagreed" });
                        setRationaleText(cue.clinician_rationale || "");
                      }}
                      className={`rounded px-2.5 py-1 text-xs font-medium ${
                        cue.status === "disagreed"
                          ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 font-bold"
                          : "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
                      }`}
                    >
                      ไม่เห็นด้วย (Disagree)
                    </button>

                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        setActiveCueAction({ cueId: cue.cue_id, action: "more_evidence_requested" });
                        setRationaleText(cue.clinician_rationale || "");
                      }}
                      className={`rounded px-2.5 py-1 text-xs font-medium ${
                        cue.status === "more_evidence_requested"
                          ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 font-bold"
                          : "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
                      }`}
                    >
                      ขอข้อมูลเพิ่ม (Request More Evidence)
                    </button>
                  </div>

                  {/* Rationale Input Popup/Drawer */}
                  {isEditingRationale && (
                    <div className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/80">
                      <label htmlFor={`rationale-input-${cue.cue_id}`} className="font-semibold text-slate-900 dark:text-white">
                        ระบุเหตุผลทางคลินิกสำหรับ {activeCueAction.action}:
                      </label>
                      <textarea
                        id={`rationale-input-${cue.cue_id}`}
                        rows={2}
                        className="mt-1 w-full rounded border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                        placeholder="กรุณาระบุเหตุผลการไม่เห็นด้วยหรือเหตุผลที่ต้องการหลักฐานเพิ่มเติม..."
                        value={rationaleText}
                        onChange={(e) => setRationaleText(e.target.value)}
                      />
                      <div className="mt-2 flex justify-end space-x-2">
                        <button
                          type="button"
                          onClick={() => setActiveCueAction(null)}
                          className="rounded px-2.5 py-1 text-xs text-slate-600 hover:text-slate-900 dark:text-slate-400"
                        >
                          ยกเลิก
                        </button>
                        <button
                          type="button"
                          disabled={!rationaleText.trim() || isBusy}
                          onClick={() =>
                            void handleCueActionSubmit(cue.cue_id, activeCueAction.action, rationaleText)
                          }
                          className="rounded bg-indigo-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
                        >
                          {isBusy ? "กำลังบันทึก…" : "ยืนยันเหตุผล"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Disposition & Summary Section */}
      <div className="space-y-4 border-t border-slate-100 pt-4 dark:border-slate-800">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
          ผลการประเมินทางคลินิกและแผนการติดตาม (Disposition & Follow-up Plan)
        </h3>

        <div className="space-y-3">
          <div>
            <label htmlFor="disposition-select" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              ผลการวินิจฉัย/การประเมินสรุป (Disposition):
            </label>
            <select
              id="disposition-select"
              value={selectedDisposition}
              onChange={(e) =>
                setSelectedDisposition(e.target.value as AssessmentV2ClinicalDispositionType)
              }
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 text-xs font-medium text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            >
              {(Object.keys(DISPOSITION_LABELS) as AssessmentV2ClinicalDispositionType[]).map((key) => (
                <option key={key} value={key}>
                  {DISPOSITION_LABELS[key].labelTh} — {DISPOSITION_LABELS[key].labelEn}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="clinical-summary-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              บทสรุปทางคลินิกโดยรวม (Clinical Summary):
            </label>
            <textarea
              id="clinical-summary-input"
              rows={3}
              value={clinicalSummary}
              onChange={(e) => setClinicalSummary(e.target.value)}
              placeholder="บันทึกภาพรวมทางภาษาและการสื่อสารของเด็กจากการตรวจประเมิน..."
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div>
            <label htmlFor="disposition-notes-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              บันทึกข้อสังเกตเพิ่มเติม (Disposition Notes):
            </label>
            <textarea
              id="disposition-notes-input"
              rows={2}
              value={dispositionNotes}
              onChange={(e) => setDispositionNotes(e.target.value)}
              placeholder="ข้อสังเกตเพิ่มเติมเกี่ยวกับการประเมินและปัจจัยแวดล้อม..."
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="followup-weeks-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                ช่วงเวลานัดติดตามผล (สัปดาห์):
              </label>
              <input
                id="followup-weeks-input"
                type="number"
                min={1}
                max={52}
                value={followUpWeeks}
                onChange={(e) => setFollowUpWeeks(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
            <div>
              <label htmlFor="followup-activities-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                กิจกรรมที่แนะนำ (Recommended Activities):
              </label>
              <input
                id="followup-activities-input"
                type="text"
                value={followUpActivities}
                onChange={(e) => setFollowUpActivities(e.target.value)}
                placeholder="กิจกรรมส่งเสริมพัฒนาการ..."
                className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>
          </div>

          <div>
            <label htmlFor="caregiver-guidance-input" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
              คำแนะนำสำหรับผู้ปกครอง (Caregiver Guidance):
            </label>
            <textarea
              id="caregiver-guidance-input"
              rows={2}
              value={caregiverGuidance}
              onChange={(e) => setCaregiverGuidance(e.target.value)}
              placeholder="คำแนะนำในการส่งเสริมการสื่อสารที่บ้าน..."
              className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={() => void handleSaveDisposition()}
              disabled={savingDisposition}
              className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50"
            >
              {savingDisposition ? "กำลังบันทึก…" : "บันทึกความเห็นและแผนติดตาม (Save Disposition)"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
