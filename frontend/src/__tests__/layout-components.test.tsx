import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

// Mock next/link to render plain anchor tags
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("Header", () => {
  it("renders brand name", () => {
    render(<Header />);
    expect(screen.getByText("AI Provenance")).toBeDefined();
  });

  it("renders desktop navigation links", () => {
    render(<Header />);
    expect(screen.getByText("Text")).toBeDefined();
    expect(screen.getByText("Image")).toBeDefined();
    expect(screen.getByText("Audio")).toBeDefined();
    expect(screen.getByText("Video")).toBeDefined();
    expect(screen.getByText("Dashboard")).toBeDefined();
  });

  it("has GitHub link with correct aria-label", () => {
    render(<Header />);
    expect(screen.getByLabelText("GitHub")).toBeDefined();
  });

  it("toggles mobile menu on button click", () => {
    render(<Header />);
    const toggle = screen.getByLabelText("Toggle menu");
    // Mobile nav should not be visible initially (mobile-only nav items are inside the mobileOpen block)
    // Click to open
    fireEvent.click(toggle);
    // After opening, mobile nav shows links with icons
    const audioLinks = screen.getAllByText("Audio");
    // Desktop + mobile = 2 instances
    expect(audioLinks.length).toBe(2);
    // Click to close
    fireEvent.click(toggle);
  });
});

describe("Footer", () => {
  it("renders brand name", () => {
    render(<Footer />);
    expect(screen.getByText("AI Provenance Tracker")).toBeDefined();
  });

  it("renders detection links", () => {
    render(<Footer />);
    expect(screen.getByText("Text Detection")).toBeDefined();
    expect(screen.getByText("Image Detection")).toBeDefined();
    expect(screen.getByText("Audio Detection")).toBeDefined();
    expect(screen.getByText("Video Detection")).toBeDefined();
  });

  it("renders platform links", () => {
    render(<Footer />);
    expect(screen.getByText("Dashboard")).toBeDefined();
    expect(screen.getByText("History")).toBeDefined();
    expect(screen.getByText("API Docs")).toBeDefined();
  });

  it("renders project links", () => {
    render(<Footer />);
    expect(screen.getByText("Contributing")).toBeDefined();
    expect(screen.getByText("MIT License")).toBeDefined();
  });

  it("renders builder attribution", () => {
    render(<Footer />);
    expect(screen.getByText("Ogulcan Aydogan")).toBeDefined();
  });

  it("renders accuracy disclaimer", () => {
    render(<Footer />);
    expect(
      screen.getByText(
        "AI detection is not 100% accurate. Use results as one signal in content verification."
      )
    ).toBeDefined();
  });
});
