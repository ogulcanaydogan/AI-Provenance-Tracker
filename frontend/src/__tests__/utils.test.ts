import { describe, it, expect } from "vitest";
import { formatConfidence, getConfidenceColor } from "@/lib/utils";

describe("formatConfidence", () => {
  it("formats score with one decimal", () => {
    expect(formatConfidence(85.678)).toBe("85.7%");
  });

  it("formats zero", () => {
    expect(formatConfidence(0)).toBe("0.0%");
  });

  it("formats 100", () => {
    expect(formatConfidence(100)).toBe("100.0%");
  });
});

describe("getConfidenceColor", () => {
  it("returns green for low scores", () => {
    expect(getConfidenceColor(10)).toBe("#22c55e");
  });

  it("returns light green for scores 20-39", () => {
    expect(getConfidenceColor(30)).toBe("#86efac");
  });

  it("returns yellow for scores 40-59", () => {
    expect(getConfidenceColor(50)).toBe("#eab308");
  });

  it("returns orange for scores 60-79", () => {
    expect(getConfidenceColor(70)).toBe("#f97316");
  });

  it("returns red for high scores", () => {
    expect(getConfidenceColor(90)).toBe("#ef4444");
  });

  it("returns red for exactly 80", () => {
    expect(getConfidenceColor(80)).toBe("#ef4444");
  });

  it("returns green for exactly 0", () => {
    expect(getConfidenceColor(0)).toBe("#22c55e");
  });
});
