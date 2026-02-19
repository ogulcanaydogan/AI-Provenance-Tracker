import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { detectText, getHistory, getExportUrl, getDashboard } from "@/lib/api";

const API_URL = "http://localhost:8000";

// Mock the global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("detectText", () => {
  it("sends POST request with text body and returns mapped result", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        analysis_id: "abc-123",
        confidence: 0.87,
        is_ai_generated: true,
        explanation: "High confidence AI text",
        model_prediction: "gpt-4",
        analysis: {
          perplexity: 10.5,
          burstiness: 0.3,
          vocabulary_richness: 0.42,
          repetition_score: 0.65,
        },
        consensus: { providers: [{ provider: "internal" }] },
      }),
    });

    const result = await detectText("test input");

    expect(mockFetch).toHaveBeenCalledWith(`${API_URL}/api/v1/detect/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "test input" }),
    });
    expect(result.id).toBe("abc-123");
    expect(result.content_type).toBe("text");
    expect(result.verdict).toBe("ai_generated");
    expect(result.confidence_score).toBeGreaterThan(0);
    expect(result.signals).toHaveLength(4);
    expect(result.summary).toBe("High confidence AI text");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Validation error" }),
    });

    await expect(detectText("short")).rejects.toThrow("Validation error");
  });
});

describe("getHistory", () => {
  it("constructs correct URL with pagination and content_type filter", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [],
        total: 0,
      }),
    });

    await getHistory(2, 10, "text");

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("limit=10");
    expect(calledUrl).toContain("offset=10");
    expect(calledUrl).toContain("content_type=text");
  });

  it("omits content_type when not provided", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [], total: 0 }),
    });

    await getHistory(1, 20);

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("content_type");
  });
});

describe("getExportUrl", () => {
  it("builds history export URL with format", () => {
    const url = getExportUrl("history", "csv");
    expect(url).toBe(`${API_URL}/api/v1/analyze/history/export?format=csv`);
  });

  it("builds dashboard export URL with days parameter", () => {
    const url = getExportUrl("dashboard", "json", { days: 30 });
    expect(url).toContain("format=json");
    expect(url).toContain("days=30");
  });

  it("includes contentType filter when provided", () => {
    const url = getExportUrl("history", "json", { contentType: "image" });
    expect(url).toContain("content_type=image");
  });
});

describe("getDashboard", () => {
  it("clamps days between 1 and 90", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ summary: {}, timeline: [] }),
    });

    await getDashboard(200);

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("days=90");
  });

  it("defaults to 14 days", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ summary: {}, timeline: [] }),
    });

    await getDashboard();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("days=14");
  });
});
