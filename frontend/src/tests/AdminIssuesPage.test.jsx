/**
 * AdminIssuesPage.test.jsx
 * Tests for the Admin Product Bugs / Student Feedback page.
 */
import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminIssuesPage from "../pages/AdminIssuesPage";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));
import { authFetch } from "../api/authClient";

const SUMMARY = {
  success: true, open: 3, critical: 1, high: 2,
  content_issues: 4, fixed_this_week: 1, total: 8,
};

const ISSUES = [
  {
    id: "issue-1", issue_type: "content_issue", severity: "high",
    title: "Missing worked example", description: "The worked example is missing.",
    status: "open", grade: "Grade 9", subject: "Science", chapter: "Motion",
    reporter_role: "student", created_at: "2026-06-28T10:00:00Z",
  },
  {
    id: "issue-2", issue_type: "wrong_answer", severity: "critical",
    title: null, description: "MCQ answer key is wrong.",
    status: "triaged", grade: "Grade 10", subject: "Maths", chapter: "Algebra",
    reporter_role: "student", created_at: "2026-06-27T08:00:00Z",
  },
];

describe("AdminIssuesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authFetch.mockImplementation(async (path) => {
      if (path.includes("/summary")) return SUMMARY;
      return { success: true, issues: ISSUES };
    });
  });

  test("renders admin issues page", async () => {
    render(<AdminIssuesPage />);
    expect(await screen.findByTestId("admin-issues-page")).toBeInTheDocument();
  });

  test("shows summary cards with counts", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => {
      expect(screen.getByTestId("stat-open")).toBeInTheDocument();
      expect(screen.getByTestId("stat-critical")).toBeInTheDocument();
    });
  });

  test("shows issue rows", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => {
      const rows = screen.getAllByTestId("issue-row");
      expect(rows.length).toBeGreaterThanOrEqual(1);
    });
  });

  test("shows filters", async () => {
    render(<AdminIssuesPage />);
    await screen.findByTestId("admin-issues-page");
    expect(screen.getByTestId("filter-status")).toBeInTheDocument();
    expect(screen.getByTestId("filter-severity")).toBeInTheDocument();
    expect(screen.getByTestId("filter-issue_type")).toBeInTheDocument();
  });

  test("clicking issue row opens drawer", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => screen.getAllByTestId("issue-row"));
    fireEvent.click(screen.getAllByTestId("issue-row")[0]);
    expect(await screen.findByTestId("issue-drawer")).toBeInTheDocument();
  });

  test("drawer shows issue description", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => screen.getAllByTestId("issue-row"));
    fireEvent.click(screen.getAllByTestId("issue-row")[0]);
    await screen.findByTestId("issue-drawer");
    expect(screen.getByText(/The worked example is missing/i)).toBeInTheDocument();
  });

  test("drawer has status selector", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => screen.getAllByTestId("issue-row"));
    fireEvent.click(screen.getAllByTestId("issue-row")[0]);
    await screen.findByTestId("issue-drawer");
    expect(screen.getByTestId("issue-status-select")).toBeInTheDocument();
  });

  test("drawer has admin notes textarea", async () => {
    render(<AdminIssuesPage />);
    await waitFor(() => screen.getAllByTestId("issue-row"));
    fireEvent.click(screen.getAllByTestId("issue-row")[0]);
    await screen.findByTestId("issue-drawer");
    expect(screen.getByTestId("admin-notes-input")).toBeInTheDocument();
  });

  test("saving issue calls PATCH endpoint", async () => {
    authFetch.mockImplementation(async (path) => {
      if (path.includes("/summary")) return SUMMARY;
      if (path.includes("PATCH") || (typeof path === "string" && path.includes("issue-1") && !path.includes("summary")))
        return { success: true, issue: { ...ISSUES[0], status: "triaged" } };
      return { success: true, issues: ISSUES };
    });
    authFetch.mockImplementation(async (path, opts) => {
      if (path.includes("/summary")) return SUMMARY;
      if (opts?.method === "PATCH") return { success: true, issue: { ...ISSUES[0], status: "triaged" } };
      return { success: true, issues: ISSUES };
    });

    render(<AdminIssuesPage />);
    await waitFor(() => screen.getAllByTestId("issue-row"));
    fireEvent.click(screen.getAllByTestId("issue-row")[0]);
    await screen.findByTestId("save-issue-btn");
    fireEvent.click(screen.getByTestId("save-issue-btn"));
    await waitFor(() => {
      const calls = authFetch.mock.calls;
      const patchCall = calls.find(c => c[1]?.method === "PATCH");
      expect(patchCall).toBeDefined();
    });
  });

  test("shows no-issues state when list is empty", async () => {
    authFetch.mockImplementation(async (path) => {
      if (path.includes("/summary")) return SUMMARY;
      return { success: true, issues: [] };
    });
    render(<AdminIssuesPage />);
    expect(await screen.findByTestId("no-issues")).toBeInTheDocument();
  });

  test("filter changes trigger refetch", async () => {
    render(<AdminIssuesPage />);
    await screen.findByTestId("admin-issues-page");
    const initialCalls = authFetch.mock.calls.length;
    fireEvent.change(screen.getByTestId("filter-severity"), { target: { value: "critical" } });
    await waitFor(() => {
      expect(authFetch.mock.calls.length).toBeGreaterThan(initialCalls);
    });
  });
});
