import { test, expect } from "@playwright/test";

test.describe("Text Detection Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/detect/text");
  });

  test("page renders input area and analyze button", async ({ page }) => {
    await expect(page.getByLabel("Text to analyze for AI detection")).toBeVisible();
    await expect(page.getByRole("button", { name: "Analyze Text" })).toBeVisible();
  });

  test("analyze button is disabled when text is too short", async ({ page }) => {
    const button = page.getByRole("button", { name: "Analyze Text" });
    await expect(button).toBeDisabled();
  });

  test("can type text and enable analyze button", async ({ page }) => {
    const textarea = page.getByLabel("Text to analyze for AI detection");
    await textarea.fill("A".repeat(60));
    const button = page.getByRole("button", { name: "Analyze Text" });
    await expect(button).toBeEnabled();
  });

  test("Try Sample button fills textarea", async ({ page }) => {
    await page.getByLabel("Load a sample AI-generated text").click();
    const textarea = page.getByLabel("Text to analyze for AI detection");
    const value = await textarea.inputValue();
    expect(value.length).toBeGreaterThan(50);
  });

  test("full analysis flow with sample text", async ({ page }) => {
    // Load sample text
    await page.getByLabel("Load a sample AI-generated text").click();

    // Click analyze
    await page.getByRole("button", { name: "Analyze Text" }).click();

    // Wait for analysis to complete (loading state appears then result)
    await expect(page.getByText("Analyzing content...")).toBeVisible({ timeout: 5000 });

    // Wait for result to appear
    await expect(page.getByText("Detection Signals")).toBeVisible({ timeout: 30000 });

    // Verify result card elements
    await expect(page.getByText("AI Confidence")).toBeVisible();

    // Verify "Analyze another text" button appears
    await expect(page.getByText("Analyze another text")).toBeVisible();
  });

  test("shows character count", async ({ page }) => {
    await expect(page.getByText("0 / 50,000")).toBeVisible();
    const textarea = page.getByLabel("Text to analyze for AI detection");
    await textarea.fill("Hello world");
    await expect(page.getByText("11 / 50,000")).toBeVisible();
  });
});
