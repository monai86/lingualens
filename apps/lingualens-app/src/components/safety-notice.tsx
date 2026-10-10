import { ShieldCheck } from "lucide-react";

import { SAFETY_NOTICE_DEFAULT } from "@/lib/clinical-safety-copy";

export function SafetyNotice({
  children = SAFETY_NOTICE_DEFAULT,
  className = ""
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <aside
      className={`rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-sm text-[color:var(--color-text-muted)] ${className}`}
    >
      <div className="flex items-start gap-3">
        <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-accent)]" />
        <p className="leading-6">{children}</p>
      </div>
    </aside>
  );
}
