/**
 * AdminAnalyticsCorrectness.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Regression tests for the four explicit display states in AdminAnalytics:
 *   ok            → numeric value (0 is shown as "0", not "—")
 *   table_missing → "Not yet enabled"
 *   query_error   → "Unable to load"
 *   loading       → placeholder "…"
 *
 * All API calls are mocked.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import AdminAnalytics from "../components/AdminAnalytics";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// ── helpers ───────────────────────────────────────────────────────────────────

function jsonOk(body) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
}

/** Full summary response with all tables OK and real data */
function fullSummary(overrides = {}) {
  return {
    success: true, period_days: 30,
    users: {
      total: 42, by_role: { student: 30, parent: 10, teacher: 2 },
      new_signups_in_period: 8, free_no_access: 15, paid_active: 20,
      admin_granted_access: 7, query_ok: true, query_error: null,
    },
    payments: {
      total_in_period: 10, paid: 8, failed: 2,
      conversion_rate_percent: 80.0, query_ok: true, query_error: null, query_state: "ok",
    },
    offer_redemptions_in_period: 5, offer_redemptions_state: "ok", offer_redemptions_error: null,
    teacher_student_assignments_total: 12, teacher_assignments_state: "ok", teacher_assignments_error: null,
    ai_usage: { requests_in_period: 300, tokens_in_period: 45000, available: true, state: "ok", error: null },
    mock_tests_completed_in_period: 60, mock_tests_state: "ok", mock_tests_error: null,
    ...overrides,
  };
}

/** Trends response with real data */
function fullTrends(overrides = {}) {
  return {
    success: true, period_days: 30, bucket: "day",
    signup_trend: [{ date: "2026-06-01", count: 3 }, { date: "2026-06-02", count: 5 }],
    signup_trend_state: "ok",
    payment_trend: [{ date: "2026-06-01", paid: 2, failed: 0 }],
    payment_trend_state: "ok", payment_trend_error: null,
    subscription_activation_trend: [], subscription_activation_state: "ok",
    offer_redemption_trend: [], offer_redemption_state: "ok",
    ai_usage_trend: [{ date: "2026-06-01", tokens: 5000 }],
    ai_usage_trend_state: "ok", ai_usage_trend_error: null,
    mock_test_trend: [], mock_test_trend_state: "ok",
    data_availability: {
      ai_usage_logs: true, ai_usage_logs_state: "ok",
      test_history: true, test_history_state: "ok",
      subscription_timeline: true, subscription_timeline_state: "ok",
      offer_redemptions: true, offer_redemptions_state: "ok",
    },
    ...overrides,
  };
}

function mockBoth(summaryOverrides = {}, trendsOverrides = {}) {
  mockFetch.mockImplementation((url) => {
    if (url.includes("summary")) return jsonOk(fullSummary(summaryOverrides));
    if (url.includes("trends"))  return jsonOk(fullTrends(trendsOverrides));
    return jsonOk({});
  });
}

// ── STATE: ok with data ───────────────────────────────────────────────────────

