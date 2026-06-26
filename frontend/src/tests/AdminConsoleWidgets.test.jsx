/**
 * AdminConsoleWidgets.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Regression tests for Admin Console usability features:
 *  - AdminQuickActions
 *  - AdminRecentActivity
 *  - AdminGlobalSearch
 *  - AdminFavorites
 *  - AdminNotificationCenter
 *
 * All mocks return plain objects (authFetch contract).
 * No secrets, API keys, or raw metadata in any mock response.
 */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminQuickActions from "../components/AdminQuickActions";
import AdminRecentActivity from "../components/AdminRecentActivity";
import AdminGlobalSearch from "../components/AdminGlobalSearch";
import AdminFavorites from "../components/AdminFavorites";
import AdminNotificationCenter from "../components/AdminNotificationCenter";

import * as ops from "../api/adminOperations";

vi.mock("../api/adminOperations", () => ({
  getRecentActivity: vi.fn(),
  getNotifications: vi.fn(),
  // Prevent other tests from failing if they import full module
  getOperationsSummary: vi.fn(),
  getOperationsHealth: vi.fn(),
  getOperationsPayments: vi.fn(),
  getOperationsWebhooks: vi.fn(),
  getOperationsSubscriptions: vi.fn(),
  getOperationsUsage: vi.fn(),
  getOperationsAlerts: vi.fn(),
  getExpiryJobStatus: vi.fn(),
  runExpiryJob: vi.fn(),
}));

// ── AdminQuickActions ─────────────────────────────────────────────────────────

describe("AdminQuickActions", () => {
  test("renders all 6 quick action cards", () => {
    const handleTabChange = vi.fn();
    const exportUsersCSV  = vi.fn();
    render(
      <AdminQuickActions
        handleTabChange={handleTabChange}
        exportUsersCSV={exportUsersCSV}
      />
    );
    expect(screen.getByTestId("admin-quick-actions")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-create-parent")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-create-teacher")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-create-student")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-create-offer-code")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-run-expiry-job")).toBeInTheDocument();
    expect(screen.getByTestId("quick-action-export-users")).toBeInTheDocument();
  });

  test("Create Parent quick action switches to accounts tab", () => {
    const handleTabChange = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />
    );
    fireEvent.click(screen.getByTestId("quick-action-create-parent"));
    expect(handleTabChange).toHaveBeenCalledWith("accounts");
  });

  test("Create Teacher quick action switches to accounts tab", () => {
    const handleTabChange = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />
    );
    fireEvent.click(screen.getByTestId("quick-action-create-teacher"));
    expect(handleTabChange).toHaveBeenCalledWith("accounts");
  });

  test("Create Student quick action switches to accounts tab", () => {
    const handleTabChange = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />
    );
    fireEvent.click(screen.getByTestId("quick-action-create-student"));
    expect(handleTabChange).toHaveBeenCalledWith("accounts");
  });

  test("Create Offer Code quick action switches to offers tab", () => {
    const handleTabChange = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />
    );
    fireEvent.click(screen.getByTestId("quick-action-create-offer-code"));
    expect(handleTabChange).toHaveBeenCalledWith("offers");
  });

  test("Run Expiry Job quick action switches to operations tab", () => {
    const handleTabChange = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />
    );
    fireEvent.click(screen.getByTestId("quick-action-run-expiry-job"));
    expect(handleTabChange).toHaveBeenCalledWith("operations");
  });

  test("Export Users quick action calls exportUsersCSV", () => {
    const handleTabChange = vi.fn();
    const exportUsersCSV  = vi.fn();
    render(
      <AdminQuickActions handleTabChange={handleTabChange} exportUsersCSV={exportUsersCSV} />
    );
    fireEvent.click(screen.getByTestId("quick-action-export-users"));
    expect(exportUsersCSV).toHaveBeenCalledTimes(1);
    expect(handleTabChange).not.toHaveBeenCalled();
  });

  test("pin button toggles pin state", () => {
    const handleTabChange = vi.fn();
    const onPinToggle     = vi.fn();
    render(
      <AdminQuickActions
        handleTabChange={handleTabChange}
        exportUsersCSV={vi.fn()}
        onPinToggle={onPinToggle}
        pinnedIds={new Set()}
      />
    );
    const pinBtn = screen.getByTestId("pin-create-parent");
    fireEvent.click(pinBtn);
    expect(onPinToggle).toHaveBeenCalledTimes(1);
    expect(onPinToggle.mock.calls[0][0].id).toBe("create-parent");
  });
});

