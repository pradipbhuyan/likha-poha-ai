import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AdminPaymentsPage from "../pages/AdminPaymentsPage";
import { getAdminPaymentLogs } from "../api/adminControl";

vi.mock("../api/adminControl", () => ({
  getAdminPaymentLogs: vi.fn(),
}));

const USER = { accessToken: "token-1", role: "admin" };

function _payment(overrides = {}) {
  return {
    id: "pay-1",
    order_id: "order_1",
    payment_id: "rzp_1",
    status: "paid",
    plan_key: "starter",
    amount: 299,
    currency: "INR",
    username: "priya",
    email: "priya@test.com",
    grade: "Grade 9",
    created_at: "2026-01-15T10:00:00",
    verified_at: "2026-01-15T10:01:00",
    failure_reason: "",
    ...overrides,
  };
}

function _response(overrides = {}) {
  return {
    success: true,
    payments: [_payment()],
    summary: {
      monthly_revenue: 299,
      total_revenue: 1196,
      active_paid_users: 3,
      total_transactions: 4,
      failed_transactions: 1,
      plan_distribution: { starter: 3, family_premium: 1 },
    },
    trends: [
      { month: "2025-02", label: "Feb 25", revenue: 0, users: 0 },
      { month: "2026-01", label: "Jan 26", revenue: 299, users: 1 },
    ],
    ...overrides,
  };
}

describe("AdminPaymentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("shows a loading state before data arrives", () => {
    getAdminPaymentLogs.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AdminPaymentsPage user={USER} />);
    expect(screen.getByText(/loading payment logs/i)).toBeInTheDocument();
  });

  test("renders summary cards once data loads", async () => {
    // No payments/plan_distribution in this response — isolates the summary
    // cards from the table/distribution sections, which reuse overlapping
    // numbers (₹299, plan labels) in other tests below.
    getAdminPaymentLogs.mockResolvedValue(_response({ payments: [], summary: {
      monthly_revenue: 897, total_revenue: 1196, active_paid_users: 3,
      total_transactions: 4, failed_transactions: 1, plan_distribution: {},
    } }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText("₹897")).toBeInTheDocument(); // this month revenue
    expect(screen.getByText("₹1,196")).toBeInTheDocument(); // total revenue
    expect(screen.getByText("3")).toBeInTheDocument(); // active paid users
    expect(screen.getByText("4")).toBeInTheDocument(); // total transactions
    expect(screen.getByText("1")).toBeInTheDocument(); // failed transactions
  });

  test("shows an error message when the API call fails", async () => {
    getAdminPaymentLogs.mockRejectedValue(new Error("Network down"));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText("Network down")).toBeInTheDocument();
  });

  test("renders a payment row with the mapped plan label", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      payments: [_payment({ plan_key: "starter" })],
      summary: {
        monthly_revenue: 0, total_revenue: 0, active_paid_users: 0,
        total_transactions: 0, failed_transactions: 0, plan_distribution: {},
      },
    }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText("priya")).toBeInTheDocument();
    expect(screen.getByText("priya@test.com")).toBeInTheDocument();
    expect(screen.getByText("Premium ₹299")).toBeInTheDocument();
    expect(screen.getByText("PAID")).toBeInTheDocument();
  });

  test("an unrecognized plan_key falls back to showing the raw key", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      payments: [_payment({ plan_key: "some_new_plan" })],
    }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText("some_new_plan")).toBeInTheDocument();
  });

  test("empty payments shows the setup hint, not the generic no-match message", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({ payments: [] }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText(/no payment records yet/i)).toBeInTheDocument();
  });

  test("search filters the table by username", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      payments: [
        _payment({ id: "p1", username: "priya", email: "priya@test.com" }),
        _payment({ id: "p2", username: "rohan", email: "rohan@test.com" }),
      ],
    }));
    render(<AdminPaymentsPage user={USER} />);

    await screen.findByText("priya");
    expect(screen.getByText("rohan")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/search by name, email, order id/i), {
      target: { value: "priya" },
    });

    expect(screen.getByText("priya")).toBeInTheDocument();
    expect(screen.queryByText("rohan")).not.toBeInTheDocument();
  });

  test("search with no matches shows the no-match message, not the setup hint", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      payments: [_payment({ username: "priya" })],
    }));
    render(<AdminPaymentsPage user={USER} />);
    await screen.findByText("priya");

    fireEvent.change(screen.getByPlaceholderText(/search by name, email, order id/i), {
      target: { value: "nobody-matches-this" },
    });

    expect(await screen.findByText(/no records match your filter/i)).toBeInTheDocument();
  });

  test("status filter narrows the table to the selected status", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      payments: [
        _payment({ id: "p1", username: "priya", status: "paid" }),
        _payment({ id: "p2", username: "rohan", status: "failed", failure_reason: "card declined" }),
      ],
    }));
    render(<AdminPaymentsPage user={USER} />);
    await screen.findByText("priya");

    fireEvent.change(screen.getByDisplayValue("All Status"), { target: { value: "failed" } });

    expect(screen.queryByText("priya")).not.toBeInTheDocument();
    expect(screen.getByText("rohan")).toBeInTheDocument();
    expect(screen.getByText("card declined")).toBeInTheDocument();
  });

  test("export button is disabled when there are no filtered payments", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({ payments: [] }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByRole("button", { name: /export excel/i })).toBeDisabled();
  });

  test("export button is enabled once payments are loaded", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response());
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByRole("button", { name: /export excel/i })).toBeEnabled();
  });

  test("refresh button re-fetches payment logs", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response());
    render(<AdminPaymentsPage user={USER} />);
    await screen.findByText("priya");

    expect(getAdminPaymentLogs).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => {
      expect(getAdminPaymentLogs).toHaveBeenCalledTimes(2);
    });
  });

  test("plan distribution renders each plan's share", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      summary: {
        monthly_revenue: 0, total_revenue: 0, active_paid_users: 0,
        total_transactions: 4, failed_transactions: 0,
        plan_distribution: { starter: 3, family_premium: 1 },
      },
    }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText("3 (75%)")).toBeInTheDocument();
    expect(screen.getByText("1 (25%)")).toBeInTheDocument();
  });

  test("no plan distribution shows the empty-state message", async () => {
    getAdminPaymentLogs.mockResolvedValue(_response({
      summary: {
        monthly_revenue: 0, total_revenue: 0, active_paid_users: 0,
        total_transactions: 0, failed_transactions: 0, plan_distribution: {},
      },
    }));
    render(<AdminPaymentsPage user={USER} />);

    expect(await screen.findByText(/no paid transactions yet/i)).toBeInTheDocument();
  });
});
