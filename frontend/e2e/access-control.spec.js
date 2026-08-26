import { test, expect } from "@playwright/test";
import { mockSupabaseLogin } from "./support/mockAuth.js";

/*
 * Free-tier access restriction coverage — the "free access restrictions"
 * and "paid upgrade flows" items on the documented E2E roadmap.
 *
 * A free-tier student's dashboard summary is mocked to return the same
 * upgrade recommendation shape backend sends for unpaid accounts (see
 * StudentDashboardPage.test.jsx), then the test follows the real "Upgrade
 * Plan" CTA through to the Subscription page.
 */

const FREE_TIER_SUMMARY = {
  success: true,
  student: { username: "e2e.student", grade: "Grade 9", study_streak_days: 0, lessons_completed: 0, xp_points: 0, student_level: 1, rank_title: "Beginner" },
  subscription: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false },
  features: { has_full_access: false, exemplar_locked: true, mock_test_limited: true, ask_doubts_limited: true },
  mock_tests: { available: false, total: 0, average_score: null, best_score: null, subject_averages: {}, recent: [], score_trend: [] },
  progress: { available: false, overall_pct: 0, completed_chapters: 0, in_progress_chapters: 0, subject_progress: {}, last_chapter: null },
  weak_topics: [],
  activity: { last_active: null, feature_counts: {}, total_90d: 0 },
  achievements: [],
  recommendations: [
    { type: "upgrade", title: "Unlock full platform access", body: "Upgrade to access Exemplar problems.", priority: "low", action: "subscription" },
  ],
  plan: { tasks: [], estimated_minutes: 15 },
};

test.describe("free-tier access restrictions", () => {
  test("free student sees an upgrade prompt and can reach the Subscription page", async ({ page }) => {
    await mockSupabaseLogin(page, {
      profile: { role: "student", username: "e2e.student", access_cbse: false, subscription_plan: "free" },
      authProfile: { access_cbse: false, subscription_plan: "free" },
    });
    await page.route("**/api/student/dashboard/summary", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FREE_TIER_SUMMARY) })
    );
    await page.route("**/api/student/exams", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, exams: [] }) })
    );

    await page.goto("/");
    await page.getByRole("button", { name: "Login" }).click();
    await page.locator("#login-username").fill("student@example.com");
    await page.locator("#login-password").fill("correct-password");
    await page.getByRole("button", { name: "Sign in", exact: true }).click();

    await expect(page.getByRole("heading", { name: "Dashboard", exact: true })).toBeVisible();
    await expect(page.getByText("Upgrade to access Exemplar problems.")).toBeVisible();

    await page.getByText("Upgrade Plan →").click();

    await expect(page.getByRole("heading", { name: "Subscription" })).toBeVisible();
    await expect(page.getByText("Your current access")).toBeVisible();
    await expect(page.locator(".subscription-current-plan strong")).toHaveText("Free Tier");
  });
});
