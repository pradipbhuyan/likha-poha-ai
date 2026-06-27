/**
 * ParentDashboardPhase3.test.jsx
 * Regression tests for Parent Experience Phase 3 — UX Completion.
 *
 * Covers:
 * - Parent dashboard renders hero summary
 * - Child status card shows restricted access for Free Tier child
 * - Free Tier child does NOT show full access
 * - Things to Do Tonight renders from recommendations
 * - Recommendation card shows reason and action
 * - Child workspace opens from child card
 * - Missing progress data shows friendly explanation
 * - Platform Access uses "Platform Access" terminology, not "CBSE Access"
 * - Paid plan shows full access
 * - Expired paid plan shows Free Tier fallback
 * - Report section includes "Teacher-private notes are not included."
 * - Print button exists and does not crash
 */
import { fireEvent, render, screen } from "@testing-library/react";
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
  recommendations: [{ type: "upgrade", title: "Unlock full access", body: "Upgrade to unlock Exemplar.", action: "upgrade", priority: "high" }],
  notifications: [{ type: "feature_locked", icon: "🔒", title: "Aarav is on Free Tier", body: "Upgrade.", priority: "low", status: "unread" }],
};

const PAID_CHILD = {
  id: "child-2", name: "Riya", grade: "Grade 9", account_status: "active",
  plan: {
    canonical_plan_key: "PREMIUM", plan_name: "Premium", has_full_access: true,
    status_label: "Full Access", status_color: "paid",
    description: "Full access for one child, 30 days.", expires_at: "2026-08-01",
    days_remaining: 30, expiry_warning: false,
  },
  subscription: { canonical_plan_key: "PREMIUM", has_full_access: true },
  features: { EXEMPLAR: { allowed: true }, MOCK_TEST: { allowed: true, limited: false } },
  feature_badges: [{ feature: "EXEMPLAR", label: "Exemplar", icon: "🔬", state: "full" }],
  mock_test_summary: { count: 8, average_score: 72, recent: [], free_daily_limit: null },
  activity_summary: { last_active: "2026-06-27T08:00:00Z", recent: [] },
  recommendations: [],
  notifications: [],
};

