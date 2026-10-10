import * as React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={`flex min-h-11 w-full rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3.5 py-2 text-sm text-[color:var(--color-text-strong)] placeholder:text-[color:var(--color-text-subtle)] shadow-2xs transition duration-150 ease-out focus-visible:outline-none focus-visible:border-[color:var(--color-pasa-teal)] focus-visible:ring-3 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