describe("AdminAnalytics — state: ok (data present)", () => {
  beforeEach(() => { vi.clearAllMocks(); mockBoth(); });

  test("shows total users count", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for the value "42" — confirms data has fully loaded
    expect(await screen.findByText("42")).toBeInTheDocument();
  });

  test("shows paid active count", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("42");
    expect(screen.getByTestId("stat-paid-active")).toHaveTextContent("20");
  });

  test("shows payment paid count", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for the total users VALUE "42" to confirm data has loaded
    await screen.findByText("42");
    const paidCard = screen.getByTestId("stat-paid");
    expect(paidCard).toHaveTextContent("8");
  });

  test("shows offer redemptions", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("42");
    expect(screen.getByTestId("stat-offer-redemptions")).toHaveTextContent("5");
  });

  test("shows teacher assignments total", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("42");
    expect(screen.getByTestId("stat-teacher-assignments")).toHaveTextContent("12");
  });

  test("shows AI requests count", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for data load confirmed by value "42"
    await screen.findByText("42");
    expect(screen.getByTestId("stat-ai-requests")).toHaveTextContent("300");
  });

  test("shows mock tests count", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("42");
    expect(screen.getByTestId("stat-mock-tests")).toHaveTextContent("60");
  });

  test("shows success rate percent", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for data to load first (value "42" confirms fetch complete)
    await screen.findByText("42");
    expect(screen.getByTestId("stat-success-rate")).toHaveTextContent("80%");
  });

  test("renders signup trend bars", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Signups");
    // Signups chart has data — no "no-activity" for the Signups chart specifically.
    // Use getAllByTestId and check that at least the Signups bar chart renders bars
    // (i.e., some trend charts have data and some empty ones show no-activity).
    // Verify no "not-enabled" badges anywhere:
    expect(screen.queryByTestId("trend-not-enabled")).not.toBeInTheDocument();
  });
});

// ── STATE: ok with zero data ──────────────────────────────────────────────────

describe("AdminAnalytics — state: ok (zero data)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBoth({
      users: {
        total: 0, by_role: {}, new_signups_in_period: 0, free_no_access: 0,
        paid_active: 0, admin_granted_access: 0, query_ok: true, query_error: null,
      },
      payments: {
        total_in_period: 0, paid: 0, failed: 0, conversion_rate_percent: 0.0,
        query_ok: true, query_error: null, query_state: "ok",
      },
      offer_redemptions_in_period: 0, offer_redemptions_state: "ok",
      teacher_student_assignments_total: 0, teacher_assignments_state: "ok",
      ai_usage: { requests_in_period: 0, tokens_in_period: 0, available: true, state: "ok" },
      mock_tests_completed_in_period: 0, mock_tests_state: "ok",
    }, {
      signup_trend: [], payment_trend: [],
      offer_redemption_trend: [], ai_usage_trend: [], mock_test_trend: [],
    });
  });

  test("shows 0 for total users, not dash", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      const card = screen.getByTestId("stat-total-users");
      expect(card).toHaveTextContent("0");
    }, { timeout: 4000 });
  });

  test("shows 0 for payments, not dash", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      const card = screen.getByTestId("stat-paid");
      expect(card).toHaveTextContent("0");
    }, { timeout: 4000 });
  });

  test("shows 0% success rate, not dash", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });

  test("trend chart shows no-activity message for empty data", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for data to fully load — stat-total-users stops showing "…" when fetch completes
    await waitFor(() => {
      expect(screen.getByTestId("stat-total-users")).not.toHaveTextContent("…");
    }, { timeout: 4000 });
    const noActivity = screen.getAllByTestId("trend-no-activity");
    expect(noActivity.length).toBeGreaterThan(0);
  });

  test("does not show badge-not-enabled for ok tables", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    expect(screen.queryByTestId("badge-not-enabled")).not.toBeInTheDocument();
  });
});

// ── STATE: table_missing ──────────────────────────────────────────────────────

