import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LongitudinalTrendCard, type LongitudinalSessionItem } from "@/features/reports/components/longitudinal-trend-card";

describe("LongitudinalTrendCard", () => {
  const SESSIONS: LongitudinalSessionItem[] = [
    {
      sessionId: "SESS-001",
      date: "01/08/2026",
      mluWords: 2.1,
      ttr: 0.52,
      turnTakingCount: 5,
      echolaliaCount: 4,
      politeParticleCount: 1,
      f0MedianHz: 320.5,
    },
    {
      sessionId: "SESS-002",
      date: "15/08/2026",
      mluWords: 2.85,
      ttr: 0.61,
      turnTakingCount: 8,
      echolaliaCount: 2,
      politeParticleCount: 3,
      f0MedianHz: 312.0,
    },
    {
      sessionId: "SESS-003",
      date: "20/09/2026",
      mluWords: 3.42,
      ttr: 0.68,
      turnTakingCount: 12,
      echolaliaCount: 1,
      politeParticleCount: 5,
      f0MedianHz: 308.2,
    },
  ];

  it("renders empty state message when no sessions are provided", () => {
    render(<LongitudinalTrendCard sessions={[]} />);
    expect(screen.getByText(/No longitudinal session data/i)).toBeInTheDocument();
  });

  it("renders longitudinal table with session dates and session IDs", () => {
    render(<LongitudinalTrendCard sessions={SESSIONS} />);
    expect(screen.getByTestId("longitudinal-trend-card")).toBeInTheDocument();
    expect(screen.getByText("SESS-001")).toBeInTheDocument();
    expect(screen.getByText("SESS-002")).toBeInTheDocument();
    expect(screen.getByText("SESS-003")).toBeInTheDocument();
    expect(screen.getByText("3 Recorded Sessions")).toBeInTheDocument();
  });

  it("calculates and displays positive MLU-w trajectory delta", () => {
    render(<LongitudinalTrendCard sessions={SESSIONS} />);
    // Delta between 3.42 and 2.10 is +1.32
    expect(screen.getByText("+1.32")).toBeInTheDocument();
    expect(screen.getByText(/MLU-w Trajectory/i)).toBeInTheDocument();
  });

  it("renders clinical safety note disclaimer", () => {
    render(<LongitudinalTrendCard sessions={SESSIONS} />);
    expect(screen.getByText(/Clinical Note:/i)).toBeInTheDocument();
    expect(screen.getByText(/Longitudinal trajectories illustrate observed descriptive speech patterns/i)).toBeInTheDocument();
  });
});
