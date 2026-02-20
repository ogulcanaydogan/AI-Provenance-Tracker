import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

/* ── Mock hooks before importing page components ───────────────────── */

const mockTextHook = {
  status: "idle" as string,
  result: null as unknown,
  error: null as string | null,
  progressMessage: null as string | null,
  analyze: vi.fn(),
  reset: vi.fn(),
};

const mockImageHook = {
  status: "idle" as string,
  result: null as unknown,
  error: null as string | null,
  analyze: vi.fn(),
  reset: vi.fn(),
};

const mockAudioHook = {
  status: "idle" as string,
  result: null as unknown,
  error: null as string | null,
  analyze: vi.fn(),
  reset: vi.fn(),
};

const mockVideoHook = {
  status: "idle" as string,
  result: null as unknown,
  error: null as string | null,
  analyze: vi.fn(),
  reset: vi.fn(),
};

vi.mock("@/hooks/useTextDetection", () => ({
  useTextDetection: () => mockTextHook,
}));

vi.mock("@/hooks/useImageDetection", () => ({
  useImageDetection: () => mockImageHook,
}));

vi.mock("@/hooks/useAudioDetection", () => ({
  useAudioDetection: () => mockAudioHook,
}));

vi.mock("@/hooks/useVideoDetection", () => ({
  useVideoDetection: () => mockVideoHook,
}));

import TextDetectionPage from "@/app/detect/text/page";
import ImageDetectionPage from "@/app/detect/image/page";
import AudioDetectionPage from "@/app/detect/audio/page";
import VideoDetectionPage from "@/app/detect/video/page";

const mockDetectionResult = {
  id: "test-1",
  content_type: "text" as const,
  confidence_score: 85,
  verdict: "ai_generated" as const,
  signals: [
    { name: "perplexity", score: 0.8, weight: 0.3, description: "Low perplexity" },
  ],
  summary: "Strong AI indicators detected.",
  analyzed_at: "2025-01-15T10:30:00Z",
  model_prediction: "gpt-4",
};

function resetAllHooks() {
  [mockTextHook, mockImageHook, mockAudioHook, mockVideoHook].forEach((h) => {
    h.status = "idle";
    h.result = null;
    h.error = null;
    h.analyze.mockClear();
    h.reset.mockClear();
  });
  if ("progressMessage" in mockTextHook) {
    mockTextHook.progressMessage = null;
  }
}

beforeEach(() => {
  resetAllHooks();
});

/* ── Text Detection Page ───────────────────────────────────────────── */

