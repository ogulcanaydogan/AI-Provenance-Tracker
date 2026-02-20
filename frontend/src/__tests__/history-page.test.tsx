import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

/* ── Mock API before importing page ───────────────────────────────── */

vi.mock("@/lib/api", () => ({
  getHistory: vi.fn(),
  getExportUrl: vi.fn(() => "http://test/export"),
}));

import * as api from "@/lib/api";

const mockGetHistory = vi.mocked(api.getHistory);
const _mockGetExportUrl = vi.mocked(api.getExportUrl);

/* ── Mock next/link ───────────────────────────────────────────────── */

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import HistoryPage from "@/app/history/page";

/* ── Mock data matching DetectionResult[] ─────────────────────────── */

const mockItems = [
  {
    id: "abc-1",
    content_type: "text" as const,
    confidence_score: 85,
    verdict: "ai_generated" as const,
    signals: [],
    summary: "AI text sample",
    analyzed_at: "2026-02-15T10:00:00Z",
    model_prediction: "gpt-4",
  },
  {
    id: "abc-2",
    content_type: "image" as const,
    confidence_score: 30,
    verdict: "likely_human" as const,
    signals: [],
    summary: "Natural photo",
    analyzed_at: "2026-02-15T09:00:00Z",
    model_prediction: null,
  },
];

const mockHistoryResponse = {
  items: mockItems,
  total: 2,
  page: 1,
  per_page: 20,
};

const mockPaginatedResponse = {
  items: mockItems,
  total: 60,
  page: 1,
  per_page: 20,
};

/* ── Tests ────────────────────────────────────────────────────────── */

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading", async () => {
    mockGetHistory.mockResolvedValue(mockHistoryResponse);
    render(<HistoryPage />);
    expect(screen.getByRole("heading", { name: /Analysis History/i })).toBeDefined();
  });

  it("shows loading state", () => {
    mockGetHistory.mockReturnValue(new Promise(() => {}));
    render(<HistoryPage />);
    expect(screen.getByRole("status")).toBeDefined();
    expect(screen.getByText("Loading...")).toBeDefined();
  });

  it("renders analysis items with verdict badges", async () => {
    mockGetHistory.mockResolvedValue(mockHistoryResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("AI Generated")).toBeDefined();
    });
    expect(screen.getByText("Likely Human")).toBeDefined();
  });

  it("renders analysis items with confidence scores", async () => {
    mockGetHistory.mockResolvedValue(mockHistoryResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("85.0%")).toBeDefined();
    });
    expect(screen.getByText("30.0%")).toBeDefined();
  });

  it("renders empty state when no items", async () => {
    mockGetHistory.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("No analyses yet.")).toBeDefined();
    });
  });

  it("renders empty state with filter message", async () => {
    mockGetHistory.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("No analyses yet.")).toBeDefined();
    });
    // Change filter to audio
    const select = screen.getByLabelText("Filter by content type");
    mockGetHistory.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
    });
    fireEvent.change(select, { target: { value: "audio" } });
    await waitFor(() => {
      expect(screen.getByText("No audio analyses found.")).toBeDefined();
    });
  });

  it("renders pagination when multiple pages exist", async () => {
    mockGetHistory.mockResolvedValue(mockPaginatedResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("Page 1 of 3")).toBeDefined();
    });
  });

  it("previous button disabled on first page", async () => {
    mockGetHistory.mockResolvedValue(mockPaginatedResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("Page 1 of 3")).toBeDefined();
    });
    const prevButton = screen.getByLabelText("Previous page");
    expect(prevButton).toHaveProperty("disabled", true);
  });

  it("next button navigates to page 2", async () => {
    mockGetHistory.mockResolvedValue(mockPaginatedResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("Page 1 of 3")).toBeDefined();
    });
    const nextButton = screen.getByLabelText("Next page");
    fireEvent.click(nextButton);
    expect(mockGetHistory).toHaveBeenCalledWith(2, 20, undefined);
  });

  it("content type filter changes refetch data", async () => {
    mockGetHistory.mockResolvedValue(mockHistoryResponse);
    render(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("AI Generated")).toBeDefined();
    });
    const select = screen.getByLabelText("Filter by content type");
    fireEvent.change(select, { target: { value: "image" } });
    expect(mockGetHistory).toHaveBeenCalledWith(1, 20, "image");
  });

  it("has CSV and JSON export buttons", async () => {
    mockGetHistory.mockResolvedValue(mockHistoryResponse);
    render(<HistoryPage />);
    expect(screen.getByText("CSV")).toBeDefined();
    expect(screen.getByText("JSON")).toBeDefined();
  });
});
