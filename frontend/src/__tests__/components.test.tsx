import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DetectError from "@/app/detect/error";
import DetectLoading from "@/app/detect/loading";
import HistoryLoading from "@/app/history/loading";
import DashboardLoading from "@/app/dashboard/loading";
import GlobalError from "@/app/error";
import RootLoading from "@/app/loading";

describe("DetectError", () => {
  it("renders error message and retry button", () => {
    const mockReset = () => {};
    render(<DetectError error={new Error("test error")} reset={mockReset} />);

    expect(screen.getByText("Detection failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go home/i })).toBeInTheDocument();
  });
});

describe("DetectLoading", () => {
  it("renders loading skeleton with accessible status role", () => {
    render(<DetectLoading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("HistoryLoading", () => {
  it("renders loading skeleton with accessible status role", () => {
    render(<HistoryLoading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("DashboardLoading", () => {
  it("renders loading skeleton with accessible status role", () => {
    render(<DashboardLoading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("GlobalError", () => {
  it("renders error UI with retry and home actions", () => {
    const mockReset = () => {};
    render(<GlobalError error={new Error("boom")} reset={mockReset} />);

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument();
  });

  it("displays error digest when available", () => {
    const error = Object.assign(new Error("boom"), { digest: "abc-123" });
    render(<GlobalError error={error} reset={() => {}} />);

    expect(screen.getByText(/abc-123/)).toBeInTheDocument();
  });
});

describe("RootLoading", () => {
  it("renders loading indicator with status role", () => {
    render(<RootLoading />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});
