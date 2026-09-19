/**
 * Benchmark baseline gate for CI.
 *
 * Compares `benchmarks/results/transcript-benchmark-latest.json` (written by
 * `npm run bench:transcript`) against the committed reference baseline
 * `benchmarks/results/transcript-benchmark-reference.json`.
 *
 * Latency measurements run on shared CI hardware. The gate compares each raw
 * sample with the reference baseline, permits isolated slow samples, and fails
 * only when a strict majority of samples for a metric exceed the tolerance.
 * This keeps a shared-runner outlier from blocking a candidate while still
 * rejecting sustained regressions. Scroll FPS remains an absolute per-sample
 * safety floor: any sample below its floor fails the gate.
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const minimumRawSampleCount = 5;
const captureLineCounts = [100, 500, 1_000];
const captureMetrics = ["keystrokeMs", "selectionMs", "filterMs", "scrollFps"];

const latencyChecks = [
  ["line100", 100, "keystrokeMs", "keystrokeP95Ms"],
  ["line100", 100, "selectionMs", "selectionP95Ms"],
  ["line100", 100, "filterMs", "filterP95Ms"],
  ["line500", 500, "keystrokeMs", "keystrokeP95Ms"],
  ["line500", 500, "selectionMs", "selectionP95Ms"],
  ["line500", 500, "filterMs", "filterP95Ms"],
  ["line1000", 1000, "keystrokeMs", "keystrokeP95Ms"],
  ["line1000", 1000, "selectionMs", "selectionP95Ms"],
  ["line1000", 1000, "filterMs", "filterP95Ms"],
];

const fpsChecks = [
  ["line500", 500],
  ["line1000", 1000],
];

/**
 * Validate that the Playwright producer captured every raw metric the baseline
 * gate needs, without applying latency thresholds. Threshold decisions belong
 * exclusively to evaluateBenchmarkBaseline so one shared-runner outlier can
 * reach the majority-based evaluator.
 */
export function validateBenchmarkCapture(results) {
  const failures = [];
  const checks = [];
  const lineEntries = lineEntriesFor(results);

  for (const lineCount of captureLineCounts) {
    const entry = lineEntries.get(lineCount);
    for (const metric of captureMetrics) {
      const samples = rawSamples(entry, metric, lineCount, failures);
      checks.push({
        label: `${lineCount}-line ${metric} capture`,
        sampleCount: samples?.length ?? 0,
        passed: samples !== null,
      });
    }
  }

  return { passed: failures.length === 0, failures, checks };
}

/**
 * Evaluate benchmark data without reading files or exiting the process.
 *
 * The benchmark spec records five raw samples per line count. A raw latency
 * sample may be noisy on a shared runner, so a metric fails only if more than
 * half of its valid samples exceed the reference tolerance. Missing or invalid
 * samples fail closed. Scroll FPS has no statistical exemption because every
 * sampled interaction must remain above its absolute floor.
 */
export function evaluateBenchmarkBaseline(results, reference) {
  const failures = [];
  const checks = [];
  const lineEntries = lineEntriesFor(results);
  const comparison = reference?.comparison;
  const latencyToleranceFactor = comparison?.latencyToleranceFactor;
  const minimumScrollFps = comparison?.minimumScrollFps;

  if (!isFiniteNumber(latencyToleranceFactor) || latencyToleranceFactor <= 0) {
    failures.push("Benchmark reference is missing a positive latencyToleranceFactor.");
  }

  for (const [referenceKey, lineCount, metric, referenceMetric] of latencyChecks) {
    const label = `${lineCount}-line ${metric.replace("Ms", "")} latency`;
    const entry = lineEntries.get(lineCount);
    const referenceValue = reference?.reference?.[referenceKey]?.[referenceMetric];
    const samples = rawSamples(entry, metric, lineCount, failures);

    if (!isFiniteNumber(referenceValue) || referenceValue <= 0) {
      failures.push(`Benchmark reference is missing a positive ${referenceKey}.${referenceMetric} value.`);
    }

    if (!isFiniteNumber(latencyToleranceFactor) || latencyToleranceFactor <= 0
      || !isFiniteNumber(referenceValue) || referenceValue <= 0
      || samples === null) {
      checks.push({ label, status: "invalid" });
      continue;
    }

    const limit = referenceValue * latencyToleranceFactor;
    const overLimitCount = samples.filter((sample) => sample > limit).length;
    const actual = median(samples);
    const passed = overLimitCount <= samples.length / 2;
    checks.push({
      label,
      actual,
      limit,
      direction: "sustained-at-or-below",
      overLimitCount,
      sampleCount: samples.length,
      passed,
    });

    if (!passed) {
      failures.push(
        `${label} has ${overLimitCount}/${samples.length} samples above the baseline limit of ${limit} ms `
        + `(reference ${referenceValue} ms x ${latencyToleranceFactor}); this is a sustained regression.`,
      );
    }
  }

  for (const [referenceKey, lineCount] of fpsChecks) {
    const label = `${lineCount}-line scroll fps (worst sampled run)`;
    const entry = lineEntries.get(lineCount);
    const limit = minimumScrollFps?.[referenceKey];
    const samples = rawSamples(entry, "scrollFps", lineCount, failures);

    if (!isFiniteNumber(limit) || limit <= 0) {
      failures.push(`Benchmark reference is missing a positive minimumScrollFps.${referenceKey} value.`);
    }

    if (!isFiniteNumber(limit) || limit <= 0 || samples === null) {
      checks.push({ label, status: "invalid" });
      continue;
    }

    const actual = Math.min(...samples);
    const passed = actual >= limit;
    checks.push({
      label,
      actual,
      limit,
      direction: "at-or-above",
      sampleCount: samples.length,
      passed,
    });

    if (!passed) {
      failures.push(`${label} ${actual.toFixed(1)} fps is below the floor of ${limit} fps.`);
    }
  }

  return { passed: failures.length === 0, failures, checks };
}

