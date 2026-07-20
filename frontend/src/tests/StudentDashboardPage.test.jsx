/**
 * StudentDashboardPage.test.jsx
 * Regression tests for the redesigned Student Dashboard.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi, beforeEach } from "vitest";

// Mock all APIs
vi.mock("../api/analytics", () => ({
  getStudentDashboardSummary: vi.fn(async () => ({
    success: true,
    student: { username: "akshita.teststudent", grade: "Grade 9", study_streak_days: 5, lessons_completed: 12 },
    subscription: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false },
    features: { has_full_access: false, exemplar_locked: true, mock_test_limited: true, ask_doubts_limited: true },
    mock_tests: {
      available: true, total: 8, average_score: 54, best_score: 80,
      subject_averages: { Science: 60, Maths: 48, English: 72 },
      recent: [
        { subject: "Science", chapter: "Motion", score: 60, date: "2026-06-24" },
        { subject: "Maths", chapter: "Fractions", score: 80, date: "2026-06-23" },
      ],
      score_trend: [],
    },
    progress: {
      available: true, overall_pct: 18, completed_chapters: 0, in_progress_chapters: 3,
      subject_progress: { Science: { total: 10, completed: 0, in_progress: 3 } },
      last_chapter: { subject: "Science", chapter: "Motion and Force", progress_pct: 42 },
    },
    weak_topics: [
      { subject: "Maths", chapter: "Fractions", score: 30 },
      { subject: "Science", chapter: "Atomic Structure", score: 25 },
    ],
    activity: { last_active: "2026-06-25T10:00:00Z", feature_counts: { doubt: 5, lesson: 20 }, total_90d: 45 },
    achievements: [
      { type: "streak", title: "5 Day Streak", icon: "🔥", value: 5 },
      { type: "lessons", title: "Completed 12 Lessons", icon: "📖", value: 12 },
      { type: "first_test", title: "First Mock Test", icon: "🏆", value: 8 },
    ],
    recommendations: [
      { type: "practice", title: "Revise: Fractions", body: "Practice Maths — Fractions needs attention.", priority: "high", action: "lessons" },
    ],
    plan: {
      tasks: [
        { task: "Continue Science lesson", done: false, type: "lesson" },
        { task: "Attempt one mock test", done: false, type: "mock_test" },
      ],
      estimated_minutes: 30,
    },
  })),
  getAnalytics: vi.fn(async () => ({ history: [] })),
  getWeakChapters: vi.fn(async () => ({ success: true, weak_chapters: [] })),
  getStudentExams: vi.fn(async () => ({ success: true, exams: [] })),
  addStudentExam: vi.fn(async () => ({ success: true, exam: { id: "e1", subject: "Science", title: "Test", exam_date: "2026-09-01", days_until: 65 } })),
  deleteStudentExam: vi.fn(async () => ({ success: true })),
}));

vi.mock("../api/profile", () => ({
  getStudentProfile: vi.fn(async () => ({ profile: { username: "test", grade: "Grade 9" } })),
}));

vi.mock("../api/recommendations", () => ({
  getRecommendations: vi.fn(async () => ({ recommendations: [] })),
}));

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: { getSession: vi.fn(async () => ({ data: { session: null }, error: null })) },
  },
}));

import StudentDashboardPage from "../pages/StudentDashboardPage";

const USER = { id: "uid-1", username: "akshita.teststudent", role: "student", grade: "Grade 9", accessCbse: false };

describe("StudentDashboardPage — redesigned", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  test("renders student dashboard", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("student-dashboard-page")).toBeInTheDocument();
  });

  test("renders hero section with greeting", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("student-hero")).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Good morning|Good afternoon|Good evening/);
    expect(document.body.textContent).toContain("akshita");
  });

  test("renders quick stats row", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("student-quick-stats")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Today's Goal");
    expect(document.body.textContent).toContain("Lessons Left");
    expect(document.body.textContent).toContain("XP Points");
  });

  test("renders Up Next card, prioritizing in-progress lesson over recommendations", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("up-next-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Up Next");
    // last_chapter is present in the mock, so it takes priority over the "Revise: Fractions" recommendation
    expect(document.body.textContent).toContain("Continue Learning →");
    expect(document.body.textContent).toContain("Motion and Force");
  });

  test("Up Next card still surfaces today's plan tasks alongside the primary CTA", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("up-next-card");
    expect(document.body.textContent).toContain("Today's Plan");
    expect(document.body.textContent).toContain("Continue Science lesson");
  });

  test("Up Next card falls back to the top recommendation when no lesson is in progress", async () => {
    const { getStudentDashboardSummary } = await import("../api/analytics");
    getStudentDashboardSummary.mockResolvedValueOnce({
      success: true,
      student: { username: "akshita.teststudent", grade: "Grade 9", study_streak_days: 5, lessons_completed: 12 },
      subscription: { canonical_plan_key: "FREE_TIER", plan_name: "Free Tier", has_full_access: false },
      features: { has_full_access: false, exemplar_locked: true, mock_test_limited: true, ask_doubts_limited: true },
      mock_tests: { available: true, total: 8, average_score: 54, best_score: 80, subject_averages: {}, recent: [], score_trend: [] },
      progress: { available: true, overall_pct: 18, completed_chapters: 0, in_progress_chapters: 3, subject_progress: {}, last_chapter: null },
      weak_topics: [],
      activity: { last_active: null, feature_counts: {}, total_90d: 0 },
      achievements: [],
      recommendations: [{ type: "upgrade", title: "Unlock full platform access", body: "Upgrade to access Exemplar problems.", priority: "low", action: "subscription" }],
      plan: { tasks: [], estimated_minutes: 15 },
    });
    const navFn = vi.fn();
    render(<StudentDashboardPage user={USER} setActivePage={navFn} />);
    await screen.findByTestId("up-next-card");
    expect(document.body.textContent).toContain("Upgrade to access Exemplar problems.");
    screen.getByText("Upgrade Plan →").click();
    expect(navFn).toHaveBeenCalledWith("subscriptionPlans");
  });

  test("renders Subject Progress card", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("subject-progress-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Subject Progress");
    expect(document.body.textContent).toContain("Science");
  });

  test("renders Recent Mock Tests card", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("recent-mock-tests-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Recent Mock Tests");
  });

  test("mock test scores never exceed 100%", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("recent-mock-tests-card");
    // Verify the displayed test scores from mock data are correct (60% and 80%)
    expect(document.body.textContent).toContain("60%");
    expect(document.body.textContent).toContain("80%");
    // Ensure no obviously wrong scores like 1200%, 1600% appear
    expect(document.body.textContent).not.toContain("1200%");
    expect(document.body.textContent).not.toContain("1600%");
    expect(document.body.textContent).not.toContain("101%");
  });

  test("renders Weak Topics card", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("weak-topics-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Weak Topics");
    expect(document.body.textContent).toContain("Fractions");
  });

  test("renders Achievements card", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("achievements-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Achievements");
    expect(document.body.textContent).toContain("5 Day Streak");
  });

  test("renders utility cards", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("student-utility-cards")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Revision Center");
    expect(document.body.textContent).toContain("AI Doubt Solver");
    expect(document.body.textContent).toContain("Quick Actions");
  });

  test("upcoming exams shows empty state, not static 12 days", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("upcoming-exams-card");
    // Must NOT show hardcoded "12 days"
    expect(document.body.textContent).not.toContain("12 days left");
    // Must show empty state message
    expect(document.body.textContent).toContain("No upcoming exams added yet");
  });

  test("Watch Concept Videos routes to resources (Learn More)", async () => {
    const navFn = vi.fn();
    render(<StudentDashboardPage user={USER} setActivePage={navFn} />);
    await screen.findByTestId("quick-actions-card");
    screen.getByTestId("qa-watch-concept-videos").click();
    expect(navFn).toHaveBeenCalledWith("resources");
  });

  test("Practice Questions routes to mockTest (practice flow)", async () => {
    const navFn = vi.fn();
    render(<StudentDashboardPage user={USER} setActivePage={navFn} />);
    await screen.findByTestId("quick-actions-card");
    screen.getByTestId("qa-practice-questions").click();
    expect(navFn).toHaveBeenCalledWith("mockTest");
  });

  test("Formula Sheet routes to formulaSheet page", async () => {
    const navFn = vi.fn();
    render(<StudentDashboardPage user={USER} setActivePage={navFn} />);
    await screen.findByTestId("quick-actions-card");
    expect(screen.queryByTestId("qa-formula-sheet-disabled")).not.toBeInTheDocument();
    screen.getByTestId("qa-formula-sheet").click();
    expect(navFn).toHaveBeenCalledWith("formulaSheet");
  });

  test("Study Materials routes to resources (Learn More)", async () => {
    const navFn = vi.fn();
    render(<StudentDashboardPage user={USER} setActivePage={navFn} />);
    await screen.findByTestId("quick-actions-card");
    screen.getByTestId("qa-study-materials").click();
    expect(navFn).toHaveBeenCalledWith("resources");
  });

  test("No quick action produces a blank page (all have testids)", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("quick-actions-card");
    expect(screen.getByTestId("qa-watch-concept-videos")).toBeInTheDocument();
    expect(screen.getByTestId("qa-practice-questions")).toBeInTheDocument();
    expect(screen.getByTestId("qa-formula-sheet")).toBeInTheDocument();
    expect(screen.getByTestId("qa-study-materials")).toBeInTheDocument();
    // None should be disabled
    expect(screen.queryByTestId("qa-formula-sheet-disabled")).not.toBeInTheDocument();
  });

  test("Today's Goal shows plan.estimated_minutes from API, not hardcoded 45", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("student-quick-stats");
    // The mock returns estimated_minutes: 30, so must show "30 min"
    expect(document.body.textContent).toContain("30 min");
    // Must NOT show the old hardcoded value
    expect(document.body.textContent).not.toContain("45 min");
  });

  test("Next Exam stat shows — when no exams exist (not hardcoded data)", async () => {
    // getStudentExams mock returns empty exams
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("student-quick-stats");
    // With no exams, should show — and "Not scheduled"
    const bodyText = document.body.textContent;
    expect(bodyText).toContain("Not scheduled");
  });

  test("Next Exam stat shows days_until when exam exists", async () => {
    const { getStudentExams } = await import("../api/analytics");
    getStudentExams.mockResolvedValueOnce({
      success: true,
      exams: [{ id: "e1", subject: "Science", title: "Unit Test", exam_date: "2026-07-15", days_until: 14 }],
    });
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("student-quick-stats");
    // Should show 14d from real exam data
    expect(document.body.textContent).toContain("14d");
    // Science is the exam subject
    expect(document.body.textContent).toContain("Science");
  });

  test("renders motivation card", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    expect(await screen.findByTestId("motivation-card")).toBeInTheDocument();
    expect(document.body.textContent).toContain("Motivation for You");
  });

  test("Free Tier: shows limited messaging for restricted features", async () => {
    render(<StudentDashboardPage user={USER} setActivePage={vi.fn()} />);
    await screen.findByTestId("student-dashboard-page");
    // Free tier students should see upgrade recommendation
    const bodyText = document.body.textContent;
    // Either sees "Upgrade" CTA or "Limited" label
    const hasFreeMessage = bodyText.includes("Limited") || bodyText.includes("Upgrade") || bodyText.includes("Free Tier");
    expect(hasFreeMessage).toBe(true);
  });

  test("missing data shows friendly fallback, not blank", async () => {
    const { getStudentDashboardSummary } = await import("../api/analytics");
    getStudentDashboardSummary.mockResolvedValueOnce({
      success: true,
      student: { username: "newstudent", grade: "Grade 9", study_streak_days: 0, lessons_completed: 0 },
      subscription: { canonical_plan_key: "FREE_TIER", has_full_access: false },
      features: { has_full_access: false, exemplar_locked: true, mock_test_limited: true },
      mock_tests: { available: false, total: 0, average_score: null, best_score: null, subject_averages: {}, recent: [], score_trend: [] },
      progress: { available: false, overall_pct: 0, completed_chapters: 0, in_progress_chapters: 0, subject_progress: {}, last_chapter: null },
      weak_topics: [],
      activity: { last_active: null, feature_counts: {}, total_90d: 0 },
      achievements: [],
      recommendations: [],
      plan: { tasks: [{ task: "Start a new lesson", done: false, type: "lesson" }], estimated_minutes: 15 },
    });
    render(<StudentDashboardPage user={{ ...USER, username: "newstudent" }} setActivePage={vi.fn()} />);
    await screen.findByTestId("student-dashboard-page");
    // Should not have blank panels — must have friendly messages
    const bt = document.body.textContent;
    expect(bt).toContain("Begin your first");
    expect(bt).not.toBe("");
  });
});
