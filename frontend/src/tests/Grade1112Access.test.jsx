/**
 * Grade1112Access.test.jsx — Grade 11/12 Registration & Access Control Tests
 * ============================================================================
 * Tests:
 *   - SignupPage shows stream picker for Grade 11/12
 *   - Stream picker hidden for Grade 5-10
 *   - Stream validation blocks submit without stream selection
 *   - Each stream card renders and is selectable
 *   - ExamPrepPage: free-tier Grade 11/12 sees paywall, not content
 *   - ExamPrepPage: nano plan sees paywall
 *   - ExamPrepPage: premium plan sees content
 *   - ExamPrepPage: admin always sees content
 *   - ExamPrepPage: Grade 5-10 student sees "not available" guard
 *   - ExamPrepPage: akshita.teststudent (Grade 9) bypasses paywall
 *   - Sidebar: Exam Prep visible for Grade 11/12 (all tiers)
 *   - Sidebar: Exam Prep hidden for Grade 5-10
 *   - ResourcesPage: subject · chapter separator renders correctly
 */

import { describe, it, expect, vi } from "vitest";
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

// ── User fixtures ─────────────────────────────────────────────────────────────

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
    // Select student role
    fireEvent.click(screen.getByTestId("role-card-student"));
    // Grade 9 is default — no stream picker
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

  it("PCM stream card shows JEE Main label", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    expect(screen.getByText("JEE Main")).toBeTruthy();
  });

  it("PCB stream card shows NEET UG label", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-grade"), { target: { value: "Grade 11" } });
    expect(screen.getByText("NEET UG")).toBeTruthy();
  });

  it("stream picker hidden for parent role even if grade 11 would be selected", () => {
    render(<SignupPage onBack={() => {}} />);
    // Stay on parent role (default)
    expect(screen.queryByTestId("stream-picker")).toBeNull();
    expect(screen.queryByTestId("signup-grade")).toBeNull(); // grade hidden for parent
  });

  it("stream picker resets when grade changes from 11 back to 9", () => {
    render(<SignupPage onBack={() => {}} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    const gradeSelect = screen.getByTestId("signup-grade");
    fireEvent.change(gradeSelect, { target: { value: "Grade 11" } });
    expect(screen.getByTestId("stream-picker")).toBeTruthy();
    // Switch back to Grade 9
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
    // Do NOT select a stream
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
    // Submit without stream to trigger error
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("signup-error").textContent).toMatch(/stream/i);
    });
    // Select PCM — error should clear
    fireEvent.click(screen.getByTestId("stream-card-PCM"));
    expect(screen.queryByTestId("signup-error")).toBeNull();
  });
});

// ── ExamPrepPage — Premium gate tests ─────────────────────────────────────────

describe("ExamPrepPage — Access Control & Premium Gate", () => {
  it("Grade 9 free-tier student sees access denied (not Grade 11/12)", () => {
    render(<ExamPrepPage user={grade9FreeTier} />);
    expect(screen.getByText(/Available for Grade 11 & 12/i)).toBeTruthy();
  });

  it("Grade 11 FREE-tier student sees premium paywall (not content)", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center — Premium Feature/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier paywall shows feature preview cards", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/JEE Main prep/i)).toBeTruthy();
      expect(screen.getByText(/NEET UG prep/i)).toBeTruthy();
      expect(screen.getByText(/Simulated tests/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier paywall shows Upgrade to Premium button", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Upgrade to Premium/i })).toBeTruthy();
    });
  });

  it("Grade 11 NANO plan sees paywall (Nano excluded from Exam Prep)", async () => {
    render(<ExamPrepPage user={grade11Nano} />);
    await waitFor(() => {
      expect(screen.getByText(/Exam Prep Center — Premium Feature/i)).toBeTruthy();
    });
  });

  it("Grade 11 NANO paywall shows nano-specific message", async () => {
    render(<ExamPrepPage user={grade11Nano} />);
    await waitFor(() => {
      expect(screen.getByText(/Premium Nano plan/i)).toBeTruthy();
    });
  });

  it("Grade 11 PREMIUM plan sees full content (JEE Main tab visible)", async () => {
    render(<ExamPrepPage user={grade11Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Exam Prep Center — Premium Feature/i)).toBeNull();
      expect(screen.getByText("JEE Main")).toBeTruthy();
    });
  });

  it("Grade 12 PREMIUM student sees content", async () => {
    render(<ExamPrepPage user={grade12Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Exam Prep Center — Premium Feature/i)).toBeNull();
    });
  });

  it("Admin user bypasses paywall and sees full content", async () => {
    render(<ExamPrepPage user={adminUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Exam Prep Center — Premium Feature/i)).toBeNull();
      expect(screen.getByText(/Admin Preview/i)).toBeTruthy();
    });
  });

  it("akshita.teststudent (Grade 9) bypasses paywall — sees content", async () => {
    render(<ExamPrepPage user={testUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Exam Prep Center — Premium Feature/i)).toBeNull();
      expect(screen.getByText(/Test Access/i)).toBeTruthy();
    });
  });

  it("Grade 11 free paywall shows exam tabs as disabled visual", async () => {
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      // Disabled tabs still render (grayed out) to give a feel of the product
      expect(screen.getByText("NEET UG")).toBeTruthy();
      expect(screen.getByText("CUET UG")).toBeTruthy();
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

// ── Subscription plan combinations ───────────────────────────────────────────

describe("ExamPrepPage — Plan-based access combinations", () => {
  const plans = [
    { plan: "free", expectLocked: true },
    { plan: "premium_nano", expectLocked: true },
    { plan: "nano", expectLocked: true },
    { plan: "premium", expectLocked: false },
    { plan: "premium_annual", expectLocked: false },
    { plan: "family", expectLocked: false },
    { plan: "school", expectLocked: false },
  ];

  plans.forEach(({ plan, expectLocked }) => {
    it(`Grade 11 with plan "${plan}" — ${expectLocked ? "LOCKED" : "UNLOCKED"}`, async () => {
      const user = { id: "x", username: "tester", role: "student", grade: "Grade 11", subscriptionPlan: plan, accessToken: "tok" };
      render(<ExamPrepPage user={user} />);
      if (expectLocked) {
        await waitFor(() => {
          expect(screen.getByText(/Exam Prep Center — Premium Feature/i)).toBeTruthy();
        });
      } else {
        await waitFor(() => {
          expect(screen.queryByText(/Exam Prep Center — Premium Feature/i)).toBeNull();
          expect(screen.getByText("JEE Main")).toBeTruthy();
        });
      }
    });
  });
});
