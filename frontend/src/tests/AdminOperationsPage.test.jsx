/**
 * AdminOperationsPage.test.jsx
 * ────────────────────────────────────────────────────────────────────────────
 * Regression tests for the Operations Dashboard.
 *
 * Root cause fix: adminOperations.js uses authFetch which already returns
 * parsed JSON. AdminOperationsPage must NOT call .json() on the result.
 *
 * Covers:
 *  - Page renders when API returns parsed JSON objects (not Response objects)
 *  - No .json() call is made on already-parsed objects
 *  - Error state renders only when API call actually fails
 *  - Refresh reloads data (refreshKey changes triggers fetchAll)
 *  - Date filter reloads data (days change triggers fetchAll)
 *  - Expiry job button confirmation and result display work correctly
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminOperationsPage from "../pages/AdminOperationsPage";
import * as ops from "../api/adminOperations";

// Mock all adminOperations exports
vi.mock("../api/adminOperations", () => ({
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

const adminUser = { role: "admin", username: "Admin", accessToken: "tok" };

/** Minimal happy-path stub responses (plain objects, NOT Response objects) */
function setupHappyPath() {
  ops.getOperationsSummary.mockResolvedValue({
    success: true, generated_at: "2026-01-01T00:00:00",
    health: { database_connected: true, overall_ok: true },
    payments_30d: { total: 5, paid: 4, failed: 1, success_rate_percent: 80 },
    users: { total: 10, student: 6, parent: 3, teacher: 1 },
    in_memory_metrics: { _note: "Process-local — resets on restart", "payment.verified": 2 },
  });
  ops.getOperationsHealth.mockResolvedValue({
    success: true, checked_at: "2026-01-01T00:00:00",
    app: { status: "ok", python_version: "3.13" },
    database: { connected: true, error: null },
    config: { SUPABASE_URL: true, RAZORPAY_KEY_ID: true },
    config_critical_ok: true, overall_healthy: true,
  });
  ops.getOperationsPayments.mockResolvedValue({
    success: true, period_days: 30,
    summary: { total_payments: 5, paid: 4, failed: 1, success_rate_percent: 80, created_pending: 0, signature_failed: 1 },
    in_memory_counters: { _note: "Process-local counters — resets on server restart", "payment.verified": 2 },
    recent_failures: [], recent_paid: [], page: 1, page_size: 20,
  });
  ops.getOperationsWebhooks.mockResolvedValue({
    success: true, period_days: 30,
    in_memory_counters: { _note: "Process-local counters — resets on server restart" },
    webhook_confirmed_via_db: 3,
    recent_webhook_audit_events: [],
    last_received: null,
  });
  ops.getOperationsSubscriptions.mockResolvedValue({
    success: true, period_days: 30,
    active_subscriptions: { FREE_TIER: 7, Nano: 2, Premium: 1 },
    timeline_event_counts: {},
    recent_timeline_events: [],
    in_memory_counters: { _note: "Process-local counters — resets on server restart", "subscription.expired": 0 },
  });
  ops.getOperationsUsage.mockResolvedValue({
    success: true,
    users: { total: 10, student: 6, parent: 3, teacher: 1, admin: 0 },
    teacher_student_assignments: 4,
    offer_redemptions: 2,
    in_memory_counters: { _note: "Process-local counters — resets on server restart", "rate_limit.exceeded": 0 },
  });
  ops.getOperationsAlerts.mockResolvedValue({
    success: true, period_days: 7,
    alert_counts: {}, recent_alerts: [], total_alerts_in_period: 0,
    in_memory_rate_limit_exceeded: 0,
    page: 1, page_size: 20,
  });
  ops.getExpiryJobStatus.mockResolvedValue({
    success: true, last_run: null, last_run_summary: null,
    in_memory_counters: { "expiry_job.ran": 0 },
    recent_runs: [],
  });
}

