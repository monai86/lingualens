import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Shared scanner for the "single-sourced copy" checks. Both the workflow
 * glossary and the clinical safety copy assert the same property: a canonical
 * string is imported from its registry module, never re-inlined by a view. The
 * detection logic lives here so the two registries cannot be guarded by two
 * subtly different scans.
 */

const SOURCE_ROOT = "src";

// Double quote, single quote, and backtick — a label is re-inlined when one of
// these delimiters wraps it on both sides.
const LABEL_QUOTES = "[\"'\u0060]";

export type LabelRegistry = ReadonlyArray<readonly [string, string]>;

/** Every non-test app source module, minus any the caller owns. */
export function sourceModules({ exclude = [] }: { exclude?: readonly string[] } = {}): string[] {
  return readdirSync(resolve(process.cwd(), SOURCE_ROOT), { recursive: true, encoding: "utf8" })
    .map((entry) => `${SOURCE_ROOT}/${entry}`)
    .filter((entry) => entry.endsWith(".ts") || entry.endsWith(".tsx"))
    .filter((entry) => !entry.includes("__tests__"))
    .filter((entry) => !exclude.includes(entry));
}

export function readSourceModule(modulePath: string): string {
  return readFileSync(resolve(process.cwd(), modulePath), "utf8");
}

export function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function isCommentLine(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*");
}

/**
 * One entry per source line that restates a registered label verbatim instead
 * of importing it. A standalone literal or JSX text node renders the label
 * word for word; the same phrase inside a longer sentence is still valid prose
 * and is not flagged.
 *
 * Use this for wording that may legitimately appear inside a sentence. Where
 * the exact phrasing itself is the deliverable — safety claims, above all — use
 * findEmbeddedLabels, which does not let a sentence hide a divergent copy.
 */
export function findReinlinedLabels(
  labels: LabelRegistry,
  { exclude = [] }: { exclude?: readonly string[] } = {},
): string[] {
  const modules = sourceModules({ exclude });
  const sources = modules.map((modulePath) => ({
    modulePath,
    lines: readSourceModule(modulePath).split("\n"),
  }));
  const offenders: string[] = [];

  for (const [constantName, label] of labels) {
    const standaloneLiteral = new RegExp(`${LABEL_QUOTES}${escapeForRegExp(label)}${LABEL_QUOTES}`);
    const standaloneJsxText = new RegExp(`>\\s*${escapeForRegExp(label)}\\s*<`);

    for (const { modulePath, lines } of sources) {
      lines.forEach((line, index) => {
        if (isCommentLine(line)) return;
        if (standaloneLiteral.test(line) || standaloneJsxText.test(line)) {
          offenders.push(`${modulePath}:${index + 1} re-inlines ${constantName}`);
        }
      });
    }
  }

  return offenders;
}

/**
 * One entry per source line that contains a registered phrase at all, whether
 * as a standalone literal or buried in a longer sentence. This is the strict
 * variant for copy that must never diverge: a view that writes
 * "Decision-support only. Not diagnostic. Final report text ..." is restating
 * the claim itself, and only composition from the constant keeps it identical
 * to every other view.
 */
export function findEmbeddedLabels(
  labels: LabelRegistry,
  { exclude = [] }: { exclude?: readonly string[] } = {},
): string[] {
  const offenders: string[] = [];

  for (const modulePath of sourceModules({ exclude })) {
    readSourceModule(modulePath)
      .split("\n")
      .forEach((line, index) => {
        if (isCommentLine(line)) return;
        for (const [constantName, label] of labels) {
          if (line.includes(label)) {
            offenders.push(`${modulePath}:${index + 1} restates ${constantName}`);
          }
        }
      });
  }

  return offenders;
}

/**
 * Registered constants that no other module mentions. A copy constant nobody
 * imports is either dead or a sign the view kept its own literal under a
 * different name, so the check treats it as drift too.
 */
export function findUnusedLabels(
  labels: LabelRegistry,
  { exclude = [] }: { exclude?: readonly string[] } = {},
): string[] {
  const sources = sourceModules({ exclude }).map(readSourceModule);

  return labels
    .map(([constantName]) => constantName)
    .filter((constantName) => !sources.some((text) => text.includes(constantName)));
}
