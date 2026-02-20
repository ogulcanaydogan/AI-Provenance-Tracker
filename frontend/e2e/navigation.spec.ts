import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("homepage loads with brand and navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/AI Provenance/i);
    await expect(page.getByRole("link", { name: /AI Provenance/i }).first()).toBeVisible();
  });

  test("navigates to text detection page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Text" }).first().click();
    await expect(page).toHaveURL("/detect/text");
    await expect(page.getByRole("heading", { name: "Text Detection" })).toBeVisible();
  });

  test("navigates to image detection page", async ({ page }) => {
    await page.goto("/detect/image");
    await expect(page.getByRole("heading", { name: "Image Detection" })).toBeVisible();
  });

  test("navigates to dashboard page", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /Dashboard/i })).toBeVisible();
  });

  test("navigates to history page", async ({ page }) => {
    await page.goto("/history");
    await expect(page.getByRole("heading", { name: "Analysis History" })).toBeVisible();
  });

  test("header has mobile menu toggle", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");
    await expect(page.getByLabel("Toggle menu")).toBeVisible();
  });

  test("footer renders detection links", async ({ page }) => {
    await page.goto("/");
    const footer = page.locator("footer");
    await expect(footer.getByText("Text Detection")).toBeVisible();
    await expect(footer.getByText("Image Detection")).toBeVisible();
  });
});
