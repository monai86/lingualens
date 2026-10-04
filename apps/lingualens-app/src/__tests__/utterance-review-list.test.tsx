import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UtteranceReviewList } from "@/components/audio-review/utterance-review-list";

describe("UtteranceReviewList", () => {
  it("renders utterances with 1-click speaker badge and triggers role change", () => {
    const onLineChange = vi.fn();
    const lines = [
      { lineId: "L1", speaker: "CHI", text: "รถ สี แดง", startMs: 1000, endMs: 2500 }
    ];
    render(
      <UtteranceReviewList
        lines={lines}
        activeLineId="L1"
        onSelectLine={vi.fn()}
        onLineChange={onLineChange}
        onPlayUtterance={vi.fn()}
      />
    );

    expect(screen.getByDisplayValue("รถ สี แดง")).toBeDefined();
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "INV" } });
    expect(onLineChange).toHaveBeenCalledWith(0, expect.objectContaining({ speaker: "INV" }));
  });

  it("handles line text edits and displays clinical cues", () => {
    const onLineChange = vi.fn();
    const lines = [
      {
        lineId: "L1",
        speaker: "CHI",
        text: "หนู เอา อันนี้",
        startMs: 2000,
        endMs: 3500,
        clinicalTag: "echolalia",
      },
    ];
    render(
      <UtteranceReviewList
        lines={lines}
        activeLineId="L1"
        onSelectLine={vi.fn()}
        onLineChange={onLineChange}
        onPlayUtterance={vi.fn()}
      />
    );

    expect(screen.getByText(/Echolalia/i)).toBeDefined();
    const input = screen.getByDisplayValue("หนู เอา อันนี้");
    fireEvent.change(input, { target: { value: "หนู อยากได้ อันนี้" } });
    expect(onLineChange).toHaveBeenCalledWith(
      0,
      expect.objectContaining({ text: "หนู อยากได้ อันนี้" })
    );
  });
});

import { renderHook, act } from "@testing-library/react";
import { useKeyboardReview } from "@/components/audio-review/use-keyboard-review";

describe("useKeyboardReview", () => {
  it("triggers keyboard shortcuts for playback, looping, and speaker roles", () => {
    const onPlayPause = vi.fn();
    const onReplayActive = vi.fn();
    const onToggleLoop = vi.fn();
    const onAssignSpeaker = vi.fn();
    const onAdvanceLine = vi.fn();

    renderHook(() =>
      useKeyboardReview({
        onPlayPause,
        onReplayActive,
        onToggleLoop,
        onAssignSpeaker,
        onAdvanceLine,
      })
    );

    // Space: Play/Pause
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));
    });
    expect(onPlayPause).toHaveBeenCalledTimes(1);

    // Cmd + Space: Replay active
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space", metaKey: true }));
    });
    expect(onReplayActive).toHaveBeenCalledTimes(1);

    // Cmd + 1: Assign CHI
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "1", metaKey: true }));
    });
    expect(onAssignSpeaker).toHaveBeenCalledWith("CHI");

    // Cmd + 2: Assign INV
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "2", metaKey: true }));
    });
    expect(onAssignSpeaker).toHaveBeenCalledWith("INV");

    // Cmd + L: Loop
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "l", metaKey: true }));
    });
    expect(onToggleLoop).toHaveBeenCalledTimes(1);

    // Cmd + Enter: Advance line
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", metaKey: true }));
    });
    expect(onAdvanceLine).toHaveBeenCalledTimes(1);
  });
});