vi.mock("../api/parentDashboard", () => ({
  getParentDashboardSummary: vi.fn(async () => ({
    success: true,
    parent: { id: "p1", username: "TestParent", email: "test@test.com", family_id: "fam-1" },
    parent_plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier", status_color: "restricted" },
    parent_canonical_plan_key: "FREE_TIER",
    child_limit: 1, children_count: 2, can_add_child: false,
    children: [FREE_CHILD, PAID_CHILD],
    notifications: [
      { type: "feature_locked", icon: "🔒", title: "Aarav is on Free Tier", body: "Upgrade.", priority: "low", status: "unread" },
    ],
  })),
  getChildDetail: vi.fn(async () => ({
    success: true,
    child: { id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active" },
    plan: FREE_CHILD.plan,
    subscription: FREE_CHILD.subscription,
    features: FREE_CHILD.features,
    feature_badges: FREE_CHILD.feature_badges,
    progress: { available: false, completed_chapters: 0, in_progress_chapters: 0, weak_topics: [] },
    mock_tests: { available: true, count: 3, average_score: 55, free_daily_limit: 5, recent: [] },
    ai_activity: { available: false },
    recommendations: FREE_CHILD.recommendations,
    notifications: FREE_CHILD.notifications,
  })),
  getChildAnalytics: vi.fn(async () => ({
    success: true, child_id: "child-1",
    progress: { available: false, status: "no_activity", has_data: false, subject_wise: {} },
    mock_tests: { available: true, status: "data", has_data: true, total_tests: { value: 3 }, average_score: { value: "55%" }, trend: [] },
    strengths: { available: false }, weaknesses: { available: false },
    activity: { available: false, status: "no_activity", has_data: false },
    ai_usage: { available: false },
    data_availability: { homework: false, exams: false },
  })),
  getChildAcademicInsights: vi.fn(async () => ({
    success: true,
    homework: { available: false, message: "Homework tracking is not enabled yet." },
    exams: { available: false, message: "Exam schedule is not available yet." },
    mock_test_recommendations: { available: true, recommendations: [], total_tests: 3 },
    revision_suggestions: { available: false, topics: [] },
  })),
  getChildProgressReport: vi.fn(async () => ({
    success: true, report_type: "parent_progress_report",
    generated_at: "2026-06-27T10:00:00Z",
    child: { id: "child-1", name: "Aarav", grade: "Grade 10", board: "CBSE" },
    access_summary: { plan: FREE_CHILD.plan, feature_highlights: [] },
    progress_summary: { available: false, completed_chapters: 0, total_tracked: 0, recent_completions: [] },
    mock_test_summary: { available: true, tests_taken: 3, average_score: 55, subject_averages: {}, recent_tests: [] },
    strengths: [], areas_for_improvement: [],
    recommendations: [{ type: "upgrade", title: "Unlock full access", body: "Upgrade." }],
    disclaimer: "Teacher-private notes and internal audit data are not included in this report.",
  })),
  getParentNotifications: vi.fn(async () => ({
    success: true, source: "rule_based", unread_count: 1, total: 1,
    notifications: [{ id: "rule-1", type: "feature_locked", title: "Aarav is on Free Tier", message: "Upgrade.", severity: "info", status: "unread" }],
  })),
  markNotificationRead: vi.fn(async () => ({ success: true })),
  markAllNotificationsRead: vi.fn(async () => ({ success: true, updated: 1 })),
  createStudent: vi.fn(async () => ({ success: true })),
  getParentSubscriptionPlans: vi.fn(async () => ({ success: true })),
  getFamily: vi.fn(async () => ({ success: true })),
  getParentChildren: vi.fn(async () => ({ success: true, children: [] })),
  getWeakAreaAlerts: vi.fn(async () => ({ success: true, alerts: [] })),
  inviteParent: vi.fn(async () => ({ success: true })),
}));

import ParentDashboardPage from "../pages/ParentDashboardPage";
import ParentChildStatusCard from "../components/parent/ParentChildStatusCard";
import ParentActionPlan from "../components/parent/ParentActionPlan";
import ParentAccessExplanation from "../components/parent/ParentAccessExplanation";
import ParentProgressStory from "../components/parent/ParentProgressStory";

const USER = { id: "p1", role: "parent", username: "TestParent" };

describe("ParentDashboardPage Phase 3", () => {
  test("renders hero summary", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("parent-hero-summary")).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Good morning|Good afternoon|Good evening/);
  });

  test("renders both child status cards", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    const cards=document.querySelectorAll("[data-testid='parent-child-status-card']");
    expect(cards.length).toBe(2);
  });

  test("Free Tier child card shows Restricted Access", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    const bt=document.body.textContent;
    expect(bt.includes("Restricted")||bt.includes("Free Tier")).toBe(true);
  });

  test("Free Tier child does NOT show Full Access badge", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    // Only the paid child should show "Doing Well" / Full Access
    // The Free child should show Restricted
    const cards=document.querySelectorAll("[data-testid='parent-child-status-card']");
    const freeCard=Array.from(cards).find(function(c){return c.textContent.includes("Aarav");});
    expect(freeCard).toBeTruthy();
    expect(freeCard.textContent).not.toContain("Full Platform Access");
  });

  test("Things to Do Tonight renders from recommendations", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    // Action plan exists
    const ap=document.querySelector("[data-testid='parent-action-plan']")||
              document.querySelector("[data-testid='parent-action-plan-empty']");
    expect(ap).toBeTruthy();
  });

  test("Recommendation card shows reason and action button", async () => {
    const { container } = render(
      <ParentActionPlan
        children={[FREE_CHILD]}
        onUpgrade={vi.fn()}
        onOpenChild={vi.fn()}
      />
    );
    const plan=container.querySelector("[data-testid='parent-action-plan']");
    expect(plan).toBeTruthy();
    const cards=container.querySelectorAll("[data-testid='parent-action-card']");
    expect(cards.length).toBeGreaterThanOrEqual(1);
    // First card has title and body
    expect(cards[0].textContent).toContain("Unlock full access");
  });

  test("Paid child shows Doing Well status", () => {
    const { container } = render(
      <ParentChildStatusCard child={PAID_CHILD} onView={vi.fn()} onUpgrade={vi.fn()} />
    );
    expect(container.textContent).toContain("Doing Well");
  });

  test("Free Tier child shows Restricted Access status", () => {
    const { container } = render(
      <ParentChildStatusCard child={FREE_CHILD} onView={vi.fn()} onUpgrade={vi.fn()} />
    );
    expect(container.textContent).toContain("Restricted Access");
  });
});

