/**
 * AdminTechDebtPage.test.jsx
 * Tests for the admin tech debt backlog approve/reject page.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminTechDebtPage from "../pages/AdminTechDebtPage";

vi.mock("../api/feedback", () => ({
  adminListTechDebt: vi.fn(),
  adminTechDebtSummary: vi.fn(),
  adminReviewTechDebt: vi.fn(),
}));

import { adminListTechDebt, adminTechDebtSummary, adminReviewTechDebt } from "../api/feedback";

const SUMMARY = { success: true, proposed: 2, approved: 1, in_progress: 1, rejected: 1, done: 0, total: 5 };

const ITEMS = [
  { id: "td-1", title: "Fix crash on submit", criticality_tier: "critical", status: "proposed",
    source_feedback_ids: ["fb-1", "fb-2"], created_at: "2026-08-01T10:00:00Z" },
  { id: "td-2", title: "Add dark mode", criticality_tier: "medium", status: "approved",
    source_feedback_ids: ["fb-3"], created_at: "2026-07-30T10:00:00Z", reviewed_at: "2026-08-01T10:00:00Z" },
];

describe("AdminTechDebtPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminTechDebtSummary.mockResolvedValue(SUMMARY);
    adminListTechDebt.mockResolvedValue({ success: true, tech_debt: ITEMS });
  });

  test("renders admin tech debt page", async () => {
    render(<AdminTechDebtPage />);
    expect(await screen.findByTestId("admin-tech-debt-page")).toBeInTheDocument();
  });

  test("shows summary cards", async () => {
    render(<AdminTechDebtPage />);
    await waitFor(() => {
      expect(screen.getByText("Proposed")).toBeInTheDocument();
      expect(screen.getByText("Approved")).toBeInTheDocument();
    });
  });

  test("shows tech debt cards sorted as returned by the server", async () => {
    render(<AdminTechDebtPage />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tech-debt-card").length).toBe(2);
    });
    expect(screen.getByText("Fix crash on submit")).toBeInTheDocument();
  });

  test("approve button calls review endpoint with approved status", async () => {
    adminReviewTechDebt.mockResolvedValueOnce({ success: true, tech_debt: { ...ITEMS[0], status: "approved" } });
    render(<AdminTechDebtPage />);
    await waitFor(() => screen.getAllByTestId("tech-debt-card"));
    fireEvent.click(screen.getByTestId("approve-td-1"));
    await waitFor(() => {
      expect(adminReviewTechDebt).toHaveBeenCalledWith("td-1", { status: "approved" });
    });
  });

  test("reject flow requires a reason before confirming", async () => {
    render(<AdminTechDebtPage />);
    await waitFor(() => screen.getAllByTestId("tech-debt-card"));
    fireEvent.click(screen.getByTestId("reject-td-1"));
    expect(screen.getByTestId("reject-reason-td-1")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-reject-td-1")).toBeDisabled();
  });

  test("confirming reject sends the rejection reason", async () => {
    adminReviewTechDebt.mockResolvedValueOnce({ success: true, tech_debt: { ...ITEMS[0], status: "rejected", rejection_reason: "Not this quarter" } });
    render(<AdminTechDebtPage />);
    await waitFor(() => screen.getAllByTestId("tech-debt-card"));
    fireEvent.click(screen.getByTestId("reject-td-1"));
    fireEvent.change(screen.getByTestId("reject-reason-td-1"), { target: { value: "Not this quarter" } });
    fireEvent.click(screen.getByTestId("confirm-reject-td-1"));
    await waitFor(() => {
      expect(adminReviewTechDebt).toHaveBeenCalledWith("td-1", { status: "rejected", rejection_reason: "Not this quarter" });
    });
  });

  test("approved item shows no action buttons", async () => {
    render(<AdminTechDebtPage />);
    await waitFor(() => screen.getAllByTestId("tech-debt-card"));
    expect(screen.queryByTestId("approve-td-2")).toBeNull();
    expect(screen.queryByTestId("reject-td-2")).toBeNull();
  });
});
