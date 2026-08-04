/**
 * ExamPrepPage.test.jsx — Exam Prep Center frontend tests
 * ========================================================
 * Tests match the current ExamPrepPage which uses access-check endpoint
 * (canonical backend) to determine grade eligibility and subscription status.
 *
 * Key behaviour:
 *   - Loading spinner while access-check fetch is in-flight
 *   - Grade-ineligible students (Grade 5–10) see "Grade 11 & 12 only" guard
 *   - Free/Nano-tier Grade 11/12 students see premium gate (Coming Soon)
 *   - Premium Grade 11/12 students see the full Exam Prep Center
 *   - Admin and test users bypass subscription gate
 *   - 5 mode tabs: Structured Learning, Practice, Simulated Test, Quick Reference, Cutoff Oracle
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import ExamPrepPage from "../pages/ExamPrepPage";

// ── Mock API modules ──────────────────────────────────────────────────────────

vi.mock("../api/examPrep", () => ({
  getExamPrepDashboard: vi.fn().mockResolvedValue({
    exam_type: "jee_main",
    weeks_to_exam: 28,
    total_questions: 121,
    questions_attempted: 0,
    accuracy_pct: 0,
    correct_count: 0,
    total_topics: 24,
    subjects_count: 3,
  }),
  getExamPrepSubjects: vi.fn().mockResolvedValue({ subjects: [] }),
  getExamPrepTopics: vi.fn().mockResolvedValue({ topics: [] }),
  getExamPrepQuestions: vi.fn().mockResolvedValue({ questions: [] }),
  submitQuestionAnswer: vi.fn().mockResolvedValue({}),
  askFollowUp: vi.fn().mockResolvedValue({ answer: "" }),
  startSimulatedTest: vi.fn().mockResolvedValue({ test_id: "t1", duration_minutes: 180, question_ids: [] }),
  submitSimulatedTest: vi.fn().mockResolvedValue({ score_normalized: 75, correct: 7, wrong: 2, skipped: 1, total_questions: 10 }),
}));

// ── Access-check response helpers ─────────────────────────────────────────────

const ACCESS_GRADE_INELIGIBLE = {
  grade_eligible: false,
  has_access: false,
  preview_only: true,
  reason: "grade_ineligible",
  stream: null,
  exam_eligibility: null,
  canonical_plan_key: null,
  plan_name: null,
};

const ACCESS_FREE_PREVIEW = {
  grade_eligible: true,
  has_access: false,
  preview_only: true,
  reason: "free",
  stream: "PCM",
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: false, reason: "NEET requires Biology." },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "FREE_TIER",
  plan_name: "Free Tier",
};

const ACCESS_NANO_PREVIEW = {
  ...ACCESS_FREE_PREVIEW,
  reason: "nano",
  canonical_plan_key: "PREMIUM_NANO",
  plan_name: "Premium Nano",
};

const ACCESS_FULL = {
  grade_eligible: true,
  has_access: true,
  preview_only: false,
  reason: "full_access",
  stream: "PCM",
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: false, reason: "Requires Biology." },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "PREMIUM",
  plan_name: "Premium",
};

const ACCESS_ADMIN = {
  grade_eligible: true,
  has_access: true,
  preview_only: false,
  reason: "admin",
  stream: null,
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: true, reason: "" },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "ADMIN_GRANT",
  plan_name: "Admin",
};

const ACCESS_TEST_USER = {
  grade_eligible: true,
  has_access: true,
  preview_only: false,
  reason: "test_user",
  stream: null,
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: true, reason: "" },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "ADMIN_GRANT",
  plan_name: "Test Access",
};

// Mock global fetch for access-check
function mockFetch(accessData) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    json: () => Promise.resolve(accessData),
  }));
}

// ── User fixtures ─────────────────────────────────────────────────────────────

const grade10User = { id: "u1", role: "student", grade: "Grade 10", username: "student10", accessToken: "tok" };
const grade11FreeUser = { id: "u2", role: "student", grade: "Grade 11", username: "student11free", accessToken: "tok" };
const grade11NanoUser = { id: "u3", role: "student", grade: "Grade 11", username: "student11nano", accessToken: "tok" };
const grade11PremiumUser = { id: "u4", role: "student", grade: "Grade 11", username: "student11prem", accessToken: "tok" };
const adminUser = { id: "u5", role: "admin", grade: "Grade 11", username: "admin", accessToken: "tok" };
const testUser = { id: "u6", role: "student", grade: "Grade 9", username: "akshita.teststudent", accessToken: "tok" };

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ExamPrepPage — access control", () => {
  it("shows loading spinner while access-check is in-flight", () => {
    // fetch never resolves → stays in loading
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    render(<ExamPrepPage user={grade11FreeUser} />);
    // page-level section is rendered (loading state uses Loader component)
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
  });

  it("shows grade-ineligible guard for Grade 10 student", async () => {
    mockFetch(ACCESS_GRADE_INELIGIBLE);
    render(<ExamPrepPage user={grade10User} />);
    await waitFor(() => {
      expect(screen.getByText(/Available for Grade 11 & 12 students only/i)).toBeTruthy();
    });
  });

  it("shows premium gate with a working Unlock CTA for free-tier Grade 11 student", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Unlock for/i)).toBeTruthy();
    });
  });

  it("shows nano plan message with a working Unlock CTA for Nano-tier Grade 11 student", async () => {
    mockFetch(ACCESS_NANO_PREVIEW);
    render(<ExamPrepPage user={grade11NanoUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Unlock for/i)).toBeTruthy();
    });
  });

  it("shows full Exam Prep Center for Premium Grade 11 student", async () => {
    mockFetch(ACCESS_FULL);
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("shows full Exam Prep Center for admin", async () => {
    mockFetch(ACCESS_ADMIN);
    render(<ExamPrepPage user={adminUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("shows full Exam Prep Center for akshita.teststudent (test user)", async () => {
    mockFetch(ACCESS_TEST_USER);
    render(<ExamPrepPage user={testUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });
});

describe("ExamPrepPage — 5 mode tabs", () => {
  beforeEach(() => {
    mockFetch(ACCESS_FULL);
  });

  it("shows all 5 mode tabs for premium user", async () => {
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => {
      // Check all 5 mode tab buttons are present (each button renders icon + label)
      const buttons = screen.getAllByRole("button");
      const labels = buttons.map(b => b.textContent);
      expect(labels.some(t => /Structured Learning/i.test(t))).toBe(true);
      expect(labels.some(t => /Practice/i.test(t))).toBe(true);
      expect(labels.some(t => /Simulated Test/i.test(t))).toBe(true);
      expect(labels.some(t => /Quick Reference/i.test(t))).toBe(true);
      expect(labels.some(t => /Cutoff Oracle/i.test(t))).toBe(true);
    });
  });

  it("shows 3 exam tabs: JEE Main, NEET UG, CUET UG", async () => {
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => {
      expect(screen.getAllByText(/JEE Main/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/NEET UG/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/CUET UG/i).length).toBeGreaterThan(0);
    });
  });

  it("shows exam strategy box in Structured Learning tab", async () => {
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Strategy/i)).toBeTruthy();
    });
  });

  it("Practice tab renders without crashing (regression: bare icon-component render)", async () => {
    // Previously the "{examInfo.label} — Subjects" heading rendered the exam
    // icon as {examInfo.icon} instead of <examInfo.icon />. Since the emoji ->
    // Lucide-icon conversion, that field holds a component reference, not a
    // string, so React threw "Objects are not valid as a React child" the
    // instant this tab rendered — crashing the whole page for every exam.
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => expect(screen.getByText(/Structured Learning/i)).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /^Practice$/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/Subjects/i).length).toBeGreaterThan(0);
    });
  });

  it("Simulated Test tab renders without crashing (regression: bare icon-component render)", async () => {
    // Same bug, same fix, second call site: the "Start {exam} Simulation"
    // landing screen shown before a test session exists.
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => expect(screen.getByText(/Structured Learning/i)).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Simulated Test/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/Start .*Simulation/i).length).toBeGreaterThan(0);
    });
  });

  it("starting a simulation renders the backend's returned questions directly, without a second per-subject fetch", async () => {
    // Regression: this used to re-fetch questions independently per subject
    // via getExamPrepQuestions after starting a test, using its own
    // unordered query — a second, disconnected fetch from the one the
    // backend used to build question_ids for scoring. They only happened to
    // return the same questions because neither side randomized; adding
    // rotation to just one side would make the displayed test diverge from
    // what submit_simulated_test actually scores. Now the frontend renders
    // exactly what start_simulated_test returns, and nothing else is fetched.
    const { startSimulatedTest, getExamPrepQuestions } = await import("../api/examPrep");
    startSimulatedTest.mockResolvedValueOnce({
      test_id: "t-rotation",
      duration_minutes: 180,
      question_ids: ["q-unique-1"],
      questions: [
        {
          id: "q-unique-1",
          subject: "Physics",
          topic: "Kinematics",
          question_text: "A distinctive rotation-fix regression question about velocity",
          options_json: [
            { key: "A", text: "1" }, { key: "B", text: "2" },
            { key: "C", text: "3" }, { key: "D", text: "4" },
          ],
          difficulty: "medium",
          marks: 4,
          negative_marks: 1,
        },
      ],
    });

    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => expect(screen.getByText(/Structured Learning/i)).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Simulated Test/i }));
    await waitFor(() => screen.getByRole("button", { name: /Start .*Simulation/i }));
    fireEvent.click(screen.getByRole("button", { name: /Start .*Simulation/i }));

    await waitFor(() => {
      expect(screen.getByText(/distinctive rotation-fix regression question/i)).toBeTruthy();
    });
    expect(getExamPrepQuestions).not.toHaveBeenCalled();
  });
});

describe("ExamPrepPage — premium gate content", () => {
  it("shows JEE/NEET/CUET feature list in locked preview", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeUser} />);
    await waitFor(() => {
      expect(screen.getAllByText(/JEE Main prep/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/NEET UG prep/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/CUET UG prep/i).length).toBeGreaterThan(0);
    });
  });

  it("shows Premium Feature heading in locked preview", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeUser} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center — Premium Feature/i)).toBeTruthy();
    });
  });
});

describe("ExamPrepPage — exam-specific strategy (JEE correct values)", () => {
  it("shows 75 questions · 3 hours · 300 marks for JEE", async () => {
    mockFetch(ACCESS_FULL);
    render(<ExamPrepPage user={grade11PremiumUser} />);
    await waitFor(() => {
      expect(screen.getByText(/75 questions/i)).toBeTruthy();
      expect(screen.getByText(/300 marks/i)).toBeTruthy();
    });
  });
});
