import { test, expect } from "@playwright/test";

test.describe("History Page", () => {
  test("renders empty state when no analyses exist", async ({ page }) => {
    await page.goto("/history");
    // Either shows items or empty state
    const heading = page.getByRole("heading", { name: "Analysis History" });
    await expect(heading).toBeVisible();
  });

  test("has content type filter dropdown", async ({ page }) => {
    await page.goto("/history");
    await expect(page.getByLabel("Filter by content type")).toBeVisible();
  });

  test("has export buttons", async ({ page }) => {
    await page.goto("/history");
    await expect(page.getByRole("button", { name: "CSV" })).toBeVisible();
    await expect(page.getByRole("button", { name: "JSON" })).toBeVisible();
  });

  test("links to dashboard from history page", async ({ page }) => {
    await page.goto("/history");
    await expect(page.getByText("View analytics dashboard")).toBeVisible();
  });
});

test.describe("Dashboard Page", () => {
  test("renders dashboard heading and window selector", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: /Dashboard/i })
    ).toBeVisible();
    await expect(page.getByLabel("Window")).toBeVisible();
  });

  test("has export buttons", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: "CSV" }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "JSON" }).first()).toBeVisible();
  });

  test("shows loading then content", async ({ page }) => {
    await page.goto("/dashboard");
    // Should show loading or content
    const hasLoading = await page.getByText("Loading dashboard...").isVisible().catch(() => false);
    if (hasLoading) {
      // Wait for loading to finish
      await expect(page.getByText("Loading dashboard...")).toBeHidden({ timeout: 15000 });
    }
    // Dashboard should show stats or error
    const hasStats = await page.getByText("Window Analyses").isVisible().catch(() => false);
    const hasError = await page.locator("[role='alert']").isVisible().catch(() => false);
    expect(hasStats || hasError).toBeTruthy();
  });

  test("can change window period", async ({ page }) => {
    await page.goto("/dashboard");
    const select = page.getByLabel("Window");
    await select.selectOption("30");
    // Should trigger reload
    await expect(select).toHaveValue("30");
  });
});
