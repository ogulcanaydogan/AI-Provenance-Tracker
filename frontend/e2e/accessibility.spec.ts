import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const ROUTES = [
  { path: "/", name: "homepage" },
  { path: "/detect/text", name: "text detection" },
  { path: "/detect/image", name: "image detection" },
  { path: "/detect/audio", name: "audio detection" },
  { path: "/detect/video", name: "video detection" },
  { path: "/dashboard", name: "dashboard" },
  { path: "/history", name: "history" },
];

test.describe("Accessibility (WCAG 2.1 AA)", () => {
  for (const route of ROUTES) {
    test(`${route.name} has no critical axe violations`, async ({ page }) => {
      await page.goto(route.path);
      await page.waitForLoadState("networkidle");
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const critical = results.violations.filter((v) => v.impact === "critical");
      expect(critical, JSON.stringify(critical, null, 2)).toEqual([]);
    });
  }
});
