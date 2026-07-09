/**
 * Grade1112Access.test.jsx — Grade 11/12 Registration & Access Control Tests
 * ============================================================================
 * Tests:
 *   - SignupPage shows stream picker for Grade 11/12
 *   - Stream picker hidden for Grade 5-10
 *   - Stream validation blocks submit without stream selection
 *   - Each stream card renders and is selectable
 *   - ExamPrepPage: grade-blocked students see "not available" guard
 *   - ExamPrepPage: Grade 11/12 free/nano students see premium gate
 *   - ExamPrepPage: Grade 11/12 premium students see full center
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
    exam_type: "jee_main",
    weeks_to_exam: 28,
    total_questions: 0,
    questions_attempted: 0,
    accuracy_pct: 0,
    correct_count: 0,
    total_topics: 24,
    subjects_count: 3,
  }),
  getExamPrepSubjects: vi.fn().mockResolvedValue({ subjects: [] }),
  getExamPrepTopics: vi.fn().mockResolvedValue({ topics: [] }),
  getExamPrepQuestions: vi.fn().mockResolvedValue({ questions: [] }),
  submitQuestionAnswer: vi.fn(),
  askFollowUp: vi.fn(),
  startSimulatedTest: vi.fn(),
  submitSimulatedTest: vi.fn(),
}));

// ── Access-check response helpers ─────────────────────────────────────────────

const ACCESS_GRADE_INELIGIBLE = {
  grade_eligible: false, has_access: false, preview_only: true,
  reason: "grade_ineligible", stream: null, exam_eligibility: null,
  canonical_plan_key: null, plan_name: null,
};

const ACCESS_FREE_PREVIEW = {
  grade_eligible: true, has_access: false, preview_only: true,
  reason: "free", stream: "PCM",
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: false, reason: "Requires Biology." },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "FREE_TIER", plan_name: "Free Tier",
};

const ACCESS_NANO_PREVIEW = {
  ...ACCESS_FREE_PREVIEW, reason: "nano",
  canonical_plan_key: "PREMIUM_NANO", plan_name: "Premium Nano",
};

const ACCESS_FULL = {
  grade_eligible: true, has_access: true, preview_only: false,
  reason: "full_access", stream: "PCM",
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: false, reason: "Requires Biology." },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "PREMIUM", plan_name: "Premium",
};

const ACCESS_ADMIN = {
  grade_eligible: true, has_access: true, preview_only: false,
  reason: "admin", stream: null,
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: true, reason: "" },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "ADMIN_GRANT", plan_name: "Admin",
};

const ACCESS_TEST_USER = {
  grade_eligible: true, has_access: true, preview_only: false,
  reason: "test_user", stream: null,
  exam_eligibility: {
    jee_main: { eligible: true, reason: "" },
    neet_ug:  { eligible: true, reason: "" },
    cuet_ug:  { eligible: true, reason: "" },
  },
  canonical_plan_key: "ADMIN_GRANT", plan_name: "Test Access",
};

function mockFetch(accessData) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    json: () => Promise.resolve(accessData),
  }));
}

// ── User fixtures ─────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
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

// ── ExamPrepPage — Access gate tests (access-check endpoint) ─────────────────

describe("ExamPrepPage — Access Control", () => {
  it("Grade 9 free-tier student sees grade access denied", async () => {
    mockFetch(ACCESS_GRADE_INELIGIBLE);
    render(<ExamPrepPage user={grade9FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/Available for Grade 11 & 12 students only/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier student sees exam prep landing (not grade-blocked)", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Exam Prep Center — Premium Feature/i)).toBeTruthy();
    });
  });

  it("Grade 11 FREE-tier landing shows all three exam types", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getAllByText(/JEE Main prep/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/NEET UG prep/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/CUET UG prep/i).length).toBeGreaterThan(0);
    });
  });

  it("Grade 11 FREE-tier landing shows Coming Soon button", async () => {
    mockFetch(ACCESS_FREE_PREVIEW);
    render(<ExamPrepPage user={grade11FreeTier} />);
    await waitFor(() => {
      expect(screen.getByText(/Coming Soon/i)).toBeTruthy();
    });
  });

  it("Grade 11 NANO plan sees premium gate", async () => {
    mockFetch(ACCESS_NANO_PREVIEW);
    render(<ExamPrepPage user={grade11Nano} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Coming Soon/i)).toBeTruthy();
    });
  });

  it("Grade 11 PREMIUM plan sees full Exam Prep Center", async () => {
    mockFetch(ACCESS_FULL);
    render(<ExamPrepPage user={grade11Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("Grade 12 PREMIUM student sees full center (not grade-blocked)", async () => {
    mockFetch(ACCESS_FULL);
    render(<ExamPrepPage user={grade12Premium} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("Admin user bypasses grade gate and sees full center", async () => {
    mockFetch(ACCESS_ADMIN);
    render(<ExamPrepPage user={adminUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("akshita.teststudent (Grade 9) bypasses grade gate and sees full center", async () => {
    mockFetch(ACCESS_TEST_USER);
    render(<ExamPrepPage user={testUser} />);
    await waitFor(() => {
      expect(screen.queryByText(/Available for Grade 11 & 12 students only/i)).toBeNull();
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
    });
  });

  it("Grade 11 premium landing shows practice questions feature text", async () => {
    mockFetch(ACCESS_FULL);
    render(<ExamPrepPage user={grade11Premium} />);
    await waitFor(() => {
      expect(screen.getByText(/Structured Learning/i)).toBeTruthy();
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

  it("Exam Prep Centre visible for admin", () => {
    renderSidebar(adminUser);
    expect(screen.getByText("Exam Prep Center")).toBeTruthy();
  });
});