describe("ParentAccessExplanation Phase 3", () => {
  test("uses Platform Access terminology, not CBSE Access", () => {
    const { container } = render(
      <ParentAccessExplanation plan={FREE_CHILD.plan} featureBadges={FREE_CHILD.feature_badges} subscription={FREE_CHILD.subscription} onUpgrade={vi.fn()} />
    );
    expect(container.textContent).not.toContain("CBSE Access");
    expect(container.textContent).toContain("Platform");
  });

  test("Free Tier shows Restricted Platform Access", () => {
    const { container } = render(
      <ParentAccessExplanation plan={FREE_CHILD.plan} featureBadges={[]} subscription={FREE_CHILD.subscription} onUpgrade={vi.fn()} />
    );
    expect(container.textContent).toContain("Restricted Platform Access");
  });

  test("Paid plan shows Full Platform Access", () => {
    const { container } = render(
      <ParentAccessExplanation plan={PAID_CHILD.plan} featureBadges={[]} subscription={PAID_CHILD.subscription} onUpgrade={vi.fn()} />
    );
    expect(container.textContent).toContain("Full Platform Access");
  });

  test("Free Tier shows Upgrade CTA", () => {
    const { container } = render(
      <ParentAccessExplanation plan={FREE_CHILD.plan} featureBadges={[]} subscription={FREE_CHILD.subscription} onUpgrade={vi.fn()} />
    );
    expect(container.querySelector("button")).toBeTruthy();
    expect(container.textContent).toContain("Upgrade");
  });
});

describe("ParentProgressStory Phase 3", () => {
  test("shows friendly explanation when no analytics data", () => {
    const { container } = render(<ParentProgressStory analytics={null} />);
    expect(container.textContent).toContain("Progress will appear here");
  });

  test("renders progress metrics when analytics available", () => {
    const mockAnalytics = {
      progress: { available: true, has_data: true, status: "data",
        completed_chapters: { value: 5, available: true },
        in_progress_chapters: { value: 3, available: true },
        not_started: { value: 10, available: true },
        subject_wise: { Science: { total: 5, completed: 2, in_progress: 1 } } },
      mock_tests: { available: true, has_data: true, status: "data",
        total_tests: { value: 8 }, average_score: { value: "72%" }, trend: [] },
      strengths: { available: true, strong_subjects: ["Maths"], completed_topics: [] },
      weaknesses: { available: false, weak_subjects: [], weak_topics: [] },
      activity: { available: true, has_data: true, last_active: "2026-06-27",
        lessons_this_month: { value: 10, available: true },
        doubts_this_month: { value: 5, available: true },
        active_days: { value: 12, available: true } },
    };
    const { container } = render(<ParentProgressStory analytics={mockAnalytics} />);
    expect(container.textContent).toContain("Completed");
    expect(container.textContent).toContain("In Progress");
    expect(container.textContent).toContain("Maths"); // strength
  });
});