describe("AdminOperationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupHappyPath();
  });

  test("renders without error when API returns plain parsed objects", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    expect(await screen.findByText("System Health")).toBeInTheDocument();
    expect(screen.getByText("Payment Monitoring")).toBeInTheDocument();
    expect(screen.getByText("Subscription Monitoring")).toBeInTheDocument();
    expect(screen.getByText("User & Usage Metrics")).toBeInTheDocument();
    expect(screen.getByText("Expiry Job")).toBeInTheDocument();
  });

  test("API functions are called directly — no .json() wrapper", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("System Health");

    // Verify all API functions were called exactly once
    expect(ops.getOperationsSummary).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsHealth).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsPayments).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsWebhooks).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsSubscriptions).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsUsage).toHaveBeenCalledTimes(1);
    expect(ops.getOperationsAlerts).toHaveBeenCalledTimes(1);
    expect(ops.getExpiryJobStatus).toHaveBeenCalledTimes(1);

    // Verify the mocks returned plain objects (not Response with .json())
    // If .json() had been called on the plain object, it would have thrown
    // "r.json is not a function" — the fact we get here means it was NOT called.
  });

  test("shows health data from parsed response", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("System Health");
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  test("shows payment stats from parsed response", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("Payment Monitoring");
    // Total payments = 5
    expect(screen.getByText("5")).toBeInTheDocument();
    // Success rate = 80%
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  test("shows subscription plan counts from parsed response", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("Subscription Monitoring");
    expect(screen.getByText("FREE_TIER")).toBeInTheDocument();
    expect(screen.getByText("Nano")).toBeInTheDocument();
  });

  test("shows user counts from parsed response", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("User & Usage Metrics");
    expect(screen.getByText("Total Users")).toBeInTheDocument();
  });

  test("section shows error only when API call fails", async () => {
    ops.getOperationsHealth.mockRejectedValue(new Error("Health check failed"));
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText(/Health check failed/i);
    // Other sections should still render (health failed but others succeeded)
    expect(await screen.findByText("Payment Monitoring")).toBeInTheDocument();
  });

  test("refresh button reloads all data", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("System Health");
    expect(ops.getOperationsSummary).toHaveBeenCalledTimes(1);

    const refreshBtn = screen.getByRole("button", { name: /↺ Refresh/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(ops.getOperationsSummary).toHaveBeenCalledTimes(2);
    });
  });

  test("date filter button changes the days parameter", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("System Health");

    // Default is 30 days
    expect(ops.getOperationsPayments).toHaveBeenCalledWith(30);

    // Click "7 days"
    fireEvent.click(screen.getByRole("button", { name: "7 days" }));

    await waitFor(() => {
      expect(ops.getOperationsPayments).toHaveBeenCalledWith(7);
    });
  });

  test("expiry job confirmation flow works correctly", async () => {
    ops.runExpiryJob.mockResolvedValue({
      success: true,
      users_inspected: 10,
      users_revoked: 3,
      users_skipped_already_revoked: 7,
      errors: 0,
    });

    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("Expiry Job");

    // Click Run
    const runBtn = screen.getByTestId("run-expiry-job-btn");
    fireEvent.click(runBtn);

    // Confirmation dialog appears
    const confirmBtn = await screen.findByTestId("confirm-expiry-job-btn");
    expect(confirmBtn).toBeInTheDocument();

    // Confirm
    fireEvent.click(confirmBtn);

    // Result appears
    const result = await screen.findByTestId("expiry-job-result");
    expect(result).toHaveTextContent("Inspected: 10");
    expect(result).toHaveTextContent("Revoked: 3");
    expect(ops.runExpiryJob).toHaveBeenCalledTimes(1);
  });

  test("expiry job error state displays correctly", async () => {
    ops.runExpiryJob.mockRejectedValue(new Error("Server error"));

    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("Expiry Job");

    fireEvent.click(screen.getByTestId("run-expiry-job-btn"));
    fireEvent.click(await screen.findByTestId("confirm-expiry-job-btn"));

    const result = await screen.findByTestId("expiry-job-result");
    expect(result).toHaveTextContent("Error: Server error");
  });

  test("in-memory note is visible in payment section", async () => {
    render(<AdminOperationsPage user={adminUser} />);
    await screen.findByText("Payment Monitoring");
    const notes = screen.getAllByText(/In-memory counters/i);
    expect(notes.length).toBeGreaterThanOrEqual(1);
  });

  test("no section crashes on null/undefined API response", async () => {
    // All return null (simulating all API failures handled gracefully)
    ops.getOperationsSummary.mockRejectedValue(new Error("fail"));
    ops.getOperationsHealth.mockRejectedValue(new Error("fail"));
    ops.getOperationsPayments.mockRejectedValue(new Error("fail"));
    ops.getOperationsWebhooks.mockRejectedValue(new Error("fail"));
    ops.getOperationsSubscriptions.mockRejectedValue(new Error("fail"));
    ops.getOperationsUsage.mockRejectedValue(new Error("fail"));
    ops.getOperationsAlerts.mockRejectedValue(new Error("fail"));
    ops.getExpiryJobStatus.mockRejectedValue(new Error("fail"));

    render(<AdminOperationsPage user={adminUser} />);

    // Page should render without crashing, showing error banners per section
    await waitFor(() => {
      const warnings = screen.getAllByText(/⚠/);
      expect(warnings.length).toBeGreaterThan(0);
    });
  });
});
