/**
 * ParentDashboardPhase1.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend regression tests for Parent Experience Phase 1.
 *
 * Covers:
 * - Dashboard renders child cards
 * - Free Tier child shows Restricted badge
 * - Free Tier child does NOT show Full Access
 * - Feature badges reflect backend feature summary
 * - Upgrade CTA appears for Free Tier child
 * - Expiry warning appears for soon-expiring paid plan
 * - Notifications render
 * - No children state renders correctly
 * - Add Child modal shows Free Tier notice
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

vi.mock("../api/parentDashboard", () => ({
  getParentDashboardSummary: vi.fn(async () => ({
    success: true,
    parent: { id: "parent-1", username: "Test Parent", email: "parent@test.com", family_id: "fam-1" },
    parent_plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier — Restricted", status_color: "restricted", description: "This child is on Free Tier with limited access." },
    parent_canonical_plan_key: "FREE_TIER",
    child_limit: 1,
    children_count: 1,
    can_add_child: false,
    children: [
      {
        id: "child-1",
        name: "Aarav",
        grade: "Grade 10",
        account_status: "active",
        plan: {
          canonical_plan_key: "FREE_TIER",
          plan_name: "Free Tier",
          has_full_access: false,
          status_label: "Free Tier — Restricted",
          status_color: "restricted",
          description: "This child is on Free Tier with limited access.",
          expires_at: null,
          days_remaining: null,
          expiry_warning: false,
        },
        subscription: { canonical_plan_key: "FREE_TIER", has_full_access: false },
        features: {
          LESSONS: { allowed: true, limited: true },
          MOCK_TEST: { allowed: true, limited: true },
          EXEMPLAR: { allowed: false, limited: false },
          EXEMPLAR_RESEARCH: { allowed: false, limited: false },
          ASK_DOUBTS: { allowed: true, limited: true },
          AI_ASSISTANT: { allowed: true, limited: true },
        },
        feature_badges: [
          { feature: "LESSONS",           label: "Lessons",           icon: "📖", state: "limited" },
          { feature: "MOCK_TEST",         label: "Mock Tests",        icon: "📝", state: "limited" },
          { feature: "EXEMPLAR",          label: "Exemplar",          icon: "🔬", state: "locked" },
          { feature: "EXEMPLAR_RESEARCH", label: "Exemplar Research", icon: "🧪", state: "locked" },
          { feature: "ASK_DOUBTS",        label: "Ask Doubts",        icon: "❓", state: "limited" },
          { feature: "AI_ASSISTANT",      label: "AI Assistant",      icon: "🤖", state: "limited" },
        ],
        mock_test_summary: { count: 3, average_score: 62, recent: [], free_daily_limit: 5 },
        activity_summary: { last_active: "2026-06-25T10:00:00Z", recent: [] },
        recommendations: [{ type: "upgrade", title: "Unlock full platform access", body: "Upgrade to Premium.", action: "upgrade", priority: "high" }],
        notifications: [{ type: "upgrade", icon: "🔒", title: "Aarav is on Free Tier", body: "Upgrade to unlock...", priority: "low" }],
      },
    ],
    notifications: [
      { type: "upgrade", icon: "🔒", title: "Aarav is on Free Tier", body: "Upgrade to unlock Exemplar, unlimited mock tests, and full AI lessons.", priority: "low" },
    ],
  })),
  getChildDetail: vi.fn(async () => ({
    success: true,
    child: { id: "child-1", name: "Aarav", grade: "Grade 10", account_status: "active" },
    plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier — Restricted", status_color: "restricted", description: "Limited access.", expiry_warning: false },
    subscription: { canonical_plan_key: "FREE_TIER", has_full_access: false },
    features: { EXEMPLAR: { allowed: false, limited: false } },
    feature_badges: [
      { feature: "EXEMPLAR", label: "Exemplar", icon: "🔬", state: "locked" },
    ],
    progress: { available: false },
    mock_tests: { available: true, count: 3, average_score: 62, free_daily_limit: 5, recent: [] },
    ai_activity: { available: false },
    recommendations: [{ type: "upgrade", title: "Unlock full access", body: "Upgrade.", action: "upgrade", priority: "high" }],
    notifications: [],
  })),
  createStudent: vi.fn(async () => ({ success: true, child: { id: "child-new", username: "NewChild" } })),
  getParentSubscriptionPlans: vi.fn(async () => ({ success: true, plans: {}, plan_order: [] })),
  getFamily: vi.fn(async () => ({ success: true, children: [], parents: [] })),
  getParentChildren: vi.fn(async () => ({ success: true, children: [] })),
  getWeakAreaAlerts: vi.fn(async () => ({ success: true, alerts: [] })),
  inviteParent: vi.fn(async () => ({ success: true })),
}));

import ParentDashboardPage from "../pages/ParentDashboardPage";
const USER = { id: "parent-1", role: "parent", username: "Test Parent" };

describe("ParentDashboardPage Phase 1", () => {
  test("renders child cards", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("parent-children-list")).toBeInTheDocument();
    expect(screen.getByText("Aarav")).toBeInTheDocument();
    expect(screen.getByText("Grade 10")).toBeInTheDocument();
  });

  test("Free Tier child shows Restricted badge", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    expect(screen.getByText(/Restricted/i)).toBeInTheDocument();
  });

  test("Free Tier child does NOT show Full Access", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    // No "Full Access" badge should appear for a free child
    const fullAccessElements = screen.queryAllByText(/Full Access/i);
    expect(fullAccessElements.length).toBe(0);
  });

  test("Exemplar badge shows locked for Free Tier", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    // Feature badges are rendered with "locked" state for Exemplar
    const exemplarBadges = screen.queryAllByTitle(/Exemplar: locked/i);
    // The badge title contains "Exemplar: locked"
    const exBadges=screen.getAllByTitle(/Exemplar.*locked/i); expect(exBadges.length).toBeGreaterThanOrEqual(1);
  });

  test("Upgrade CTA appears for Free Tier child", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    expect(screen.getByText(/Free Tier — limited access/i)).toBeInTheDocument();
  });

  test("Notifications render", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    expect(screen.getByText(/Notifications/i)).toBeInTheDocument();
    const freeTexts=screen.getAllByText(/Free Tier/i); expect(freeTexts.length).toBeGreaterThanOrEqual(1);
  });

  test("Add Child modal shows Free Tier notice", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    // Click add child button
    const addBtn = screen.getAllByRole("button", { name: /Add Child/i })[0];
    fireEvent.click(addBtn);
    await waitFor(() => {
      expect(screen.getByTestId("add-child-free-tier-notice")).toBeInTheDocument();
    });
    expect(screen.getByText(/New children start on Free Tier/i)).toBeInTheDocument();
  });

  test("No children state renders correctly", async () => {
    const { getParentDashboardSummary } = await import("../api/parentDashboard");
    getParentDashboardSummary.mockResolvedValueOnce({
      success: true,
      parent: { id: "parent-2", username: "New Parent" },
      parent_plan: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false, status_label: "Free Tier — Restricted", status_color: "restricted" },
      parent_canonical_plan_key: "FREE_TIER",
      child_limit: 1,
      children_count: 0,
      can_add_child: true,
      children: [],
      notifications: [],
    });
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("parent-no-children")).toBeInTheDocument();
    const noChildTexts=screen.getAllByText(/No children linked yet/i); expect(noChildTexts.length).toBeGreaterThanOrEqual(1);
  });

  test("Child detail drawer opens on View click", async () => {
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    fireEvent.click(screen.getByText(/View →/i));
    expect(await screen.findByTestId("child-detail-drawer")).toBeInTheDocument();
  });

  test("Expiry warning visible for expiring plan", async () => {
    const { getParentDashboardSummary } = await import("../api/parentDashboard");
    getParentDashboardSummary.mockResolvedValueOnce({
      success: true,
      parent: { id: "parent-3", username: "Parent" },
      parent_plan: { canonical_plan_key: "NANO", plan_name: "Premium Nano", has_full_access: true, status_label: "Full Access", status_color: "paid" },
      parent_canonical_plan_key: "NANO",
      child_limit: 1,
      children_count: 1,
      can_add_child: false,
      children: [{
        id: "child-2", name: "Riya", grade: "Grade 9", account_status: "active",
        plan: {
          canonical_plan_key: "NANO", plan_name: "Premium Nano", has_full_access: true,
          status_label: "Full Access", status_color: "paid",
          description: "Full access for 8 days. Expiring soon!",
          expires_at: "2026-07-01", days_remaining: 2, expiry_warning: true,
        },
        subscription: { canonical_plan_key: "NANO" },
        features: { EXEMPLAR: { allowed: true, limited: false } },
        feature_badges: [{ feature: "EXEMPLAR", label: "Exemplar", icon: "🔬", state: "full" }],
        mock_test_summary: { count: 5, average_score: 78, recent: [], free_daily_limit: null },
        activity_summary: { last_active: "2026-06-27T08:00:00Z", recent: [] },
        recommendations: [],
        notifications: [{ type: "expiry_warning", icon: "⚠️", title: "Riya: Plan expires in 2 days", body: "Renew now.", priority: "high" }],
      }],
      notifications: [{ type: "expiry_warning", icon: "⚠️", title: "Riya: Plan expires in 2 days", body: "Renew now.", priority: "high" }],
    });
    render(<ParentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("parent-children-list");
    expect(screen.getByText(/Expiring soon/i)).toBeInTheDocument();
  });
});
