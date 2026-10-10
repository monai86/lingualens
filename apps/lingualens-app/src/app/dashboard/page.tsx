import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { PracticeDashboardView } from "@/features/dashboard/components/practice-dashboard-view";
import { getDashboardSummary, type DashboardSummary } from "@/lib/workflow";

// The practice summary is live backend data — never statically cache it.
export const dynamic = "force-dynamic";

const FALLBACK_DASHBOARD_SUMMARY: DashboardSummary = {
  organization_id: "clinic_local",
  generated_at: new Date().toISOString(),
  cases: {
    total: 3,
    consent_counts: {
      granted: 3,
    },
    with_latest_reviewed_session: 3,
  },
  sessions: {
    total: 3,
    status_counts: {
      completed: 3,
    },
    with_transcript: 3,
    with_features: 3,
    with_ml_review: 3,
    with_report: 2,
  },
  reports: {
    total: 3,
    signoff_counts: {
      "Signed Off": 2,
      "Needs Review": 1,
    },
  },
  recent_sessions: [
    {
      session_id: "session_demo_001",
      case_id: "case_demo_001",
      case_label: "น้องกานต์ (4 ปี 2 เดือน) · C-1024",
      session_date: "2026-06-12",
      status: "Needs Review",
      has_transcript: true,
      has_features: true,
      has_ml_review: true,
      has_report: true,
    },
    {
      session_id: "session_demo_002",
      case_id: "case_demo_002",
      case_label: "น้องฟ้าใส (3 ปี 8 เดือน) · C-1031",
      session_date: "2026-06-10",
      status: "Signed Off",
      has_transcript: true,
      has_features: true,
      has_ml_review: true,
      has_report: true,
    },
    {
      session_id: "session_demo_003",
      case_id: "case_demo_003",
      case_label: "น้องภูผา (5 ปี 1 เดือน) · C-1045",
      session_date: "2026-06-08",
      status: "Draft",
      has_transcript: true,
      has_features: true,
      has_ml_review: false,
      has_report: false,
    },
  ],
  feature_trends: {
    features: [
      { key: "mlu_words", label: "ความยาวประโยคเฉลี่ย (MLU-words)", unit: "words/utt" },
      { key: "type_token_ratio", label: "ความหลากหลายคำศัพท์ (TTR)", unit: "ratio" },
      { key: "responsiveness_rate", label: "อัตราการตอบสนองต่อคู่สนทนา", unit: "%" },
    ],
    cases: [
      {
        case_id: "case_demo_001",
        case_label: "น้องกานต์ (C-1024)",
        points: [
          { session_id: "session_demo_001_s1", session_date: "2026-04-10", values: { mlu_words: 2.1, type_token_ratio: 0.42, responsiveness_rate: 65 } },
          { session_id: "session_demo_001_s2", session_date: "2026-05-15", values: { mlu_words: 2.8, type_token_ratio: 0.49, responsiveness_rate: 74 } },
          { session_id: "session_demo_001", session_date: "2026-06-12", values: { mlu_words: 3.5, type_token_ratio: 0.58, responsiveness_rate: 85 } },
        ],
        reference: {
          age_band: "48-60m",
          task_type: "free_play",
          features: {
            mlu_words: { q1: 2.5, median: 3.4, q3: 4.2 },
            type_token_ratio: { q1: 0.45, median: 0.55, q3: 0.65 },
            responsiveness_rate: { q1: 70, median: 80, q3: 92 },
          },
        },
      },
    ],
  },
};

export default async function DashboardPage() {
  let summary;
  try {
    summary = await getDashboardSummary();
  } catch {
    summary = undefined;
  }

  return (
    <AppShell active="Dashboard">
      {summary ? (
        <PracticeDashboardView summary={summary} />
      ) : (
        <main className="mx-auto flex min-h-dvh w-full max-w-4xl items-center px-4 py-10 sm:px-6">
          <section
            className="w-full rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-8 shadow-xs text-[color:var(--color-text-strong)]"
            role="alert"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--color-warm-butter-border)] bg-[color:var(--color-warm-butter-soft)] px-3 py-1 text-xs font-semibold text-[color:var(--color-warning-text)]">
              <span>Backend Offline · หรือเซิร์ฟเวอร์กำลังเริ่มต้น</span>
            </div>
            <p className="sr-only">Dashboard unavailable</p>
            <h1 className="mt-3 text-2xl sm:text-3xl font-bold text-[color:var(--color-text-strong)]">
              Practice summary could not be loaded
            </h1>
            <p className="mt-2 text-sm leading-6 text-[color:var(--color-text-muted)]">
              The backend summary endpoint did not respond. เซิร์ฟเวอร์ API หลังบ้านอาจยังไม่ได้รัน
              ท่านสามารถทดลองใช้งานเคสสาธิต (Demo Cases) หรือสตูดิโอวิเคราะห์ได้ทันที
            </p>

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href="/today"
                className="inline-flex min-h-11 items-center rounded-xl bg-[color:var(--color-pasa-teal)] px-5 text-sm font-semibold text-white transition hover:bg-[color:var(--color-pasa-teal-hover)]"
              >
                Back to Today
              </Link>
              <Link
                href="/cases"
                className="inline-flex min-h-11 items-center rounded-xl border border-[color:var(--color-border)] bg-white px-5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:bg-[color:var(--color-surface-muted)]"
              >
                ดูรายการเคสทั้งหมด (Cases)
              </Link>
              <Link
                href="/sessions/session_demo_001?view=findings"
                className="inline-flex min-h-11 items-center rounded-xl border border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] px-5 text-sm font-semibold text-[color:var(--color-pasa-teal)] transition hover:bg-[color:var(--color-pasa-teal)] hover:text-white"
              >
                เปิดสตูดิโอวิเคราะห์ (Assessment Studio)
              </Link>
            </div>
          </section>
        </main>
      )}
    </AppShell>
  );
}
