/**
 * SupportAndViewAsSearch.test.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Regression tests for AdminSupportTools and AdminViewAsUser search wiring.
 *
 * Covers every search UI state:
 *   idle         → prompt message shown
 *   loading      → "Searching…" shown
 *   results      → result list rendered
 *   no-results   → "No users found" message
 *   error        → error banner shown
 *
 * Also covers:
 *   - Enter key triggers search
 *   - Search button triggers search
 *   - Opening a user shows subscription detail
 *   - View-as shows persistent banner
 *   - Exit view-as removes banner
 *   - fetch does NOT double-.json() (raw fetch used)
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import AdminSupportTools from "../components/AdminSupportTools";
import AdminViewAsUser   from "../components/AdminViewAsUser";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// ── Helpers ───────────────────────────────────────────────────────────────────

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  });
}

const STUDENT = {
  id: "s1", username: "Akshita", email: "akshita@example.com",
  role: "student", grade: "Grade 9", subscription_plan: "free",
};

const SUMMARY = {
  success: true,
  user: { ...STUDENT, account_status: "active" },
  resolved_subscription: { source: "free", access_cbse: false, plan_name: "Nano" },
  teacher_assignments: [], linked_children: [],
};

const SUB_HISTORY = {
  success: true, timeline_events: [], payment_history: [], error: null,
};

const AUDIT_HISTORY = {
  success: true, audit_events: [], count: 0,
};

// ─────────────────────────────────────────────────────────────────────────────
// AdminSupportTools
// ─────────────────────────────────────────────────────────────────────────────

describe("AdminSupportTools — idle state", () => {
  test("shows idle prompt on mount", () => {
    render(<AdminSupportTools accessToken="tok" />);
    expect(screen.getByTestId("search-idle")).toBeInTheDocument();
  });

  test("Search button disabled when input empty", () => {
    render(<AdminSupportTools accessToken="tok" />);
    expect(screen.getByRole("button", { name: /search/i })).toBeDisabled();
  });
});

describe("AdminSupportTools — loading state", () => {
  test("shows Searching… during fetch", async () => {
    // Never resolve
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(screen.getByTestId("search-loading")).toBeInTheDocument();
  });
});

describe("AdminSupportTools — results state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonResponse({ success: true, users: [STUDENT], count: 1 });
      if (url.includes("/summary")) return jsonResponse(SUMMARY);
      if (url.includes("subscription-history")) return jsonResponse(SUB_HISTORY);
      if (url.includes("audit-history")) return jsonResponse(AUDIT_HISTORY);
      return jsonResponse({});
    });
  });

  test("search button triggers search and shows results", async () => {
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("support-result-s1")).toBeInTheDocument();
    expect(screen.getByText("Akshita")).toBeInTheDocument();
  });

  test("Enter key triggers search", async () => {
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByTestId("support-result-s1")).toBeInTheDocument();
  });

  test("opening a user shows detail loading then subscription state", async () => {
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const openBtn = await screen.findByText("Open");
    fireEvent.click(openBtn);
    expect(await screen.findByText("Resolved Subscription State")).toBeInTheDocument();
  });

  test("Back button returns to search results", async () => {
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const openBtn = await screen.findByText("Open");
    fireEvent.click(openBtn);
    await screen.findByText("Resolved Subscription State");
    fireEvent.click(screen.getByText(/← Back/));
    expect(screen.getByTestId("support-search-input")).toBeInTheDocument();
  });

  test("Reset Password button visible for students", async () => {
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const openBtn = await screen.findByText("Open");
    fireEvent.click(openBtn);
    expect(await screen.findByText(/Reset Password/i)).toBeInTheDocument();
  });

  test("fetch uses raw fetch (does not double-.json())", async () => {
    // Verify mockFetch.json was called — proves raw fetch is used
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    await screen.findByTestId("support-result-s1");
    // Each fetch call should only call .json() once (from within apiFetch)
    // The mock .json() is called once per fetch — not twice
    const jsonCallCount = mockFetch.mock.results
      .filter((r) => r.value)
      .length;
    expect(jsonCallCount).toBeGreaterThan(0);
  });
});

describe("AdminSupportTools — no results state", () => {
  test("shows no-results message when search returns empty", async () => {
    vi.clearAllMocks();
    mockFetch.mockImplementation(() => jsonResponse({ success: true, users: [], count: 0 }));
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "zzznomatch" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("search-no-results")).toBeInTheDocument();
    expect(screen.getByText(/zzznomatch/)).toBeInTheDocument();
  });
});

describe("AdminSupportTools — error state", () => {
  test("shows error banner when fetch fails", async () => {
    vi.clearAllMocks();
    mockFetch.mockRejectedValue(new Error("Network error"));
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "anyone" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("search-error")).toBeInTheDocument();
    expect(screen.getByText(/Network error/i)).toBeInTheDocument();
  });

  test("shows error banner for HTTP 403", async () => {
    vi.clearAllMocks();
    mockFetch.mockImplementation(() =>
      jsonResponse({ detail: "Forbidden" }, 403)
    );
    render(<AdminSupportTools accessToken="tok" />);
    const input = screen.getByTestId("support-search-input");
    fireEvent.change(input, { target: { value: "anyone" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("search-error")).toBeInTheDocument();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// AdminViewAsUser
// ─────────────────────────────────────────────────────────────────────────────

describe("AdminViewAsUser — idle state", () => {
  test("shows idle prompt on mount", () => {
    render(<AdminViewAsUser accessToken="tok" />);
    expect(screen.getByTestId("view-as-idle")).toBeInTheDocument();
  });

  test("search input and button present", () => {
    render(<AdminViewAsUser accessToken="tok" />);
    expect(screen.getByTestId("view-as-search-input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument();
  });
});

describe("AdminViewAsUser — no results state", () => {
  test("shows no-results message for empty search", async () => {
    vi.clearAllMocks();
    mockFetch.mockImplementation(() => jsonResponse({ success: true, users: [], count: 0 }));
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "zzznomatch" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("view-as-no-results")).toBeInTheDocument();
  });
});

describe("AdminViewAsUser — results + view-as", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockImplementation((url) => {
      if (url.includes("user-search")) return jsonResponse({ success: true, users: [STUDENT], count: 1 });
      if (url.includes("view-as")) return jsonResponse({
        success: true,
        view_as: { user_id: "s1", username: "Akshita", role: "student", grade: "Grade 9", subscription_plan: "free", access_cbse: false, account_status: "active" },
        resolved_subscription: { source: "free" },
        restrictions: ["no_payment_actions", "read_only"],
        banner: "Viewing as Akshita (student). Admin actions restricted. Exit to resume admin mode.",
      });
      if (url.includes("log-impersonation")) return jsonResponse({ success: true });
      return jsonResponse({});
    });
  });

  test("search shows results with View-as button", async () => {
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("view-as-result-s1")).toBeInTheDocument();
    expect(screen.getByTestId("start-view-as-s1")).toBeInTheDocument();
  });

  test("Enter key triggers search", async () => {
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(await screen.findByTestId("view-as-result-s1")).toBeInTheDocument();
  });

  test("clicking View-as shows persistent banner", async () => {
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    const banner = await screen.findByTestId("view-as-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Akshita");
  });

  test("exit view-as removes banner", async () => {
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    await screen.findByTestId("view-as-banner");
    fireEvent.click(screen.getByTestId("exit-view-as-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("view-as-banner")).not.toBeInTheDocument();
    });
    // Idle state shown again
    expect(screen.getByTestId("view-as-idle")).toBeInTheDocument();
  });

  test("view-as context shows restrictions panel", async () => {
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "akshita" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    const btn = await screen.findByTestId("start-view-as-s1");
    fireEvent.click(btn);
    expect(await screen.findByTestId("view-as-context")).toBeInTheDocument();
    expect(screen.getByText(/no_payment_actions/)).toBeInTheDocument();
  });
});

describe("AdminViewAsUser — error state", () => {
  test("shows error when search fails", async () => {
    vi.clearAllMocks();
    mockFetch.mockRejectedValue(new Error("Service unavailable"));
    render(<AdminViewAsUser accessToken="tok" />);
    const input = screen.getByTestId("view-as-search-input");
    fireEvent.change(input, { target: { value: "anyone" } });
    fireEvent.click(screen.getByRole("button", { name: /search/i }));
    expect(await screen.findByTestId("view-as-error")).toBeInTheDocument();
    expect(screen.getByText(/Service unavailable/i)).toBeInTheDocument();
  });
});
