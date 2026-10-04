import { WorkflowVisual } from "@/components/app-shell";
import { PasaScopeLogo } from "@/components/pasascope-logo";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import { FileText, ShieldCheck, Waves } from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-dvh bg-[color:var(--color-page-bg)] px-4 py-8 text-[color:var(--color-text-strong)] sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100dvh-4rem)] w-full max-w-6xl items-center gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(24rem,28rem)]">
        <section className="min-w-0 space-y-6">
          <div className="flex flex-col items-start gap-4">
            <PasaScopeLogo size="lg" showSubtitle={false} priority />
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] px-3.5 py-1 text-xs font-semibold text-[color:var(--color-pasa-teal)]">
              <span className="h-2 w-2 rounded-full bg-[color:var(--color-scope-coral)]" />
              Clinical transcript workbench
            </span>
          </div>

          <div>
            <h1 className="max-w-2xl text-4xl font-extrabold leading-tight tracking-tight text-[color:var(--color-text-strong)] sm:text-5xl">
              PasaScope <span className="text-2xl font-normal text-[color:var(--color-text-muted)] sm:text-3xl">(ภาษา-สโคป)</span>
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-relaxed text-[color:var(--color-text-muted)]">
              Clinical decision-support suite for Thai pediatric speech-language therapy. Review child language samples, verify TalkBank transcript evidence, and prepare therapist-signed progress reports from one controlled workspace.
            </p>
          </div>

          <div className="grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 shadow-2xs">
              <div className="flex items-center gap-2 text-[color:var(--color-scope-coral)]">
                <Waves className="h-4 w-4 shrink-0" />
                <p className="font-semibold text-[color:var(--color-text-strong)]">Transcript first</p>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-[color:var(--color-text-muted)]">
                Line-level audio sync &amp; review before feature extraction.
              </p>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 shadow-2xs">
              <div className="flex items-center gap-2 text-[color:var(--color-pasa-teal)]">
                <FileText className="h-4 w-4 shrink-0" />
                <p className="font-semibold text-[color:var(--color-text-strong)]">Human sign-off</p>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-[color:var(--color-text-muted)]">
                Reports remain therapist-owned and attested.
              </p>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 shadow-2xs">
              <div className="flex items-center gap-2 text-[color:var(--color-pasa-teal)]">
                <ShieldCheck className="h-4 w-4 shrink-0" />
                <p className="font-semibold text-[color:var(--color-text-strong)]">Private runtime</p>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-[color:var(--color-text-muted)]">
                Consent-gated and strictly confidential.
              </p>
            </div>
          </div>

          <div>
            <WorkflowVisual />
          </div>
        </section>

        <RuntimeLoginPanelClient />
      </div>
    </main>
  );
}
