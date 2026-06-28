/**
 * FormulaSheetPage.test.jsx
 * Tests for the grade-based formula sheet page.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

vi.mock("../api/authClient", () => ({
  authFetch: vi.fn(),
}));

import FormulaSheetPage from "../pages/FormulaSheetPage";
import { authFetch } from "../api/authClient";

const USER_G9 = { id: "u1", username: "test", grade: "Grade 9" };

const MOCK_RESPONSE = {
  success: true,
  available: true,
  grade: "Grade 9",
  subject: "Mathematics",
  subjects: ["Mathematics", "Science"],
  sections: [
    {
      title: "Equations of Motion",
      formulas: [
        { name: "First Equation", expression: "v = u + at", explanation: "v=final velocity", example: "u=0,a=10,t=5 → v=50", chapter: "Motion" },
        { name: "Kinetic Energy", expression: "KE = (1/2)mv²", explanation: "m=mass, v=velocity", example: "m=2,v=4 → KE=16J", chapter: "Work & Energy" },
      ],
    },
  ],
  total: 2,
};

const UNAVAILABLE_RESPONSE = {
  success: true,
  available: false,
  grade: "Grade 3",
  subject: "Mathematics",
  message: "Formula sheet is not available for Grade 3 yet.",
  sections: [],
  subjects: [],
};

describe("FormulaSheetPage", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders formula sheet page", async () => {
    authFetch.mockResolvedValueOnce(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    expect(await screen.findByTestId("formula-sheet-page")).toBeInTheDocument();
    expect(screen.getByText(/Formula Sheet/)).toBeInTheDocument();
  });

  test("shows grade in heading", async () => {
    authFetch.mockResolvedValueOnce(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    await screen.findByTestId("formula-sheet-page");
    expect(screen.getByText(/Grade 9/)).toBeInTheDocument();
  });

  test("Grade 9 student sees formula content", async () => {
    authFetch.mockResolvedValueOnce(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    expect(await screen.findByTestId("formula-sheet-content")).toBeInTheDocument();
    const cards = screen.getAllByTestId("formula-card");
    expect(cards.length).toBeGreaterThan(0);
    expect(screen.getByText("First Equation")).toBeInTheDocument();
    expect(screen.getByText("v = u + at")).toBeInTheDocument();
  });

  test("unavailable grade shows friendly empty state", async () => {
    authFetch.mockResolvedValueOnce(UNAVAILABLE_RESPONSE);
    render(<FormulaSheetPage user={{ ...USER_G9, grade: "Grade 3" }} />);
    expect(await screen.findByTestId("formula-sheet-unavailable")).toBeInTheDocument();
    expect(screen.getByText(/not available for Grade 3/i)).toBeInTheDocument();
  });

  test("subject filter buttons render", async () => {
    authFetch.mockResolvedValueOnce(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    await screen.findByTestId("formula-sheet-page");
    expect(screen.getByTestId("fs-subject-mathematics")).toBeInTheDocument();
    expect(screen.getByTestId("fs-subject-science")).toBeInTheDocument();
  });

  test("clicking subject filter triggers reload with new subject", async () => {
    authFetch.mockResolvedValue(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    await screen.findByTestId("formula-sheet-content");

    const callsBefore = authFetch.mock.calls.length;
    fireEvent.click(screen.getByTestId("fs-subject-science"));
    await waitFor(() => expect(authFetch.mock.calls.length).toBeGreaterThan(callsBefore));
    const lastUrl = authFetch.mock.calls.at(-1)?.[0] || "";
    expect(lastUrl).toContain("subject=Science");
  });

  test("formula card shows expression, explanation and example", async () => {
    authFetch.mockResolvedValueOnce(MOCK_RESPONSE);
    render(<FormulaSheetPage user={USER_G9} />);
    await screen.findByTestId("formula-sheet-content");
    expect(screen.getByText(/u=0,a=10,t=5/)).toBeInTheDocument();
    expect(screen.getByText(/v=final velocity/)).toBeInTheDocument();
  });

  test("Formula Sheet quick action navigates to formulaSheet page", async () => {
    // Test that qa-formula-sheet testid exists and calls nav
    const { authFetch: mockAuth } = await import("../api/authClient");
    mockAuth.mockResolvedValue(MOCK_RESPONSE);

    const navFn = vi.fn();
    const { default: StudentDashboardPage } = await import("../pages/StudentDashboardPage");

    vi.mock("../api/analytics", () => ({
      getStudentDashboardSummary: vi.fn(async () => ({
        success: true,
        student: { username: "test", grade: "Grade 9", study_streak_days: 0, lessons_completed: 0 },
        subscription: { canonical_plan_key: "FREE_TIER", has_full_access: false },
        features: {}, mock_tests: { available: false, total: 0, average_score: null, best_score: null, subject_averages: {}, recent: [], score_trend: [] },
        progress: { available: false, overall_pct: 0, completed_chapters: 0, in_progress_chapters: 0, subject_progress: {}, last_chapter: null },
        weak_topics: [], activity: { total_90d: 0, feature_counts: {} }, achievements: [], recommendations: [],
        plan: { tasks: [], estimated_minutes: 0 },
      })),
      getAnalytics: vi.fn(async () => ({ history: [] })),
      getWeakChapters: vi.fn(async () => ({ success: true, weak_chapters: [] })),
      getStudentExams: vi.fn(async () => ({ success: true, exams: [] })),
      addStudentExam: vi.fn(),
      deleteStudentExam: vi.fn(),
    }));

    render(<StudentDashboardPage user={{ id: "u1", username: "test", grade: "Grade 9", accessCbse: false }} setActivePage={navFn} />);
    await screen.findByTestId("quick-actions-card");
    const fsBtn = screen.getByTestId("qa-formula-sheet");
    fireEvent.click(fsBtn);
    expect(navFn).toHaveBeenCalledWith("formulaSheet");
  });
});
