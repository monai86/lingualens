import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SettingsNavigation } from "@/features/settings/components/settings-navigation";

function appFile(relative: string): string {
  return readFileSync(resolve(process.cwd(), relative), "utf8");
}

// Third-party component/design frameworks that would compete with the in-repo
// design system plus Tailwind. Headless primitive libraries are intentionally
// absent from this list: they ship no visual language of their own.
const COMPETING_UI_FRAMEWORKS = [
  "@astryxdesign/",
  "@mui/",
  "@material-ui/",
  "@chakra-ui/",
  "@mantine/",
  "antd",
  "bootstrap",
  "react-bootstrap",
  "semantic-ui",
  "primereact",
];

function isCompetingUiFramework(packageName: string): boolean {
  return COMPETING_UI_FRAMEWORKS.some((framework) =>
    framework.endsWith("/") ? packageName.startsWith(framework) : packageName === framework,
  );
}

function appSourceFiles(): string[] {
  return readdirSync(resolve(process.cwd(), "src"), { recursive: true, encoding: "utf8" })
    .map((entry) => `src/${entry}`)
    .filter((entry) => entry.endsWith(".ts") || entry.endsWith(".tsx"))
    .filter((entry) => !entry.includes("__tests__"));
}

describe("final UI remediation contracts", () => {
  it("keeps the selected-state accent family clinical teal and separate from warning amber", () => {
    const tokens = appFile("src/design-system/tokens.css");

    expect(tokens).toContain("--color-accent: #0f766e;");
    expect(tokens).toContain("--color-accent-subtle: #0d9488;");
    expect(tokens).toContain("--color-warning-text: #92400e;");
    expect(tokens).not.toContain("--color-accent-subtle: #b7791f;");
  });

  it("uses only the LinguaLens design system and Tailwind in the active app foundation", () => {
    const packageManifest = JSON.parse(appFile("package.json")) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const dependencyNames = [
      ...Object.keys(packageManifest.dependencies ?? {}),
      ...Object.keys(packageManifest.devDependencies ?? {}),
    ];
    // Nothing in the competing set may be declared as a dependency, not just the
    // one framework that happened to be banned first.
    expect(dependencyNames.filter((name) => isCompetingUiFramework(name))).toEqual([]);

    // A framework can also arrive without being declared, so scan every app
    // source module instead of the two files that previously held an import.
    const sourceOffenders: string[] = [];
    for (const relative of appSourceFiles()) {
      const text = appFile(relative);
      for (const framework of COMPETING_UI_FRAMEWORKS) {
        if (text.includes(framework)) {
          sourceOffenders.push(`${relative} references ${framework}`);
        }
      }
    }
    expect(sourceOffenders).toEqual([]);
  });

  it("uses valid escaped utility selectors in the print stylesheet", () => {
    const globalCss = appFile("src/styles/globals.css");

    expect(globalCss).toContain("header.lg\\:hidden,");
    expect(globalCss).toContain(".print\\:hidden {");
    expect(globalCss).not.toContain("\\\\:hidden");
  });

  it("does not retain unsupported dashboard score primitives", () => {
    const primitives = appFile("src/components/workbench-ui.tsx");

    for (const name of [
      "AppHeader",
      "QuickActionCard",
      "SessionCard",
      "ResultMetricCard",
      "SmallListRow",
      "PrimaryActionRow",
      "ProgressSummaryCard",
    ]) {
      expect(primitives).not.toContain(`function ${name}`);
    }
    expect(primitives).not.toContain("Overall Progress");
    expect(primitives).not.toContain("Pronunciation");
  });

  it("renders mobile Settings as a role-safe category list", () => {
    render(
      <SettingsNavigation
        sections={["account", "organization", "accessibility", "notifications", "privacy", "export", "help"]}
        selected="account"
        onSelect={vi.fn()}
      />,
    );

    const mobileNavigation = screen.getByRole("navigation", { name: "Settings categories mobile" });
    expect(within(mobileNavigation).getByRole("link", { name: /Account/i })).toBeInTheDocument();
    expect(within(mobileNavigation).getByRole("link", { name: /Privacy & Security/i })).toBeInTheDocument();
    expect(within(mobileNavigation).queryByRole("link", { name: /Team/i })).not.toBeInTheDocument();
  });
});
