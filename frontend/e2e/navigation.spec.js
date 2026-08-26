import { test, expect } from "@playwright/test";

/*
 * Unauthenticated navigation coverage.
 *
 * Fills a gap where the only existing E2E tests checked that the app
 * loads at all. These confirm the public entry points a real visitor
 * uses actually render, and that no dashboard content ever leaks to a
 * signed-out visitor (the most basic authorization regression).
 */

test.describe("public navigation", () => {
  test("fresh visit shows the landing page, not a dashboard", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("button", { name: "Login" })).toBeVisible();
    // No authenticated-only chrome should ever be visible to a signed-out visitor.
    await expect(page.getByTestId("student-dashboard-page")).toHaveCount(0);
  });

  test("landing page Login button navigates to the sign-in form", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Login" }).click();

    await expect(page.locator("#login-username")).toBeVisible();
    await expect(page.locator("#login-password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  });

  test("login page Create an account link navigates to signup", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Login" }).click();

    await page.getByText("Create an account").click();

    await expect(page.getByTestId("signup-page")).toBeVisible();
    await expect(page.getByTestId("signup-name")).toBeVisible();
  });

  test("signup page Sign in link navigates back to login", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByTestId("signup-page")).toBeVisible();

    await page.getByTestId("signup-signin-link").click();

    await expect(page.locator("#login-username")).toBeVisible();
  });

  test("direct URL to /signup renders the signup form", async ({ page }) => {
    await page.goto("/signup");

    await expect(page.getByTestId("signup-page")).toBeVisible();
    await expect(page.getByTestId("role-card-parent")).toBeVisible();
    await expect(page.getByTestId("role-card-student")).toBeVisible();
  });

  test("direct URL to /teacher-signup renders the teacher signup form", async ({ page }) => {
    await page.goto("/teacher-signup");

    await expect(page.getByTestId("teacher-signup-page")).toBeVisible();
  });

  test.describe("static legal pages render for signed-out visitors", () => {
    for (const [path, heading] of [
      ["/privacy-policy", "Privacy Policy"],
      ["/terms-of-service", "Terms of Service"],
      ["/refund-policy", "Refund Policy"],
    ]) {
      test(`${path} shows "${heading}"`, async ({ page }) => {
        await page.goto(path);
        await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      });
    }
  });
});