describe("TextDetectionPage", () => {
  it("renders heading and description", () => {
    render(<TextDetectionPage />);
    expect(screen.getByText("Text Detection")).toBeDefined();
    expect(
      screen.getByText(/Paste or type text to analyze/)
    ).toBeDefined();
  });

  it("renders TextInput in idle state", () => {
    render(<TextDetectionPage />);
    expect(screen.getByPlaceholderText(/minimum 50 characters/)).toBeDefined();
  });

  it("shows AnalysisLoader when loading", () => {
    mockTextHook.status = "loading";
    render(<TextDetectionPage />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("shows progress message during loading", () => {
    mockTextHook.status = "loading";
    mockTextHook.progressMessage = "Computing consensus...";
    render(<TextDetectionPage />);
    expect(screen.getByText("Computing consensus...")).toBeDefined();
  });

  it("shows error alert on error status", () => {
    mockTextHook.status = "error";
    mockTextHook.error = "Network timeout";
    render(<TextDetectionPage />);
    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText("Network timeout")).toBeDefined();
  });

  it("shows ResultCard and reset button on success", () => {
    mockTextHook.status = "success";
    mockTextHook.result = mockDetectionResult;
    render(<TextDetectionPage />);
    expect(screen.getByText("Strong AI indicators detected.")).toBeDefined();
    expect(screen.getByText("Analyze another text")).toBeDefined();
  });

  it("calls reset when reset button is clicked", () => {
    mockTextHook.status = "success";
    mockTextHook.result = mockDetectionResult;
    render(<TextDetectionPage />);
    fireEvent.click(screen.getByText("Analyze another text"));
    expect(mockTextHook.reset).toHaveBeenCalledOnce();
  });
});

/* ── Image Detection Page ──────────────────────────────────────────── */

describe("ImageDetectionPage", () => {
  it("renders heading and description", () => {
    render(<ImageDetectionPage />);
    expect(screen.getByText("Image Detection")).toBeDefined();
    expect(screen.getByText(/Upload an image to analyze/)).toBeDefined();
  });

  it("renders ImageUpload dropzone in idle state", () => {
    render(<ImageDetectionPage />);
    expect(screen.getByText(/Drag & drop an image/)).toBeDefined();
  });

  it("shows AnalysisLoader when loading", () => {
    mockImageHook.status = "loading";
    render(<ImageDetectionPage />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("shows error alert on error status", () => {
    mockImageHook.status = "error";
    mockImageHook.error = "File too large";
    render(<ImageDetectionPage />);
    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText("File too large")).toBeDefined();
  });

  it("shows reset button on success", () => {
    mockImageHook.status = "success";
    mockImageHook.result = mockDetectionResult;
    render(<ImageDetectionPage />);
    expect(screen.getByText("Analyze another image")).toBeDefined();
  });
});

/* ── Audio Detection Page ──────────────────────────────────────────── */

describe("AudioDetectionPage", () => {
  it("renders heading and Beta badge", () => {
    render(<AudioDetectionPage />);
    expect(screen.getByText("Audio Detection")).toBeDefined();
    expect(screen.getByText("Beta")).toBeDefined();
  });

  it("renders description", () => {
    render(<AudioDetectionPage />);
    expect(screen.getByText(/Upload a WAV file to analyze/)).toBeDefined();
  });

  it("renders AudioUpload dropzone in idle state", () => {
    render(<AudioDetectionPage />);
    expect(screen.getByText(/Drag & drop a WAV file/)).toBeDefined();
  });

  it("shows AnalysisLoader when loading", () => {
    mockAudioHook.status = "loading";
    render(<AudioDetectionPage />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("shows error alert on error status", () => {
    mockAudioHook.status = "error";
    mockAudioHook.error = "Unsupported format";
    render(<AudioDetectionPage />);
    expect(screen.getByText("Unsupported format")).toBeDefined();
  });

  it("shows reset button on success", () => {
    mockAudioHook.status = "success";
    mockAudioHook.result = mockDetectionResult;
    render(<AudioDetectionPage />);
    expect(screen.getByText("Analyze another audio file")).toBeDefined();
  });
});

/* ── Video Detection Page ──────────────────────────────────────────── */

describe("VideoDetectionPage", () => {
  it("renders heading and Beta badge", () => {
    render(<VideoDetectionPage />);
    expect(screen.getByText("Video Detection")).toBeDefined();
    expect(screen.getByText("Beta")).toBeDefined();
  });

  it("renders description", () => {
    render(<VideoDetectionPage />);
    expect(screen.getByText(/Upload a short video clip to analyze/)).toBeDefined();
  });

  it("renders VideoUpload dropzone in idle state", () => {
    render(<VideoDetectionPage />);
    expect(screen.getByText(/Drag & drop a video/)).toBeDefined();
  });

  it("shows AnalysisLoader when loading", () => {
    mockVideoHook.status = "loading";
    render(<VideoDetectionPage />);
    expect(screen.getByRole("status")).toBeDefined();
  });

  it("shows error alert on error status", () => {
    mockVideoHook.status = "error";
    mockVideoHook.error = "Server error";
    render(<VideoDetectionPage />);
    expect(screen.getByText("Server error")).toBeDefined();
  });

  it("shows reset button on success", () => {
    mockVideoHook.status = "success";
    mockVideoHook.result = mockDetectionResult;
    render(<VideoDetectionPage />);
    expect(screen.getByText("Analyze another video")).toBeDefined();
  });
});

/* ── Legacy Components (TextDetector, ImageDetector on homepage) ──── */

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => {
    const { src, alt, ...rest } = props;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src as string} alt={alt as string} {...rest} />;
  },
}));

// Global fetch mock for legacy detectors
const originalFetch = globalThis.fetch;
beforeEach(() => {
  globalThis.fetch = vi.fn();
});

import TextDetector from "@/components/TextDetector";
import ImageDetector from "@/components/ImageDetector";

describe("TextDetector (legacy)", () => {
  it("renders textarea and analyze button", () => {
    render(<TextDetector />);
    expect(screen.getByPlaceholderText(/Paste the text you want to analyze/)).toBeDefined();
    expect(screen.getByText("Analyze Text")).toBeDefined();
  });

  it("disables Analyze button when text is empty", () => {
    render(<TextDetector />);
    const button = screen.getByText("Analyze Text").closest("button");
    expect(button?.disabled).toBe(true);
  });

  it("enables Analyze button when text is entered", () => {
    render(<TextDetector />);
    fireEvent.change(screen.getByPlaceholderText(/Paste the text/), {
      target: { value: "Some test text" },
    });
    const button = screen.getByText("Analyze Text").closest("button");
    expect(button?.disabled).toBe(false);
  });

  it("shows character and word counts", () => {
    render(<TextDetector />);
    expect(screen.getByText("0 / 50,000 characters")).toBeDefined();
    expect(screen.getByText("0 words")).toBeDefined();
  });

  it("clears text when Clear button is clicked", () => {
    render(<TextDetector />);
    const textarea = screen.getByPlaceholderText(
      /Paste the text/
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "hello world" } });
    expect(textarea.value).toBe("hello world");
    fireEvent.click(screen.getByText("Clear"));
    expect(textarea.value).toBe("");
  });
});

describe("ImageDetector (legacy)", () => {
  it("renders upload area", () => {
    render(<ImageDetector />);
    expect(screen.getByText(/Upload an image to analyze/)).toBeDefined();
  });

  it("renders format guidance text", () => {
    render(<ImageDetector />);
    expect(screen.getByText(/Supports PNG, JPEG, WebP/)).toBeDefined();
  });

  it("disables Analyze button when no file is selected", () => {
    render(<ImageDetector />);
    const button = screen.getByText("Analyze Image").closest("button");
    expect(button?.disabled).toBe(true);
  });
});

// Restore global fetch
afterAll(() => {
  globalThis.fetch = originalFetch;
});