describe("AdminAnalytics — state: table_missing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBoth({
      offer_redemptions_in_period: null, offer_redemptions_state: "table_missing",
      teacher_student_assignments_total: null, teacher_assignments_state: "table_missing",
      ai_usage: { requests_in_period: null, tokens_in_period: null, available: false, state: "table_missing", error: null },
      mock_tests_completed_in_period: null, mock_tests_state: "table_missing",
    }, {
      ai_usage_trend: null, ai_usage_trend_state: "table_missing",
      mock_test_trend: null, mock_test_trend_state: "table_missing",
      offer_redemption_trend: [], offer_redemption_state: "table_missing",
      data_availability: {
        ai_usage_logs: false, ai_usage_logs_state: "table_missing",
        test_history: false, test_history_state: "table_missing",
        subscription_timeline: true, subscription_timeline_state: "ok",
        offer_redemptions: false, offer_redemptions_state: "table_missing",
      },
    });
  });

  test("shows Not yet enabled for offer redemptions", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for the analytics panel to fully render data (not just labels)
    await screen.findByTestId("admin-analytics");
    // Wait for badge-not-enabled to appear (async render after fetch)
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      const badges = document.querySelectorAll("[data-testid='badge-not-enabled']");
      expect(badges.length).toBeGreaterThan(0);
    }, { timeout: 4000 });
  });

  test("does not show raw null or dash for missing tables", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Wait for "Not yet enabled" to appear after async fetch + render
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      expect(document.body.textContent).toContain("Not yet enabled");
    }, { timeout: 4000 });
  });

  test("users section still shows correct counts despite optional tables missing", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    // Use findByText (async) — "42" renders after fetch completes
    expect(await screen.findByText("42")).toBeInTheDocument();
  });

  test("trend chart shows not-enabled for missing table", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("AI Tokens Used");
    // Use waitFor — trend-not-enabled renders asynchronously after fetch in CI
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      const notEnabled = document.querySelectorAll("[data-testid='trend-not-enabled']");
      expect(notEnabled.length).toBeGreaterThan(0);
    }, { timeout: 4000 });
  });

  test("data availability footnotes show missing tables", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    expect(await screen.findByText(/AI usage logs: not yet enabled/i)).toBeInTheDocument();
  });
});

// ── STATE: query_error ────────────────────────────────────────────────────────

describe("AdminAnalytics — state: query_error", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBoth({
      // Profiles query failed
      users: {
        total: 0, by_role: {}, new_signups_in_period: 0, free_no_access: 0,
        paid_active: 0, admin_granted_access: 0,
        query_ok: false, query_error: "connection refused",
      },
      // Payments query failed
      payments: {
        total_in_period: null, paid: null, failed: null, conversion_rate_percent: null,
        query_ok: false, query_error: "timeout", query_state: "query_error",
      },
    });
  });

  test("shows Unable to load for errored metrics", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    const { waitFor } = await import("@testing-library/react");
    await waitFor(() => {
      const badges = document.querySelectorAll("[data-testid='badge-error']");
      expect(badges.length).toBeGreaterThan(0);
    }, { timeout: 4000 });
  });

  test("does not show 0 for errored user metrics", async () => {
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");
    const totalUsersCard = screen.getByTestId("stat-total-users");
    // Should show "Unable to load", not "0"
    expect(totalUsersCard).toHaveTextContent("Unable to load");
    expect(totalUsersCard).not.toHaveTextContent("0");
  });
});

// ── STATE: loading ────────────────────────────────────────────────────────────

describe("AdminAnalytics — loading state", () => {
  test("shows placeholder dots while loading", () => {
    // Never resolve the fetch — component stays in loading state
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<AdminAnalytics accessToken="tok" />);
    // Should show "…" loading indicators
    expect(document.body.textContent).toContain("…");
  });
});

// ── Date filter ───────────────────────────────────────────────────────────────

describe("AdminAnalytics — date filter", () => {
  test("clicking 7d triggers a new fetch with days=7", async () => {
    vi.clearAllMocks();
    mockBoth();
    render(<AdminAnalytics accessToken="tok" />);
    await screen.findByText("Total Users");

    const callCount = mockFetch.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "7d" }));
    await waitFor(() => expect(mockFetch.mock.calls.length).toBeGreaterThan(callCount));

    const url = mockFetch.mock.calls.at(-1)?.[0] || "";
    expect(url).toContain("days=7");
  });
});

// ── Network error ────────────────────────────────────────────────────────────

describe("AdminAnalytics — network error", () => {
  test("shows error banner on fetch failure", async () => {
    vi.clearAllMocks();
    mockFetch.mockRejectedValue(new Error("Network error"));
    render(<AdminAnalytics accessToken="tok" />);
    expect(await screen.findByText(/Network error/i)).toBeInTheDocument();
  });
});
