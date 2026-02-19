import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { ConfidenceGauge } from "@/components/detection/ConfidenceGauge";
import { SignalBreakdown } from "@/components/detection/SignalBreakdown";
import { ResultCard } from "@/components/detection/ResultCard";
import { TextInput } from "@/components/detection/TextInput";

describe("AnalysisLoader", () => {
  it("renders accessible loading state", () => {
    render(<AnalysisLoader />);
    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByText("Analyzing content...")).toBeDefined();
  });
});

describe("ConfidenceGauge", () => {
  it("displays score and verdict label", () => {
    render(<ConfidenceGauge score={87} verdict="ai_generated" />);
    expect(screen.getByText("87%")).toBeDefined();
    expect(screen.getByText("AI Generated")).toBeDefined();
  });

  it("shows AI Confidence subtitle", () => {
    render(<ConfidenceGauge score={15} verdict="human" />);
    expect(screen.getByText("AI Confidence")).toBeDefined();
  });

  it("falls back for unknown verdict", () => {
    render(<ConfidenceGauge score={50} verdict="unknown_type" />);
    expect(screen.getByText("unknown_type")).toBeDefined();
  });
});

describe("SignalBreakdown", () => {
  const signals = [
    { name: "perplexity", score: 0.7, weight: 0.3, description: "Perplexity: 10.50" },
    { name: "burstiness", score: 0.4, weight: 0.25, description: "Burstiness: 40%" },
  ];

  it("renders all signals", () => {
    render(<SignalBreakdown signals={signals} />);
    expect(screen.getByText("Perplexity Analysis")).toBeDefined();
    expect(screen.getByText("Burstiness")).toBeDefined();
  });

  it("shows signal descriptions", () => {
    render(<SignalBreakdown signals={signals} />);
    expect(screen.getByText("Perplexity: 10.50")).toBeDefined();
    expect(screen.getByText("Burstiness: 40%")).toBeDefined();
  });

  it("displays percentage for each signal", () => {
    render(<SignalBreakdown signals={signals} />);
    expect(screen.getByText("70%")).toBeDefined();
    expect(screen.getByText("40%")).toBeDefined();
  });

  it("uses fallback label for unknown signal name", () => {
    render(
      <SignalBreakdown
        signals={[{ name: "custom_signal", score: 0.5, weight: 0.2, description: "Custom" }]}
      />
    );
    expect(screen.getByText("custom_signal")).toBeDefined();
  });
});

describe("ResultCard", () => {
  const result = {
    id: "test-1",
    content_type: "text" as const,
    confidence_score: 75.5,
    verdict: "likely_ai" as const,
    signals: [
      { name: "perplexity", score: 0.8, weight: 0.3, description: "Low perplexity" },
    ],
    summary: "This text shows strong AI indicators.",
    analyzed_at: "2025-01-15T10:30:00Z",
    model_prediction: "gpt-4",
  };

  it("renders verdict badge", () => {
    render(<ResultCard result={result} />);
    // Both the badge and the gauge render the verdict label
    const matches = screen.getAllByText("Likely AI");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders summary text", () => {
    render(<ResultCard result={result} />);
    expect(screen.getByText("This text shows strong AI indicators.")).toBeDefined();
  });

  it("renders Detection Signals heading", () => {
    render(<ResultCard result={result} />);
    expect(screen.getByText("Detection Signals")).toBeDefined();
  });
});

describe("TextInput", () => {
  it("renders textarea with placeholder", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    expect(
      screen.getByPlaceholderText("Paste or type text to analyze (minimum 50 characters)...")
    ).toBeDefined();
  });

  it("disables analyze button when text is too short", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    const button = screen.getByText("Analyze Text");
    expect(button).toHaveProperty("disabled", true);
  });

  it("enables analyze button when text is long enough", () => {
    const onAnalyze = vi.fn();
    render(<TextInput onAnalyze={onAnalyze} isLoading={false} />);
    const textarea = screen.getByLabelText("Text to analyze for AI detection");
    fireEvent.change(textarea, { target: { value: "A".repeat(60) } });
    const button = screen.getByText("Analyze Text");
    expect(button).toHaveProperty("disabled", false);
  });

  it("calls onAnalyze with text when button is clicked", () => {
    const onAnalyze = vi.fn();
    render(<TextInput onAnalyze={onAnalyze} isLoading={false} />);
    const textarea = screen.getByLabelText("Text to analyze for AI detection");
    fireEvent.change(textarea, { target: { value: "A".repeat(60) } });
    fireEvent.click(screen.getByText("Analyze Text"));
    expect(onAnalyze).toHaveBeenCalledWith("A".repeat(60));
  });

  it("shows Analyzing... when loading", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={true} />);
    expect(screen.getByText("Analyzing...")).toBeDefined();
  });

  it("loads sample text via Try Sample button", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    fireEvent.click(screen.getByLabelText("Load a sample AI-generated text"));
    const textarea = screen.getByLabelText(
      "Text to analyze for AI detection"
    ) as HTMLTextAreaElement;
    expect(textarea.value.length).toBeGreaterThan(50);
  });

  it("shows Clear button only when text is entered", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.queryByLabelText("Clear text input")).toBeNull();
    const textarea = screen.getByLabelText("Text to analyze for AI detection");
    fireEvent.change(textarea, { target: { value: "some text" } });
    expect(screen.getByLabelText("Clear text input")).toBeDefined();
  });

  it("clears text when Clear button is clicked", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    const textarea = screen.getByLabelText(
      "Text to analyze for AI detection"
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "some text" } });
    fireEvent.click(screen.getByLabelText("Clear text input"));
    expect(textarea.value).toBe("");
  });

  it("shows character count", () => {
    render(<TextInput onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText("0 / 50,000")).toBeDefined();
  });
});
