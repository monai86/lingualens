export type WorkflowStatus =
  | "Draft"
  | "Needs Review"
  | "Attested"
  | "Processing"
  | "Failed"
  | "Ready"
  | "Signed Off"
  | "Withdrawn"
  | "Awaiting Consent"
  | "Ready for Audio"
  | "Recording"
  | "Uploading"
  | "Transcribing"
  | "CHA Generating"
  | "ML Pending"
  | "Review Required"
  | "Report Ready";

const styles: Record<WorkflowStatus, string> = {
  Draft: "border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] text-[color:var(--color-text-muted)]",
  "Needs Review": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  Attested: "border-emerald-200 bg-emerald-50 text-emerald-800",
  Processing: "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]",
  Failed: "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  Ready: "border-emerald-200 bg-emerald-50 text-emerald-800",
  "Signed Off": "border-[color:var(--color-pasa-teal)] bg-[color:var(--color-pasa-teal)] text-white",
  Withdrawn: "border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]",
  "Awaiting Consent": "border-[color:var(--color-warm-butter-border)] bg-[color:var(--color-warm-butter-soft)] text-[color:var(--color-warning-text)]",
  "Ready for Audio": "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]",
  "Recording": "border-[color:var(--color-scope-coral-border)] bg-[color:var(--color-scope-coral-soft)] text-[color:var(--color-scope-coral-hover)] animate-pulse font-bold",
  "Uploading": "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)] animate-pulse",
  "Transcribing": "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]",
  "CHA Generating": "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]",
  "ML Pending": "border-[color:var(--color-warm-butter-border)] bg-[color:var(--color-warm-butter-soft)] text-[color:var(--color-warning-text)]",
  "Review Required": "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  "Report Ready": "border-emerald-200 bg-emerald-50 text-emerald-800",
};

export function StatusBadge({ status }: { status: string }) {
  const getNormalizedStatus = (s: string): WorkflowStatus | null => {
    const keys = Object.keys(styles) as WorkflowStatus[];
    if (keys.includes(s as WorkflowStatus)) {
      return s as WorkflowStatus;
    }

    const canonicalize = (val: string) =>
      val.toLowerCase().replace(/[_-]/g, " ").replace(/\s+/g, " ").trim();

    const canonicalInput = canonicalize(s);
    return keys.find((key) => canonicalize(key) === canonicalInput) || null;
  };

  const matched = getNormalizedStatus(status);
  const matchedStatus = matched || "Draft";
  const displayText = matched ? matched : status;

  return (
    <span
      className={`inline-flex min-h-8 min-w-24 items-center justify-center rounded-full border px-3 py-1 text-xs font-semibold ${styles[matchedStatus]}`}
    >
      {displayText}
    </span>
  );
}

