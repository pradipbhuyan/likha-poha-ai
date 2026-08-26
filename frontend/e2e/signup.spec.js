import { test, expect } from "@playwright/test";
import { mockSupabaseLogin } from "./support/mockAuth.js";

/*
 * Free signup coverage (SignupPage.jsx) — the top item on the documented
 * E2E roadmap ("signup/free onboarding") that had no automated coverage.
 *
 * The backend `/api/auth/signup-free` call and the Supabase auto-login that
 * follows a successful signup are mocked at the network layer so these
 * tests don't create real accounts.
 */

test.describe("signup — happy path", () => {
  test("free parent signup succeeds and shows the account setup screen", async ({ page }) => {
    await mockSupabaseLogin(page, { profile: { role: "parent", username: "E2E Parent" } });
    await page.route("**/api/auth/signup-free", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) })
    );

    await page.goto("/signup");
    await page.getByTestId("role-card-parent").click();
    await page.getByTestId("signup-name").fill("E2E Parent");
    await page.getByTestId("signup-email").fill("e2e.newparent@example.com");
    await page.getByTestId("signup-password").fill("longenoughpassword");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-setting-up")).toBeVisible();
    await expect(page.getByText("Setting up your parent account…")).toBeVisible();
  });
});

test.describe("signup — validation", () => {
  test("rejects a password shorter than 8 characters without calling the API", async ({ page }) => {
    let signupCalled = false;
    await page.route("**/api/auth/signup-free", (route) => {
      signupCalled = true;
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) });
    });

    await page.goto("/signup");
    await page.getByTestId("signup-name").fill("E2E Parent");
    await page.getByTestId("signup-email").fill("e2e.parent@example.com");
    await page.getByTestId("signup-password").fill("short");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-error")).toHaveText(/at least 8 characters/i);
    expect(signupCalled).toBe(false);
  });

  test("Grade 11 student must choose a stream before submitting", async ({ page }) => {
    await page.goto("/signup");
    await page.getByTestId("role-card-student").click();
    await page.getByTestId("signup-grade").selectOption("Grade 11");

    await page.getByTestId("signup-name").fill("E2E Student");
    await page.getByTestId("signup-email").fill("e2e.student11@example.com");
    await page.getByTestId("signup-password").fill("longenoughpassword");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-error")).toHaveText(/choose your academic stream/i);
  });
});

test.describe("signup — API responses", () => {
  test("duplicate email shows a friendly already-registered error", async ({ page }) => {
    await page.route("**/api/auth/signup-free", (route) =>
      route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ success: false, detail: "Email already exists" }),
      })
    );

    await page.goto("/signup");
    await page.getByTestId("signup-name").fill("E2E Parent");
    await page.getByTestId("signup-email").fill("existing@example.com");
    await page.getByTestId("signup-password").fill("longenoughpassword");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-error")).toHaveText(/already registered/i);
  });

  test("rate limiting shows a friendly retry-later error", async ({ page }) => {
    await page.route("**/api/auth/signup-free", (route) =>
      route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ success: false, detail: "over_email_send_rate_limit" }),
      })
    );

    await page.goto("/signup");
    await page.getByTestId("signup-name").fill("E2E Parent");
    await page.getByTestId("signup-email").fill("e2e.parent2@example.com");
    await page.getByTestId("signup-password").fill("longenoughpassword");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-error")).toHaveText(/too many signup attempts/i);
  });

  test("account created but unconfirmed shows the confirm-email message", async ({ page }) => {
    await page.route("**/api/auth/signup-free", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) })
    );
    await page.route("**/auth/v1/logout**", (route) => route.fulfill({ status: 204, body: "" }));
    await page.route("**/auth/v1/token**", (route) =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ error: "invalid_grant", error_description: "Email not confirmed", msg: "Email not confirmed" }),
      })
    );

    await page.goto("/signup");
    await page.getByTestId("signup-name").fill("E2E Parent");
    await page.getByTestId("signup-email").fill("e2e.parent3@example.com");
    await page.getByTestId("signup-password").fill("longenoughpassword");
    await page.getByTestId("signup-submit").click();

    await expect(page.getByTestId("signup-info")).toHaveText(/check your inbox for a confirmation email/i);
  });
});
