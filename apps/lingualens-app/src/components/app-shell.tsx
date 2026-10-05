"use client";

import { useState, useEffect, ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Menu, X } from "lucide-react";

import { Sidebar, type ShellActive } from "@/components/sidebar";
import { BottomNav } from "@/components/bottom-nav";
import { RightRail } from "@/components/right-rail";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseWorkspaceAccessGate } from "@/components/supabase-workspace-access-gate";
import { WorkspaceAccessGate } from "@/components/workspace-access-gate";
import { ConfirmedRuntimeSettingsProvider } from "@/lib/confirmed-runtime-settings";
import { loadMockAccessSession } from "@/lib/mock-access-session";
import { loadOrRestoreSupabaseAccessSession, useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export type { ShellActive };

export function AppShell({
  children,
  active = "Today",
  activeSessionId,
  activeCaseId,
  rightRail,
}: {
  children: ReactNode;
  active?: ShellActive;
  activeSessionId?: string;
  activeCaseId?: string;
  rightRail?: ReactNode;
}) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const runtimeSettings = useRuntimeSettings();
  const confirmedRuntimeSettings = runtimeSettings.status === "success" ? runtimeSettings.data : null;
  const session = typeof window !== "undefined" ? loadMockAccessSession() : null;
  const supabaseSession = useSupabaseAccessSession();

  useEffect(() => {
    // If returning from an OAuth callback (?code=... or #access_token=...), wait for Supabase to exchange token
    if (typeof window !== "undefined") {
      const search = window.location.search;
      const hash = window.location.hash;
      if (search.includes("code=") || hash.includes("access_token=")) {
        return;
      }
    }

    // If user is completely unauthenticated on the client, redirect directly to /login
    const restored = loadOrRestoreSupabaseAccessSession();
    const mock = loadMockAccessSession();
    if (!mock && (!restored || restored.stage === "signed_out")) {
      router.replace("/login");
    }
  }, [router, supabaseSession]);

  const gateRequired = confirmedRuntimeSettings?.auth_mode === "mock" && session?.aal === "aal1";
  const mfaRequired = confirmedRuntimeSettings?.access_model?.required_app_aal === "aal2";
  const hasValidAal = mfaRequired
    ? supabaseSession?.aal === "aal2"
    : Boolean(supabaseSession?.aal && (supabaseSession.aal === "aal1" || supabaseSession.aal === "aal2"));
  const supabaseGateRequired =
    confirmedRuntimeSettings?.auth_mode === "supabase" &&
    !(
      supabaseSession?.stage === "authenticated" &&
      supabaseSession.organizationId &&
      hasValidAal
    );

  if (runtimeSettings.status !== "success") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-xl text-slate-900" role="alert">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Runtime verification required
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900">Workspace access is blocked</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Authentication mode and access requirements must be confirmed before workspace content can load.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/login"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-emerald-700 px-5 text-sm font-semibold text-white transition hover:bg-emerald-800"
            >
              Go to login • เข้าสู่ระบบ
            </Link>
          </div>
        </section>
      </main>
    );
  }

  if (supabaseGateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <SupabaseWorkspaceAccessGate>{children}</SupabaseWorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  if (gateRequired) {
    return (
      <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
        <SupabaseAuthRuntimeBridge />
        <WorkspaceAccessGate>{children}</WorkspaceAccessGate>
      </ConfirmedRuntimeSettingsProvider>
    );
  }

  return (
    <ConfirmedRuntimeSettingsProvider value={runtimeSettings.data}>
      <SupabaseAuthRuntimeBridge />
      <div className="flex h-screen w-full overflow-hidden bg-[color:var(--color-page-bg)] font-sans text-[color:var(--color-text-strong)]">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-slate-900 focus:shadow-md"
        >
          Skip to main content
        </a>

        {/* Mobile Backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <Sidebar
          active={active}
          activeSessionId={activeSessionId}
          activeCaseId={activeCaseId}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
          {/* Mobile Header Top Bar */}
          <header className="flex h-14 items-center justify-between border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 lg:hidden">
            <button
              type="button"
              aria-label="Toggle navigation"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="grid h-11 w-11 place-items-center rounded-md text-[color:var(--color-text-muted)] transition hover:bg-[color:var(--color-surface)]"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <PasaScopeLogo size="sm" showSubtitle={false} href="/dashboard" />
            <div className="w-11" />
          </header>

          <main id="main-content" className="min-w-0 flex-1 overflow-y-auto bg-[color:var(--color-page-bg)] p-4 max-md:pb-44 md:p-6">
            <div className="flex items-start gap-6">
              <div className="min-w-0 flex-1">{children}</div>
              {rightRail ? <RightRail>{rightRail}</RightRail> : null}
            </div>
          </main>

          {/* Mobile bottom navigation (hidden at md+ via .mobile-bottom-nav) */}
          <BottomNav active={active} activeSessionId={activeSessionId} activeCaseId={activeCaseId} />
        </div>
      </div>
    </ConfirmedRuntimeSettingsProvider>
  );
}

export function WorkflowVisual() {
  return (
    <div className="p-4 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] shadow-xs">
      <Image src="/clinical-workflow.svg" width={960} height={320} alt="Case to transcript review to signed report workflow" priority />
    </div>
  );
}
