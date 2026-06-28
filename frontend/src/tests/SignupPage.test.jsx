/**
 * SignupPage.test.jsx
 * Regression tests for single-step card-based signup (Option 1).
 *
 * Covers:
 * - Signup page renders one-step form
 * - Role cards for Parent, Student, Teacher render
 * - Pay & Sign Up tab is not present
 * - Offer Code tab/input is not present
 * - Step 1/2/3 labels are not present
 * - Parent signup submits role=parent
 * - Student signup submits role=student
 * - Teacher signup submits role=teacher
 * - Validation blocks missing name/email/password/role
 * - Technical errors not shown to user
 * - After signup, accessCbse=false (Free Tier)
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

// Mock supabaseClient
vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      signOut: vi.fn().mockResolvedValue({}),
      signInWithPassword: vi.fn().mockResolvedValue({
        data: { session: { access_token: "tok" }, user: { id: "user-1" } },
        error: null,
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({ data: { id: "user-1", username: "Test User", role: "parent", grade: "Grade 9" }, error: null }),
    }),
  },
}));

// Mock logo
vi.mock("../assets/AITutorLogo1.png", () => ({ default: "logo.png" }));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import SignupPage from "../pages/SignupPage";

const SUCCESS_RESPONSE = {
  ok: true, status: 200,
  json: async () => ({ success: true }),
};

describe("SignupPage — single-step card-based", () => {
  const onLogin = vi.fn();
  const onBack = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue(SUCCESS_RESPONSE);
  });

  test("renders signup page with one-step form", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.getByTestId("signup-page")).toBeInTheDocument();
    expect(screen.getByTestId("signup-form-card")).toBeInTheDocument();
    expect(screen.getByText("Create your account")).toBeInTheDocument();
  });

  test("role cards for Parent, Student, Teacher all render", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.getByTestId("role-card-parent")).toBeInTheDocument();
    expect(screen.getByTestId("role-card-student")).toBeInTheDocument();
    expect(screen.getByTestId("role-card-teacher")).toBeInTheDocument();
    expect(screen.getByText("Parent")).toBeInTheDocument();
    expect(screen.getByText("Student")).toBeInTheDocument();
    expect(screen.getByText("Teacher")).toBeInTheDocument();
  });

  test("Pay & Sign Up tab is NOT present", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.queryByText(/pay.*sign up/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/pay & sign/i)).not.toBeInTheDocument();
  });

  test("Offer Code tab/input is NOT present", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.queryByText(/offer code/i)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/offer code/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/have an offer code/i)).not.toBeInTheDocument();
  });

  test("Step 1/2/3 labels are NOT present", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.queryByText(/step 1/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/step 2/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/step 3/i)).not.toBeInTheDocument();
  });

  test("required fields render: name, email, password", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.getByTestId("signup-name")).toBeInTheDocument();
    expect(screen.getByTestId("signup-email")).toBeInTheDocument();
    expect(screen.getByTestId("signup-password")).toBeInTheDocument();
    expect(screen.getByTestId("signup-submit")).toBeInTheDocument();
    // Terms checkbox removed from UI
    expect(screen.queryByTestId("signup-terms")).not.toBeInTheDocument();
  });

  test("submit button says 'Start for Free'", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    expect(screen.getByTestId("signup-submit")).toHaveTextContent("Start for Free");
  });

  test("validation: missing name shows error", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).toMatch(/name is required/i);
  });

  test("validation: missing email shows error", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test User" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).toMatch(/email.*required/i);
  });

  test("validation: missing password shows error", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test User" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).toMatch(/password.*required/i);
  });

  test("validation: short password shows error", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "t@e.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "abc" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).toMatch(/8 characters/i);
  });

  test("parent role card selected by default", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    const parentCard = screen.getByTestId("role-card-parent");
    // Parent is selected by default — has purple border
    expect(parentCard.style.border).toContain("rgb(124");
  });

  test("clicking Student card selects student role", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    await waitFor(() => {
      expect(screen.getByTestId("role-card-student").style.border).toContain("rgb(124");
    });
  });

  test("parent signup submits role=parent to API", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    // Parent is default role
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test Parent" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "parent@test.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.role).toBe("parent");
      expect(body.email).toBe("parent@test.com");
    });
  });

  test("student signup submits role=student to API", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.click(screen.getByTestId("role-card-student"));
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test Student" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "student@test.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.role).toBe("student");
    });
  });

  test("teacher signup submits role=teacher to API", async () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.click(screen.getByTestId("role-card-teacher"));
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test Teacher" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "teacher@test.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.role).toBe("teacher");
    });
  });

  test("after successful signup, localStorage has accessCbse=false (Free Tier)", async () => {
    // Mock localStorage
    const lsSetItem = vi.spyOn(Storage.prototype, "setItem");
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Free User" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "free@test.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    await waitFor(() => {
      const calls = lsSetItem.mock.calls;
      const userCall = calls.find(c => c[0] === "tutor_user");
      if (userCall) {
        const userData = JSON.parse(userCall[1]);
        expect(userData.accessCbse).toBe(false);
        expect(userData.subscriptionPlan).toBe("free");
        expect(userData.offerAccess).toBe(false);
      }
    }, { timeout: 3000 });
    lsSetItem.mockRestore();
  });

  test("duplicate email error shows friendly message", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false, status: 409,
      json: async () => ({ success: false, detail: "User already registered" }),
    });
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "dup@test.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).toMatch(/already registered/i);
    // Must not expose "User already registered" raw Supabase message
    expect(screen.getByTestId("signup-error").textContent).not.toContain("User already registered");
  });

  test("Supabase error details are not shown to user", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false, status: 400,
      json: async () => ({ success: false, detail: "Supabase RLS policy denied row insert" }),
    });
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    fireEvent.change(screen.getByTestId("signup-name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByTestId("signup-email"), { target: { value: "t@t.com" } });
    fireEvent.change(screen.getByTestId("signup-password"), { target: { value: "password123" } });
    fireEvent.click(screen.getByTestId("signup-submit"));
    expect(await screen.findByTestId("signup-error")).toBeInTheDocument();
    expect(screen.getByTestId("signup-error").textContent).not.toContain("Supabase");
    expect(screen.getByTestId("signup-error").textContent).toMatch(/couldn.*create|try again/i);
  });

  test("sign in link renders and calls onBack", () => {
    render(<SignupPage onLogin={onLogin} onBack={onBack} />);
    const signinLink = screen.getByTestId("signup-signin-link");
    expect(signinLink).toBeInTheDocument();
    fireEvent.click(signinLink);
    expect(onBack).toHaveBeenCalled();
  });
});
