import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTextDetection } from "@/hooks/useTextDetection";
import { useImageDetection } from "@/hooks/useImageDetection";
import { useAudioDetection } from "@/hooks/useAudioDetection";
import { useVideoDetection } from "@/hooks/useVideoDetection";

vi.mock("@/lib/api", () => ({
  detectTextStream: vi.fn(),
  detectImage: vi.fn(),
  detectAudio: vi.fn(),
  detectVideo: vi.fn(),
}));

import {
  detectTextStream,
  detectImage,
  detectAudio,
  detectVideo,
} from "@/lib/api";

const mockResult = {
  id: "test-1",
  content_type: "text" as const,
  confidence_score: 85,
  verdict: "ai_generated" as const,
  signals: [],
  summary: "Test result",
  analyzed_at: "2025-01-01T00:00:00Z",
  model_prediction: "gpt-4",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useTextDetection", () => {
  it("starts in idle state", () => {
    const { result } = renderHook(() => useTextDetection());
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.progressMessage).toBeNull();
  });

  it("transitions to success on successful analysis", async () => {
    vi.mocked(detectTextStream).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useTextDetection());

    await act(async () => {
      await result.current.analyze("test text");
    });

    expect(result.current.status).toBe("success");
    expect(result.current.result).toEqual(mockResult);
    expect(result.current.error).toBeNull();
    expect(result.current.progressMessage).toBeNull();
  });

  it("transitions to error on failure", async () => {
    vi.mocked(detectTextStream).mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useTextDetection());

    await act(async () => {
      await result.current.analyze("test text");
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Network error");
    expect(result.current.result).toBeNull();
  });

  it("handles non-Error failures", async () => {
    vi.mocked(detectTextStream).mockRejectedValue("unknown");
    const { result } = renderHook(() => useTextDetection());

    await act(async () => {
      await result.current.analyze("test text");
    });

    expect(result.current.error).toBe("Analysis failed");
  });

  it("invokes onProgress callback with progress messages", async () => {
    vi.mocked(detectTextStream).mockImplementation(async (_text, onProgress) => {
      onProgress?.({
        event: "started",
        stage: "started",
        message: "Detection started",
        payload: {},
      });
      return mockResult;
    });
    const { result } = renderHook(() => useTextDetection());

    await act(async () => {
      await result.current.analyze("test text");
    });

    expect(detectTextStream).toHaveBeenCalledWith("test text", expect.any(Function));
  });

  it("resets state correctly", async () => {
    vi.mocked(detectTextStream).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useTextDetection());

    await act(async () => {
      await result.current.analyze("test text");
    });
    expect(result.current.status).toBe("success");

    act(() => {
      result.current.reset();
    });
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.progressMessage).toBeNull();
  });
});

describe("useImageDetection", () => {
  const file = new File(["img"], "test.png", { type: "image/png" });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useImageDetection());
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("transitions to success on successful analysis", async () => {
    vi.mocked(detectImage).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useImageDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("success");
    expect(result.current.result).toEqual(mockResult);
  });

  it("transitions to error on failure", async () => {
    vi.mocked(detectImage).mockRejectedValue(new Error("Upload failed"));
    const { result } = renderHook(() => useImageDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Upload failed");
  });

  it("handles non-Error failures", async () => {
    vi.mocked(detectImage).mockRejectedValue(42);
    const { result } = renderHook(() => useImageDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.error).toBe("Analysis failed");
  });

  it("resets state correctly", async () => {
    vi.mocked(detectImage).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useImageDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    act(() => {
      result.current.reset();
    });
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });
});

describe("useAudioDetection", () => {
  const file = new File(["wav"], "test.wav", { type: "audio/wav" });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useAudioDetection());
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("transitions to success on successful analysis", async () => {
    vi.mocked(detectAudio).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useAudioDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("success");
    expect(result.current.result).toEqual(mockResult);
  });

  it("transitions to error on failure", async () => {
    vi.mocked(detectAudio).mockRejectedValue(new Error("Audio error"));
    const { result } = renderHook(() => useAudioDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Audio error");
  });

  it("resets state correctly", async () => {
    vi.mocked(detectAudio).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useAudioDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    act(() => {
      result.current.reset();
    });
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
  });
});

describe("useVideoDetection", () => {
  const file = new File(["mp4"], "test.mp4", { type: "video/mp4" });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useVideoDetection());
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("transitions to success on successful analysis", async () => {
    vi.mocked(detectVideo).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useVideoDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("success");
    expect(result.current.result).toEqual(mockResult);
  });

  it("transitions to error on failure", async () => {
    vi.mocked(detectVideo).mockRejectedValue(new Error("Video error"));
    const { result } = renderHook(() => useVideoDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Video error");
  });

  it("resets state correctly", async () => {
    vi.mocked(detectVideo).mockResolvedValue(mockResult);
    const { result } = renderHook(() => useVideoDetection());

    await act(async () => {
      await result.current.analyze(file);
    });

    act(() => {
      result.current.reset();
    });
    expect(result.current.status).toBe("idle");
    expect(result.current.result).toBeNull();
  });
});
