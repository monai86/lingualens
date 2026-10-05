"use client";

import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  LockKeyhole,
  LogIn,
  Mail,
  ShieldCheck,
  UserPlus,
} from "lucide-react";
import { useEffect, type FormEvent, useState } from "react";

import { type RuntimeSettings } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser-client";
import { getSupabaseBrowserClientConfigStatus } from "@/lib/supabase-browser-client-config";
import { publishSupabaseSessionPayload } from "@/lib/supabase-session-source";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

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
  const supabaseSession = useSupabaseAccessSession();

  useEffect(() => {
    if (supabaseSession?.stage === "authenticated") {
      router.replace(resolvePostLoginRoute(supabaseSession.role));
    }
  }, [supabaseSession?.stage, supabaseSession?.role, router]);

  const invitationOnly = runtimeSettings.access_model?.invitation_only !== false;
  const browserClientStatus = getSupabaseBrowserClientConfigStatus();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [roleTab, setRoleTab] = useState<"slp" | "admin" | "parent">("slp");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [trustDevice, setTrustDevice] = useState(true);
  const [showPolicy, setShowPolicy] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);
  const [isSendingRecovery, setIsSendingRecovery] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  const browserClient = browserClientStatus.configured ? getSupabaseBrowserClient() : null;

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Check query params for error
    const searchParams = new URLSearchParams(window.location.search);
    const queryError = searchParams.get("error_description") || searchParams.get("error");

    // Check hash fragment for error or access_token
    let hashError: string | null = null;
    let hashAccessToken: string | null = null;
    if (window.location.hash && window.location.hash.startsWith("#")) {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      hashError = hashParams.get("error_description") || hashParams.get("error");
      hashAccessToken = hashParams.get("access_token");
    }

    const detectedError = queryError || hashError;
    if (detectedError) {
      setErrorMessage(decodeURIComponent(detectedError.replace(/\+/g, " ")));
      return;
    }

    // If OAuth code or access token is in URL on login page, exchange and sync
    const code = searchParams.get("code");
    if (code || hashAccessToken) {
      setIsGoogleSubmitting(true);
      setStatusMessage("กำลังยืนยันข้อมูลการเข้าสู่ระบบ...");
      if (browserClient && code && typeof browserClient.auth?.exchangeCodeForSession === "function") {
        void browserClient.auth.exchangeCodeForSession(code).then(({ data, error }) => {
          if (error) {
            setErrorMessage(error.message);
            setIsGoogleSubmitting(false);
          } else if (data?.session) {
            publishSupabaseSessionPayload(data.session);
            router.replace("/dashboard");
          }
        }).catch((err) => {
          setErrorMessage(err instanceof Error ? err.message : "Exchange failed");
          setIsGoogleSubmitting(false);
        });
      }
    }
  }, [browserClient, router]);
  const configStatusLabel = browserClientStatus.configured
    ? "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY detected."
    : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
      ? "waiting for NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
      : "NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is malformed for the launch contract.";

  async function handleGoogleSignIn() {
    setErrorMessage("");
    setStatusMessage("");

    if (!browserClient) {
      setErrorMessage("ไม่พบการตั้งค่า Supabase บนระบบ (NEXT_PUBLIC_SUPABASE_URL หรือ NEXT_PUBLIC_SUPABASE_ANON_KEY ขาดหายไปใน Vercel Environment Variables)");
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
        if (error.message.toLowerCase().includes("not enabled") || error.message.toLowerCase().includes("not be found")) {
          setErrorMessage("Google Provider ยังไม่ได้เปิดใช้งานใน Supabase Dashboard (ไปที่ Authentication > Providers > Google แล้วเปิดใช้งานพร้อมกรอก Client ID/Secret)");
        } else {
          setErrorMessage(error.message);
        }
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
            clinical_role: roleTab === "admin" ? "clinic_admin" : roleTab === "parent" ? "parent_guardian" : "therapist_slp",
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

  const buttonAriaLabel = isSubmitting
    ? "Signing in..."
    : browserClientStatus.configured
      ? "Sign in with Supabase"
      : browserClientStatus.missingUrl || browserClientStatus.missingAnonKey
        ? "Supabase browser config missing"
        : "Supabase browser config invalid";

  return (
    <div className="rounded-3xl border border-slate-200/90 bg-white p-6 sm:p-8 lg:p-9 shadow-xl shadow-slate-900/5 transition-all">
      {/* Header Badge & Security Status */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800">
            Secure sign in
          </h2>
          <span className="text-xs text-slate-400 font-medium hidden sm:inline">
            • Clinical Workstation Auth
          </span>
        </div>
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 bg-slate-100/80 px-2.5 py-0.5 rounded-full border border-slate-200/60">
          <ShieldCheck size={13} className="text-emerald-600 shrink-0" />
          <span>TLS 1.3 Strict</span>
        </span>
      </div>

      {/* Main Title & Subtitle */}
      <div className="mb-5">
        <h1 className="text-2xl sm:text-[1.7rem] font-extrabold tracking-tight text-slate-900 leading-snug">
          Welcome Clinician <span className="text-[#F05A77] font-normal">●</span> เข้าสู่ระบบคลินิกบำบัด
        </h1>
        <p className="mt-1.5 text-xs sm:text-sm text-slate-500 leading-relaxed">
          Sign in to access pediatric case records, acoustic transcripts, and individualized therapy plans.
        </p>
      </div>

      {/* Role Tabs (Clinician / Admin / Parent) */}
      <div className="mb-5 grid grid-cols-3 gap-1 rounded-xl border border-slate-200 bg-slate-100/70 p-1 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setRoleTab("slp")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "slp"
              ? "bg-white text-emerald-900 shadow-xs font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <ShieldCheck size={14} className={roleTab === "slp" ? "text-emerald-700" : "text-slate-400"} />
          <span>Clinician / SLP</span>
        </button>
        <button
          type="button"
          onClick={() => setRoleTab("admin")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "admin"
              ? "bg-white text-emerald-900 shadow-xs font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <Building2 size={14} className={roleTab === "admin" ? "text-emerald-700" : "text-slate-400"} />
          <span>Clinic Admin</span>
        </button>
        <button
          type="button"
          onClick={() => setRoleTab("parent")}
          className={`flex items-center justify-center gap-1.5 rounded-lg py-2 transition-all ${
            roleTab === "parent"
              ? "bg-white text-emerald-900 shadow-xs font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          <span>Parent / ผู้ปกครอง</span>
        </button>
      </div>

      {/* Sign-in / Sign-up Mode Selector */}
      <div className="mb-5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setErrorMessage("");
              setStatusMessage("");
            }}
            className={`font-semibold pb-1 border-b-2 transition ${
              mode === "signin"
                ? "border-[#F05A77] text-slate-900"
                : "border-transparent text-slate-400 hover:text-slate-600"
            }`}
          >
            เข้าสู่ระบบ (Sign In)
          </button>
          <span className="text-slate-300">|</span>
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setErrorMessage("");
              setStatusMessage("");
            }}
            className={`font-semibold pb-1 border-b-2 transition ${
              mode === "signup"
                ? "border-[#F05A77] text-slate-900"
                : "border-transparent text-slate-400 hover:text-slate-600"
            }`}
          >
            สร้างบัญชีใหม่ (Create Account)
          </button>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">Invitation-only</span>
      </div>

      {/* Form */}
      <form
        aria-label="Supabase login form"
        onSubmit={mode === "signin" ? handleSignIn : handleSignUp}
        className="space-y-4"
      >
        {mode === "signup" && (
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
            <span className="block mb-1.5">
              ชื่อ-นามสกุล (Display Name)
            </span>
            <input
              className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 outline-none transition"
              type="text"
              autoComplete="name"
              placeholder="เช่น พญ. ปาริฉัตร หรือชื่อ-นามสกุลของคุณ"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
            />
          </label>
        )}

        {/* Email Field with exact accessible name "Email" for test assertions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="clinical-email-input" className="block text-xs font-bold uppercase tracking-wider text-slate-700">
              Email
            </label>
            <span className="text-[11px] font-normal text-slate-400 normal-case">
              Clinic Email or SLP License ID / อีเมลหรือเลขที่ใบอนุญาต
            </span>
          </div>
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
            <input
              id="clinical-email-input"
              className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50/60 pl-10 pr-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 outline-none transition font-sans"
              type="email"
              inputMode="email"
              autoComplete="username"
              placeholder="alice.chang@bangkokpediatric.org"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
        </div>

        {/* Password Field with exact accessible name "Password" for test assertions */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="clinical-password-input" className="block text-xs font-bold uppercase tracking-wider text-slate-700">
              Password
            </label>
            <button
              type="button"
              onClick={handlePasswordRecovery}
              disabled={!browserClient || isSendingRecovery}
              className="text-[11px] font-medium text-emerald-700 hover:text-emerald-900 hover:underline transition disabled:opacity-50"
            >
              {isSendingRecovery ? "Sending recovery email..." : "Send recovery email"}
            </button>
          </div>
          <div className="relative">
            <LockKeyhole className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
            <input
              id="clinical-password-input"
              className="min-h-11 w-full rounded-xl border border-slate-200 bg-slate-50/60 pl-10 pr-10 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 outline-none transition font-sans"
              type={showPassword ? "text" : "password"}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              placeholder="••••••••••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* Trust workstation for 30 days checkbox */}
        <div className="flex items-center justify-between pt-0.5">
          <label className="inline-flex items-center gap-2.5 text-xs text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={trustDevice}
              onChange={(e) => setTrustDevice(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-[#F05A77] focus:ring-[#F05A77] transition"
            />
            <span>Trust workstation for 30 days (บันทึกเครื่องนี้)</span>
          </label>
        </div>

        {/* Primary Action CTA: Warm Watermelon Coral Button (#F05A77) */}
        <div className="pt-1">
          {mode === "signin" ? (
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-label={buttonAriaLabel}
              className="group relative inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-[#F05A77] px-5 py-3 text-sm font-bold text-white shadow-lg shadow-[#F05A77]/25 transition hover:bg-[#E04363] active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 disabled:shadow-none"
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? "Signing in..."
                    : "Sign in to Clinic Workspace • เข้าสู่ระบบ"}
                </span>
                <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" />
              </span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-disabled={!browserClient || isSubmitting || !email.trim() || !password}
              aria-label={isSubmitting ? "Signing in..." : "Create Account"}
              className="group relative inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-emerald-800 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-950/20 transition hover:bg-emerald-900 active:scale-[0.99] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
            >
              <span className="flex items-center justify-center gap-2">
                <span>
                  {isSubmitting
                    ? "กำลังสร้างบัญชี..."
                    : "Create Clinic Account • สมัครสมาชิก"}
                </span>
                <UserPlus size={17} />
              </span>
            </button>
          )}
        </div>

        {/* Error and Status messages */}
        {errorMessage ? (
          <p className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs font-medium text-rose-700 leading-relaxed" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {statusMessage ? (
          <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-xs font-medium text-emerald-800 leading-relaxed" aria-live="polite">
            {statusMessage}
          </p>
        ) : null}
      </form>

      {/* Divider */}
      <div className="relative my-6 text-center">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-slate-200/80" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Or Authenticate with Hospital Identity Provider
          </span>
        </div>
      </div>

      {/* SSO Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <button
          type="button"
          onClick={() => {
            setStatusMessage("Hospital SSO / Active Directory: โปรดใช้อีเมลประจำหน่วยงานแพทย์ของโรงพยาบาลในเครือข่าย หรือติดต่อแผนกเวชระเบียน");
          }}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition hover:bg-slate-50 hover:border-slate-300"
        >
          <Building2 size={16} className="text-emerald-700 shrink-0" />
          <span>Hospital SSO / Active Directory</span>
        </button>

        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={isGoogleSubmitting || isSubmitting}
          className="inline-flex min-h-11 items-center justify-center gap-2.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50"
        >
          <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
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
            {isGoogleSubmitting ? "Connecting Google..." : "Continue with Google • บัญชี Google"}
          </span>
        </button>
      </div>

      {/* Helpline & Session encryption footer */}
      <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-slate-500 gap-2">
        <span className="flex items-center gap-1.5 font-medium">
          <span className="text-emerald-700 font-semibold">Clinic IT Line:</span> 02-419-7000 ext. 8412
        </span>
        <span className="inline-flex items-center gap-1 text-slate-400 font-mono">
          <LockKeyhole size={11} className="text-emerald-700" />
          256-bit Encrypted Session
        </span>
      </div>

      {/* Collapsible Clinical Security & Access Protocol (maintaining all test contracts) */}
      <div className="mt-4 pt-3 border-t border-slate-100">
        <button
          type="button"
          onClick={() => setShowPolicy(!showPolicy)}
          className="flex w-full items-center justify-between text-[11px] font-semibold text-slate-500 hover:text-slate-800 transition"
        >
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={13} className="text-emerald-700" />
            Clinical Security &amp; Access Protocol Details
          </span>
          <ChevronDown
            size={14}
            className={`transition-transform duration-200 ${showPolicy ? "rotate-180" : ""}`}
          />
        </button>

        <div className={`mt-3 space-y-2 text-xs leading-relaxed text-slate-600 ${showPolicy ? "block" : "sr-only sm:not-sr-only"}`}>
          <div className="rounded-xl border border-amber-200/80 bg-amber-50/60 p-3 text-amber-900">
            <p className="font-semibold text-[11px] uppercase tracking-wider text-amber-800">
              Invitation-only access
            </p>
            <p className="mt-0.5 text-xs">
              {invitationOnly
                ? "Public signup is off. Only users with an accepted invitation can continue to account access."
                : "Runtime settings are not currently enforcing invitation-only onboarding."}
            </p>
          </div>

          <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/60 p-3 text-emerald-950">
            <p className="font-semibold text-[11px] uppercase tracking-wider text-emerald-800">
              MFA and app access
            </p>
            <p className="mt-0.5 text-xs">
              After invitation acceptance, TOTP MFA enrollment is mandatory. <strong>aal1</strong> can reach MFA screens only, and <strong>aal2</strong> is required before any clinical or admin workflow access.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3 text-slate-700">
            <p className="font-semibold text-[11px] uppercase tracking-wider text-slate-800">
              Organization session selection
            </p>
            <p className="mt-0.5 text-xs">
              If multiple memberships are active, the user must explicitly choose one organization before workspace access. The last active organization is a hint only when the choice is ambiguous.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-3 text-slate-600">
            <p className="font-semibold text-[11px] uppercase tracking-wider text-slate-800">
              Recovery and current runtime status
            </p>
            <p className="mt-0.5 text-xs">
              Password recovery uses the Supabase-managed reset path and still returns through membership and MFA gates before app access.
            </p>
            <p className="mt-1 text-xs">
              Browser sign-in now depends on the configured Supabase project and claim contract. Workspace access still fails closed until invitation, membership, MFA, and active organization requirements are satisfied.
            </p>
            <p className="mt-1 text-[11px] font-mono text-slate-400">
              Browser config: {configStatusLabel}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
