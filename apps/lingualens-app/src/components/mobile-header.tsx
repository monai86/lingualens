import Link from "next/link";
import { LogOut, Menu } from "lucide-react";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { ActiveOrganizationSummary } from "@/components/active-organization-summary";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";

export function MobileHeader({ title = "pasascope" }: { title?: string }) {
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const showLogout = (runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase")
    || Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out");

  async function handleLogout() {
    await signOutSupabaseWorkspace();
    window.location.assign("/");
  }

  return (
    <header className="grid gap-2 pb-3 md:hidden">
      <div className="flex items-center justify-between gap-3">
        <PasaScopeLogo size="sm" href="/dashboard" subtitle="ภาษา-สโคป • Decision Support" />

        <div className="flex items-center gap-2">
          {showLogout ? (
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] px-3 text-sm font-semibold text-[color:var(--color-text-strong)]"
            >
              <LogOut size={16} aria-hidden="true" />
              Log out
            </button>
          ) : null}
          <button
            type="button"
            className="grid h-11 w-11 place-items-center rounded-[var(--radius-card)] border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)]"
            aria-label="Open navigation"
          >
            <Menu size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
      <ActiveOrganizationSummary compact />
    </header>
  );
}
