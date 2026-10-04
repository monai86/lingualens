"use client";

import { useRouter } from "next/navigation";
import { Building2, LockKeyhole, Mail, ShieldCheck, UserPlus, LogIn } from "lucide-react";
import { type FormEvent, useState } from "react";

import { type RuntimeSettings } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";

function resolvePostLoginRoute(role: unknown): string {
  if (role === "org_admin" || role === "platform_operator") {
    return "/settings?scope=admin";
  }

  return "/dashboard";
}

export function SupabaseLoginFormClient({
  runtimeSettings,
}: {
  runtimeSettings: RuntimeSettings;
}) {
  const router = useRouter();
  const invitationOnly = runtimeSettings.access_model?.invitation_only !== false;
  const browserClientStatus = getSupabaseBrowserClientConfigStatus();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [isSendingRecovery, setIsSendingRecovery] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const browserClient = browserClientStatus.configured ? getSupabaseBrowserClient() : null;
  const configStatusLabel = browserClientStatus.configured
    ? "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY detected."
    : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
      ? "waiting for NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
      : "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.";

  async function handleGoogleSignIn() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    if (typeof browserClient?.auth?.signInWithOAuth !== "function") {
      setErrorMessage("Google OAuth is not supported in this client configuration.");
      return;
    }

    setIsGoogleSubmitting(true);

    try {
      const { error } = await browserClient.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}/dashboard`,
        },
      });

      if (error) {
        setErrorMessage(error.message);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Google sign-in failed.");
    } finally {
      setIsGoogleSubmitting(false);
    }
  }

  async function handleSignUp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    if (typeof browserClient?.auth?.signUp !== "function") {
      setErrorMessage("Sign-up is not supported in this client configuration.");
      return;
    }

    setIsSubmitting(true);

    try {
      const { data, error } = await browserClient.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: {
            full_name: fullName.trim() || undefined,
            display_name: fullName.trim() || undefined,
          },
          emailRedirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}/dashboard`,
        },
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      if (data.session) {
        publishSupabaseSessionPayload(data.session);
        setStatusMessage("สมัครสมาชิกสำเร็จ กำลังเข้าสู่ระบบ...");
        router.push(resolvePostLoginRoute(data.session.user?.app_metadata?.role));
        router.refresh();
      } else {
        setStatusMessage("สมัครสมาชิกสำเร็จ! หากระบบต้องการยืนยันอีเมล โปรดตรวจสอบกล่องข้อความใน Gmail/อีเมลของคุณเพื่อกดยืนยันบัญชี หรือลองเข้าสู่ระบบ");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-up failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    setIsSubmitting(true);

    try {
      const { data, error } = await browserClient.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      publishSupabaseSessionPayload(data.session ?? null);
      setStatusMessage("Sign-in accepted. Routing through organization and MFA access gates.");
      router.push(resolvePostLoginRoute(data.session?.user?.app_metadata?.role));
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Sign-in failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePasswordRecovery() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("Supabase browser configuration is missing for this runtime.");
      return;
    }

    if (!email.trim()) {
      setErrorMessage("Enter the invitation email address first.");
      return;
    }

    setIsSendingRecovery(true);

    try {
      const { error } = await browserClient.auth.resetPasswordForEmail(email.trim(), {
        redirectTo: typeof window === "undefined" ? undefined : `${window.location.origin}/login`,
      });

      if (error) {
        setErrorMessage(error.message);
        return;
      }

      setStatusMessage("Recovery email sent. App access still requires accepted membership and AAL2 after reset.");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Recovery request failed.");
    } finally {
      setIsSendingRecovery(false);
    }
  }

  return (
    <div className="workspace-panel self-start p-6 sm:p-7 shadow-xs">
      {/* Header */}
      <div className="mb-5 flex items-start gap-3">
        <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-pasa-teal)]" />
        <div>
          <h2 className="text-lg font-bold text-[color:var(--color-text-strong)]">Secure sign in</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
            เข้าสู่ระบบหรือสมัครสมาชิก PasaScope ด้วย Gmail หรืออีเมลทั่วไป
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-5 flex rounded-[var(--radius-card)] border border-[color:var(--color-border)] p-1 bg-[color:var(--color-surface-muted)]">
        <button
          type="button"
          onClick={() => {
            setMode("signin");
            setErrorMessage("");
            setStatusMessage("");
          }}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-[var(--radius-card)] py-2 text-sm font-semibold transition ${
            mode === "signin"
              ? "bg-[color:var(--color-pasa-teal)] text-white shadow-xs"
              : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-strong)]"
          }`}
        >
          <LogIn size={16} aria-hidden="true" />
          เข้าสู่ระบบ (Sign In)
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("signup");
            setErrorMessage("");
            setStatusMessage("");
          }}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-[var(--radius-card)] py-2 text-sm font-semibold transition ${
            mode === "signup"
              ? "bg-[color:var(--color-pasa-teal)] text-white shadow-xs"
              : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-strong)]"
          }`}
        >
          <UserPlus size={16} aria-hidden="true" />
          สมัครสมาชิก (Sign Up)
        </button>
      </div>

      {/* Google OAuth Button */}
      <button
        type="button"
        onClick={handleGoogleSignIn}
        disabled={!browserClient || isGoogleSubmitting || isSubmitting}
        className="inline-flex min-h-11 w-full items-center justify-center gap-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-white px-4 py-2 text-sm font-medium text-[color:var(--color-text-strong)] shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            fill="#EA4335"
          />
        </svg>
        <span>
          {isGoogleSubmitting
            ? "กำลังเชื่อมต่อ Google..."
            : mode === "signup"
              ? "สมัครด้วย Google (Gmail)"
              : "เข้าสู่ระบบด้วย Google (Gmail)"}
        </span>
      </button>

      {/* Divider */}
      <div className="my-5 flex items-center gap-3">
        <div className="h-px flex-1 bg-[color:var(--color-border)]" />
        <span className="text-xs text-[color:var(--color-text-muted)]">หรือใช้อีเมลและรหัสผ่าน</span>
        <div className="h-px flex-1 bg-[color:var(--color-border)]" />
      </div>

      {/* Form */}
      <form
        aria-label="Supabase login form"
        onSubmit={mode === "signin" ? handleSignIn : handleSignUp}
      >
        {mode === "signup" && (
          <label className="mb-4 block text-sm font-medium text-[color:var(--color-text-strong)]">
            ชื่อ-นามสกุล (Display Name)
            <input
              className="mt-1.5 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3.5 py-2 text-[color:var(--color-text-strong)] placeholder:text-[color:var(--color-text-subtle)] focus:border-[color:var(--color-pasa-teal)] focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition"
              type="text"
              autoComplete="name"
              placeholder="เช่น ดร. สมชาย หรือชื่อของคุณ"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
        )}

        <label className="mb-4 block text-sm font-medium text-[color:var(--color-text-strong)]">
          Email
          <input
            className="mt-1.5 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3.5 py-2 text-[color:var(--color-text-strong)] placeholder:text-[color:var(--color-text-subtle)] focus:border-[color:var(--color-pasa-teal)] focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition"
            type="email"
            inputMode="email"
            autoComplete="username"
            placeholder="yourname@gmail.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="mb-4 block text-sm font-medium text-[color:var(--color-text-strong)]">
          Password
          <input
            className="mt-1.5 min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3.5 py-2 text-[color:var(--color-text-strong)] placeholder:text-[color:var(--color-text-subtle)] focus:border-[color:var(--color-pasa-teal)] focus:ring-2 focus:ring-[color:var(--color-focus-ring)] outline-none transition"
            type="password"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            placeholder="Enter password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {mode === "signin" ? (
          <>
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-pasa-teal)] px-4 py-2 text-sm font-semibold text-white shadow-xs transition hover:bg-[color:var(--color-pasa-teal-hover)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-border-strong)] disabled:text-[color:var(--color-text-muted)] motion-reduce:transition-none"
            >
              {isSubmitting
                ? "Signing in..."
                : browserClientStatus.configured
                  ? "Sign in with Supabase"
                  : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
                    ? "Supabase browser config missing"
                    : "Supabase browser config invalid"}
            </button>

            <button
              type="button"
              onClick={handlePasswordRecovery}
              disabled={!browserClient || isSendingRecovery}
              className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-medium text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-pasa-teal)] hover:text-[color:var(--color-pasa-teal)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-surface-muted)] disabled:text-[color:var(--color-text-subtle)] motion-reduce:transition-none"
            >
              {isSendingRecovery ? "Sending recovery email..." : "Send recovery email"}
            </button>
          </>
        ) : (
          <button
            type="submit"
            disabled={!browserClient || isSubmitting || !email.trim() || !password}
            aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-pasa-teal)] px-4 py-2 text-sm font-semibold text-white shadow-xs transition hover:bg-[color:var(--color-pasa-teal-hover)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-border-strong)] disabled:text-[color:var(--color-text-muted)] motion-reduce:transition-none"
          >
            {isSubmitting ? "กำลังสร้างบัญชี..." : "สมัครสมาชิกใหม่ (Create Account)"}
          </button>
        )}

        {errorMessage ? (
          <p className="mt-3 rounded-[var(--radius-card)] border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-3 py-2 text-sm text-[color:var(--color-danger-text)]" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {statusMessage ? (
          <p className="mt-3 rounded-[var(--radius-card)] border border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] px-3 py-2 text-sm text-[color:var(--color-success-text)]" aria-live="polite">
            {statusMessage}
          </p>
        ) : null}
      </form>

      {/* Access policy information */}
      <div className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm leading-6 text-[color:var(--color-warning-text)]">
        <div className="flex items-start gap-2">
          <Mail size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Invitation-only access</p>
            <p className="mt-1">
              {invitationOnly
                ? "Public signup is off. Only users with an accepted invitation can continue to account access."
                : "Runtime settings are not currently enforcing invitation-only onboarding."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-accent-soft)] p-3 text-sm leading-6 text-[color:var(--color-accent-strong)]">
        <div className="flex items-start gap-2">
          <LockKeyhole size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">MFA and app access</p>
            <p className="mt-1">
              After invitation acceptance, TOTP MFA enrollment is mandatory. <strong>aal1</strong> can reach MFA screens
              only, and <strong>aal2</strong> is required before any clinical or admin workflow access.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
        <div className="flex items-start gap-2">
          <Building2 size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold">Organization session selection</p>
            <p className="mt-1">
              If multiple memberships are active, the user must explicitly choose one organization before workspace
              access. The last active organization is a hint only when the choice is ambiguous.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-3 text-sm leading-6 text-[color:var(--color-text-muted)]">
        <p className="font-semibold text-[color:var(--color-text-strong)]">Recovery and current runtime status</p>
        <p className="mt-1">
          Password recovery uses the Supabase-managed reset path and still returns through membership and MFA gates
          before app access.
        </p>
        <p className="mt-2">
          Browser sign-in now depends on the configured Supabase project and claim contract. Workspace access still
          fails closed until invitation, membership, MFA, and active organization requirements are satisfied.
        </p>
        <p className="mt-2">
          Browser config:
          {" "}
          {configStatusLabel}
        </p>
      </div>
    </div>
  );
}
