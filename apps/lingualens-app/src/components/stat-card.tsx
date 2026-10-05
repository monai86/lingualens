import type { LucideIcon } from "lucide-react";
import { Activity } from "lucide-react";

type StatTone = "neutral" | "accent" | "success" | "warning";

const toneClasses: Record<StatTone, string> = {
  neutral: "bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]",
  accent: "bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)] border border-[color:var(--color-pasa-teal-border)]",
  success: "bg-emerald-50 text-emerald-800 border border-emerald-200",
  warning: "bg-[color:var(--color-warm-butter-soft)] text-[color:var(--color-warning-text)] border border-[color:var(--color-warm-butter-border)]"
};

export function StatCard({
  label,
  value,
  helper,
  icon: Icon = Activity,
  tone = "neutral"
}: {
  label: string;
  value: string;
  helper?: string;
  icon?: LucideIcon;
  tone?: StatTone;
}) {
  return (
    <section className="rounded-2xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5 shadow-xs transition-shadow duration-200 hover:shadow-lift">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[color:var(--color-text-muted)]">{label}</p>
          <p className="mt-2 text-3xl font-extrabold tracking-tight text-[color:var(--color-text-strong)]">{value}</p>
        </div>
        <span className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${toneClasses[tone]}`}>
          <Icon size={20} aria-hidden="true" />
        </span>
      </div>
      {helper ? <p className="mt-3 text-xs leading-5 text-[color:var(--color-text-muted)]">{helper}</p> : null}
    </section>
  );
}
