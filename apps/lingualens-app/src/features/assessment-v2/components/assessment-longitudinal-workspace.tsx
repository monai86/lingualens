"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AssessmentV2Client,
  type AssessmentV2ChildHistoryItem,
  type AssessmentV2Comparison,
  type AssessmentV2FeatureComparison,
} from "@/services/assessment-v2-client";

export type AssessmentLongitudinalClient = Pick<
  AssessmentV2Client,
  "getChildAssessmentHistory" | "getComparisons" | "createComparison" | "getComparison"
>;

type AssessmentLongitudinalWorkspaceProps = {
  assessmentId: string;
  childId?: string;
  client?: AssessmentLongitudinalClient;
};

const defaultClient = new AssessmentV2Client();

function formatDelta(val: number | null): string {
  if (val === null || val === undefined) return "—";
  if (val > 0) return `+${val.toFixed(2)}`;
  return val.toFixed(2);
}

function formatPercent(feat: AssessmentV2FeatureComparison): string {
  if (feat.percent_change_limitation === "zero_baseline") {
    return "N/A (zero_baseline)";
  }
  if (feat.percent_change === null || feat.percent_change === undefined) {
    return "—";
  }
  if (feat.percent_change > 0) {
    return `+${feat.percent_change.toFixed(1)}%`;
  }
  return `${feat.percent_change.toFixed(1)}%`;
}

