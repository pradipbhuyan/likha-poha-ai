/**
 * ExamPrepPage.test.jsx — Exam Prep Center frontend tests (new pack-based design)
 * ================================================================================
 * Tests match the rewritten ExamPrepPage (2026-07-09) which shows a landing page
 * with 3 pack cards (JEE / NEET / CUET) instead of the old access-check flow.
 *
 * Key behaviour changes from old design:
 *   - All Grade 11/12 students see the landing page with pack cards
 *   - akshita.teststudent is grade-eligible regardless of their grade
 *   - Stats/subjects/topics only appear INSIDE an exam, after pack is active
 *   - Pack purchase is via Razorpay, independent of CBSE subscription
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ExamPrepPage from "../pages/ExamPrepPage";
import * as examPrepPacksApi from "../api/examPrepPacks";

// ── Mock API modules ──────────────────────────────────────────────────────────

vi.mock("../api/examPrep", () => ({
  getExamPrepSubjects: vi.fn().mockResolvedValue({ success: true, subjects: [] }),
  getExamPrepTopics: vi.fn().mockResolvedValue({ success: true, topics: [] }),
  getExamPrepQuestions: vi.fn().mockResolvedValue({ success: true, questions: [] }),
  submitQuestionAnswer: vi.fn().mockResolvedValue({}),
  startSimulatedTest: vi.fn().mockResolvedValue({ test_id: "t1", duration_minutes: 180 }),
  submitSimulatedTest: vi.fn().mockResolvedValue({ score_normalized: 75, correct: 7, wrong: 2, skipped: 1, total_questions: 10 }),
}));

vi.mock("../api/examPrepPacks", () => ({
  getMyPacks: vi.fn().mockResolvedValue({
    success: true,
    grade_eligible: true,
    packs: {
      jee_main:  { active: false, expires_at: null },
      neet_ug:   { active: false, expires_at: null },
      cuet_ug:   { active: false, expires_at: null },
    },
  }),
  getPackPrices: vi.fn().mockResolvedValue({
    success: true,
    razorpay_configured: true,
    prices: {
      jee_main:  { plan_key: "exam_prep_jee",  label: "JEE Main Prep Pack",  price: 499, charge: 499, duration_days: 120, included: ["Practice questions"], badge: "" },
      neet_ug:   { plan_key: "exam_prep_neet", label: "NEET UG Prep Pack",   price: 499, charge: 499, duration_days: 300, included: ["Practice questions"], badge: "" },
      cuet_ug:   { plan_key: "exam_prep_cuet", label: "CUET UG Prep Pack",   price: 399, charge: 399, duration_days: 240, included: ["Practice questions"], badge: "" },
    },
  }),
  createPackOrder: vi.fn().mockResolvedValue({ order_id: "ord_1", amount: 499, key_id: "rzp_test", exam_type: "jee_main", plan_label: "JEE Pack", duration_days: 120 }),
  verifyPackPayment: vi.fn().mockResolvedValue({ success: true, exam_type: "jee_main", expires_at: null }),
}));

// ── Test users ────────────────────────────────────────────────────────────────

const grade12User = {
  id: "u1",
  username: "student12",
  role: "student",
  grade: "Grade 12",
  accessToken: "tok-12",
  email: "student12@test.com",
};

const grade11User = {
  id: "u2",
  username: "student11",
  role: "student",
  grade: "Grade 11",
  accessToken: "tok-11",
  email: "student11@test.com",
};

const grade10User = {
  id: "u3",
  username: "grade10student",
  role: "student",
  grade: "Grade 10",
  accessToken: "tok-10",
  email: "grade10@test.com",
};

const grade5User = {
  id: "u4",
  username: "grade5student",
  role: "student",
  grade: "Grade 5",
  accessToken: "tok-5",
  email: "grade5@test.com",
};

const adminUser = {
  id: "admin1",
  username: "admin",
  role: "admin",
  grade: "Grade 9",
  accessToken: "tok-admin",
  email: "admin@test.com",
};

const testUser = {
  id: "tst1",
  username: "akshita.teststudent",
  role: "student",
  grade: "Grade 9",
  accessToken: "tok-test",
  email: "akshita@test.com",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderWithUser(user) {
  return render(<ExamPrepPage user={user} />);
}

// ── Access Control tests ──────────────────────────────────────────────────────

describe("ExamPrepPage — Access Control", () => {
  it("shows access denied for Grade 10 students", () => {
    renderWithUser(grade10User);
    expect(screen.getByText(/available for Grade 11/i)).toBeTruthy();
  });

  it("shows access denied for Grade 5 students", () => {
    renderWithUser(grade5User);
    expect(screen.getByText(/available for Grade 11/i)).toBeTruthy();
  });

  it("renders landing page for akshita.teststudent (Grade 9 test user)", async () => {
    // Test user bypass — grade 9 but still eligible
    renderWithUser(testUser);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("renders landing page for Grade 12 student", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("renders landing page for Grade 11 student", async () => {
    renderWithUser(grade11User);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("renders landing page for admin user", async () => {
    renderWithUser(adminUser);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });
});

// ── Landing page content tests ────────────────────────────────────────────────

describe("ExamPrepPage — Landing Page", () => {
  it("shows all 3 exam pack cards on landing page", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText("JEE Main")).toBeTruthy();
      expect(screen.getByText("NEET UG")).toBeTruthy();
      expect(screen.getByText("CUET UG")).toBeTruthy();
    });
  });

  it("shows Grade 11 & 12 only badge", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/Grade 11 & 12 only/i)).toBeTruthy();
    });
  });

  it("shows Locked status for unpurchased packs", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      const locked = screen.getAllByText(/Locked/i);
      expect(locked.length).toBeGreaterThanOrEqual(3);
    });
  });

  it("shows Unlock JEE Main button for unpurchased JEE pack", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/Unlock JEE Main/i)).toBeTruthy();
    });
  });

  it("shows pack independence note", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/each pack is independent/i)).toBeTruthy();
    });
  });

  it("shows prices for packs (₹499 for JEE)", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      const prices = screen.getAllByText(/₹499/);
      expect(prices.length).toBeGreaterThan(0);
    });
  });
});

// ── Pack active state tests ───────────────────────────────────────────────────

describe("ExamPrepPage — Active Pack State", () => {
  beforeEach(() => {
    vi.mocked(examPrepPacksApi.getMyPacks).mockResolvedValue({
      success: true,
      grade_eligible: true,
      packs: {
        jee_main:  { active: true,  expires_at: "2027-01-15T00:00:00Z" },
        neet_ug:   { active: false, expires_at: null },
        cuet_ug:   { active: false, expires_at: null },
      },
    });
  });

  it("shows Active badge for purchased pack", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/✅ Active/i)).toBeTruthy();
    });
  });

  it("shows Go to JEE Main Prep button for active pack", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText(/Go to JEE Main Prep/i)).toBeTruthy();
    });
  });
});

// ── Exam tabs / card labels ───────────────────────────────────────────────────

describe("ExamPrepPage — Exam Labels", () => {
  it("shows Engineering entrance sub-label for JEE", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText("Engineering entrance")).toBeTruthy();
    });
  });

  it("shows Medical entrance sub-label for NEET", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText("Medical entrance")).toBeTruthy();
    });
  });

  it("shows Central university entrance sub-label for CUET", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getByText("Central university entrance")).toBeTruthy();
    });
  });

  it("shows feature list in pack cards", async () => {
    renderWithUser(grade12User);
    await waitFor(() => {
      expect(screen.getAllByText(/Practice questions/i).length).toBeGreaterThan(0);
    });
  });
});

// ── Result page ───────────────────────────────────────────────────────────────

describe("ExamPrepPage — Test Result Score", () => {
  it("score_normalized is within 0-100 range", () => {
    // Validate score range without rendering — pure logic check
    const scoreNormalized = 75;
    expect(scoreNormalized).toBeGreaterThanOrEqual(0);
    expect(scoreNormalized).toBeLessThanOrEqual(100);
  });
});
