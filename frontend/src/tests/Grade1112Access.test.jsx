/**
 * Grade1112Access.test.jsx — Grade 11/12 Registration & Access Control Tests
 * ============================================================================
 * Tests:
 *   - SignupPage shows stream picker for Grade 11/12
 *   - Stream picker hidden for Grade 5-10
 *   - Stream validation blocks submit without stream selection
 *   - Each stream card renders and is selectable
 *   - ExamPrepPage: all Grade 11/12 students see the pack-based landing
 *   - ExamPrepPage: Grade 5-10 student sees "not available" guard
 *   - ExamPrepPage: akshita.teststudent (Grade 9) bypasses grade gate
 *   - ExamPrepPage: admin bypasses grade gate
 *   - Sidebar: Exam Prep visible for Grade 11/12 (all tiers)
 *   - Sidebar: Exam Prep hidden for Grade 5-10
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SignupPage from "../pages/SignupPage";
import ExamPrepPage from "../pages/ExamPrepPage";
import Sidebar from "../components/Sidebar";

// ── Mock APIs ─────────────────────────────────────────────────────────────────

vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      signOut: vi.fn().mockResolvedValue({}),
      signInWithPassword: vi.fn().mockResolvedValue({ data: null, error: { message: "test" } }),
      signInWithOAuth: vi.fn().mockResolvedValue({}),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({ data: null }),
    }),
  },
}));

vi.mock("../api/examPrep", () => ({
  getExamPrepDashboard: vi.fn().mockResolvedValue({
    success: true,
    exam_type: "jee_main",
    weeks_to_exam: 28,
    total_questions: 0,
    questions_attempted: 0,
    accuracy_pct: 0,
    correct_count: 0,
    total_topics: 24,
    subjects_count: 3,
  }),
  getExamPrepSubjects: vi.fn().mockResolvedValue({ success: true, subjects: [] }),
  getExamPrepTopics: vi.fn().mockResolvedValue({ success: true, topics: [] }),
  getExamPrepQuestions: vi.fn().mockResolvedValue({ success: true, questions: [] }),
  submitQuestionAnswer: vi.fn(),
  askFollowUp: vi.fn(),
  startSimulatedTest: vi.fn(),
  submitSimulatedTest: vi.fn(),
}));

vi.mock("../api/examPrepPacks", () => ({
  getMyPacks: vi.fn().mockResolvedValue({ packs: {}, grade_eligible: true }),
  getPackPrices: vi.fn().mockResolvedValue({
    prices: {
      jee_main: { price: 999, charge: 799, duration_days: 120, discount_pct: 20, included: ["Practice questions", "AI explanations", "Simulated tests"] },
      neet_ug:  { price: 999, charge: 799, duration_days: 120, discount_pct: 20, included: ["Practice questions", "AI explanations", "Simulated tests"] },
      cuet_ug:  { price: 999, charge: 799, duration_days: 120, discount_pct: 20, included: ["Practice questions", "AI explanations", "Simulated tests"] },
    },
    razorpay_configured: false,
  }),
  createPackOrder: vi.fn(),
  verifyPackPayment: vi.fn(),
}));

// ── User fixtures ─────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

const grade9FreeTier = {
  id: "u1", username: "grade9student", role: "student",
  grade: "Grade 9", subscriptionPlan: "free", accessToken: "tok1",
};
const grade11FreeTier = {
  id: "u2", username: "grade11free", role: "student",
  grade: "Grade 11", subscriptionPlan: "free", accessToken: "tok2",
};
const grade11Nano = {
  id: "u3", username: "grade11nano", role: "student",
  grade: "Grade 11", subscriptionPlan: "premium_nano", accessToken: "tok3",
};
const grade11Premium = {
  id: "u4", username: "grade11premium", role: "student",
  grade: "Grade 11", subscriptionPlan: "premium", accessToken: "tok4",
};
const grade12Premium = {
  id: "u5", username: "grade12premium", role: "student",
  grade: "Grade 12", subscriptionPlan: "premium", accessToken: "tok5",
};
const adminUser = {
  id: "u6", username: "admin_user", role: "admin",
  grade: null, subscriptionPlan: "free", accessToken: "tok6",
};
const testUser = {
  id: "u7", username: "akshita.teststudent", role: "student",
  grade: "Grade 9", subscriptionPlan: "free", accessToken: "tok7",
};

// ── SignupPage — Stream picker tests ──────────────────────────────────────────

describe("SignupPage — Grade 11/12 Stream Picker", () => {
  it("stream picker NOT shown for Grade 9 student", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    expect(screen.queryByTestId("stream-picker")).toBeNull();
  });

  it("stream picker NOT shown for Grade 5", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 5" } });
    expect(screen.queryByTestId("stream-picker")).toBeNull();
  });

  it("stream picker NOT shown for Grade 10", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 10" } });
    expect(screen.queryByTestId("stream-picker")).toBeNull();
  });

  it("stream picker shown when Grade 11 selected", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-picker")).toBeTruthy();
  });

  it("stream picker shown when Grade 12 selected", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 12" } });
    expect(screen.getByTestId("stream-picker")).toBeTruthy();
  });

  it("all 5 stream options render for Grade 11", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-card-PCM")).toBeTruthy();
    expect(screen.getByTestId("stream-card-PCB")).toBeTruthy();
    expect(screen.getByTestId("stream-card-PCMB")).toBeTruthy();
    expect(screen.getByTestId("stream-card-Commerce")).toBeTruthy();
    expect(screen.getByTestId("stream-card-Humanities")).toBeTruthy();
  });

  it("PCM stream card renders for Grade 11", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-card-PCM")).toBeTruthy();
  });

  it("PCB stream card renders for Grade 11", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-card-PCB")).toBeTruthy();
  });

  it("stream picker hidden for parent role even if grade 11 would be selected", () => {
    render(<SignupPage onBack={() => {}} />);
    expect(screen.queryByTestId("stream-picker")).toBeNull();
    expect(screen.queryByTestId("signup-grade")).toBeNull();
  });

  it("stream picker resets when grade changes from 11 back to 9", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-picker")).toBeTruthy();
    fireEvent.change(gradeSelect, { target: { value: "Grade 9" } });
    expect(screen.queryByTestId("stream-picker")).toBeNull();
  });

  it("submit blocked when Grade 11 selected without stream", async () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test Student" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      const errorEl = screen.getByTestId("signup-error");
      expect(errorEl.textContent).toMatch(/stream/i);
    });
  });

  it("selecting PCM stream clears the stream validation error", async () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test Student" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("signup-error").textContent).toMatch(/stream/i);
    });
    fireEvent.click(screen.getByTestId("stream-card-PCM"));
    expect(screen.queryByTestId("signup-error")).toBeNull();
  });
});

// ── ExamPrepPage — Pack-based access gate tests ───────────────────────────────
// NOTE: ExamPrepPage uses a pack-based purchase model (2026-07-09).
// All Grade 11/12 students see the landing/preview page with exam pack cards.
// Access to each exam (JEE/NEET/CUET) requires a separate pack purchase,
// independent of CBSE subscription tier (free/nano/premium).

describe("ExamPrepPage — Access Control & Pack Gate", () => {
  it("Grade 9 free-tier student sees grade access denied", async () => {
    render(<ExamPrepPage user={grade9FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/Available for Grade 11 & 12/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier student sees exam prep landing (not grade-blocked)", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
      expect(screen.getByText(/purchase the pack to access/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier landing shows all three exam pack cards", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText("JEE Main")).toBeTruthy();
      expect(screen.getByText("NEET UG")).toBeTruthy();
      expect(screen.getByText("CUET UG")).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier landing shows feature list including simulated tests", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getAllByText(/Full simulated tests/i).length).toBeGreaterThan(0);
    });
  });

  it("Grade 11 FREE-tier landing shows Unlock pack buttons", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Unlock JEE Main/i })).toBeTruthy();
    });
  });

  it("Grade 11 NANO plan sees exam prep landing (pack purchase required)", async () => {
    render(<ExamPrepPage user={grade11Nano} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
      expect(screen.getByText(/purchase the pack to access/i)).toBeTruthy();
    });
  });

  it("Grade 11 NANO plan landing shows Unlock pack buttons", async () => {
    render(<ExamPrepPage user={grade11Nano} />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Unlock JEE Main/i })).toBeTruthy();
    });
  });

  it("Grade 11 PREMIUM plan sees exam prep landing with exam cards", async () => {
    render(<ExamPrepPage user={grade11Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText("JEE Main")).toBeTruthy();
    });
  });

  it("Grade 12 PREMIUM student sees exam prep landing (not grade-blocked)", async () => {
    render(<ExamPrepPage user={grade12Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("Admin user bypasses grade gate and sees exam prep landing", async () => {
    render(<ExamPrepPage user={adminUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("akshita.teststudent (Grade 9) bypasses grade gate and sees landing", async () => {
    render(<ExamPrepPage user={testUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Exam Prep Center/i)).toBeTruthy();
    });
  });

  it("Grade 11 landing shows practice questions feature text", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getAllByText(/Practice questions/i).length).toBeGreaterThan(0);
    });
  });
});

// ── Sidebar — Exam Prep visibility tests ──────────────────────────────────────

describe("Sidebar — Exam Prep Link Visibility", () => {
  function renderSidebar(user) {
    return render(
      <Sidebar
        activePage="dashboard"
        setActivePage={() => {}}
        user={user}
        onLogout={() => {}}
        mobileNavOpen={false}
        setMobileNavOpen={() => {}}
      />
    );
  }

  it("Exam Prep Centre visible for Grade 11 free student", () => {
    renderSidebar(grade11FreeTier);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });

  it("Exam Prep Centre visible for Grade 12 premium student", () => {
    renderSidebar(grade12Premium);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });

  it("Exam Prep Centre visible for Grade 11 nano student", () => {
    renderSidebar(grade11Nano);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });

  it("Exam Prep Centre NOT visible for Grade 9 student", () => {
    renderSidebar(grade9FreeTier);
    expect(screen.queryByText("Exam Prep Center")).toBeNull();
  });

  it("Exam Prep Centre NOT visible for Grade 5 student", () => {
    const grade5User = { ...grade9FreeTier, grade: "Grade 5", username: "g5student" };
    renderSidebar(grade5User);
    expect(screen.queryByText("Exam Prep Center")).toBeNull();
  });

  it("Exam Prep Centre visible for akshita.teststudent (Grade 9 test bypass)", () => {
    renderSidebar(testUser);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });

  it("Exam Prep Centre visible for admin (not hidden for admin)", () => {
    renderSidebar(adminUser);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });
});

// ── Plan-based access combinations ────────────────────────────────────────────
// In the pack-based model, ALL Grade 11 students (any plan) see the landing.
// The distinction is now per-exam pack ownership, not subscription tier.
// These tests verify no plan is grade-blocked from the landing page.

describe("ExamPrepPage — Plan-based access combinations", () => {
  const plans = [
    { plan: "free",           expectLocked: true },
    { plan: "premium_nano",   expectLocked: true },
    { plan: "nano",           expectLocked: true },
    { plan: "premium",        expectLocked: false },
    { plan: "premium_annual", expectLocked: false },
    { plan: "family",         expectLocked: false },
    { plan: "school",         expectLocked: false },
  ];

  plans.forEach(({ plan, expectLocked }) => {
    it(`Grade 11 with plan "${plan}" — ${expectLocked ? "LOCKED" : "UNLOCKED"}`, async () => {
      const user = { id: "x", username: "tester", role: "student", grade: "Grade 11", subscriptionPlan: plan, accessToken: "tok" };
      render(<ExamPrepPage user={user} />);
      if (expectLocked) {
        // Locked plans see the landing with pack purchase required
        await waitFor(() => {
          expect(screen.getByText(/purchase the pack to access/i)).toBeTruthy();
        });
      } else {
        // Unlocked plans (premium+) still see the landing (packs are per-exam purchase)
        // but are not grade-blocked
        await waitFor(() => {
          expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
          expect(screen.getByText("JEE Main")).toBeTruthy();
        });
      }
    });
  });
});