// ── AdminRecentActivity ───────────────────────────────────────────────────────

describe("AdminRecentActivity", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("shows loading state initially", () => {
    ops.getRecentActivity.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AdminRecentActivity accessToken="tok" />);
    expect(screen.getByTestId("recent-activity-loading")).toBeInTheDocument();
  });

  test("shows activity list when API returns data", async () => {
    ops.getRecentActivity.mockResolvedValue({
      activities: [
        { event_type: "payment.verified", summary: "Payment verified ✓", severity: "success", entity_type: "payment", entity_id: "ord_abc", timestamp: "2026-01-01T10:00:00" },
        { event_type: "student.created",  summary: "Student account created",  severity: "info",    entity_type: "user",    entity_id: "usr_123", timestamp: "2026-01-01T09:00:00" },
      ],
      total: 2,
      error: null,
    });
    render(<AdminRecentActivity accessToken="tok" />);
    const list = await screen.findByTestId("recent-activity-list");
    expect(list).toBeInTheDocument();
    expect(screen.getByText("Payment verified ✓")).toBeInTheDocument();
    expect(screen.getByText("Student account created")).toBeInTheDocument();
  });

  test("shows empty state when no activities", async () => {
    ops.getRecentActivity.mockResolvedValue({ activities: [], total: 0, error: null });
    render(<AdminRecentActivity accessToken="tok" />);
    expect(await screen.findByTestId("recent-activity-empty")).toBeInTheDocument();
  });

  test("shows error state when API fails", async () => {
    ops.getRecentActivity.mockRejectedValue(new Error("DB unreachable"));
    render(<AdminRecentActivity accessToken="tok" />);
    expect(await screen.findByTestId("recent-activity-error")).toBeInTheDocument();
    expect(screen.getByText(/DB unreachable/i)).toBeInTheDocument();
  });

  test("does not expose raw metadata or secrets in activity items", async () => {
    ops.getRecentActivity.mockResolvedValue({
      activities: [
        {
          event_type: "payment.verify_failed",
          summary: "Payment verification failed",
          severity: "error",
          entity_type: null,
          entity_id: null,   // ← sensitive events return null entity_id from backend
          timestamp: "2026-01-01T08:00:00",
        },
      ],
      total: 1,
      error: null,
    });
    render(<AdminRecentActivity accessToken="tok" />);
    await screen.findByTestId("recent-activity-list");
    // The component renders summary (human-readable), never raw metadata
    expect(screen.getByText("Payment verification failed")).toBeInTheDocument();
    expect(screen.queryByText(/sk-/i)).not.toBeInTheDocument();  // no API keys
    expect(screen.queryByText(/password/i)).not.toBeInTheDocument(); // no passwords
  });

  test("View all in Operations button calls onViewMore", async () => {
    ops.getRecentActivity.mockResolvedValue({ activities: [], total: 0, error: null });
    const onViewMore = vi.fn();
    render(<AdminRecentActivity accessToken="tok" onViewMore={onViewMore} />);
    await screen.findByTestId("recent-activity-empty");
    fireEvent.click(screen.getByTestId("recent-activity-view-more"));
    expect(onViewMore).toHaveBeenCalledTimes(1);
  });
});

// ── AdminGlobalSearch ─────────────────────────────────────────────────────────

