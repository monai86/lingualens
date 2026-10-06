import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { CheckCircle2, ClipboardPaste, FileText, ShieldCheck, Sparkles, UploadCloud } from "lucide-react";

import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { SessionIntakeSource } from "@/features/sessions/intake/session-intake-view";
import { GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";
import type { WorkflowSource, WorkflowState } from "@/lib/workflow";

export function sourceSummaryLabel(source: SessionIntakeSource): string {
  if (source === "recording") return "Browser recording";
  if (source === "audio") return "Audio upload";
  if (source === "cha") return "CHAT file upload";
  return "Pasted transcript";
}

export function capitalizeWord(value: string) {
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}

export function workflowSessionHref(view: "intake" | "transcript" | "findings" | "report", state: WorkflowState, reportId?: string) {
  return resolveSessionHref(view, state.backendSessionId ?? state.backendTranscriptSessionId ?? state.sessionId, {
    caseId: state.caseId,
    transcriptId: state.backendTranscriptId,
    reportId: reportId ?? state.backendReportId ?? state.reportId,
  });
}

export function isTranscriptUnlocked(state: WorkflowState) {
  return state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
}


export function Field({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`.trim()}>
      {children}
    </div>
  );
}

export function SourceChoiceButton({
  label,
  active,
  icon: Icon,
  onClick
}: {
  label: string;
  active: boolean;
  icon: LucideIcon;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex min-h-24 flex-col items-start justify-between rounded-[var(--radius-card)] border px-4 py-4 text-left transition motion-reduce:transition-none ${
        active
          ? "border-[color:var(--color-accent-subtle)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]"
          : "border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-strong)]"
      }`}
      aria-pressed={active}
    >
      <Icon size={20} aria-hidden="true" />
      <span className="text-sm font-semibold">{label}</span>
    </button>
  );
}

export function ReviewSummaryCard({
  title,
  rows
}: {
  title: string;
  rows: Array<{ label: string; value: string }>;
}) {
  return (
    <WorkspacePanel className="p-5">
      <h3 className="font-bold text-ink">{title}</h3>
      <dl className="mt-4 space-y-3">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="grid gap-1 border-b border-line/70 pb-3 last:border-b-0 last:pb-0">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{row.label}</dt>
            <dd className="text-sm text-slate-700">{row.value}</dd>
          </div>
        ))}
      </dl>
    </WorkspacePanel>
  );
}


const SAMPLE_THAI_TRANSCRIPT = [
  "@Begin",
  "@Languages:\ttha",
  "@Participants:\tCHI น้องมิน Target_Child, THER นักบำบัด Investigator",
  "*THER:\tวันนี้หนูเล่นอะไรมาบ้างครับ?",
  "*CHI:\tหนู เล่น รถ ไฟ คัน ใหญ่ สี แดง ครับ.",
  "*THER:\tรถไฟวิ่งเร็วไหมนะ?",
  "*CHI:\tวิ่ง เร็ว มาก เลย ครับ.",
  "*THER:\tในรถไฟมีใครนั่งอยู่บ้าง?",
  "*CHI:\tมี คุณ พ่อ คุณ แม่ แล้ว ก็ น้อง มิน ครับ.",
  "*THER:\tเก่งมากครับ แล้วจะไปเที่ยวที่ไหนกันต่อ?",
  "*CHI:\tไป เที่ยว สวน สัตว์ ดู ช้าง ครับ.",
  "@End"
].join("\n");

const SAMPLE_ENG_TRANSCRIPT = [
  "@Begin",
  "@Languages:\teng",
  "@Participants:\tCHI Target_Child, THER Investigator",
  "*THER:\tWhat do you see?",
  "*CHI:\tI see a big blue block.",
  "*THER:\tWhat color is it?",
  "*CHI:\tIt is blue.",
  "*THER:\tCan you ask me a question?",
  "*CHI:\tWhat color do you like?",
  "@End"
].join("\n");

