import { describe, it, expect } from "vitest";
import {
  VERDICT_LABELS,
  VERDICT_COLORS,
  VERDICT_BG_COLORS,
  SAMPLE_AI_TEXT,
} from "@/lib/constants";

const VERDICTS = ["human", "likely_human", "uncertain", "likely_ai", "ai_generated"];

describe("VERDICT_LABELS", () => {
  it("has entries for all verdict types", () => {
    for (const v of VERDICTS) {
      expect(VERDICT_LABELS[v]).toBeDefined();
      expect(VERDICT_LABELS[v].length).toBeGreaterThan(0);
    }
  });
});

describe("VERDICT_COLORS", () => {
  it("has CSS class entries for all verdict types", () => {
    for (const v of VERDICTS) {
      expect(VERDICT_COLORS[v]).toBeDefined();
      expect(VERDICT_COLORS[v]).toMatch(/^text-/);
    }
  });
});

describe("VERDICT_BG_COLORS", () => {
  it("has CSS class entries for all verdict types", () => {
    for (const v of VERDICTS) {
      expect(VERDICT_BG_COLORS[v]).toBeDefined();
      expect(VERDICT_BG_COLORS[v]).toContain("bg-");
    }
  });
});

describe("SAMPLE_AI_TEXT", () => {
  it("is a non-empty string with enough length for analysis", () => {
    expect(SAMPLE_AI_TEXT.length).toBeGreaterThan(50);
  });
});
