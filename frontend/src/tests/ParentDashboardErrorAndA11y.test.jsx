/**
 * ParentDashboardErrorAndA11y.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Regression tests added alongside the parent-dashboard weakness fixes:
 *
 * - A failed workspace-tab fetch shows a distinct, retryable error banner
 *   instead of silently rendering the same "no data yet" copy as an empty
 *   section (previously the catch blocks swallowed the error entirely).
 * - Retrying re-issues the failed request.
 * - A non-blocking `data_warnings` notice from the backend surfaces on the
 *   dashboard and inside the child workspace without blocking the rest of
 *   the page.
 * - The Add Child modal and the child workspace drawer are real dialogs:
 *   role="dialog", aria-modal, and Escape-to-close.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

const FREE_CHILD = {
  id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active",
  plan: {
    canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false,
    status_label: "Free Tier — Restricted", status_color: "restricted",
    description: "This child is on Free Tier with limited access.",
    expires_at: null, days_remaining: null, expiry_warning: false,
  },
  subscription: { canonical_plan_key: "FREE_TIER", has_full_access: false },
  features: { EXEMPLAR: { allowed: false }, MOCK_TEST: { allowed: true, limited: true } },
  feature_badges: [{ feature: "EXEMPLAR", label: "Exemplar", icon: "🔬", state: "locked" }],
  mock_test_summary: { count: 3, average_score: 55, recent: [], free_daily_limit: 5 },
  activity_summary: { last_active: "2026-06-25T10:00:00Z", recent: [] },
  recommendations: [],
  notifications: [],
};

const baseSummary = {
  success: true,
  parent: { id: "p1", username: "TestParent", email: "test@test.com", family_id: "fam-1" },
  parent_plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier", status_color: "restricted" },
  parent_canonical_plan_key: "FREE_TIER",
  child_limit: 1, children_count: 1, can_add_child: false,
  children: [FREE_CHILD],
  notifications: [],
};

const getParentDashboardSummary = vi.fn(async () => baseSummary);
const getChildDetail = vi.fn(async () => ({
  success: true,
  child: { id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active" },
  plan: FREE_CHILD.plan,
  subscription: FREE_CHILD.subscription,
  features: FREE_CHILD.features,
  feature_badges: FREE_CHILD.feature_badges,
  progress: { available: false, completed_chapters: 0, in_progress_chapters: 0, weak_topics: [] },
  mock_tests: { available: true, count: 3, average_score: 55, free_daily_limit: 5, recent: [] },
  ai_activity: { available: false },
  recommendations: [],
  notifications: [],
  data_warnings: [],
}));
const getChildAnalytics = vi.fn(async () => ({ success: true, progress: {}, mock_tests: {}, strengths: {}, weaknesses: {}, activity: {} }));
const getChildAcademicInsights = vi.fn(async () => ({ success: true, homework: {}, exams: {}, mock_test_recommendations: {}, revision_suggestions: {} }));
const getChildProgressReport = vi.fn(async () => ({ success: true, child: {}, progress_summary: {}, mock_test_summary: {} }));

vi.mock("../api/parentDashboard", () => ({
  getParentDashboardSummary: (...args) => getParentDashboardSummary(...args),
  getChildDetail: (...args) => getChildDetail(...args),
  getChildAnalytics: (...args) => getChildAnalytics(...args),
  getChildAcademicInsights: (...args) => getChildAcademicInsights(...args),
  getChildProgressReport: (...args) => getChildProgressReport(...args),
  getParentNotifications: vi.fn(async () => ({ success: true, source: "rule_based", unread_count: 0, total: 0, notifications: [] })),
  markNotificationRead: vi.fn(async () => ({ success: true })),
  markAllNotificationsRead: vi.fn(async () => ({ success: true, updated: 0 })),
  createStudent: vi.fn(async () => ({ success: true })),
  getParentSubscriptionPlans: vi.fn(async () => ({ success: true })),
  getFamily: vi.fn(async () => ({ success: true })),
  getParentChildren: vi.fn(async () => ({ success: true, children: [] })),
  getWeakAreaAlerts: vi.fn(async () => ({ success: true, alerts: [] })),
  inviteParent: vi.fn(async () => ({ success: true })),
}));

import ParentDashboardPage from "../pages/ParentDashboardPage";
const USER = { id: "p1", role: "parent", username: "TestParent" };

async function openWorkspace() {
  render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
  await screen.findByTestId("parent-children-list");
  const statusCard = document.querySelector("[data-testid='parent-child-status-card']");
  statusCard.click();
  return waitFor(() => {
    expect(document.querySelector("[data-testid='parent-child-workspace']")).toBeTruthy();
  });
}

describe("Workspace fetch errors are distinct from empty states", () => {
  test("a failed child-detail fetch shows a retryable error banner, not silent 'no data'", async () => {
    getChildDetail.mockRejectedValueOnce(new Error("We're having trouble right now. Please try again in a moment."));
    await openWorkspace();

    const banner = await screen.findByTestId("workspace-fetch-error");
    expect(banner.textContent).toContain("We're having trouble right now");
    expect(screen.getByTestId("workspace-retry-btn")).toBeInTheDocument();
  });

  test("clicking Retry re-issues the failed request", async () => {
    getChildDetail.mockRejectedValueOnce(new Error("Network error"));
    await openWorkspace();
    await screen.findByTestId("workspace-fetch-error");

    const callsBeforeRetry = getChildDetail.mock.calls.length;
    fireEvent.click(screen.getByTestId("workspace-retry-btn"));

    await waitFor(() => {
      expect(getChildDetail.mock.calls.length).toBeGreaterThan(callsBeforeRetry);
    });
  });

  test("a successful load shows no error banner", async () => {
    await openWorkspace();
    expect(document.querySelector("[data-testid='workspace-fetch-error']")).toBeNull();
  });
});

describe("Non-blocking data_warnings notices", () => {
  test("dashboard shows a partial-data notice when summary reports data_warnings", async () => {
    getParentDashboardSummary.mockResolvedValueOnce({
      ...baseSummary,
      data_warnings: ["Mock test data could not be loaded."],
    });
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    const warning = await screen.findByTestId("parent-data-warning");
    expect(warning.textContent).toContain("Mock test data could not be loaded");
    // The rest of the dashboard still renders — not a blocking error page.
    expect(screen.getByTestId("parent-children-list")).toBeInTheDocument();
  });

  test("dashboard shows no partial-data notice when there are no warnings", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    expect(document.querySelector("[data-testid='parent-data-warning']")).toBeNull();
  });

  test("workspace shows a partial-data notice when child detail reports data_warnings", async () => {
    getChildDetail.mockResolvedValueOnce({
      success: true,
      child: { id: "child-1", name: "Aarav", grade: "Grade 10" },
      plan: FREE_CHILD.plan, subscription: FREE_CHILD.subscription,
      features: {}, feature_badges: [],
      progress: { available: false }, mock_tests: { available: false }, ai_activity: { available: false },
      recommendations: [], notifications: [],
      data_warnings: ["Recent activity data could not be loaded."],
    });
    await openWorkspace();
    const warning = await screen.findByTestId("workspace-data-warning");
    expect(warning.textContent).toContain("Recent activity data could not be loaded");
  });
});

describe("Modal accessibility", () => {
  test("child workspace is a labeled dialog that closes on Escape", async () => {
    await openWorkspace();
    const ws = document.querySelector("[data-testid='parent-child-workspace']");
    expect(ws.getAttribute("role")).toBe("dialog");
    expect(ws.getAttribute("aria-modal")).toBe("true");
    expect(ws.getAttribute("aria-label")).toBeTruthy();

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(document.querySelector("[data-testid='parent-child-workspace']")).toBeNull();
    });
  });

  test("workspace close button has an accessible label", async () => {
    await openWorkspace();
    const closeBtn = screen.getByLabelText("Close learning workspace");
    expect(closeBtn).toBeInTheDocument();
  });

  test("Add Child modal is a labeled dialog that closes on Escape", async () => {
    getParentDashboardSummary.mockResolvedValueOnce({
      ...baseSummary,
      children: [],
      children_count: 0,
      can_add_child: true,
    });
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    const noChildren = await screen.findByTestId("parent-no-children");
    fireEvent.click(noChildren.querySelector("button"));

    const dialog = await waitFor(() => {
      const el = document.querySelector('[role="dialog"][aria-label="Add Child"]');
      expect(el).toBeTruthy();
      return el;
    });
    expect(dialog.getAttribute("aria-modal")).toBe("true");

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(document.querySelector('[role="dialog"][aria-label="Add Child"]')).toBeNull();
    });
  });
});
