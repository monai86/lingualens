import { PasaScopeLogo } from "@/components/pasascope-logo";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import {
  Activity,
  CheckCircle2,
  FileAudio,
  Lock,
  Mic2,
  Radio,
  Shield,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-dvh bg-gradient-to-br from-[#f2f7f4] via-[#edf3f0] to-[#e4ede8] text-[color:var(--color-text-strong)] flex flex-col justify-between p-3 sm:p-5 lg:p-7 selection:bg-emerald-500/20 font-sans">
      {/* 1. TOP BAR HEADER */}
      <header className="mx-auto w-full max-w-7xl flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200/60">
        <div className="flex items-center gap-3">
          <PasaScopeLogo size="sm" showSubtitle={false} priority />
          <div className="hidden sm:block h-4 w-px bg-slate-300/80" />
          <span className="text-xs font-semibold text-emerald-900 tracking-tight">
            Pediatric Speech &amp; Language Research Platform
          </span>
          <span className="sr-only">Clinical transcript workbench</span>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-[11px] font-medium text-slate-600">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/80 border border-slate-200/80 px-2.5 py-1 shadow-2xs">
            <ShieldCheck size={13} className="text-emerald-700" />
            <span>Research &amp; Clinical Prototype</span>
          </span>

          <span className="hidden lg:inline-flex items-center gap-1.5 rounded-full bg-white/80 border border-slate-200/80 px-2.5 py-1 shadow-2xs">
            <Lock size={13} className="text-emerald-700" />
            <span>End-to-End De-identified Data Boundary</span>
          </span>

          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-900/10 border border-emerald-800/20 px-2.5 py-1 text-emerald-900 font-semibold shadow-2xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
            </span>
            <span>PasaScope Workbench v1.7</span>
          </span>
        </div>
      </header>

      {/* 2. CENTERPIECE CONTAINER (2-COLUMN GRID) */}
      <div className="mx-auto my-5 sm:my-7 w-full max-w-7xl grid grid-cols-1 lg:grid-cols-[1.12fr_1fr] gap-6 lg:gap-8 items-stretch">
        
        {/* LEFT CARD: Dark Forest Pine Hero Card */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#12362c] via-[#0d2a22] to-[#071c16] text-white p-6 sm:p-8 lg:p-9 shadow-2xl shadow-emerald-950/25 border border-emerald-800/40 flex flex-col justify-between">
          {/* Ambient Lighting Gradients */}
          <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-[#F05A77]/15 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-emerald-400/15 blur-3xl" />

          <div className="relative z-10 space-y-6">
            {/* Header pill tags */}
            <div className="flex items-center justify-between gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-950/60 backdrop-blur-sm px-3.5 py-1.5 text-xs font-semibold text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-[#F05A77] shadow-[0_0_8px_#F05A77]" />
                <span>ภาษา-สโคป • Thai Speech &amp; Language Assessment</span>
              </div>

              <div className="inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-950/50 p-0.5 text-xs font-medium">
                <span className="rounded-full bg-emerald-700/80 px-2.5 py-0.5 text-white font-bold">TH</span>
                <span className="px-2.5 py-0.5 text-emerald-300/70 hover:text-white cursor-pointer transition">EN</span>
              </div>
            </div>

            {/* Hero Title & Subheading */}
            <div>
              <h2 className="text-3xl sm:text-4xl lg:text-[2.6rem] font-extrabold tracking-tight leading-[1.18] text-white">
                Empowering every child&apos;s voice through intelligent analytics
              </h2>
              <p className="mt-3 text-sm sm:text-base leading-relaxed text-emerald-100/90 font-light max-w-xl">
                ระบบสนับสนุนการประเมินพัฒนาการทางภาษาสำหรับนักอรรถบำบัด พร้อมการตรวจจับลักษณะเสียงและการสื่อสารตามธรรมชาติ
              </p>
            </div>

            {/* ACOUSTIC WAVEFORM & MLU WIDGET */}
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/50 backdrop-blur-md p-4 sm:p-5 shadow-inner">
              <div className="flex items-center justify-between text-xs font-semibold text-emerald-300 pb-2.5 border-b border-emerald-800/40">
                <div className="flex items-center gap-2">
                  <Activity size={15} className="text-[#F05A77]" />
                  <span>Acoustic Waveform &amp; Language Sample Analysis (LSA)</span>
                </div>
                <div className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-200 bg-emerald-900/60 px-2 py-0.5 rounded-full border border-emerald-700/50">
                  <span className="font-semibold text-white">MLU-w Tracker</span>
                </div>
              </div>

              {/* Stylized soundwave visualizer */}
              <div className="py-3.5 flex items-center justify-between gap-1 sm:gap-1.5 h-16 sm:h-20">
                {[
                  { h: 35, c: "#34D399" },
                  { h: 55, c: "#34D399" },
                  { h: 25, c: "#F05A77" },
                  { h: 70, c: "#F05A77" },
                  { h: 90, c: "#F05A77" },
                  { h: 45, c: "#34D399" },
                  { h: 80, c: "#34D399" },
                  { h: 60, c: "#F05A77" },
                  { h: 100, c: "#F05A77" },
                  { h: 85, c: "#34D399" },
                  { h: 65, c: "#34D399" },
                  { h: 40, c: "#34D399" },
                  { h: 95, c: "#F05A77" },
                  { h: 75, c: "#F05A77" },
                  { h: 50, c: "#34D399" },
                  { h: 85, c: "#34D399" },
                  { h: 30, c: "#34D399" },
                  { h: 60, c: "#F05A77" },
                  { h: 70, c: "#F05A77" },
                  { h: 40, c: "#34D399" },
                  { h: 20, c: "#34D399" },
                ].map((bar, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-full transition-all duration-300"
                    style={{
                      height: `${bar.h}%`,
                      backgroundColor: bar.c,
                      opacity: 0.85,
                    }}
                  />
                ))}
              </div>

              <div className="flex items-center justify-between text-xs text-emerald-300/80 pt-2 border-t border-emerald-800/40">
                <span className="inline-flex items-center gap-1 font-mono">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Thai Particles &amp; Turn-Taking Metrics
                </span>
                <span className="inline-flex items-center gap-1 font-mono text-emerald-300 font-semibold">
                  <CheckCircle2 size={12} />
                  Clinician Review Mandatory
                </span>
              </div>
            </div>

            {/* 3 FEATURE HIGHLIGHTS */}
            <div className="grid gap-3 sm:grid-cols-3 text-xs">
              <div className="rounded-xl border border-emerald-700/30 bg-emerald-950/40 p-3.5 backdrop-blur-xs">
                <div className="flex items-center gap-2 text-[#F05A77] font-bold">
                  <Radio size={14} className="shrink-0" />
                  <span>Audio &amp; LSA</span>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-emerald-100/75 font-light">
                  ประมวลผลบทสนทนาจากการเล่นและกิจกรรม เพื่อสกัดตัวชี้วัดความคล่อง
                </p>
              </div>

              <div className="rounded-xl border border-emerald-700/30 bg-emerald-950/40 p-3.5 backdrop-blur-xs">
                <div className="flex items-center gap-2 text-emerald-300 font-bold">
                  <Mic2 size={14} className="shrink-0" />
                  <span>Thai Pragmatics</span>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-emerald-100/75 font-light">
                  วิเคราะห์คำอนุภาค คำลงท้าย และความหลากหลายของคำศัพท์ (TTR)
                </p>
              </div>

              <div className="rounded-xl border border-emerald-700/30 bg-emerald-950/40 p-3.5 backdrop-blur-xs">
                <div className="flex items-center gap-2 text-emerald-300 font-bold">
                  <Shield size={14} className="shrink-0" />
                  <span>Consent &amp; Privacy</span>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-emerald-100/75 font-light">
                  จัดการความยินยอมผู้ปกครอง ปลอดการระบุตัวตนและเข้ารหัสข้อมูล
                </p>
              </div>
            </div>
          </div>

          {/* Clinical Disclaimer Footer */}
          <div className="relative z-10 mt-6 pt-5 border-t border-emerald-800/40 flex items-center gap-3.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-emerald-700 bg-emerald-950 text-emerald-300 text-xs font-bold">
              <ShieldCheck size={16} />
            </div>

            <div className="text-xs">
              <p className="font-bold text-white">
                Clinical Research &amp; Decision Support Prototype
              </p>
              <p className="text-[11px] text-emerald-200/80">
                ระบบนี้ไม่ใช่เครื่องมือวินิจฉัยโรค ผลการวิเคราะห์ต้องได้รับการรับรองจากผู้เชี่ยวชาญก่อนนำไปใช้
              </p>
            </div>
          </div>
        </section>

        {/* RIGHT CARD: Crisp White Clinical Auth Card */}
        <section className="flex flex-col justify-center">
          <RuntimeLoginPanelClient />
        </section>
      </div>

      {/* 3. BOTTOM COMPLIANCE & TRUST BAR */}
      <footer className="mx-auto w-full max-w-7xl pt-4 border-t border-slate-200/60 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white/70 backdrop-blur-xs p-3.5 shadow-2xs">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <FileAudio size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800">
                CHAT / TalkBank Compatible
              </p>
              <p className="text-[11px] text-slate-500">
                ส่งออกและวิเคราะห์ไฟล์ตามมาตรฐานสากล TalkBank / CHILDES
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white/70 backdrop-blur-xs p-3.5 shadow-2xs">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-[#F05A77]">
              <Sparkles size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800">
                Decision Support Assistance
              </p>
              <p className="text-[11px] text-slate-500">
                สนับสนุนการตัดสินใจและร่างข้อความรายงานทางคลินิก
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white/70 backdrop-blur-xs p-3.5 shadow-2xs">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
              <ShieldCheck size={18} />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-800">
                De-identification Invariants
              </p>
              <p className="text-[11px] text-slate-500">
                ไม่เก็บชื่อ-นามสกุล หรือข้อมูลระบุตัวตนเด็กในระบบวิเคราะห์
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 pt-1">
          <p>
            PasaScope Research Platform
          </p>
          <p className="text-[11px] text-slate-400">
            &copy; 2026 PasaScope. De-identified clinical research prototype.
          </p>
          <div className="flex items-center gap-3 text-[11px] font-medium text-slate-500">
            <span>Research &amp; Education Boundary</span>
            <span>•</span>
            <span>Non-Diagnostic</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
