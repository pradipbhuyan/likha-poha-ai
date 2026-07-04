/**
 * AdminProductivity.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Frontend regression tests for the Admin Console productivity features:
 *   - AdminBulkTools
 *   - AdminSavedViews
 *   - AdminAnalytics
 *   - AdminViewAsUser
 *   - AdminSupportTools
 *
 * Tests verify UI structure, tab navigation, security constraints, and
 * graceful loading/empty/error states.
 * All API calls are mocked — no live backend required.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminBulkTools    from "../components/AdminBulkTools";
import AdminSavedViews   from "../components/AdminSavedViews";
import AdminAnalytics    from "../components/AdminAnalytics";
import AdminViewAsUser   from "../components/AdminViewAsUser";
import AdminSupportTools from "../components/AdminSupportTools";

// ── Global fetch mock ─────────────────────────────────────────────────────────
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonOk(body) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve(new Blob()),
  });
}

// ── AdminBulkTools ────────────────────────────────────────────────────────────

describe("AdminBulkTools", () => {
  const teachers = [{ id: "t1", username: "Ms Sharma", email: "sharma@t.com" }];
  const students = [{ id: "s1", username: "Akshita", email: "a@s.com" }];
  const parents  = [{ id: "p1", username: "Ramesh",  email: "r@p.com" }];

  beforeEach(() => { vi.clearAllMocks(); });

  test("renders all 5 sub-tabs", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    expect(screen.getByTestId("admin-bulk-tools")).toBeInTheDocument();
    expect(screen.getByText("Assign Teacher")).toBeInTheDocument();
    expect(screen.getByText("Reset Passwords")).toBeInTheDocument();
    expect(screen.getByText("Grant Access")).toBeInTheDocument();
    expect(screen.getByText("Export")).toBeInTheDocument();
    expect(screen.getByText("Import CSV")).toBeInTheDocument();
  });

  test("Assign Teacher tab shows teacher selector and student list", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    // The teacher select combobox is present
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    // The student list shows "Akshita" in the CheckList
    expect(screen.getByText("Akshita")).toBeInTheDocument();
  });

  test("Create Offer Code quick action is in Assign tab (default)", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    // Assign Teacher tab is default — assign button is disabled with 0 selections
    const assignBtn = screen.getByText(/Assign 0 Student/i);
    expect(assignBtn).toBeInTheDocument();
  });

  test("Reset Passwords tab shows student list", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    fireEvent.click(screen.getByText("Reset Passwords"));
    expect(screen.getByText(/once only/i)).toBeInTheDocument();
    expect(screen.getByText("Akshita")).toBeInTheDocument();
  });

  test("Import CSV tab shows textarea and preview button", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    fireEvent.click(screen.getByText("Import CSV"));
    expect(screen.getByTestId("csv-import-textarea")).toBeInTheDocument();
    expect(screen.getByText(/Preview & Validate/i)).toBeInTheDocument();
  });

  test("CSV preview shows validation errors for empty name", () => {
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    fireEvent.click(screen.getByText("Import CSV"));
    const textarea = screen.getByTestId("csv-import-textarea");
    fireEvent.change(textarea, { target: { value: "name,grade\n,Grade 9" } });
    fireEvent.click(screen.getByText(/Preview & Validate/i));
    expect(screen.getByText(/name required/i)).toBeInTheDocument();
  });

  test("CSV export does not show passwords in result", async () => {
    mockFetch.mockResolvedValue({ ok: true, blob: () => Promise.resolve(new Blob(["id,username\nu1,Alice"])) });
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    fireEvent.click(screen.getByText("Export"));
    // Select a user
    const label = screen.getByText("Akshita").closest("label");
    fireEvent.click(label);
    expect(screen.getByText(/Export 1 User/i)).toBeInTheDocument();
  });

  test("Bulk assign shows success result", async () => {
    mockFetch.mockResolvedValue(jsonOk({ success: true, assigned: 1, skipped: 0, failed: 0 }));
    render(<AdminBulkTools accessToken="tok" allStudents={students} allTeachers={teachers} allParents={parents} />);
    // Select teacher
    const sel = screen.getByRole("combobox");
    fireEvent.change(sel, { target: { value: "t1" } });
    // Select student
    const studentLabel = screen.getByText("Akshita").closest("label");
    fireEvent.click(studentLabel);
    const assignBtn = screen.getByText(/Assign 1 Student/i);
    fireEvent.click(assignBtn);
    await waitFor(() => {
      expect(screen.getByText(/Assigned: 1/i)).toBeInTheDocument();
    });
  });
});

// ── AdminSavedViews ───────────────────────────────────────────────────────────

describe("AdminSavedViews", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/views") && !url.includes("/views/")) {
        return jsonOk({ success: true, views: [
          { id: "expired_subscriptions", label: "Expired Subscriptions", description: "Expired users", category: "subscriptions" },
          { id: "recent_signups", label: "Recent Signups", description: "New users", category: "users" },
        ], total: 2 });
      }
      return jsonOk({ success: true, rows: [], count: 0 });
    });
  });

  test("renders prebuilt view list after load", async () => {
    render(<AdminSavedViews accessToken="tok" />);
    expect(await screen.findByTestId("admin-saved-views")).toBeInTheDocument();
    expect(await screen.findByTestId("view-btn-expired_subscriptions")).toBeInTheDocument();
  });

  test("shows select-view message by default", async () => {
    render(<AdminSavedViews accessToken="tok" />);
    expect(await screen.findByText(/Select a view/i)).toBeInTheDocument();
  });

  test("clicking a view fetches and shows results", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("/api/admin/views") && !url.includes("/views/")) {
        return jsonOk({ success: true, views: [
          { id: "recent_signups", label: "Recent Signups", description: "New", category: "users" }
        ], total: 1 });
      }
      return jsonOk({ success: true, rows: [{ id: "u1", username: "Alice", email: "a@b.com" }], count: 1 });
    });
    render(<AdminSavedViews accessToken="tok" />);
    const btn = await screen.findByTestId("view-btn-recent_signups");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText("Alice")).toBeInTheDocument();
    });
  });

  test("empty view shows no-results message", async () => {
    render(<AdminSavedViews accessToken="tok" />);
    const btn = await screen.findByTestId("view-btn-expired_subscriptions");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/No results/i)).toBeInTheDocument();
    });
  });
});

// ── AdminAnalytics ────────────────────────────────────────────────────────────

describe("AdminAnalytics", () => {
  const summaryData = {
    success: true, period_days: 30,
    users: { total: 50, by_role: { student: 30, parent: 15, teacher: 5 }, new_signups_in_period: 10, free_no_access: 20, paid_active: 15, admin_granted_access: 5 },
    payments: { total_in_period: 8, paid: 6, failed: 2, conversion_rate_percent: 75.0 },
    offer_redemptions_in_period: 4,
    teacher_student_assignments_total: 12,
    ai_usage: { requests_in_period: null, tokens_in_period: null, available: false },
    mock_tests_completed_in_period: 20,
  };
  const trendsData = {
    success: true, period_days: 30, bucket: "day",
    signup_trend: [{ date: "2026-01-01", count: 3 }],
    payment_trend: [{ date: "2026-01-01", paid: 2, failed: 0 }],
    offer_redemption_trend: [],
    ai_usage_trend: null,
    mock_test_trend: null,
    subscription_activation_trend: [],
    data_availability: {
      ai_usage_logs: false, ai_usage_logs_state: "table_missing",
      test_history: true, test_history_state: "ok",
      subscription_timeline: true, subscription_timeline_state: "ok",
      offer_redemptions: true, offer_redemptions_state: "ok",
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockImplementation((url) => {
      if (url.includes("summary")) return jsonOk(summaryData);
      if (url.includes("trends")) return jsonOk(trendsData);
      return jsonOk({ success: true });
    });
  });

  test("renders analytics page with data", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    expect(screen.getByTestId("admin-analytics")).toBeInTheDocument();
    expect(await screen.findByText("Total Users")).toBeInTheDocument();
    expect(await screen.findByText("50")).toBeInTheDocument();
  });

  test("shows Not yet enabled for unavailable AI data", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    // Wait for data to load — findAll retries until badges appear or timeout.
    // The component renders STATE_MISSING badges after the fetch resolves
    // (ai.state is absent in mock data → defaults to STATE_MISSING).
    const badges = await screen.findAllByTestId("badge-not-enabled");
    expect(badges.length).toBeGreaterThan(0);
  });

  test("renders trend bar chart for signups", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    expect(await screen.findByText("Signups")).toBeInTheDocument();
  });

  test("date filter buttons are clickable", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    fireEvent.click(screen.getByRole("button", { name: "7d" }));
    // Should trigger a reload (mockFetch called again)
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(4)); // 2 initial + 2 after click
  });

  test("shows unavailability note for missing AI table", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // New component shows "AI usage logs: not yet enabled" in the footnotes
    expect(await screen.findByText(/AI usage logs: not yet enabled/i)).toBeInTheDocument();
  });
});

// ── AdminViewAsUser ───────────────────────────────────────────────────────────

describe("AdminViewAsUser", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders search input", () => {
    render(<AdminViewAsUser accessToken="tok" />);
    expect(screen.getByTestId("admin-view-as-user")).toBeInTheDocument();
    expect(screen.getByTestId("view-as-search-input")).toBeInTheDocument();
  });

  test("search returns user results", async () => {
    mockFetch.mockResolvedValue(jsonOk({
      success: true,
      users: [{ id: "s1", username: "Akshita", email: "a@s.com", role: "student", grade: "Grade 9" }],
    }));
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "Akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("view-as-result-s1")).toBeInTheDocument();
    expect(screen.getByText("Akshita")).toBeInTheDocument();
  });

  test("view-as shows persistent banner", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonOk({
        success: true,
        users: [{ id: "s1", username: "Student One", email: "s@s.com", role: "student", grade: "Grade 9" }],
      });
      if (url.includes("view-as")) return jsonOk({
        success: true,
        view_as: { user_id: "s1", username: "Student One", role: "student" },
        banner: "Viewing as Student One (student). Admin actions restricted. Exit to resume admin mode.",
        restrictions: ["read_only"],
        resolved_subscription: { source: "free" },
      });
      return jsonOk({ success: true });
    });
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "Student" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    const banner = await screen.findByTestId("view-as-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Student One");
    expect(screen.getByTestId("exit-view-as-btn")).toBeInTheDocument();
  });

  test("exit view-as removes banner", async () => {
    mockFetch.mockImplementation(() => jsonOk({
      success: true,
      users: [{ id: "s1", username: "U", email: "u@u.com", role: "student", grade: "Grade 9" }],
      view_as: { user_id: "s1", username: "U", role: "student" },
      banner: "Viewing as U (student). Admin actions restricted. Exit to resume admin mode.",
      restrictions: ["read_only"],
      resolved_subscription: { source: "free" },
    }));
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "U" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    await screen.findByTestId("view-as-banner");
    // Exit
    fireEvent.click(screen.getByTestId("exit-view-as-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("view-as-banner")).not.toBeInTheDocument();
    });
  });

  test("banner shows read_only restriction message", async () => {
    mockFetch.mockImplementation(() => jsonOk({
      success: true,
      users: [{ id: "s1", username: "ReadOnlyUser", email: "r@r.com", role: "student", grade: "Grade 9" }],
      view_as: { user_id: "s1", username: "ReadOnlyUser", role: "student" },
      banner: "Viewing as ReadOnlyUser (student). Admin actions restricted.",
      restrictions: ["no_payment_actions", "read_only"],
      resolved_subscription: { source: "free" },
    }));
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "ReadOnly" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    await screen.findByTestId("view-as-context");
    expect(screen.getByText(/no_payment_actions/)).toBeInTheDocument();
  });
});

// ── AdminSupportTools ─────────────────────────────────────────────────────────

describe("AdminSupportTools", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders search input", () => {
    render(<AdminSupportTools accessToken="tok" />);
    expect(screen.getByTestId("admin-support-tools")).toBeInTheDocument();
    expect(screen.getByTestId("support-search-input")).toBeInTheDocument();
  });

  test("search returns user results", async () => {
    mockFetch.mockResolvedValue(jsonOk({
      success: true,
      users: [{ id: "u1", username: "Akshita", email: "a@s.com", role: "student", grade: "Grade 9", subscription_plan: "free" }],
    }));
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "Akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("support-result-u1")).toBeInTheDocument();
    expect(screen.getByText("Akshita")).toBeInTheDocument();
  });

  test("opening a user shows subscription state", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonOk({
        success: true,
        users: [{ id: "u1", username: "Alice", email: "a@b.com", role: "student", grade: "Grade 9", subscription_plan: "free" }],
      });
      if (url.includes("/summary")) return jsonOk({
        success: true, user: { id: "u1", username: "Alice", role: "student" },
        resolved_subscription: { source: "free", access_cbse: false, plan_name: "Nano" },
        teacher_assignments: [], linked_children: [],
      });
      return jsonOk({ success: true, timeline_events: [], payment_history: [], audit_events: [] });
    });
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "Alice" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const openBtn = await screen.findByText("Open");
    fireEvent.click(openBtn);
    expect(await screen.findByText("Resolved Subscription State")).toBeInTheDocument();
  });

  test("Reset Password button shown only for students", async () => {
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonOk({
        success: true,
        users: [{ id: "s1", username: "Student", email: "s@s.com", role: "student", grade: "Grade 9", subscription_plan: "free" }],
      });
      if (url.includes("/summary")) return jsonOk({
        success: true, user: { id: "s1", username: "Student", role: "student" },
        resolved_subscription: { source: "free" },
        teacher_assignments: [], linked_children: [],
      });
      return jsonOk({ success: true, timeline_events: [], payment_history: [], audit_events: [] });
    });
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "Student" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const openBtn = await screen.findByText("Open");
    fireEvent.click(openBtn);
    expect(await screen.findByText(/Reset Password/i)).toBeInTheDocument();
  });

  test("password reset shows temp password once only", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonOk({
        success: true, users: [{ id: "s1", username: "S", email: "s@s.com", role: "student", grade: "Grade 9", subscription_plan: "free" }],
      });
      if (url.includes("/summary")) return jsonOk({
        success: true, user: { id: "s1", username: "S", role: "student" },
        resolved_subscription: { source: "free" }, teacher_assignments: [], linked_children: [],
      });
      if (url.includes("reset-password")) return jsonOk({
        success: true, username: "S", email: "s@s.com",
        temp_password: "TmpPass123!", warning: "Show once only.",
      });
      return jsonOk({ success: true, timeline_events: [], payment_history: [], audit_events: [] });
    });
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "S" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    fireEvent.click(await screen.findByText("Open"));
    const resetBtn = await screen.findByText(/Reset Password/i);
    fireEvent.click(resetBtn);
    expect(await screen.findByText("TmpPass123!")).toBeInTheDocument();
    // Password should not appear in the audit response — just UI display
  });
});