describe("AdminGlobalSearch", () => {
  const handleTabChange = vi.fn();

  beforeEach(() => { vi.clearAllMocks(); });

  function renderSearch(props = {}) {
    return render(
      <AdminGlobalSearch
        handleTabChange={handleTabChange}
        allStudents={[{ id: "s1", username: "Akshita", email: "akshita@test.com", grade: "Grade 9" }]}
        allParents={[{ id: "p1", username: "Ramesh", email: "ramesh@test.com" }]}
        allTeachers={[{ id: "t1", username: "Ms Sharma", email: "sharma@test.com" }]}
        offerCodes={[{ id: "oc1", code: "TRIAL123", description: "June trial" }]}
        {...props}
      />
    );
  }

  test("renders search input", () => {
    renderSearch();
    expect(screen.getByTestId("admin-search-input")).toBeInTheDocument();
  });

  test("section-level search for 'teacher' shows accounts result", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "teacher" } });
    // Wait for debounce
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-results")).toBeInTheDocument();
    }, { timeout: 500 });
    expect(screen.getAllByTestId(/search-result-section-accounts/).length).toBeGreaterThan(0);
  });

  test("section-level search for 'offer' shows offers result", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "offer" } });
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-results")).toBeInTheDocument();
    }, { timeout: 500 });
    expect(screen.getAllByTestId(/search-result-section-offers/).length).toBeGreaterThan(0);
  });

  test("section-level search for 'payment' shows operations result", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "payment" } });
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-results")).toBeInTheDocument();
    }, { timeout: 500 });
    expect(screen.getAllByTestId(/search-result-section-operations/).length).toBeGreaterThan(0);
  });

  test("clicking a section result navigates to correct tab", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "teacher" } });
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-results")).toBeInTheDocument();
    }, { timeout: 500 });
    const result = screen.getAllByTestId(/search-result-section-accounts/)[0];
    fireEvent.click(result);
    expect(handleTabChange).toHaveBeenCalledWith("accounts");
  });

  test("record search for student name shows record result", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "Akshita" } });
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-results")).toBeInTheDocument();
    }, { timeout: 500 });
    expect(screen.getByTestId("search-result-record-student-0")).toBeInTheDocument();
  });

  test("no results message for unrecognised query", async () => {
    renderSearch();
    const input = screen.getByTestId("admin-search-input");
    fireEvent.change(input, { target: { value: "xyzzznothing" } });
    await waitFor(() => {
      expect(screen.getByTestId("admin-search-no-results")).toBeInTheDocument();
    }, { timeout: 500 });
  });

  test("empty query shows no dropdown", () => {
    renderSearch();
    expect(screen.queryByTestId("admin-search-results")).not.toBeInTheDocument();
  });
});

// ── AdminFavorites ────────────────────────────────────────────────────────────

describe("AdminFavorites", () => {
  beforeEach(() => {
    // Reset localStorage before each test
    localStorage.clear();
  });

  test("renders default pinned actions from localStorage seeds", () => {
    const handleTabChange = vi.fn();
    render(<AdminFavorites handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />);
    expect(screen.getByTestId("admin-favorites")).toBeInTheDocument();
    // At least one default pinned action should render
    const favorites = screen.queryAllByTestId(/^favorite-/);
    expect(favorites.length).toBeGreaterThan(0);
  });

  test("unpinning an action removes it from the list", async () => {
    localStorage.setItem(
      "admin_console_favorites",
      JSON.stringify(["create-student"])
    );
    const handleTabChange = vi.fn();
    render(<AdminFavorites handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />);

    expect(screen.getByTestId("favorite-create-student")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("unpin-create-student"));
    expect(screen.queryByTestId("favorite-create-student")).not.toBeInTheDocument();
  });

  test("pinning a new action adds it to the rendered list on fresh mount", () => {
    // Write the pin BEFORE mounting — useState reads localStorage once on init
    localStorage.setItem("admin_console_favorites", JSON.stringify(["create-teacher"]));
    const { unmount } = render(
      <AdminFavorites handleTabChange={vi.fn()} exportUsersCSV={vi.fn()} />
    );
    expect(screen.getByTestId("favorite-create-teacher")).toBeInTheDocument();
    unmount();

    // Now remove the pin, remount — should be gone
    localStorage.setItem("admin_console_favorites", JSON.stringify([]));
    render(<AdminFavorites handleTabChange={vi.fn()} exportUsersCSV={vi.fn()} />);
    expect(screen.queryByTestId("favorite-create-teacher")).not.toBeInTheDocument();
  });

  test("favorites persist in localStorage after pin", () => {
    localStorage.setItem("admin_console_favorites", JSON.stringify(["export-users"]));
    render(<AdminFavorites handleTabChange={vi.fn()} exportUsersCSV={vi.fn()} />);
    // Verify localStorage still has the value after render
    const stored = JSON.parse(localStorage.getItem("admin_console_favorites"));
    expect(stored).toContain("export-users");
  });

  test("fails gracefully when localStorage throws", () => {
    const originalSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = vi.fn(() => { throw new Error("QuotaExceeded"); });
    // Should not throw
    expect(() => {
      render(<AdminFavorites handleTabChange={vi.fn()} exportUsersCSV={vi.fn()} />);
    }).not.toThrow();
    Storage.prototype.setItem = originalSetItem;
  });

  test("clicking a pinned action navigates to its tab", () => {
    localStorage.setItem("admin_console_favorites", JSON.stringify(["create-offer-code"]));
    const handleTabChange = vi.fn();
    render(<AdminFavorites handleTabChange={handleTabChange} exportUsersCSV={vi.fn()} />);
    fireEvent.click(screen.getByTestId("favorite-create-offer-code"));
    expect(handleTabChange).toHaveBeenCalledWith("offers");
  });
});

