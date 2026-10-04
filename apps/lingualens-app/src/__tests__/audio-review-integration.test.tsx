import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { SessionTranscriptView } from "@/features/sessions/transcript/session-transcript-view";

// Mock Canvas 2D context for jsdom
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    fill: vi.fn(),
    fillText: vi.fn(),
    strokeRect: vi.fn(),
    setLineDash: vi.fn(),
  }) as any;
});

describe("SessionTranscriptView with AudioReviewWorkbench", () => {
  it("renders audio review workbench when audio is present and falls back gracefully", () => {
    const onLinesChange = vi.fn();
    const onAttest = vi.fn();

    render(
      <SessionTranscriptView
        sessionContext={{ sessionId: "sess-1", caseId: "case-1", dataMode: "local_draft", activeView: "transcript" }}
        state={
          {
            transcriptSaveStatus: "saved",
            qaStatus: "pass",
            qaIssues: [],
            transcriptAttested: false,
            featuresExtracted: false,
            backendTranscriptId: "tr-1",
          } as any
        }
        lines={[
          { lineId: "L1", speaker: "CHI", text: "ทดสอบการพูด", startMs: 500, endMs: 2500 },
          { lineId: "L2", speaker: "INV", text: "เก่งมากเลย", startMs: 3000, endMs: 4500 },
        ]}
        busy={false}
        onLinesChange={onLinesChange}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={onAttest}
        onExtractFeatures={vi.fn()}
        onGenerateReport={vi.fn()}
        onExport={vi.fn()}
        audioUrl="/api/v1/sessions/sess-1/audio/mock.wav"
      />
    );

    expect(screen.getByText(/Review Transcript/i)).toBeDefined();
    expect(screen.getByDisplayValue("ทดสอบการพูด")).toBeDefined();
    expect(screen.getByTestId("dual-view-waveform")).toBeDefined();

    // Toggle to Classic Text Editor
    const classicBtn = screen.getByText("Classic Text Editor");
    fireEvent.click(classicBtn);
    expect(screen.queryByTestId("dual-view-waveform")).toBeNull();

    // Toggle back to Audio Workbench
    const audioBtn = screen.getByText("Audio & Diarization Workbench");
    fireEvent.click(audioBtn);
    expect(screen.getByTestId("dual-view-waveform")).toBeDefined();
  });

  it("falls back to classic editor when audioUrl is not provided", () => {
    render(
      <SessionTranscriptView
        sessionContext={{ sessionId: "sess-2", caseId: "case-2", dataMode: "local_draft", activeView: "transcript" }}
        state={
          {
            transcriptSaveStatus: "saved",
            qaStatus: "pass",
            qaIssues: [],
            transcriptAttested: false,
            featuresExtracted: false,
          } as any
        }
        lines={[{ lineId: "L1", speaker: "CHI", text: "ไม่มีไฟล์เสียง", startMs: 0, endMs: 1000 }]}
        busy={false}
        onLinesChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExtractFeatures={vi.fn()}
        onGenerateReport={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.queryByTestId("dual-view-waveform")).toBeNull();
    expect(screen.queryByText("Audio & Diarization Workbench")).toBeNull();
    expect(screen.getByText(/ไม่มีไฟล์เสียง/)).toBeDefined();
  });
});
