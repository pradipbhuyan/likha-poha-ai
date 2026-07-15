/**
 * MockTestPage.test.jsx — Mock Test Page regression tests
 * Covers: setup phase, format cards, free/paid gating, MCQ exam phase,
 * empty-options guard, result phase, written question rendering.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import MockTestPage from "../pages/MockTestPage";

// ── Mocks ─────────────────────────────────────────────────────────────────────
vi.mock("../api/syllabus", () => ({
  getSyllabus: vi.fn().mockResolvedValue({
    syllabus: {
      "Grade 9": {
        CBSE: {
          Mathematics: ["Chapter 1: Number Systems", "Chapter 2: Polynomials"],
          Science: ["Chapter 1: Matter in Our Surroundings"],
        },
      },
    },
  }),
}));
vi.mock("../api/mockTest", () => ({ generateMockTest: vi.fn() }));
vi.mock("../api/analytics", () => ({
  saveTestHistory: vi.fn().mockResolvedValue({}),
  saveWrongAnswers: vi.fn().mockResolvedValue({}),
}));
vi.mock("../api/profile", () => ({ logStudentActivity: vi.fn().mockResolvedValue({}) }));
vi.mock("../api/evaluation", () => ({
  evaluateStudentAnswer: vi.fn().mockResolvedValue({ success: true, evaluation: "Good answer.", score: 8 }),
}));
vi.mock("../utils/syllabusDefaults", () => ({
  getSyllabus: vi.fn(),
  getDefaultSelection: vi.fn().mockReturnValue({
    grade: "Grade 9", mode: "CBSE", subject: "Mathematics", chapter: "Chapter 1: Number Systems",
  }),
  getUserBoard: vi.fn().mockReturnValue("CBSE"),
  getUserGrade: vi.fn().mockReturnValue("Grade 9"),
  getVisibleGrades: vi.fn().mockReturnValue(["Grade 9"]),
}));
vi.mock("../utils/subjectAccess", () => ({
  filterAllowedSubjects: vi.fn((_user, subjects) => subjects),
  isSchoolBoardMode: vi.fn().mockReturnValue(true),
}));
vi.mock("../utils/testAccounts", () => ({ isAllAccessTestUser: vi.fn().mockReturnValue(false) }));
vi.mock("../utils/resolveSubscription", () => ({ hasPaidAccess: vi.fn() }));

import { generateMockTest } from "../api/mockTest";
import { hasPaidAccess } from "../utils/resolveSubscription";

// ── Fixtures ──────────────────────────────────────────────────────────────────
const paidUser = {
  id: "u1", role: "student", username: "paid.student",
  accessCbse: true, subscriptionExpiresAt: "2099-01-01T00:00:00Z", accessToken: "tok",
};
const freeUser = {
  id: "u2", role: "student", username: "free.student",
  accessCbse: false, subscriptionExpiresAt: null, accessToken: "tok",
};

const makeMCQQuestions = (count = 3) =>
  Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    db_id: `db_${i + 1}`,
    question_type: "mcq",
    section: "Section A",
    question: `What is the answer to question ${i + 1}?`,
    options: { A: "Option A", B: "Option B", C: "Option C", D: "Option D" },
    answer: "A",
    explanation: `Explanation for Q${i + 1}`,
    marks: 1,
  }));

const makeEmptyOptionsQuestion = () => ({
  id: 1, db_id: "db_empty", question_type: "mcq", section: "Section A",
  question: "Question with missing options?", options: {}, answer: "A",
  explanation: "Explanation", marks: 1,
});

const makeWrittenQuestion = () => ({
  id: 1, db_id: "db_w1", question_type: "written_short", section: "Section B",
  question: "Explain the concept briefly.", options: {}, answer: "",
  explanation: "", marks: 3, model_answer: "Reference answer.", expected_keywords: ["concept"],
});

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  hasPaidAccess.mockReturnValue(true);
});
afterEach(() => { localStorage.clear(); });

// ── Setup Phase ───────────────────────────────────────────────────────────────
describe("MockTestPage — setup phase", () => {
  it("shows loading state before syllabus resolves", () => {
    render(<MockTestPage user={paidUser} />);
    expect(screen.getByText(/Loading mock test setup/i)).toBeTruthy();
  });

  it("renders 3 format selector cards after syllabus loads", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => {
      expect(screen.getByText(/MCQ Practice/i)).toBeTruthy();
      expect(screen.getByText(/Written Practice/i)).toBeTruthy();
      expect(screen.getByText(/Mixed \(CBSE style\)/i)).toBeTruthy();
    });
  });

  it("renders Generate Mock Test button", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => expect(screen.getByText(/Generate Mock Test/i)).toBeTruthy());
  });

  it("shows Test Setup heading", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => expect(screen.getByText(/Test Setup/i)).toBeTruthy());
  });

  it("shows lock badges on Written and Mixed for free user", async () => {
    hasPaidAccess.mockReturnValue(false);
    render(<MockTestPage user={freeUser} />);
    await waitFor(() => expect(screen.getAllByText(/Upgrade to unlock/i).length).toBe(2));
  });

  it("shows Premium unlocked badge on Written/Mixed for paid user", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => expect(screen.getAllByText(/Premium unlocked/i).length).toBe(2));
  });

  it("shows daily limit counter for free student", async () => {
    hasPaidAccess.mockReturnValue(false);
    render(<MockTestPage user={freeUser} />);
    await waitFor(() => expect(screen.getByText(/free mock tests used today/i)).toBeTruthy());
  });

  it("shows daily limit reached banner when 5 tests used", async () => {
    hasPaidAccess.mockReturnValue(false);
    const key = `mock_daily_free.student_${new Date().toISOString().slice(0, 10)}`;
    localStorage.setItem(key, "5");
    render(<MockTestPage user={freeUser} />);
    // Both the banner span AND the disabled button contain "Daily limit reached" text
    await waitFor(() => {
      expect(screen.getAllByText(/Daily limit reached/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Upgrade for unlimited/i)).toBeTruthy();
    });
  });

  it("disables Generate button when daily limit reached", async () => {
    hasPaidAccess.mockReturnValue(false);
    const key = `mock_daily_free.student_${new Date().toISOString().slice(0, 10)}`;
    localStorage.setItem(key, "5");
    render(<MockTestPage user={freeUser} />);
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /Daily Limit Reached/i });
      expect(btn.disabled).toBe(true);
    });
  });

  it("clicking locked Written format shows upgrade error", async () => {
    hasPaidAccess.mockReturnValue(false);
    render(<MockTestPage user={freeUser} />);
    await waitFor(() => screen.getByText(/Written Practice/i));
    fireEvent.click(screen.getByText(/Written Practice/i).closest("button"));
    await waitFor(() =>
      expect(screen.getByText(/Written and Mixed modes require a paid subscription/i)).toBeTruthy()
    );
  });

  it("paid user does NOT see daily limit counter", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    expect(screen.queryByText(/free mock tests used today/i)).toBeNull();
  });
});

// ── Exam Phase (MCQ) ──────────────────────────────────────────────────────────
describe("MockTestPage — exam phase (MCQ)", () => {
  beforeEach(() => {
    generateMockTest.mockResolvedValue({
      success: true, questions: makeMCQQuestions(3), message: "Generated",
    });
  });

  it("transitions to exam phase after generation", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getByText(/0\/3 answered/i)).toBeTruthy());
  });

  it("renders question navigator buttons 1, 2, 3", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "1" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "2" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "3" })).toBeTruthy();
    });
  });

  it("renders 12 radio inputs (4 options × 3 questions)", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getAllByRole("radio").length).toBe(12));
  });

  it("selects an answer when radio is clicked", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("radio"));
    const radios = screen.getAllByRole("radio");
    fireEvent.click(radios[0]);
    expect(radios[0].checked).toBe(true);
    expect(radios[1].checked).toBe(false);
  });

  it("answered count increments after selecting an answer", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("radio"));
    fireEvent.click(screen.getAllByRole("radio")[0]);
    await waitFor(() => expect(screen.getByText(/1\/3 answered/i)).toBeTruthy());
  });

  it("shows Submit Test button during exam phase", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() =>
      expect(screen.getAllByRole("button", { name: /Submit Test/i }).length).toBeGreaterThan(0)
    );
  });

  it("shows error when API returns success false", async () => {
    generateMockTest.mockResolvedValue({
      success: false, questions: [], message: "Service unavailable",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getByText(/Service unavailable/i)).toBeTruthy());
  });

  it("stays on setup phase when API throws", async () => {
    generateMockTest.mockRejectedValue(new Error("Network error"));
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() =>
      expect(screen.getByText(/Could not generate mock test/i)).toBeTruthy()
    );
  });
});

// ── Empty Options Guard ───────────────────────────────────────────────────────
describe("MockTestPage — empty options guard", () => {
  it("shows warning when MCQ question has empty options dict", async () => {
    generateMockTest.mockResolvedValue({
      success: true, questions: [makeEmptyOptionsQuestion()], message: "Generated",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() =>
      expect(screen.getByText(/Answer options unavailable/i)).toBeTruthy()
    );
  });

  it("does NOT render radio buttons when options are empty", async () => {
    generateMockTest.mockResolvedValue({
      success: true, questions: [makeEmptyOptionsQuestion()], message: "Generated",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getByText(/Answer options unavailable/i));
    expect(screen.queryAllByRole("radio").length).toBe(0);
  });

  it("valid options render radio buttons without warning", async () => {
    generateMockTest.mockResolvedValue({
      success: true, questions: makeMCQQuestions(1), message: "Generated",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getAllByRole("radio").length).toBe(4));
    expect(screen.queryByText(/Answer options unavailable/i)).toBeNull();
  });
});

// ── Written Question Rendering ────────────────────────────────────────────────
describe("MockTestPage — written question rendering", () => {
  it("renders textarea for written_short question", async () => {
    generateMockTest.mockResolvedValue({
      success: true, questions: [makeWrittenQuestion()], message: "Generated",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getByRole("textbox")).toBeTruthy());
    expect(screen.queryAllByRole("radio").length).toBe(0);
  });

  it("shows AI Feedback button for written question", async () => {
    generateMockTest.mockResolvedValue({
      success: true, questions: [makeWrittenQuestion()], message: "Generated",
    });
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => expect(screen.getByText(/Get AI Feedback/i)).toBeTruthy());
  });
});

// ── Result Phase ──────────────────────────────────────────────────────────────
describe("MockTestPage — result phase", () => {
  beforeEach(() => {
    generateMockTest.mockResolvedValue({
      success: true, questions: makeMCQQuestions(3), message: "Generated",
    });
  });

  it("transitions to result phase after submit", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("button", { name: /Submit Test/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Submit Test/i })[0]);
    await waitFor(() => expect(screen.getByText(/Results/i)).toBeTruthy());
  });

  it("shows score in result phase", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("button", { name: /Submit Test/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Submit Test/i })[0]);
    await waitFor(() => expect(screen.getByText(/Percentage/i)).toBeTruthy());
  });

  it("shows Answer Review section in result phase", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("button", { name: /Submit Test/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Submit Test/i })[0]);
    await waitFor(() => expect(screen.getByText(/Answer Review/i)).toBeTruthy());
  });

  it("Take Another Test button returns to setup phase", async () => {
    render(<MockTestPage user={paidUser} />);
    await waitFor(() => screen.getByText(/Generate Mock Test/i));
    fireEvent.click(screen.getByText(/Generate Mock Test/i));
    await waitFor(() => screen.getAllByRole("button", { name: /Submit Test/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Submit Test/i })[0]);
    await waitFor(() => screen.getByText(/Take Another Test/i));
    fireEvent.click(screen.getByText(/Take Another Test/i));
    await waitFor(() => expect(screen.getByText(/Generate Mock Test/i)).toBeTruthy());
  });
});
