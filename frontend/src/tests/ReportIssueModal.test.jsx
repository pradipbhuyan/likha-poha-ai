/**
 * ReportIssueModal.test.jsx
 * Tests for the student issue reporting modal.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReportIssueModal from "../components/ReportIssueModal";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));

import { authFetch } from "../api/authClient";

const MOCK_USER = { id: "user-1", role: "student", grade: "Grade 9" };
const MOCK_CONTEXT = {
  route: "/lessons",
  grade: "Grade 9",
  subject: "Science",
  chapter: "Motion",
  lessonStep: "Core explanation",
};

describe("ReportIssueModal", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("does not render when open=false", () => {
    render(<ReportIssueModal open={false} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.queryByTestId("report-issue-modal")).toBeNull();
  });

  test("renders modal when open=true", () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("report-issue-modal")).toBeInTheDocument();
  });

  test("shows issue type selector", () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("issue-type-select")).toBeInTheDocument();
  });

  test("shows severity buttons", () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("severity-low")).toBeInTheDocument();
    expect(screen.getByTestId("severity-critical")).toBeInTheDocument();
  });

  test("shows description field", () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    expect(screen.getByTestId("issue-description")).toBeInTheDocument();
  });

  test("shows context when provided", () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    expect(screen.getByText(/Grade 9/)).toBeInTheDocument();
    expect(screen.getByText(/Science/)).toBeInTheDocument();
  });

  test("shows error if description is empty on submit", async () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    fireEvent.click(screen.getByTestId("submit-issue-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("report-issue-error")).toBeInTheDocument();
    });
  });

  test("shows error if description is too short", async () => {
    render(<ReportIssueModal open={true} onClose={vi.fn()} user={MOCK_USER} />);
    fireEvent.change(screen.getByTestId("issue-description"), { target: { value: "short" } });
    fireEvent.click(screen.getByTestId("submit-issue-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("report-issue-error")).toBeInTheDocument();
    });
  });

  test("submits successfully and shows success state", async () => {
    authFetch.mockResolvedValueOnce({ success: true, id: "issue-1",
      message: "Thank you for reporting this issue." });
    render(<ReportIssueModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    fireEvent.change(screen.getByTestId("issue-description"), {
      target: { value: "The worked example section is missing the final answer." }
    });
    fireEvent.click(screen.getByTestId("submit-issue-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("report-issue-success")).toBeInTheDocument();
    });
  });

  test("includes context in submitted payload", async () => {
    authFetch.mockResolvedValueOnce({ success: true, id: "issue-2" });
    render(<ReportIssueModal open={true} onClose={vi.fn()} context={MOCK_CONTEXT} user={MOCK_USER} />);
    fireEvent.change(screen.getByTestId("issue-description"), {
      target: { value: "The simple explanation is missing real examples." }
    });
    fireEvent.click(screen.getByTestId("submit-issue-btn"));
    await waitFor(() => expect(authFetch).toHaveBeenCalledOnce());
    const call = authFetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.grade).toBe("Grade 9");
    expect(body.subject).toBe("Science");
    expect(body.chapter).toBe("Motion");
  });

  test("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<ReportIssueModal open={true} onClose={onClose} user={MOCK_USER} />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalled();
  });
});
