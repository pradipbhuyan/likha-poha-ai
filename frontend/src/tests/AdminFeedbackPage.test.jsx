/**
 * AdminFeedbackPage.test.jsx
 * Tests for the admin feedback triage dashboard.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminFeedbackPage from "../pages/AdminFeedbackPage";

vi.mock("../api/feedback", () => ({
  adminListFeedback: vi.fn(),
  adminFeedbackSummary: vi.fn(),
  adminUpdateFeedback: vi.fn(),
  adminCreateTechDebt: vi.fn(),
}));

import {
  adminListFeedback, adminFeedbackSummary, adminUpdateFeedback, adminCreateTechDebt,
} from "../api/feedback";

const SUMMARY = { success: true, open: 5, critical: 2, this_week: 3, converted: 1, total: 9 };

const FEEDBACK = [
  { id: "fb-1", feedback_type: "bug", message: "Crashes on submit", criticality_tier: "critical",
    username: "aarav", user_role: "student", status: "new", created_at: "2026-08-01T10:00:00Z" },
  { id: "fb-2", feedback_type: "feature_request", message: "Add dark mode", criticality_tier: "medium",
    username: "priya", user_role: "parent", status: "new", created_at: "2026-08-02T10:00:00Z" },
];

describe("AdminFeedbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminFeedbackSummary.mockResolvedValue(SUMMARY);
    adminListFeedback.mockResolvedValue({ success: true, feedback: FEEDBACK });
  });

  test("renders admin feedback page", async () => {
    render(<AdminFeedbackPage />);
    expect(await screen.findByTestId("admin-feedback-page")).toBeInTheDocument();
  });

  test("shows summary cards", async () => {
    render(<AdminFeedbackPage />);
    await waitFor(() => {
      expect(screen.getByTestId("stat-open")).toBeInTheDocument();
      expect(screen.getByTestId("stat-critical")).toBeInTheDocument();
      expect(screen.getByTestId("stat-converted")).toBeInTheDocument();
    });
  });

  test("shows feedback rows", async () => {
    render(<AdminFeedbackPage />);
    await waitFor(() => {
      expect(screen.getAllByTestId("feedback-row").length).toBe(2);
    });
  });

  test("selecting rows shows bulk convert toolbar", async () => {
    render(<AdminFeedbackPage />);
    await waitFor(() => screen.getAllByTestId("feedback-row"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[1]); // first row checkbox (index 0 is select-all)
    expect(screen.getByTestId("bulk-toolbar")).toBeInTheDocument();
    expect(screen.getByText("1 selected")).toBeInTheDocument();
  });

  test("converts selected feedback to a tech debt item", async () => {
    adminCreateTechDebt.mockResolvedValueOnce({ success: true, tech_debt: { id: "td-1" } });
    render(<AdminFeedbackPage />);
    await waitFor(() => screen.getAllByTestId("feedback-row"));
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByTestId("open-convert-btn"));
    fireEvent.change(screen.getByTestId("convert-title-input"), { target: { value: "Fix submit crash" } });
    fireEvent.click(screen.getByTestId("convert-confirm-btn"));
    await waitFor(() => {
      expect(adminCreateTechDebt).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Fix submit crash", source_feedback_ids: ["fb-1"] })
      );
    });
  });

  test("dismisses a feedback item", async () => {
    adminUpdateFeedback.mockResolvedValueOnce({ success: true, feedback: { ...FEEDBACK[0], status: "dismissed" } });
    render(<AdminFeedbackPage />);
    await waitFor(() => screen.getAllByTestId("feedback-row"));
    fireEvent.click(screen.getByTestId("dismiss-fb-1"));
    await waitFor(() => {
      expect(adminUpdateFeedback).toHaveBeenCalledWith("fb-1", { status: "dismissed" });
    });
  });
});
