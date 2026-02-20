import { test, expect } from "@playwright/test";

test.describe("Image Detection Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/detect/image");
  });

  test("renders heading and description", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Image Detection" })
    ).toBeVisible();
    await expect(
      page.getByText("Upload an image to analyze")
    ).toBeVisible();
  });

  test("renders upload dropzone with format text", async ({ page }) => {
    await expect(page.getByText(/Drag & drop an image/)).toBeVisible();
    await expect(page.getByText(/Supports JPEG, PNG, WebP/)).toBeVisible();
  });

  test("file input has correct aria-label", async ({ page }) => {
    await expect(
      page.getByLabel("Upload image file for AI detection")
    ).toBeAttached();
  });

  test("no analyze button visible without file", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: "Analyze Image" })
    ).not.toBeVisible();
  });
});

test.describe("Audio Detection Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/detect/audio");
  });

  test("renders heading with Beta badge", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Audio Detection" })
    ).toBeVisible();
    await expect(page.getByText("Beta")).toBeVisible();
  });

  test("renders description", async ({ page }) => {
    await expect(
      page.getByText("Upload a WAV file to analyze")
    ).toBeVisible();
  });

  test("renders upload dropzone for WAV files", async ({ page }) => {
    await expect(page.getByText(/Drag & drop a WAV file/)).toBeVisible();
    await expect(page.getByText(/Supports WAV/)).toBeVisible();
  });

  test("file input has correct aria-label", async ({ page }) => {
    await expect(
      page.getByLabel("Upload audio file for AI detection")
    ).toBeAttached();
  });
});

test.describe("Video Detection Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/detect/video");
  });

  test("renders heading with Beta badge", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Video Detection" })
    ).toBeVisible();
    await expect(page.getByText("Beta")).toBeVisible();
  });

  test("renders description", async ({ page }) => {
    await expect(
      page.getByText("Upload a short video clip to analyze")
    ).toBeVisible();
  });

  test("renders upload dropzone for video files", async ({ page }) => {
    await expect(page.getByText(/Drag & drop a video/)).toBeVisible();
    await expect(
      page.getByText(/Supports MP4, WebM, MOV, AVI, MKV/)
    ).toBeVisible();
  });

  test("file input has correct aria-label", async ({ page }) => {
    await expect(
      page.getByLabel("Upload video file for AI detection")
    ).toBeAttached();
  });
});
