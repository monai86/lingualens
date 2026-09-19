import { describe, expect, it } from "vitest";

import {
  evaluateBenchmarkBaseline,
  validateBenchmarkCapture,
} from "../../scripts/check-benchmark-baseline.mjs";

const reference = {
  reference: {
    line100: {
      keystrokeP95Ms: 10,
      selectionP95Ms: 10,
      filterP95Ms: 10,
    },
    line500: {
      keystrokeP95Ms: 10,
      selectionP95Ms: 10,
      filterP95Ms: 10,
    },
    line1000: {
      keystrokeP95Ms: 10,
      selectionP95Ms: 10,
      filterP95Ms: 10,
    },
  },
  comparison: {
    latencyToleranceFactor: 2,
    minimumScrollFps: {
      line500: 45,
      line1000: 40,
    },
  },
};

function makeResults() {
  return {
    capturedAt: "2026-08-25T00:00:00.000Z",
    conditions: {
      platform: "test",
      cpu: "test",
    },
    results: [100, 500, 1000].map((lineCount) => ({
      lineCount,
      runs: Array.from({ length: 5 }, () => ({
        keystrokeMs: 10,
        selectionMs: 10,
        filterMs: 10,
        scrollFps: 60,
      })),
    })),
  };
}

function entryFor(results: ReturnType<typeof makeResults>, lineCount: number) {
  const entry = results.results.find((candidate) => candidate.lineCount === lineCount);
  if (!entry) throw new Error(`Fixture is missing ${lineCount}-line results.`);
  return entry;
}

describe("evaluateBenchmarkBaseline", () => {
  it("lets the benchmark producer publish one latency outlier for majority baseline evaluation", () => {
    const results = makeResults();
    entryFor(results, 500).runs[0].keystrokeMs = 99;

    expect(validateBenchmarkCapture(results).passed).toBe(true);
    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(true);
  });

  it("accepts one shared-runner latency outlier when the remaining samples meet the baseline", () => {
    const results = makeResults();
    entryFor(results, 100).runs[0].keystrokeMs = 99;

    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(true);
  });

  it("rejects a majority of latency samples that exceed the baseline", () => {
    const results = makeResults();
    const runs = entryFor(results, 500).runs;
    runs[0].filterMs = 40;
    runs[1].filterMs = 41;
    runs[2].filterMs = 42;

    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(false);
  });

  it("rejects benchmark results with a missing required measurement", () => {
    const results = makeResults();
    delete (entryFor(results, 1000).runs[0] as Partial<{ selectionMs: number }>).selectionMs;

    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(false);
  });

  it("rejects an invalid negative latency measurement", () => {
    const results = makeResults();
    entryFor(results, 1000).runs[0].selectionMs = -1;

    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(false);
  });

  it("rejects any scroll-fps sample below its absolute floor", () => {
    const results = makeResults();
    entryFor(results, 500).runs[0].scrollFps = 44;

    expect(evaluateBenchmarkBaseline(results, reference).passed).toBe(false);
  });
});