export function AssessmentLongitudinalWorkspace({
  assessmentId,
  childId,
  client = defaultClient,
}: AssessmentLongitudinalWorkspaceProps) {
  const [history, setHistory] = useState<AssessmentV2ChildHistoryItem[]>([]);
  const [selectedBaselineId, setSelectedBaselineId] = useState<string>("");
  const [currentComparison, setCurrentComparison] = useState<AssessmentV2Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const priorAssessments = history.filter((h) => h.assessment_id !== assessmentId);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (childId) {
        const hist = await client.getChildAssessmentHistory(childId);
        setHistory(hist);
        const priors = hist.filter((h) => h.assessment_id !== assessmentId && h.is_comparable);
        if (priors.length > 0) {
          setSelectedBaselineId((current) => current ?? priors[0].assessment_id);
        }
      }

      const existingComparisons = await client.getComparisons(assessmentId);
      if (existingComparisons.length > 0) {
        setCurrentComparison(existingComparisons[0]);
        setSelectedBaselineId(existingComparisons[0].baseline_assessment_id);
      }
    } catch (err: unknown) {
      setError("ไม่สามารถโหลดข้อมูลประวัติการประเมินได้");
    } finally {
      setLoading(false);
    }
  }, [assessmentId, childId, client]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCompare = async () => {
    if (!selectedBaselineId) return;
    setComparing(true);
    setError(null);
    try {
      const comp = await client.createComparison(assessmentId, selectedBaselineId);
      setCurrentComparison(comp);
    } catch (err: unknown) {
      setError("ไม่สามารถสร้างผลการเปรียบเทียบได้ กรุณาตรวจสอบความถูกต้องของข้อมูล");
    } finally {
      setComparing(false);
    }
  };

  if (loading) {
    return (
      <section className="workspace-panel rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900" aria-busy="true">
        <div className="flex items-center space-x-3 text-slate-500">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm font-medium">กำลังโหลดประวัติการประเมินและการเปรียบเทียบ…</p>
        </div>
      </section>
    );
  }

  // Frame H14-NoHistory
  if (priorAssessments.length === 0) {
    return (
      <section className="workspace-panel rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900" aria-labelledby="no-history-heading">
        <div className="flex items-center space-x-2 text-indigo-600 dark:text-indigo-400">
          <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider dark:bg-indigo-950/50">
            H14-NoHistory
          </span>
          <h2 id="no-history-heading" className="text-lg font-bold text-slate-900 dark:text-white">
            การประเมินตั้งต้น (Baseline Visit)
          </h2>
        </div>
        <div className="mt-4 rounded-lg bg-slate-50 p-4 border border-slate-200 text-sm text-slate-700 dark:bg-slate-800/60 dark:border-slate-700 dark:text-slate-300">
          <p className="font-medium text-slate-900 dark:text-white">
            This is the child&apos;s initial recorded assessment. Longitudinal comparison will be available on subsequent assessments under matching protocols.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            การประเมินนี้เป็นครั้งแรกของเด็ก การเปรียบเทียบเชิงพัฒนาการจะเปิดให้ใช้งานในครั้งถัดไปเมื่อใช้ชุดเครื่องมือและภาษาที่เข้ากันได้
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="workspace-panel space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* Header & Safety Disclaimer */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold uppercase text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
              Longitudinal Analysis
            </span>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              ประวัติการติดตามและการเปรียบเทียบเชิงตัวเลข
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Descriptive numerical delta only; indeterminate clinical interpretation. Not a diagnostic tool.
          </p>
        </div>

        {/* Baseline Selector */}
        <div className="flex items-center space-x-3">
          <label htmlFor="baseline-select" className="text-xs font-medium text-slate-700 dark:text-slate-300">
            เลือกการประเมินพื้นฐาน:
          </label>
          <select
            id="baseline-select"
            aria-label="เลือกการประเมินพื้นฐาน"
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
            value={selectedBaselineId}
            onChange={(e) => setSelectedBaselineId(e.target.value)}
          >
            {priorAssessments.map((a) => (
              <option key={a.assessment_id} value={a.assessment_id}>
                {new Date(a.created_at).toLocaleDateString()} — {a.age_months} เดือน ({a.purpose})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void handleCompare()}
            disabled={comparing || !selectedBaselineId}
            className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50"
          >
            {comparing ? "กำลังคำนวณ…" : "เปรียบเทียบ"}
          </button>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-rose-50 p-4 text-xs font-medium text-rose-800 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Stale Warning Banner */}
      {currentComparison?.is_stale && (
        <div role="alert" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-xs font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <div className="flex items-center space-x-2">
            <span className="font-bold">คำเตือน:</span>
            <span>ข้อมูลต้นทางมีการอัปเดตใหม่ (Stale Source) ผลการเปรียบเทียบนี้สร้างขึ้นจากรุ่นก่อนหน้า กรุณากดเปรียบเทียบใหม่เพื่อผลล่าสุด</span>
          </div>
        </div>
      )}

      {/* Comparison Body */}
      {currentComparison && (
        <div className="space-y-4">
          {currentComparison.status === "not_comparable" ? (
            /* Frame H14-Incompatible */
            <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-5 dark:border-amber-900/60 dark:bg-amber-950/30">
              <div className="flex items-center space-x-2">
                <span className="rounded bg-amber-200 px-2 py-0.5 text-xs font-bold text-amber-900 dark:bg-amber-900 dark:text-amber-200">
                  H14-Incompatible
                </span>
                <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                  ชุดข้อมูลไม่สามารถเปรียบเทียบได้ (Incompatible Comparison)
                </h3>
              </div>
              <p className="mt-2 text-xs text-amber-800 dark:text-amber-300">
                Notice: Comparisons are not permitted across differing protocol structures, languages, or missing evidence. Delta cannot be clinically interpreted.
              </p>

              <div className="mt-4 divide-y divide-amber-200 rounded-md border border-amber-200 bg-white text-xs dark:divide-amber-900/50 dark:border-amber-900/50 dark:bg-slate-900">
                {currentComparison.features.map((feat) => (
                  <div key={feat.feature_key} className="flex items-center justify-between p-3">
                    <span className="font-mono font-medium text-slate-800 dark:text-slate-200">
                      {feat.feature_key}
                    </span>
                    <div className="flex items-center space-x-2">
                      {feat.incompatibility_reasons.map((r) => (
                        <span key={r} className="rounded bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                          {r}
                        </span>
                      ))}
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        status: {feat.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Frame H14-Compatible */
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  H14-Compatible
                </span>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  การเปรียบเทียบเชิงตัวเลขที่เข้ากันได้ (Compatible Comparison)
                </h3>
              </div>

              <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs dark:divide-slate-800">
                  <thead className="bg-slate-50 font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    <tr>
                      <th className="px-4 py-3">Feature (ตัวแปร)</th>
                      <th className="px-4 py-3">Baseline</th>
                      <th className="px-4 py-3">Current</th>
                      <th className="px-4 py-3">Absolute Delta</th>
                      <th className="px-4 py-3">% Change</th>
                      <th className="px-4 py-3">Numerical Trend</th>
                      <th className="px-4 py-3">Clinical Interpretation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-800/60 dark:bg-slate-900">
                    {currentComparison.features.map((f) => (
                      <tr key={f.feature_key} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                        <td className="px-4 py-3 font-mono font-medium text-slate-900 dark:text-white">
                          {f.feature_key}
                          {f.unit && (
                            <span className="block text-[10px] text-slate-400 font-sans">
                              unit: {f.unit}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                          {f.baseline_value !== null ? f.baseline_value.toFixed(2) : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                          {f.current_value !== null ? f.current_value.toFixed(2) : "—"}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">
                          {formatDelta(f.absolute_delta)}
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {formatPercent(f)}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                              f.numerical_trend === "increased"
                                ? "bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300"
                                : f.numerical_trend === "decreased"
                                ? "bg-orange-50 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300"
                                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            }`}
                          >
                            {f.numerical_trend}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                            {f.clinical_interpretation}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
