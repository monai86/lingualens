import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--color-text-strong)",
        panel: "var(--color-surface)",
        clinical: "var(--color-accent)",
        safety: "var(--color-warning-text)",
        line: "var(--color-border)",
        field: "var(--color-surface-strong)",
        moss: "var(--color-success-text)",
        river: "var(--color-info-text)",
        blossom: "var(--color-scope-coral)",
        aqua: "var(--color-accent)",
        pasa: {
          teal: "var(--color-pasa-teal)",
          hover: "var(--color-pasa-teal-hover)",
          soft: "var(--color-pasa-teal-soft)",
          border: "var(--color-pasa-teal-border)",
        },
        scope: {
          coral: "var(--color-scope-coral)",
          hover: "var(--color-scope-coral-hover)",
          soft: "var(--color-scope-coral-soft)",
          border: "var(--color-scope-coral-border)",
        },
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        lift: "var(--shadow-lift)"
      }
    }
  },
  plugins: []
};

export default config;
