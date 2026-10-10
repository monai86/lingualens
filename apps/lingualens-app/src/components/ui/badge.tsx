import * as React from "react";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "warning"
  | "accent";

const variantClasses: Record<BadgeVariant, string> = {
  default:
    "border-transparent bg-[color:var(--color-pasa-teal)] text-white hover:bg-[color:var(--color-pasa-teal-hover)]",
  secondary:
    "border-transparent bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]",
  destructive:
    "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  outline:
    "border-[color:var(--color-border)] text-[color:var(--color-text-strong)]",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning:
    "border-[color:var(--color-warm-butter-border)] bg-[color:var(--color-warm-butter-soft)] text-[color:var(--color-warning-text)]",
  accent:
    "border-[color:var(--color-pasa-teal-border)] bg-[color:var(--color-pasa-teal-soft)] text-[color:var(--color-pasa-teal)]",
};

export function Badge({
  className = "",
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: BadgeVariant }) {
  return (
    <div
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[color:var(--color-focus-ring)] ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}