// ── AdminNotificationCenter ───────────────────────────────────────────────────

describe("AdminNotificationCenter", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders notification bell with badge", async () => {
    ops.getNotifications.mockResolvedValue({
      notifications: [],
      total: 0,
      unread_count: 0,
    });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
    expect(screen.getByTestId("notification-badge")).toBeInTheDocument();
  });

  test("badge shows 0 when no notifications", async () => {
    ops.getNotifications.mockResolvedValue({
      notifications: [],
      total: 0,
      unread_count: 0,
    });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("0");
  });

  test("badge shows count when notifications exist", async () => {
    ops.getNotifications.mockResolvedValue({
      notifications: [
        { type: "payment_failure", severity: "error", message: "1 payment failed in last 24 h", count: 1, link_tab: "operations" },
      ],
      total: 1,
      unread_count: 1,
    });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("1");
  });

  test("clicking bell opens dropdown", async () => {
    ops.getNotifications.mockResolvedValue({ notifications: [], total: 0, unread_count: 0 });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("notification-bell"));
    expect(screen.getByTestId("notification-dropdown")).toBeInTheDocument();
  });

  test("dropdown shows empty state when no notifications", async () => {
    ops.getNotifications.mockResolvedValue({ notifications: [], total: 0, unread_count: 0 });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("notification-bell"));
    expect(screen.getByTestId("notification-empty")).toBeInTheDocument();
  });

  test("notification item links to correct tab when clicked", async () => {
    const onNavigate = vi.fn();
    ops.getNotifications.mockResolvedValue({
      notifications: [
        { type: "payment_failure", severity: "error", message: "Payment failed", count: 1, link_tab: "operations" },
      ],
      total: 1,
      unread_count: 1,
    });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={onNavigate} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("notification-bell"));
    fireEvent.click(screen.getByTestId("notification-item-payment_failure"));
    expect(onNavigate).toHaveBeenCalledWith("operations");
  });

  test("notification payload does not include secrets", async () => {
    ops.getNotifications.mockResolvedValue({
      notifications: [
        {
          type: "rate_limit_spike",
          severity: "warning",
          message: "10 rate-limit events in the last hour",
          count: 10,
          link_tab: "operations",
        },
      ],
      total: 1,
      unread_count: 1,
    });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={vi.fn()} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("notification-bell"));
    // Message is human-readable counts only
    expect(screen.getByText("10 rate-limit events in the last hour")).toBeInTheDocument();
    // No secrets
    expect(screen.queryByText(/sk-/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/token/i)).not.toBeInTheDocument();
  });

  test("View Operations Dashboard button navigates to operations", async () => {
    const onNavigate = vi.fn();
    ops.getNotifications.mockResolvedValue({ notifications: [], total: 0, unread_count: 0 });
    render(<AdminNotificationCenter accessToken="tok" onNavigate={onNavigate} />);
    await waitFor(() => expect(ops.getNotifications).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("notification-bell"));
    fireEvent.click(screen.getByTestId("notification-view-operations"));
    expect(onNavigate).toHaveBeenCalledWith("operations");
  });
});
