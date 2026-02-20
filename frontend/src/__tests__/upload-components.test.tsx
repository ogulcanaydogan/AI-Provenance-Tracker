import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ImageUpload } from "@/components/detection/ImageUpload";
import { AudioUpload } from "@/components/detection/AudioUpload";
import { VideoUpload } from "@/components/detection/VideoUpload";

describe("ImageUpload", () => {
  it("renders dropzone with upload instructions", () => {
    render(<ImageUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Drag & drop an image/)).toBeDefined();
  });

  it("renders correct format and size text", () => {
    render(<ImageUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Supports JPEG, PNG, WebP/)).toBeDefined();
    expect(screen.getByText(/Max 10 MB/)).toBeDefined();
  });

  it("has accessible file input", () => {
    render(<ImageUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByLabelText("Upload image file for AI detection")).toBeDefined();
  });

  it("does not show Analyze button when no file is selected", () => {
    render(<ImageUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.queryByText("Analyze Image")).toBeNull();
  });

  it("hides upload icon from screen readers", () => {
    const { container } = render(<ImageUpload onAnalyze={vi.fn()} isLoading={false} />);
    const hiddenSvgs = container.querySelectorAll("[aria-hidden='true']");
    expect(hiddenSvgs.length).toBeGreaterThanOrEqual(1);
  });
});

describe("AudioUpload", () => {
  it("renders dropzone with upload instructions", () => {
    render(<AudioUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Drag & drop a WAV file/)).toBeDefined();
  });

  it("renders correct format and size text", () => {
    render(<AudioUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Supports WAV/)).toBeDefined();
    expect(screen.getByText(/Max 25 MB/)).toBeDefined();
  });

  it("has accessible file input", () => {
    render(<AudioUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByLabelText("Upload audio file for AI detection")).toBeDefined();
  });

  it("does not show Analyze button when no file is selected", () => {
    render(<AudioUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.queryByText("Analyze Audio")).toBeNull();
  });

  it("hides upload icon from screen readers", () => {
    const { container } = render(<AudioUpload onAnalyze={vi.fn()} isLoading={false} />);
    const hiddenSvgs = container.querySelectorAll("[aria-hidden='true']");
    expect(hiddenSvgs.length).toBeGreaterThanOrEqual(1);
  });
});

describe("VideoUpload", () => {
  it("renders dropzone with upload instructions", () => {
    render(<VideoUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Drag & drop a video/)).toBeDefined();
  });

  it("renders correct format and size text", () => {
    render(<VideoUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByText(/Supports MP4, WebM, MOV, AVI, MKV/)).toBeDefined();
    expect(screen.getByText(/Max 150 MB/)).toBeDefined();
  });

  it("has accessible file input", () => {
    render(<VideoUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.getByLabelText("Upload video file for AI detection")).toBeDefined();
  });

  it("does not show Analyze button when no file is selected", () => {
    render(<VideoUpload onAnalyze={vi.fn()} isLoading={false} />);
    expect(screen.queryByText("Analyze Video")).toBeNull();
  });

  it("hides upload icon from screen readers", () => {
    const { container } = render(<VideoUpload onAnalyze={vi.fn()} isLoading={false} />);
    const hiddenSvgs = container.querySelectorAll("[aria-hidden='true']");
    expect(hiddenSvgs.length).toBeGreaterThanOrEqual(1);
  });
});
