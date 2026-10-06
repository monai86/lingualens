"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ExternalLink, Printer } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { Skeleton } from "@/components/skeleton";
import { SafetyNote, WorkspacePanel } from "@/components/workbench-ui";
import { ReportsLibrary } from "@/features/reports/components/reports-library";
import { listBackendReports, type BackendReport } from "@/lib/workflow";

export function ReportsWorkspaceClient() {
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [reports, setReports] = useState<BackendReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const loaded = await listBackendReports();
        if (cancelled) return;
        setReports(loaded);
        setBackendUnavailable(false);
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setBackendUnavailable]);

  return (
    <div className="space-y-5">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <header className="workspace-panel flex flex-col gap-4 p-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-ink">Reports</h1>
          <p className="mt-2 max-w-[70ch] text-[color:var(--color-text-muted)]">
            รายการร่างรายงานผลการประเมินทางคลินิก และประวัติรายงานที่ได้รับการรับรองแล้ว
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/reports/preview"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[color:var(--color-pasa-teal)] px-4 text-sm font-semibold text-white shadow-xs hover:bg-[color:var(--color-pasa-teal-hover)] transition"
          >
            <Printer size={16} aria-hidden="true" />
            <span>พิมพ์รายงาน A4 / PDF</span>
          </Link>
          <Link
            href="/cases?intent=start-session"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm font-semibold text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-surface-muted)] transition"
          >
            <span>Start session</span>
            <ExternalLink size={16} aria-hidden="true" />
          </Link>
        </div>
      </header>

      {loading && !backendUnavailable ? (
        <WorkspacePanel className="p-5" role="status" aria-live="polite">
          <span className="sr-only">Loading persisted reports…</span>
          <Skeleton className="h-6 w-2/5" />
          <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-hidden="true">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-16" />)}
          </div>
          <div className="mt-5 space-y-3" aria-hidden="true">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-14 w-full" />)}
          </div>
        </WorkspacePanel>
      ) : null}

      {!loading && !backendUnavailable && reports.length === 0 ? (
        <WorkspacePanel className="p-6">
          <p className="font-semibold text-ink text-base">ยังไม่มีประวัติรายงานที่บันทึกไว้ (No persisted reports yet)</p>
          <p className="mt-1 text-sm text-slate-600">
            ท่านสามารถสร้างรายงานใหม่จากการตรวจประเมิน หรือเปิดดูตัวอย่างใบคะแนนและพิมพ์ออก PDF ได้ทันที
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Link
              href="/reports/preview"
              className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[color:var(--color-pasa-teal)] px-4 text-sm font-semibold text-white shadow-xs hover:bg-[color:var(--color-pasa-teal-hover)] transition"
            >
              <Printer size={16} />
              <span>เปิดดูตัวอย่างใบคะแนน (Preview Clinical Report)</span>
            </Link>
            <Link href="/cases?intent=start-session" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[color:var(--color-border)] bg-white px-4 text-sm font-semibold text-[color:var(--color-text-strong)] hover:bg-[color:var(--color-surface-muted)] transition">
              <span>Choose a case</span>
              <ExternalLink size={16} aria-hidden="true" />
            </Link>
          </div>
        </WorkspacePanel>
      ) : null}

      {!loading && !backendUnavailable && reports.length > 0 ? <ReportsLibrary reports={reports} /> : null}

      <SafetyNote>Reports remain export-eligible only after therapist review and sign-off. Stale drafts require regeneration.</SafetyNote>
    </div>
  );
}