export function SourceInputPanel({
  mode,
  draftTranscript,
  busy,
  error,
  warnings,
  validationIssues,
  onDraftChange,
  onChaFile,
  onAudioUpload,
  onTranscriptSubmit
}: {
  mode?: string;
  draftTranscript: string;
  busy: boolean;
  error: string;
  warnings: string[];
  validationIssues: string[];
  onDraftChange: (value: string) => void;
  onChaFile: (file: File) => void;
  onAudioUpload: () => void;
  onTranscriptSubmit: (source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">) => void;
}) {
  if (mode === "audio") {
    return (
      <WorkspacePanel className="p-5">
        <h2 className="font-bold text-ink">Upload audio</h2>
        <p className="mt-2 text-sm text-slate-600">Experimental only. This creates a session record, but real ASR is not implemented in this step.</p>
        <PrimaryActionButton icon={UploadCloud} className="mt-4 w-full" onClick={onAudioUpload} disabled={busy}>
          Mark audio upload as experimental
        </PrimaryActionButton>
      </WorkspacePanel>
    );
  }

  if (mode === "cha" || mode === "paste") {
    const source = mode === "cha" ? "cha-upload" : "paste-transcript";
    return (
      <WorkspacePanel className="p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {mode === "cha" ? <FileText size={22} aria-hidden="true" className="text-blossom" /> : <ClipboardPaste size={22} aria-hidden="true" className="text-aqua" />}
            <h2 className="font-bold text-ink">{mode === "cha" ? "Upload .cha" : "Paste transcript"}</h2>
          </div>
          {mode === "paste" && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-500 font-medium">Quick Demo:</span>
              <button
                type="button"
                onClick={() => onDraftChange(SAMPLE_THAI_TRANSCRIPT)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-emerald-300 bg-emerald-50 text-emerald-800 font-semibold hover:bg-emerald-100 transition shadow-sm"
                title="Load sample Thai conversation for demonstration"
              >
                <Sparkles size={13} aria-hidden="true" />
                ตัวอย่างภาษาไทย
              </button>
              <button
                type="button"
                onClick={() => onDraftChange(SAMPLE_ENG_TRANSCRIPT)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-300 bg-slate-50 text-slate-700 font-semibold hover:bg-slate-100 transition"
                title="Load sample English conversation"
              >
                English Sample
              </button>
            </div>
          )}
        </div>
        {mode === "cha" ? (
          <>
            <label className="sr-only" htmlFor="cha-transcript-file">CHA transcript file</label>
            <input
              id="cha-transcript-file"
              type="file"
              accept=".cha"
              className="mb-3 block w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] px-3 py-3 text-sm"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                if (file) void onChaFile(file);
              }}
            />
          </>
        ) : null}
        <textarea
          className="min-h-44 w-full rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-3 text-sm text-ink outline-none focus:ring-2 focus:ring-clinical"
          value={draftTranscript}
          onChange={(event) => onDraftChange(event.target.value)}
          aria-label={mode === "cha" ? "CHA transcript text" : "Pasted transcript text"}
          aria-describedby={error ? "source-transcript-error" : undefined}
          data-testid="transcript-input"
        />
        {error ? (
          <p id="source-transcript-error" className="mt-3 rounded-[var(--radius-card)] border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-900 animate-fade-in" role="alert">
            {error}
          </p>
        ) : null}
        {warnings.length > 0 ? (
          <div className="mt-3 rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
            <p className="font-semibold">Import warnings</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
          </div>
        ) : null}
        {validationIssues.length > 0 ? (
          <div className="mt-3 rounded-[var(--radius-card)] border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900" role="alert">
            <p className="font-semibold">CHAT validation</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{validationIssues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </div>
        ) : null}
        <PrimaryActionButton
          icon={CheckCircle2}
          className="mt-3 w-full"
          onClick={() => onTranscriptSubmit(source)}
          disabled={busy || Boolean(error)}
          data-testid="save-transcript-button"
          aria-describedby={error ? "source-transcript-error" : undefined}
        >
          Save transcript
        </PrimaryActionButton>
      </WorkspacePanel>
    );
  }

  return null;
}


export function SessionResultsPreview({ state, onGenerateReport, busy }: { state: WorkflowState; onGenerateReport: () => void; busy: boolean }) {
  return (
    <WorkspacePanel className="hidden p-6 lg:block">
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-[color:var(--color-accent-soft)] font-bold text-clinical">EL</span>
        <div>
          <h2 className="text-xl font-bold text-ink">Session Results</h2>
          <p className="text-sm text-slate-600">{state.childName} · {state.qaStatus ?? "Not analyzed"}</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <MiniResult value={`${state.transcriptCompleteness || 0}%`} label="Transcript Ready" />
        <MiniResult value={`${state.featurePercent || 0}%`} label="Feature Summary" />
        <MiniResult value={String(state.reviewNeededCount)} label="Review Needed" />
      </div>
      <div className="mt-6 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
        <h3 className="font-bold text-ink">Key insights</h3>
        <ul className="mt-3 space-y-3 text-sm text-slate-700">
          {state.insights.map((insight) => <li key={insight.title}>{insight.title}: {insight.text}</li>)}
        </ul>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <PrimaryActionButton href={workflowSessionHref("transcript", state)} icon={FileText}>Review Transcript</PrimaryActionButton>
        <PrimaryActionButton icon={ShieldCheck} onClick={onGenerateReport} disabled={busy || !isResultsReportReady(state)}>{GENERATE_REPORT_ACTION}</PrimaryActionButton>
      </div>
    </WorkspacePanel>
  );
}

function isResultsReportReady(state: WorkflowState) {
  if (state.analysisStatus === "stale") return false;
  return isTranscriptUnlocked(state) && state.featuresExtracted;
}

export function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) {
    return null;
  }
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) {
    return null;
  }
  const className = isError
    ? "rounded-[var(--radius-panel)] border border-red-200 bg-red-50 p-4 text-sm text-red-950 animate-fade-in"
    : isSuccess
      ? "rounded-[var(--radius-panel)] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 animate-fade-in"
      : "demo-note rounded-[var(--radius-panel)] p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}

function MiniResult({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[1.25rem] border border-line bg-[color:var(--color-surface-reading)] p-4 text-center">
      <p className="text-3xl font-bold text-ink">{value}</p>
      <p className="mt-2 text-sm font-semibold text-slate-700">{label}</p>
    </div>
  );
}
