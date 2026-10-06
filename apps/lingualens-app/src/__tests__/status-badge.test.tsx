import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge component pipeline statuses and normalization", () => {
  it("renders new pipeline statuses with correct styles", () => {
    // 1. Awaiting Consent
    const { rerender } = render(<StatusBadge status="Awaiting Consent" />);
    let badge = screen.getByText("Awaiting Consent");
    expect(badge).toHaveClass("border-[color:var(--color-warm-butter-border)]", "bg-[color:var(--color-warm-butter-soft)]", "text-[color:var(--color-warning-text)]");

    // 2. Ready for Audio
    rerender(<StatusBadge status="Ready for Audio" />);
    badge = screen.getByText("Ready for Audio");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");

    // 3. Recording (pulse animation)
    rerender(<StatusBadge status="Recording" />);
    badge = screen.getByText("Recording");
    expect(badge).toHaveClass("border-[color:var(--color-scope-coral-border)]", "bg-[color:var(--color-scope-coral-soft)]", "text-[color:var(--color-scope-coral-hover)]", "animate-pulse");

    // 4. Uploading (pulse animation)
    rerender(<StatusBadge status="Uploading" />);
    badge = screen.getByText("Uploading");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]", "animate-pulse");

    // 5. Transcribing
    rerender(<StatusBadge status="Transcribing" />);
    badge = screen.getByText("Transcribing");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");

    // 6. CHA Generating
    rerender(<StatusBadge status="CHA Generating" />);
    badge = screen.getByText("CHA Generating");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");

    // 7. ML Pending
    rerender(<StatusBadge status="ML Pending" />);
    badge = screen.getByText("ML Pending");
    expect(badge).toHaveClass("border-[color:var(--color-warm-butter-border)]", "bg-[color:var(--color-warm-butter-soft)]", "text-[color:var(--color-warning-text)]");

    // 8. Review Required (warning styles of Needs Review)
    rerender(<StatusBadge status="Review Required" />);
    badge = screen.getByText("Review Required");
    expect(badge).toHaveClass("border-[color:var(--color-warning-border)]", "bg-[color:var(--color-warning-bg)]", "text-[color:var(--color-warning-text)]");

    // 9. Report Ready (success styles of Ready)
    rerender(<StatusBadge status="Report Ready" />);
    badge = screen.getByText("Report Ready");
    expect(badge).toHaveClass("border-emerald-200", "bg-emerald-50", "text-emerald-800");
  });

  it("handles normalizations like converting case and underscores", () => {
    // awaiting_consent -> Awaiting Consent
    const { rerender } = render(<StatusBadge status="awaiting_consent" />);
    let badge = screen.getByText("Awaiting Consent");
    expect(badge).toHaveClass("border-[color:var(--color-warm-butter-border)]", "bg-[color:var(--color-warm-butter-soft)]", "text-[color:var(--color-warning-text)]");

    // ml_pending -> ML Pending
    rerender(<StatusBadge status="ml_pending" />);
    badge = screen.getByText("ML Pending");
    expect(badge).toHaveClass("border-[color:var(--color-warm-butter-border)]", "bg-[color:var(--color-warm-butter-soft)]", "text-[color:var(--color-warning-text)]");

    // review_required -> Review Required
    rerender(<StatusBadge status="review_required" />);
    badge = screen.getByText("Review Required");
    expect(badge).toHaveClass("border-[color:var(--color-warning-border)]", "bg-[color:var(--color-warning-bg)]", "text-[color:var(--color-warning-text)]");

    // report_ready -> Report Ready
    rerender(<StatusBadge status="report_ready" />);
    badge = screen.getByText("Report Ready");
    expect(badge).toHaveClass("border-emerald-200", "bg-emerald-50", "text-emerald-800");

    // ready_for_audio -> Ready for Audio
    rerender(<StatusBadge status="ready_for_audio" />);
    badge = screen.getByText("Ready for Audio");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");

    // recording -> Recording
    rerender(<StatusBadge status="recording" />);
    badge = screen.getByText("Recording");
    expect(badge).toHaveClass("border-[color:var(--color-scope-coral-border)]", "bg-[color:var(--color-scope-coral-soft)]", "text-[color:var(--color-scope-coral-hover)]", "animate-pulse");

    // uploading -> Uploading
    rerender(<StatusBadge status="uploading" />);
    badge = screen.getByText("Uploading");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]", "animate-pulse");

    // transcribing -> Transcribing
    rerender(<StatusBadge status="transcribing" />);
    badge = screen.getByText("Transcribing");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");

    // cha_generating -> CHA Generating
    rerender(<StatusBadge status="cha_generating" />);
    badge = screen.getByText("CHA Generating");
    expect(badge).toHaveClass("border-[color:var(--color-pasa-teal-border)]", "bg-[color:var(--color-pasa-teal-soft)]", "text-[color:var(--color-pasa-teal)]");
  });

  it("renders unknown/unmatched statuses with draft styles but keeps original text", () => {
    render(<StatusBadge status="Unknown Status" />);
    const badge = screen.getByText("Unknown Status");
    expect(badge).toHaveClass(
      "border-[color:var(--color-border)]",
      "bg-[color:var(--color-surface-strong)]",
      "text-[color:var(--color-text-muted)]"
    );
  });

  it("properly capitalizes draft when casing variation is provided", () => {
    render(<StatusBadge status="draft" />);
    const badge = screen.getByText("Draft");
    expect(badge).toBeInTheDocument();
  });
});
