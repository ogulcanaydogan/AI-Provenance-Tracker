import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

/* ── Mock API before importing page ───────────────────────────────── */

vi.mock("@/lib/api", () => ({
  getDashboard: vi.fn(),
  getEvaluation: vi.fn(),
  getXCollectEstimate: vi.fn(),
  getExportUrl: vi.fn(() => "http://test/export"),
}));

import * as api from "@/lib/api";

const mockGetDashboard = vi.mocked(api.getDashboard);
const mockGetEvaluation = vi.mocked(api.getEvaluation);
const mockGetXCollectEstimate = vi.mocked(api.getXCollectEstimate);
const _mockGetExportUrl = vi.mocked(api.getExportUrl);

/* ── Mock next/link ───────────────────────────────────────────────── */

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import DashboardPage from "@/app/dashboard/page";

/* ── Mock data matching TypeScript interfaces ─────────────────────── */

const mockDashboard = {
  window_days: 14,
  summary: {
    total_analyses_all_time: 150,
    total_analyses_window: 42,
    ai_detected_window: 20,
    human_detected_window: 22,
    ai_rate_window: 0.476,
    average_confidence_window: 0.72,
  },
  by_type_window: { text: 30, image: 10, audio: 2 },
  by_source_window: { api: 35, extension: 7 },
  top_models_window: [
    { model: "gpt-4", count: 15 },
    { model: "claude-3", count: 5 },
  ],
  alerts_window: [],
  timeline: [
    { date: "2026-02-06", total: 5, ai_detected: 3, human_detected: 2 },
    { date: "2026-02-07", total: 3, ai_detected: 1, human_detected: 2 },
  ],
};

const mockEvaluation = {
  window_days: 30,
  total_reports: 1,
  by_content_type: { text: 1 },
  latest_by_content_type: {
    text: {
      generated_at: "2026-02-10T12:00:00Z",
      sample_count: 50,
      recommended_threshold: 0.55,
      precision: 0.85,
      recall: 0.78,
      f1: 0.81,
      accuracy: 0.82,
    },
  },
  trend: [
    {
      date: "2026-02-10",
      generated_at: "2026-02-10T12:00:00Z",
      content_type: "text",
      sample_count: 50,
      threshold: 0.55,
      precision: 0.85,
      recall: 0.78,
      f1: 0.81,
      accuracy: 0.82,
    },
  ],
  alerts: [],
};

const mockEstimate = {
  estimated_requests: 5,
  worst_case_requests: 12,
  page_cap: 1,
  target_limit: 50,
  mention_limit: 20,
  interaction_limit: 10,
  guard_enabled: true,
  max_requests_per_run: 8,
  within_budget: true,
  recommended_max_posts: 60,
};

/* ── Helpers ──────────────────────────────────────────────────────── */

function setupSuccessMocks() {
  mockGetDashboard.mockResolvedValue(mockDashboard);
  mockGetEvaluation.mockResolvedValue(mockEvaluation);
  mockGetXCollectEstimate.mockResolvedValue(mockEstimate);
}

/* ── Tests ────────────────────────────────────────────────────────── */

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { name: /API Analytics Dashboard/i })).toBeDefined();
  });

  it("shows loading state before data arrives", () => {
    // Never-resolving promise to keep loading state
    mockGetDashboard.mockReturnValue(new Promise(() => {}));
    mockGetEvaluation.mockReturnValue(new Promise(() => {}));
    mockGetXCollectEstimate.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByText(/Loading dashboard/i)).toBeDefined();
  });

  it("renders stat cards with correct values", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("42")).toBeDefined();
    });
    expect(screen.getByText("150")).toBeDefined();
    expect(screen.getByText("47.6%")).toBeDefined();
    expect(screen.getByText("72.0%")).toBeDefined();
  });

  it("renders stat card labels", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Window Analyses")).toBeDefined();
    });
    expect(screen.getByText("AI Rate")).toBeDefined();
    expect(screen.getByText("Avg Confidence")).toBeDefined();
    expect(screen.getByText("All-Time Analyses")).toBeDefined();
  });

  it("renders Daily Activity section", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Daily Activity")).toBeDefined();
    });
    expect(screen.getByText("2026-02-06")).toBeDefined();
    expect(screen.getByText("2026-02-07")).toBeDefined();
  });

  it("renders By Content Type section", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("By Content Type")).toBeDefined();
    });
    // Check for counts next to type names (30 for text, 10 for image)
    expect(screen.getByText("30")).toBeDefined();
    expect(screen.getByText("10")).toBeDefined();
  });

  it("renders By Source section", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("By Source")).toBeDefined();
    });
    expect(screen.getByText("api")).toBeDefined();
    expect(screen.getByText("extension")).toBeDefined();
  });

  it("renders Top Predicted Models", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Top Predicted Models")).toBeDefined();
    });
    expect(screen.getByText("gpt-4")).toBeDefined();
    expect(screen.getByText("claude-3")).toBeDefined();
  });

  it("renders Evaluation Trend section", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Evaluation Trend")).toBeDefined();
    });
    expect(screen.getByText("Latest by Content Type")).toBeDefined();
    expect(screen.getByText("Recent Snapshots")).toBeDefined();
  });

  it("renders X Collection Cost Precheck", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("X Collection Cost Precheck")).toBeDefined();
    });
    expect(screen.getByText("Recalculate")).toBeDefined();
  });

  it("shows error state on API failure", async () => {
    mockGetDashboard.mockRejectedValue(new Error("Server error"));
    mockGetEvaluation.mockRejectedValue(new Error("Server error"));
    mockGetXCollectEstimate.mockResolvedValue(mockEstimate);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeDefined();
    });
  });

  it("window selector changes refetch data", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("42")).toBeDefined();
    });
    const select = screen.getByLabelText("Window");
    fireEvent.change(select, { target: { value: "30" } });
    expect(mockGetDashboard).toHaveBeenCalledWith(30);
  });

  it("has CSV and JSON export buttons", async () => {
    setupSuccessMocks();
    render(<DashboardPage />);
    expect(screen.getByText("CSV")).toBeDefined();
    expect(screen.getByText("JSON")).toBeDefined();
  });
});
