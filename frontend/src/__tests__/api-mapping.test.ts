import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  detectImage,
  detectAudio,
  detectVideo,
  getAnalysis,
  getEvaluation,
} from "@/lib/api";

const API_URL = "http://localhost:8000";

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("detectImage", () => {
  it("sends FormData with file and returns mapped result", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        analysis_id: "img-1",
        confidence: 0.65,
        is_ai_generated: true,
        explanation: "Suspicious frequency patterns",
        model_prediction: null,
        analysis: {
          frequency_anomaly: 0.7,
          artifact_score: 0.5,
          metadata_flags: ["missing_exif"],
        },
      }),
    });

    const file = new File(["fake"], "test.png", { type: "image/png" });
    const result = await detectImage(file);

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_URL}/api/v1/detect/image`,
      expect.objectContaining({ method: "POST" })
    );
    expect(result.id).toBe("img-1");
    expect(result.content_type).toBe("image");
    expect(result.signals).toHaveLength(3);
    expect(result.signals[0].name).toBe("frequency_analysis");
  });
});

describe("detectAudio", () => {
  it("sends FormData and returns mapped audio result", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        analysis_id: "aud-1",
        confidence: 0.3,
        is_ai_generated: false,
        explanation: "Likely natural audio",
        model_prediction: null,
        analysis: {
          spectral_flatness: 0.25,
          dynamic_range: 0.8,
          clipping_ratio: 0.01,
          zero_crossing_rate: 0.3,
          sample_rate: 44100,
          duration_seconds: 5.0,
          channel_count: 2,
        },
      }),
    });

    const file = new File(["fake"], "test.wav", { type: "audio/wav" });
    const result = await detectAudio(file);

    expect(result.content_type).toBe("audio");
    expect(result.signals).toHaveLength(4);
    expect(result.verdict).toBe("likely_human");
  });
});

describe("detectVideo", () => {
  it("sends FormData and returns mapped video result", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        analysis_id: "vid-1",
        confidence: 0.5,
        is_ai_generated: false,
        explanation: "Inconclusive analysis",
        model_prediction: null,
        analysis: {
          entropy_score: 6.5,
          byte_uniformity: 0.4,
          repeated_chunk_ratio: 0.05,
          signature_flags: [],
          file_size_mb: 12.5,
        },
      }),
    });

    const file = new File(["fake"], "test.mp4", { type: "video/mp4" });
    const result = await detectVideo(file);

    expect(result.content_type).toBe("video");
    expect(result.signals).toHaveLength(4);
  });
});

describe("getAnalysis", () => {
  it("fetches detailed analysis by ID and maps result", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content_id: "abc",
        analysis_type: "text",
        details: {
          analysis_id: "abc",
          content_type: "text",
          result: {
            analysis_id: "abc",
            confidence: 0.9,
            is_ai_generated: true,
            explanation: "AI generated",
            model_prediction: "gpt-4",
            analysis: {
              perplexity: 8,
              burstiness: 0.2,
              vocabulary_richness: 0.4,
              repetition_score: 0.7,
            },
          },
        },
        metadata: { created_at: "2025-01-01T00:00:00Z" },
      }),
    });

    const result = await getAnalysis("abc");

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_URL}/api/v1/analyze/detailed`,
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("abc"),
      })
    );
    expect(result.id).toBe("abc");
    expect(result.analyzed_at).toBe("2025-01-01T00:00:00Z");
  });
});

describe("getEvaluation", () => {
  it("clamps days between 1 and 365", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        window_days: 365,
        total_reports: 0,
        by_content_type: {},
        latest_by_content_type: {},
        trend: [],
        alerts: [],
      }),
    });

    await getEvaluation(500);

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("days=365");
  });

  it("defaults to 90 days", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        window_days: 90,
        total_reports: 0,
        by_content_type: {},
        latest_by_content_type: {},
        trend: [],
        alerts: [],
      }),
    });

    await getEvaluation();

    const calledUrl = mockFetch.mock.calls[0][0] as string;
    expect(calledUrl).toContain("days=90");
  });
});
