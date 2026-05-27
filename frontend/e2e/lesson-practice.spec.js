import { test, expect } from "@playwright/test";

test("app loads", async ({ page }) => {
  await page.goto("http://localhost:5173");

  await expect(page.locator("body")).toBeVisible();

  await expect(page.getByText(/dashboard|lesson|login|loading/i).first()).toBeVisible();
});