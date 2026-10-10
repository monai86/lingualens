import { describe, expect, it } from "vitest";

import {
  EVIDENCE_REVIEW_NOUN,
  EXTRACT_FEATURES_ACTION,
  FEATURE_EXTRACTION_NOUN,
  GENERATE_EVIDENCE_REVIEW_ACTION,
  GENERATE_REPORT_ACTION,
} from "@/lib/workflow-glossary";
import { findReinlinedLabels, findUnusedLabels } from "./support/single-sourcing";

const GLOSSARY_MODULE = "src/lib/workflow-glossary.ts";
const EXCLUDE_SELF = { exclude: [GLOSSARY_MODULE] };

const GLOSSARY_LABELS: ReadonlyArray<readonly [string, string]> = [
  ["EXTRACT_FEATURES_ACTION", EXTRACT_FEATURES_ACTION],
  ["FEATURE_EXTRACTION_NOUN", FEATURE_EXTRACTION_NOUN],
  ["GENERATE_EVIDENCE_REVIEW_ACTION", GENERATE_EVIDENCE_REVIEW_ACTION],
  ["EVIDENCE_REVIEW_NOUN", EVIDENCE_REVIEW_NOUN],
  ["GENERATE_REPORT_ACTION", GENERATE_REPORT_ACTION],
];

describe("workflow glossary", () => {
  it("keeps one canonical action label for feature extraction", () => {
    expect(EXTRACT_FEATURES_ACTION).toBe("Extract language-sample features");
  });

  it("keeps one canonical noun for feature extraction", () => {
    expect(FEATURE_EXTRACTION_NOUN).toBe("Feature extraction");
  });

  it("keeps one canonical action label for the evidence review", () => {
    expect(GENERATE_EVIDENCE_REVIEW_ACTION).toBe("Generate evidence review");
  });

  it("keeps one canonical noun for the evidence review", () => {
    expect(EVIDENCE_REVIEW_NOUN).toBe("Evidence review");
  });

  it("keeps one canonical action label for the report draft", () => {
    expect(GENERATE_REPORT_ACTION).toBe("Generate report draft");
  });

  it("registers every exported workflow label, so none escapes the scan", () => {
    expect(GLOSSARY_LABELS.map(([name]) => name).sort()).toEqual(
      [
        "EVIDENCE_REVIEW_NOUN",
        "EXTRACT_FEATURES_ACTION",
        "FEATURE_EXTRACTION_NOUN",
        "GENERATE_EVIDENCE_REVIEW_ACTION",
        "GENERATE_REPORT_ACTION",
      ],
    );
  });

  it("keeps each workflow label single-sourced instead of re-inlined by a view", () => {
    // A re-inlined label still renders the right words today, so only this check
    // catches that copy silently drifting away from the glossary later.
    expect(findReinlinedLabels(GLOSSARY_LABELS, EXCLUDE_SELF)).toEqual([]);
  });

  it("leaves no registered workflow label unimported", () => {
    expect(findUnusedLabels(GLOSSARY_LABELS, EXCLUDE_SELF)).toEqual([]);
  });

  it("distinguishes the feature-extraction and evidence-review steps", () => {
    expect(EXTRACT_FEATURES_ACTION.toLowerCase()).not.toContain(EVIDENCE_REVIEW_NOUN.toLowerCase());
    expect(GENERATE_EVIDENCE_REVIEW_ACTION.toLowerCase()).toContain(EVIDENCE_REVIEW_NOUN.toLowerCase());
    expect(GENERATE_EVIDENCE_REVIEW_ACTION.toLowerCase()).not.toContain(FEATURE_EXTRACTION_NOUN.toLowerCase());
  });
});