function rawSamples(entry, metric, lineCount, failures) {
  if (!entry) {
    failures.push(`Benchmark results are missing the ${lineCount}-line measurement.`);
    return null;
  }

  if (!Array.isArray(entry.runs) || entry.runs.length < minimumRawSampleCount) {
    failures.push(
      `Benchmark results for ${lineCount} lines must include at least ${minimumRawSampleCount} raw samples.`,
    );
    return null;
  }

  const samples = [];
  for (const [index, run] of entry.runs.entries()) {
    const value = run?.[metric];
    if (!isValidMeasurement(value)) {
      failures.push(`Benchmark results are missing a finite non-negative ${metric} measurement for ${lineCount} lines, run ${index + 1}.`);
      return null;
    }
    samples.push(value);
  }
  return samples;
}

function lineEntriesFor(results) {
  return new Map(
    Array.isArray(results?.results)
      ? results.results
        .filter((entry) => Number.isInteger(entry?.lineCount))
        .map((entry) => [entry.lineCount, entry])
      : [],
  );
}

function median(samples) {
  const sorted = [...samples].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
}

function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function isValidMeasurement(value) {
  return isFiniteNumber(value) && value >= 0;
}

export function formatBenchmarkDecision(decision, results) {
  const conditions = results?.conditions ?? {};
  const lines = [
    `Benchmark baseline gate — ${results?.capturedAt ?? "unknown capture time"}`,
    `Conditions: ${conditions.platform ?? "unknown platform"} / ${conditions.cpu ?? "unknown CPU"}`,
    "",
  ];

  for (const check of decision.checks) {
    if (check.status === "invalid") {
      lines.push(`FAIL  ${check.label.padEnd(46)} invalid or missing measurement`);
      continue;
    }

    if (check.direction === "sustained-at-or-below") {
      lines.push(
        `${check.passed ? "PASS" : "FAIL"}  ${check.label.padEnd(46)} median ${String(check.actual).padStart(9)} ms  `
        + `${String(check.overLimitCount).padStart(2)}/${check.sampleCount} over ${String(check.limit).padStart(9)} ms`,
      );
      continue;
    }

    lines.push(
      `${check.passed ? "PASS" : "FAIL"}  ${check.label.padEnd(46)} actual ${String(check.actual).padStart(9)}  `
      + `floor ${String(check.limit).padStart(9)}`,
    );
  }

  lines.push("");
  if (!decision.passed) {
    lines.push(`${decision.failures.length} benchmark baseline violation(s):`);
    for (const failure of decision.failures) lines.push(`  - ${failure}`);
  }

  return lines.join("\n");
}

async function main() {
  const projectRoot = process.cwd();
  const resultPath = path.resolve(projectRoot, "benchmarks/results/transcript-benchmark-latest.json");
  const referencePath = path.resolve(projectRoot, "benchmarks/results/transcript-benchmark-reference.json");
  const [rawResults, rawReference] = await Promise.all([
    readFile(resultPath, "utf8"),
    readFile(referencePath, "utf8"),
  ]);
  const results = JSON.parse(rawResults);
  const reference = JSON.parse(rawReference);
  const decision = evaluateBenchmarkBaseline(results, reference);
  const output = formatBenchmarkDecision(decision, results);

  if (!decision.passed) {
    process.stderr.write(`${output}\n`);
    process.exitCode = 1;
    return;
  }

  process.stdout.write(`${output}\nBenchmark within baseline tolerance. ✓\n`);
}

const invokedPath = process.argv[1];
if (invokedPath && path.basename(invokedPath) === "check-benchmark-baseline.mjs") {
  main().catch((error) => {
    process.stderr.write(`Benchmark baseline gate failed to run: ${error.message}\n`);
    process.exitCode = 1;
  });
}
