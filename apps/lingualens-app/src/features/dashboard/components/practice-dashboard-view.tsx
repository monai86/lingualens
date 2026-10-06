import Link from "next/link";
import {
  Activity,
  ArrowRight,
  AudioLines,
  CheckCircle2,
  FileCheck2,
  FileCode,
  FolderOpen,
  LayoutDashboard,
  ListChecks,
  MessagesSquare,
  Printer,
  Sparkles,
} from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { LanguageProgressChart } from "@/features/dashboard/components/language-progress-chart";
import type { DashboardSummary } from "@/lib/workflow";

function consentLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function sessionStage(session: DashboardSummary["recent_sessions"][number]) {
  if (session.has_report) return "Report drafted";
  if (session.has_ml_review) return "Evidence review";
  if (session.has_features) return "Findings extracted";
  if (session.has_transcript) return "Transcript ready";
  return "Intake only";
}

export function PracticeDashboardView({ summary }: { summary: DashboardSummary }) {
  const consentCounts = Object.entries(summary.cases.consent_counts).sort((a, b) => b[1] - a[1]);
  const reviewedSessions = summary.cases.with_latest_reviewed_session;

  return (
    <div className="min-w-0 space-y-6">
      <PageHeader
        eyebrow="Clinical Overview"
        title="Dashboard"
        description="ภาพรวมเคสที่กำลังดูแล การวิเคราะห์ตัวอย่างภาษา (LSA) และความก้าวหน้าตามเกณฑ์พัฒนาการ"
        meta={[
          summary.organization_id ? `Organization: ${summary.organization_id}` : "",
          summary.generated_at ? `อัปเดต ${new Date(summary.generated_at).toLocaleDateString("th-TH")}` : "",
        ].filter(Boolean)}
      />

      {/* 4 Core Pillars Architecture & Quick Action Cards */}
      <section aria-label="Core workflow pillars" className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[color:var(--color-border)]/60">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-[color:var(--color-text-strong)]">
              ขั้นตอนการทำงาน
            </h2>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
              เข้าถึง 4 ขั้นตอนหลักของระบบเพื่อเริ่มการประเมินหรือดูผลสรุป
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/sessions/session_demo_001?view=findings"
              className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-[color:var(--color-pasa-teal)] px-4 text-xs font-bold text-white shadow-xs hover:bg-[color:var(--color-pasa-teal-hover)] transition"
            >
              <Activity className="h-3.5 w-3.5" />
              <span>ทดลองดูผลวิเคราะห์ตัวอย่าง (Demo Case)</span>
            </Link>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Pillar 1: Dashboard */}
          <div className="flex flex-col justify-between rounded-xl border border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)]/50 p-4 transition hover:shadow-xs">
            <div>
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[color:var(--color-pasa-teal)] text-white shadow-2xs">
                  <LayoutDashboard className="h-4 w-4" />
                </span>
                <span className="text-[11px] font-bold text-[color:var(--color-pasa-teal)] bg-white px-2 py-0.5 rounded-full border border-[color:var(--color-pasa-teal-border)]">
                  หน้าปัจจุบัน
                </span>
              </div>
              <h3 className="mt-3 text-sm font-bold text-[color:var(--color-text-strong)]">
                1. แดชบอร์ดภาพรวม
              </h3>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)] leading-relaxed">
                ดูสถิติเคสที่กำลังดูแล และวิเคราะห์กราฟแนวโน้มพัฒนาการทางภาษา (MLU, TTR)
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[color:var(--color-border)]/50">
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-[color:var(--color-pasa-teal)]">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>กำลังแสดงผลอยู่ด้านล่าง</span>
              </span>
            </div>
          </div>

          {/* Pillar 2: Cases */}
          <div className="flex flex-col justify-between rounded-xl border border-[color:var(--color-border)] bg-white p-4 transition hover:border-[color:var(--color-pasa-teal-border)] hover:shadow-xs">
            <div>
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[color:var(--color-surface-muted)] text-[color:var(--color-pasa-teal)]">
                  <FolderOpen className="h-4 w-4" />
                </span>
                <span className="text-[11px] font-bold text-[color:var(--color-text-subtle)] bg-[color:var(--color-surface-muted)] px-2 py-0.5 rounded-full">
                  จัดการเด็ก
                </span>
              </div>
              <h3 className="mt-3 text-sm font-bold text-[color:var(--color-text-strong)]">
                2. จัดการข้อมูลเคส
              </h3>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)] leading-relaxed">
                ค้นหาเคส ตรวจสอบอายุ เพศ ข้อมูลพัฒนาการ และหนังสือยินยอมของผู้ปกครอง
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[color:var(--color-border)]/50">
              <Link
                href="/cases"
                className="inline-flex min-h-9 items-center justify-between w-full rounded-lg bg-[color:var(--color-surface-muted)]/70 px-3 text-xs font-bold text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-pasa-teal-soft)] hover:text-[color:var(--color-pasa-teal)] transition"
              >
                <span>ไปที่หน้าเคสทั้งหมด</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {/* Pillar 3: Studio */}
          <div className="flex flex-col justify-between rounded-xl border border-[color:var(--color-border)] bg-white p-4 transition hover:border-[color:var(--color-pasa-teal-border)] hover:shadow-xs">
            <div>
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[color:var(--color-scope-coral-soft)] text-[color:var(--color-scope-coral)]">
                  <AudioLines className="h-4 w-4" />
                </span>
                <span className="text-[11px] font-bold text-[color:var(--color-scope-coral)] bg-[color:var(--color-scope-coral-soft)] px-2 py-0.5 rounded-full border border-[color:var(--color-scope-coral-border)]">
                  วิเคราะห์ LSA
                </span>
              </div>
              <h3 className="mt-3 text-sm font-bold text-[color:var(--color-text-strong)]">
                3. สตูดิโอวิเคราะห์ภาษา
              </h3>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)] leading-relaxed">
                นำเข้าไฟล์เสียง/TalkBank (.cha) คำนวณ 15 ดัชนีภาษา และสร้าง Spider Diagram
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[color:var(--color-border)]/50 flex flex-col gap-1.5">
              <Link
                href="/sessions/session_demo_001?view=findings"
                className="inline-flex min-h-9 items-center justify-between w-full rounded-lg bg-[color:var(--color-surface-muted)]/70 px-3 text-xs font-bold text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-pasa-teal-soft)] hover:text-[color:var(--color-pasa-teal)] transition"
              >
                <span>ดูกราฟใยแมงมุม (Spider)</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/sessions/session_demo_001?view=transcript"
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[color:var(--color-text-muted)] hover:text-[color:var(--color-pasa-teal)] px-1"
              >
                <FileCode className="h-3 w-3" />
                <span>เปิดห้องตรวจ TalkBank (.cha)</span>
              </Link>
            </div>
          </div>

          {/* Pillar 4: Reports */}
          <div className="flex flex-col justify-between rounded-xl border border-[color:var(--color-border)] bg-white p-4 transition hover:border-[color:var(--color-pasa-teal-border)] hover:shadow-xs">
            <div>
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[color:var(--color-warm-butter-soft)] text-[color:var(--color-pasa-teal)]">
                  <FileCheck2 className="h-4 w-4" />
                </span>
                <span className="text-[11px] font-bold text-[color:var(--color-pasa-teal)] bg-[color:var(--color-warm-butter-soft)] px-2 py-0.5 rounded-full border border-[color:var(--color-warm-butter-border)]">
                  รายงานคลินิก
                </span>
              </div>
              <h3 className="mt-3 text-sm font-bold text-[color:var(--color-text-strong)]">
                4. รายงานผล &amp; พิมพ์ PDF
              </h3>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)] leading-relaxed">
                สรุปข้อค้นพบทางภาษา ตรวจสอบผล และพิมพ์รายงานแบบมาตรฐานสำหรับอาจารย์
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[color:var(--color-border)]/50 flex flex-col gap-1.5">
              <Link
                href="/reports/preview"
                className="inline-flex min-h-9 items-center justify-between w-full rounded-lg bg-[color:var(--color-surface-muted)]/70 px-3 text-xs font-bold text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-pasa-teal-soft)] hover:text-[color:var(--color-pasa-teal)] transition"
              >
                <span className="flex items-center gap-1.5">
                  <Printer className="h-3.5 w-3.5" />
                  <span>พิมพ์ใบคะแนน / PDF</span>
                </span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/reports"
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[color:var(--color-text-muted)] hover:text-[color:var(--color-pasa-teal)] px-1"
              >
                <span>ดูประวัติรายงานทั้งหมด</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="dashboard-stats" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="dashboard-stats" className="sr-only">
          Caseload summary
        </h2>
        <StatCard
          label="Active cases"
          value={String(summary.cases.total)}
          helper={`${reviewedSessions} with a reviewed latest session`}
          icon={FolderOpen}
          tone="accent"
        />
        <StatCard
          label="Sessions"
          value={String(summary.sessions.total)}
          helper={`${summary.sessions.with_transcript} transcript · ${summary.sessions.with_features} features extracted`}
          icon={MessagesSquare}
          tone="neutral"
        />
        <StatCard
          label="Evidence review"
          value={String(summary.sessions.with_ml_review)}
          helper="Sessions with an ML decision-support review"
          icon={ListChecks}
          tone="neutral"
        />
        <StatCard
          label="Reports"
          value={String(summary.reports.total)}
          helper={summary.reports.signoff_counts["Signed Off"]
            ? `${summary.reports.signoff_counts["Signed Off"]} signed off`
            : "None signed off yet"}
          icon={FileCheck2}
          tone={summary.reports.signoff_counts["Signed Off"] ? "success" : "neutral"}
        />
      </section>

      <section aria-labelledby="progress-heading" className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[color:var(--color-border)]/60">
          <div>
            <h2 id="progress-heading" className="text-base font-bold text-[color:var(--color-text-strong)]">
              Language progress
            </h2>
            <p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
              Track a language-sample feature across each case&apos;s sessions over time.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[color:var(--color-pasa-teal-soft)] border border-[color:var(--color-pasa-teal-border)] px-2.5 py-1 text-xs font-semibold text-[color:var(--color-pasa-teal)]">
            <Activity className="h-3.5 w-3.5" />
            Linguistic Trajectory
          </span>
        </div>
        <div className="pt-4">
          <LanguageProgressChart trends={summary.feature_trends} />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section aria-labelledby="consent-heading" className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 shadow-2xs">
          <h2 id="consent-heading" className="text-base font-bold text-[color:var(--color-text-strong)] pb-3 border-b border-[color:var(--color-border)]/60">
            Consent status
          </h2>
          {consentCounts.length ? (
            <ul className="mt-4 space-y-3">
              {consentCounts.map(([status, count]) => (
                <li key={status} className="flex items-center justify-between gap-3 text-sm rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
                  <span className="flex items-center gap-2 text-[color:var(--color-text-muted)] font-medium">
                    <span className={`h-2 w-2 rounded-full ${status === "granted" ? "bg-[color:var(--color-pasa-teal)]" : "bg-[color:var(--color-warm-butter-strong)]"}`} />
                    {consentLabel(status)}
                  </span>
                  <span className="font-bold text-[color:var(--color-text-strong)]">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-[color:var(--color-text-muted)]">No cases yet.</p>
          )}
        </section>

        <section aria-labelledby="pipeline-heading" className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 shadow-2xs">
          <h2 id="pipeline-heading" className="text-base font-bold text-[color:var(--color-text-strong)] pb-1">
            Pipeline progress
          </h2>
          <p className="text-xs text-[color:var(--color-text-muted)] pb-3 border-b border-[color:var(--color-border)]/60">
            Sessions that reached each stage of the analysis pipeline.
          </p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-[color:var(--color-text-muted)] font-medium">Transcript recorded</span>
              <span className="font-bold text-[color:var(--color-text-strong)]">{summary.sessions.with_transcript}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-[color:var(--color-text-muted)] font-medium">Features extracted</span>
              <span className="font-bold text-[color:var(--color-text-strong)]">{summary.sessions.with_features}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-[color:var(--color-text-muted)] font-medium">ML decision support</span>
              <span className="font-bold text-[color:var(--color-text-strong)]">{summary.sessions.with_ml_review}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-[color:var(--color-text-muted)] font-medium">Report drafted</span>
              <span className="font-bold text-[color:var(--color-text-strong)]">{summary.sessions.with_report}</span>
            </li>
          </ul>
        </section>

        <section aria-labelledby="report-heading" className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-6 shadow-2xs">
          <h2 id="report-heading" className="text-base font-bold text-[color:var(--color-text-strong)] pb-3 border-b border-[color:var(--color-border)]/60">
            Report sign-off
          </h2>
          {summary.reports.total ? (
            <ul className="mt-4 space-y-2.5 text-sm">
              {Object.entries(summary.reports.signoff_counts)
                .sort((a, b) => b[1] - a[1])
                .map(([status, count]) => (
                  <li key={status} className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
                    <StatusBadge status={status} />
                    <span className="font-bold text-[color:var(--color-text-strong)]">{count}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-[color:var(--color-text-muted)]">No reports yet.</p>
          )}
        </section>
      </div>

      <section aria-labelledby="recent-heading" className="mt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 id="recent-heading" className="text-base font-bold text-[color:var(--color-text-strong)]">
              Recent sessions
            </h2>
            <p className="text-xs text-[color:var(--color-text-muted)]">Active pediatric assessment sessions and pipeline status</p>
          </div>
          <Link
            href="/cases"
            className="inline-flex min-h-10 items-center rounded-xl border border-[color:var(--color-border)] bg-white px-3.5 text-xs font-bold text-[color:var(--color-pasa-teal)] shadow-2xs transition hover:bg-[color:var(--color-pasa-teal-soft)] hover:border-[color:var(--color-pasa-teal-border)]"
          >
            View all cases
          </Link>
        </div>
        {summary.recent_sessions.length ? (
          <>
            <div className="overflow-hidden rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] shadow-2xs hidden md:block">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)]/60 text-left">
                    <th scope="col" className="px-5 py-3.5 font-bold text-[color:var(--color-text-strong)] text-xs uppercase tracking-wider">
                      Case
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-[color:var(--color-text-strong)] text-xs uppercase tracking-wider">
                      Date
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-[color:var(--color-text-strong)] text-xs uppercase tracking-wider">
                      Stage
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-[color:var(--color-text-strong)] text-xs uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-[color:var(--color-text-strong)] text-xs uppercase tracking-wider text-right">
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--color-border)]/60">
                  {summary.recent_sessions.map((session) => (
                    <tr key={session.session_id} className="transition-colors hover:bg-[color:var(--color-pasa-teal-soft)]/30">
                      <td className="px-5 py-4">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="font-bold text-[color:var(--color-pasa-teal)] hover:underline"
                        >
                          {session.case_label}
                        </Link>
                      </td>
                      <td className="px-5 py-4 text-xs text-[color:var(--color-text-muted)] font-mono">{session.session_date}</td>
                      <td className="px-5 py-4 text-xs font-medium text-[color:var(--color-text-strong)]">{sessionStage(session)}</td>
                      <td className="px-5 py-4">
                        <StatusBadge status={session.status} />
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="inline-flex min-h-8 items-center rounded-lg border border-[color:var(--color-border)] bg-white px-3 text-xs font-bold text-[color:var(--color-pasa-teal)] shadow-2xs hover:bg-[color:var(--color-pasa-teal-soft)] hover:border-[color:var(--color-pasa-teal-border)] transition"
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="space-y-3 md:hidden">
              {summary.recent_sessions.map((session) => (
                <li key={session.session_id} className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 shadow-2xs">
                  <div className="flex items-center justify-between gap-3">
                    <Link
                      href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                      className="font-bold text-[color:var(--color-pasa-teal)] hover:underline"
                    >
                      {session.case_label}
                    </Link>
                    <StatusBadge status={session.status} />
                  </div>
                  <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
                    {session.session_date} · {sessionStage(session)}
                  </p>
                  <Link
                    href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                    className="mt-3 inline-flex min-h-10 w-full items-center justify-center rounded-xl bg-[color:var(--color-pasa-teal-soft)] text-xs font-bold text-[color:var(--color-pasa-teal)] border border-[color:var(--color-pasa-teal-border)] transition hover:bg-[color:var(--color-pasa-teal)] hover:text-white"
                  >
                    Open session
                  </Link>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-8 text-center text-sm text-[color:var(--color-text-muted)] shadow-2xs">
            No sessions yet. Start a session from the Cases list to populate the pipeline.
          </div>
        )}
      </section>
    </div>
  );
}
