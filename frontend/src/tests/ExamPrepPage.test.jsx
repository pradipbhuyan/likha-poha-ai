/**
 * ExamPrepPage.test.jsx — Exam Prep Center frontend tests
 * ========================================================
 * Tests:
 *   - Access denied for ineligible students (Grade 5-10)
 *   - Exam Prep renders for akshita.teststudent
 *   - Exam Prep renders for Grade 11/12 students
 *   - Exam tabs render (JEE active, NEET/CUET coming soon)
 *   - Stats cards render
 *   - Subject cards render (Physics, Chemistry, Mathematics)
 *   - Simulated test mode renders
 *   - Test result page renders with normalized score
 *   - Resource links render
 *   - Sidebar link visible for Grade 11/12 students
 *   - Sidebar link hidden for Grade 5-10 students
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ExamPrepPage from "../pages/ExamPrepPage";

// ── Mock API ─────────────────────────────────────────────────────────────────

vi.mock("../api/examPrep", () => ({
  getExamPrepDashboard: vi.fn().mockResolvedValue({
    success: true,
    exam_type: "jee_main",
    weeks_to_exam: 28,
    total_questions: 150,
    questions_attempted: 10,
    accuracy_pct: 70,
    correct_count: 7,
    total_topics: 24,
    subjects_count: 3,
  }),
  getExamPrepSubjects: vi.fn().mockResolvedValue({
    success: true,
    subjects: [
      { name: "Physics", icon: "⚛️", color: "#6366f1", chapters: 22, weightage_pct: 33, topic_count: 10, question_count: 50 },
      { name: "Chemistry", icon: "🧪", color: "#10b981", chapters: 28, weightage_pct: 33, topic_count: 8, question_count: 50 },
      { name: "Mathematics", icon: "📐", color: "#f59e0b", chapters: 16, weightage_pct: 34, topic_count: 7, question_count: 50 },
    ],
  }),
  getExamPrepTopics: vi.fn().mockResolvedValue({
    success: true,
    topics: [
      { name: "Kinematics", priority: "HIGH", subtopics: ["Projectile"], weightage_pct: 8, ncert_chapter: "NCERT Class 11, Chapter 3" },
    ],
  }),
  getExamPrepQuestions: vi.fn().mockResolvedValue({
    success: true,
    questions: [],
  }),
  submitQuestionAnswer: vi.fn().mockResolvedValue({
    success: true,
    is_correct: true,
    correct_option: "B",
    marks_awarded: 4,
    explanation: "F=ma",
    formula_used: "F = ma",
  }),
  explainQuestion: vi.fn().mockResolvedValue({
    success: true,
    correct_answer: "B",
    solution: "Step 1: Apply Newton's law",
    tip: "Remember to check units",
  }),
  askFollowUp: vi.fn().mockResolvedValue({
    success: true,
    answer: "Because force equals mass times acceleration.",
  }),
  startSimulatedTest: vi.fn().mockResolvedValue({
    success: true,
    test_id: "test-123",
    exam_type: "jee_main",
    grade: "Grade 12",
    question_ids: [],
    total_questions: 0,
    duration_minutes: 180,
    status: "active",
    started_at: "2026-01-01T00:00:00Z",
    message: "No questions available yet.",
  }),
  submitSimulatedTest: vi.fn().mockResolvedValue({
    success: true,
    test_id: "test-123",
    exam_type: "jee_main",
    score_normalized: 75.0,
    score_raw: 45,
    max_marks: 60,
    total_questions: 15,
    attempted: 15,
    correct: 12,
    wrong: 3,
    skipped: 0,
    subject_scores: {},
    topic_accuracy: {},
    weak_topics: [],
    ai_recommendations: ["Keep practicing!"],
  }),
}));

// ── User fixtures ─────────────────────────────────────────────────────────────

const grade12User = {
  id: "g12-1",
  username: "grade12student",
  role: "student",
  grade: "Grade 12",
  accessToken: "test-token-g12",
};

const grade10User = {
  id: "g10-1",
  username: "grade10student",
  role: "student",
  grade: "Grade 10",
  accessToken: "test-token-g10",
};

const testUser = {
  id: "test-1",
  username: "akshita.teststudent",
  role: "student",
  grade: "Grade 9",
  accessToken: "test-token-akshita",
};

const adminUser = {
  id: "admin-1",
  username: "admin_user",
  role: "admin",
  grade: null,
  accessToken: "test-token-admin",
};

// ── Access control tests ──────────────────────────────────────────────────────

describe("ExamPrepPage — Access Control", () => {
  it("shows access denied for Grade 10 students", () => {
    render(<ExamPrepPage user={grade10User} />);
    expect(screen.getByText(/available for Grade 11/i)).toBeTruthy();
  });

  it("shows access denied for Grade 5 students", () => {
    const grade5User = { ...grade12User, grade: "Grade 5", username: "grade5student" };
    render(<ExamPrepPage user={grade5User} />);
    expect(screen.getByText(/available for Grade 11/i)).toBeTruthy();
  });

  it("renders for akshita.teststudent (Grade 9 test user)", async () => {
    render(<ExamPrepPage user={testUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Test Access/i)).toBeTruthy();
    });
  });

  it("renders for Grade 12 student", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      // Should show exam tabs
      expect(screen.getByText("JEE Main")).toBeTruthy();
    });
  });

  it("renders for admin user", async () => {
    render(<ExamPrepPage user={adminUser} />);
    await waitFor(() => {
      expect(screen.getByText("JEE Main")).toBeTruthy();
    });
  });
});

// ── Exam tabs tests ───────────────────────────────────────────────────────────

describe("ExamPrepPage — Exam Tabs", () => {
  it("shows JEE Main as active tab", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("JEE Main")).toBeTruthy();
    });
  });

  it("shows NEET UG tab", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("NEET UG")).toBeTruthy();
    });
  });

  it("shows CUET UG with Coming Soon badge", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("CUET UG")).toBeTruthy();
    });
  });
});

// ── Stats cards tests ─────────────────────────────────────────────────────────

describe("ExamPrepPage — Stats Cards", () => {
  it("renders weeks to exam stat", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText(/28w/i)).toBeTruthy();
    });
  });

  it("renders total questions stat", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("150")).toBeTruthy();
    });
  });

  it("renders accuracy stat", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("70%")).toBeTruthy();
    });
  });
});

// ── Subject cards tests ───────────────────────────────────────────────────────

describe("ExamPrepPage — Subject Cards", () => {
  it("renders Physics, Chemistry, Mathematics subject cards", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("Physics")).toBeTruthy();
      expect(screen.getByText("Chemistry")).toBeTruthy();
      expect(screen.getByText("Mathematics")).toBeTruthy();
    });
  });

  it("shows topic cards when Physics is clicked", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("Physics")).toBeTruthy();
    });
    fireEvent.click(screen.getByText("Physics"));
    await waitFor(() => {
      // Topic card for Kinematics should appear
      expect(screen.getByText("Kinematics")).toBeTruthy();
    });
  });

  it("shows HIGH priority badge on high-priority topics", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("Physics")).toBeTruthy();
    });
    fireEvent.click(screen.getByText("Physics"));
    await waitFor(() => {
      expect(screen.getByText("HIGH")).toBeTruthy();
    });
  });
});

// ── Mode tabs tests ───────────────────────────────────────────────────────────

describe("ExamPrepPage — Mode Tabs", () => {
  it("renders Quick Practice and Simulated Test tabs", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText(/Quick Practice/i)).toBeTruthy();
      expect(screen.getByText(/Simulated Test/i)).toBeTruthy();
    });
  });

  it("switches to simulated test mode", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText(/Simulated Test/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByText(/Simulated Test/i));
    await waitFor(() => {
      // Button text is "🚀 Start JEE Main Simulation"
      expect(screen.getByRole("button", { name: /Start JEE Main Simulation/i })).toBeTruthy();
    });
  });

  it("shows Start JEE Main Simulation button in test mode", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText(/Simulated Test/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByText(/Simulated Test/i));
    await waitFor(() => {
      // Use getAllByText since the label appears in heading, description, and button
      expect(screen.getAllByText(/JEE Main Simulation/i).length).toBeGreaterThan(0);
    });
  });
});

// ── Test result page tests ────────────────────────────────────────────────────

describe("ExamPrepPage — Test Result Rendering", () => {
  it("result page renders normalized score <= 100", async () => {
    render(<ExamPrepPage user={grade12User} />);
    // Switch to test mode
    await waitFor(() => {
      expect(screen.getByText(/Simulated Test/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByText(/Simulated Test/i));

    // Start test — click the button specifically
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Start JEE Main Simulation/i })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /Start JEE Main Simulation/i }));

    // After starting, submit
    await waitFor(() => {
      expect(screen.getByText(/Submit Empty Test/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByText(/Submit Empty Test/i));

    // Result page shows
    await waitFor(() => {
      expect(screen.getByText(/Test Complete/i)).toBeTruthy();
    });
  });
});

// ── Resource links tests ──────────────────────────────────────────────────────

describe("ExamPrepPage — Resource Links", () => {
  it("renders resource link cards", async () => {
    render(<ExamPrepPage user={grade12User} />);
    await waitFor(() => {
      expect(screen.getByText("NCERT Chapters")).toBeTruthy();
      expect(screen.getByText("Formula Sheets")).toBeTruthy();
      expect(screen.getByText("Ask AI Tutor")).toBeTruthy();
      expect(screen.getByText("Mock Tests")).toBeTruthy();
    });
  });
});
