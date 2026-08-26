import { test, expect } from "@playwright/test";
import { mockSupabaseLogin } from "./support/mockAuth.js";

/*
 * Email/password login coverage.
 *
 * Network calls to Supabase and the backend are mocked (see
 * support/mockAuth.js) so these tests are deterministic and don't depend on
 * live credentials — but real browser navigation, form submission, and the
 * app's own role-routing logic (App.jsx handleLogin) all run for real.
 *
 * Login is always done with an email (contains "@") so the app skips the
 * username -> email lookup call and only the flow in mockSupabaseLogin
 * needs to be intercepted.
 */

async function submitLogin(page, email, password) {
  await page.goto("/");
  await page.getByRole("button", { name: "Login" }).click();
  await page.locator("#login-username").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test.describe("login — role routing", () => {
  test("student lands on the student Dashboard", async ({ page }) => {
    await mockSupabaseLogin(page, { profile: { role: "student", username: "e2e.student" } });

    await submitLogin(page, "student@example.com", "correct-password");

    await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
  });

  test("parent lands on the Parent Dashboard", async ({ page }) => {
    await mockSupabaseLogin(page, { profile: { role: "parent", username: "e2e.parent" } });

    await submitLogin(page, "parent@example.com", "correct-password");

    await expect(page.getByRole("heading", { name: "Parent Dashboard" })).toBeVisible();
  });

  test("teacher lands on the Teacher Dashboard", async ({ page }) => {
    await mockSupabaseLogin(page, {
      profile: { role: "teacher", username: "e2e.teacher", account_status: "active" },
    });

    await submitLogin(page, "teacher@example.com", "correct-password");

    await expect(page.getByRole("heading", { name: "Teacher Dashboard" })).toBeVisible();
  });

  test("admin lands on Admin Control", async ({ page }) => {
    await mockSupabaseLogin(page, { profile: { role: "admin", username: "e2e.admin" } });

    await submitLogin(page, "admin@example.com", "correct-password");

    await expect(page.getByRole("heading", { name: "Admin Control" })).toBeVisible();
  });
});

test.describe("login — failure handling", () => {
  test("invalid credentials shows a friendly error and stays on the login form", async ({ page }) => {
    await mockSupabaseLogin(page, { failure: { status: 400, message: "Invalid login credentials" } });

    await submitLogin(page, "student@example.com", "wrong-password");

    await expect(page.getByText("Incorrect username or password. Please try again.")).toBeVisible();
    await expect(page.locator("#login-username")).toBeVisible();
  });

  test("unconfirmed email shows the verification message", async ({ page }) => {
    await mockSupabaseLogin(page, { failure: { status: 400, message: "Email not confirmed" } });

    await submitLogin(page, "student@example.com", "correct-password");

    await expect(page.getByText(/has not been verified yet/i)).toBeVisible();
  });
});

test.describe("login — forgot password", () => {
  test("submitting forgot password shows the generic reset message", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Login" }).click();
    await page.locator("#login-username").fill("student@example.com");

    await page.route("**/api/auth/forgot-password", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true }),
      })
    );

    await page.getByRole("button", { name: "Forgot password?" }).click();

    await expect(page.getByText(/if this account exists, a reset link has been sent/i)).toBeVisible();
  });
});
