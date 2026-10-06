"use client";

import Link from "next/link";
import { Plus, LogOut } from "lucide-react";

import { PasaScopeLogo } from "@/components/pasascope-logo";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { getWorkbenchNavigation } from "@/services/navigation/workbench-navigation";

export type ShellActive = "Today" | "Dashboard" | "Cases" | "Session" | "Reports" | "Settings";

const NAV_SUBTITLES: Record<string, string> = {
  Today: "งานวันนี้",
  Dashboard: "ภาพรวมคลินิก",
  Cases: "จัดการเคส",
  Session: "ห้องวิเคราะห์",
  Reports: "รายงาน & PDF",
  Settings: "ตั้งค่า",
};

export function Sidebar({
  active,
  activeSessionId,
  activeCaseId,
  isOpen = false,
  onClose,
}: {
  active: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
  isOpen?: boolean;
  onClose?: () => void;
}) {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const showLogout =
    (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase") ||
    Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  const allNavItems = getWorkbenchNavigation(activeSessionId, activeCaseId).map((item) => ({
    ...item,
    active: item.active === active,
  }));

  // Group into Core Workflow and Workspace Management
  const coreWorkflowItems = allNavItems.filter((i) =>
    ["Dashboard", "Cases", "Session", "Reports"].includes(i.label)
  );
  const workspaceItems = allNavItems.filter((i) =>
    ["Today", "Settings"].includes(i.label)
  );

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex w-[264px] flex-col border-r border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] transition-transform duration-200 lg:static lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* Brand */}
      <div className="px-5 pb-2 pt-5">
        <PasaScopeLogo size="md" href="/dashboard" />
        <p className="mt-1.5 text-[11px] font-medium text-[color:var(--color-text-subtle)]">
          ระบบประเมินพัฒนาการทางภาษาเด็ก
        </p>
      </div>

      {/* New Session Action */}
      <div className="p-3">
        <Link
          href="/cases?intent=start-session"
          onClick={onClose}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-transparent bg-[color:var(--color-scope-coral)] px-4 py-2.5 text-sm font-bold text-white shadow-xs transition hover:bg-[color:var(--color-scope-coral-hover)] active:scale-[0.99]"
        >
          <Plus className="h-4 w-4 stroke-[2.5]" />
          <span>New Session</span>
        </Link>
      </div>

      {/* Navigation Sections */}
      <nav aria-label="Primary navigation" className="flex-1 space-y-4 overflow-y-auto px-3 py-2 text-sm">
        {/* Core Workflow Section */}
        <div>
          <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-[color:var(--color-text-subtle)]">
            ขั้นตอนหลัก (Workflow)
          </p>
          <div className="space-y-1">
            {coreWorkflowItems.map((item) => {
              const Icon = item.icon;
              const sub = NAV_SUBTITLES[item.label] ?? "";
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  aria-current={item.active ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3.5 py-2.5 transition ${
                    item.active
                      ? "bg-[color:var(--color-pasa-teal-soft)] font-bold text-[color:var(--color-pasa-teal)] border border-[color:var(--color-pasa-teal-border)] shadow-2xs"
                      : "text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface)] hover:text-[color:var(--color-text-strong)] font-medium"
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      item.active ? "text-[color:var(--color-pasa-teal)] stroke-[2.2]" : "text-[color:var(--color-text-subtle)]"
                    }`}
                  />
                  <span className="flex-1">{item.label}</span>
                  {sub ? (
                    <span
                      aria-hidden="true"
                      className={`text-[11px] font-normal transition ${
                        item.active
                          ? "text-[color:var(--color-pasa-teal)] opacity-80"
                          : "text-[color:var(--color-text-subtle)] opacity-60"
                      }`}
                    >
                      {sub}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Workspace Management Section */}
        <div>
          <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-[color:var(--color-text-subtle)]">
            การจัดการ (Management)
          </p>
          <div className="space-y-1">
            {workspaceItems.map((item) => {
              const Icon = item.icon;
              const sub = NAV_SUBTITLES[item.label] ?? "";
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  aria-current={item.active ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3.5 py-2.5 transition ${
                    item.active
                      ? "bg-[color:var(--color-pasa-teal-soft)] font-bold text-[color:var(--color-pasa-teal)] border border-[color:var(--color-pasa-teal-border)] shadow-2xs"
                      : "text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface)] hover:text-[color:var(--color-text-strong)] font-medium"
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      item.active ? "text-[color:var(--color-pasa-teal)] stroke-[2.2]" : "text-[color:var(--color-text-subtle)]"
                    }`}
                  />
                  <span className="flex-1">{item.label}</span>
                  {sub ? (
                    <span
                      aria-hidden="true"
                      className={`text-[11px] font-normal transition ${
                        item.active
                          ? "text-[color:var(--color-pasa-teal)] opacity-80"
                          : "text-[color:var(--color-text-subtle)] opacity-60"
                      }`}
                    >
                      {sub}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* User / Settings / Logout Footer */}
      <div className="space-y-1 border-t border-[color:var(--color-border)] p-3">
        {showLogout ? (
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3.5 py-2 text-sm text-[color:var(--color-text-muted)] transition hover:bg-[color:var(--color-surface)] hover:text-[color:var(--color-scope-coral)] font-medium"
          >
            <LogOut className="h-4 w-4 text-[color:var(--color-text-subtle)]" />
            <span>Log out</span>
          </button>
        ) : null}

        <div className="px-3.5 py-1 text-[11px] text-[color:var(--color-text-subtle)]">
          <span>PasaScope v1.7.0</span>
        </div>
      </div>
    </aside>
  );
}
