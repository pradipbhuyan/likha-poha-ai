import { test, expect } from "@playwright/test";

test("app loads", async ({ page }) => {
  /*
   * This E2E test checks that the app can load in the browser.
   *
   * Expected result:
   * - The page should open successfully.
   * - The body should be visible.
   * - At least one common app text should appear.
   */

  await page.goto("http://localhost:5173");

  await expect(page.locator("body")).toBeVisible();

  await expect(
    page.getByText(/dashboard|lesson|login|loading/i).first()
  ).toBeVisible();
});

test("page shows main app content", async ({ page }) => {
  /*
   * This E2E test checks that the frontend renders visible content.
   *
   * It does not test the full lesson flow yet.
   * It only confirms that the page is not blank after loading.
   */

  await page.goto("http://localhost:5173");

  await expect(page.locator("body")).toBeVisible();

  const bodyText = await page.locator("body").innerText();

  expect(bodyText.trim().length).toBeGreaterThan(0);
});