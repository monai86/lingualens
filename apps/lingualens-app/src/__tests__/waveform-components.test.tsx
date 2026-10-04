import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest";

import { AudioScrubberBar } from "@/components/audio-review/audio-scrubber-bar";
import { DualViewWaveform } from "@/components/audio-review/dual-view-waveform";
import { WaveformMinimap } from "@/components/audio-review/waveform-minimap";
import { WaveformDetailCanvas } from "@/components/audio-review/waveform-detail-canvas";

// Mock canvas 2D context for jsdom environment
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

describe("AudioScrubberBar", () => {
  it("renders playback controls, timecode, and handles speed changes", () => {
    const onSpeedChange = vi.fn();
    const onPlayPause = vi.fn();
    const onToggleLoop = vi.fn();
    const onTogglePitch = vi.fn();

    render(
      <AudioScrubberBar
        isPlaying={false}
        currentTimeMs={84400}
        durationMs={300000}
        speed={1.0}
        isLooping={false}
        showPitch={false}
        onPlayPause={onPlayPause}
        onSpeedChange={onSpeedChange}
        onToggleLoop={onToggleLoop}
        onTogglePitch={onTogglePitch}
      />
    );

    expect(screen.getByText(/01:24\.400/)).toBeDefined();
    expect(screen.getByText(/05:00\.000/)).toBeDefined();

    const speedBtn = screen.getByText("0.75x");
    fireEvent.click(speedBtn);
    expect(onSpeedChange).toHaveBeenCalledWith(0.75);

    const loopBtn = screen.getByRole("button", { name: /loop/i });
    fireEvent.click(loopBtn);
    expect(onToggleLoop).toHaveBeenCalled();

    const pitchBtn = screen.getByRole("button", { name: /f0 pitch/i });
    fireEvent.click(pitchBtn);
    expect(onTogglePitch).toHaveBeenCalled();
  });
});

describe("DualViewWaveform", () => {
  it("renders quality indicators and multi-track lanes", () => {
    const segments = [
      { id: "s1", speaker: "CHI", startMs: 1000, endMs: 2500, text: "รถ สี แดง" },
      { id: "s2", speaker: "INV", startMs: 2800, endMs: 3500, text: "ใช่แล้ว" },
    ];

    render(
      <DualViewWaveform
        currentTimeMs={1500}
        durationMs={60000}
        segments={segments}
        snrDb={22.4}
        diarizationConfidence={88.5}
        responseLatencyMs={420}
        showPitch={true}
        onSeek={vi.fn()}
        onSegmentBoundaryChange={vi.fn()}
      />
    );

    expect(screen.getByText(/22\.4 dB/)).toBeDefined();
    expect(screen.getByText(/88\.5%/)).toBeDefined();
    expect(screen.getByText(/420 ms/)).toBeDefined();
    expect(screen.getByTestId("dual-view-waveform")).toBeDefined();
  });
});
