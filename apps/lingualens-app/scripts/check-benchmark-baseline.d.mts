export interface BenchmarkDecision {
  passed: boolean;
  failures: string[];
  checks: Array<Record<string, unknown>>;
}

export function evaluateBenchmarkBaseline(
  results: unknown,
  reference: unknown,
): BenchmarkDecision;

export function validateBenchmarkCapture(results: unknown): BenchmarkDecision;

export function formatBenchmarkDecision(
  decision: BenchmarkDecision,
  results: unknown,
): string;
