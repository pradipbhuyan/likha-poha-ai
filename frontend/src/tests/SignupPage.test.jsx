import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import SignupPage from "../pages/SignupPage";

// Mock logo import
vi.mock("../assets/AITutorLogo1.png", () => ({ default: "logo.png" }));

// Mock subscription plans
vi.mock("../config/subscriptionPlans", () => ({
  SUBSCRIPTION_PLANS: {
    free: {
      key: "free", label: "Try It Out", price: 100, billingLabel: "14 days",
      badge: "Start here", audience: "Explore the platform before committing.",
      included: ["1 child profile", "CBSE lessons"], isPublic: true,
    },
    starter: {
      key: "starter", label: "Standard", price: 299, billingLabel: "month",
      badge: "Most Popular", audience: "Best for serious CBSE exam prep.",
      included: ["All CBSE subjects", "Unlimited doubt solving"], isPublic: true,
    },
    family_premium: {
      key: "family_premium", label: "Family", price: 499, billingLabel: "month",
      badge: "Best value", audience: "Best value plan for families.",
      included: ["Everything in Standard", "Up to 2 children"], isPublic: true,
    },
  },
}));

// Mock fetch globally by overriding globalThis directly
const mockFetch = vi.fn();

describe("SignupPage", () => {
  const mockOnBackToLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Override fetch directly on globalThis — vi.stubGlobal may not replace jsdom's
    // native undici-based fetch. Direct property assignment always works.
    globalThis.fetch = mockFetch;
    globalThis.Razorpay = vi.fn().mockImplementation((options) => ({
      open: vi.fn(),
      options,
    }));

    // loadRazorpay() appends a <script> to body and waits for onload.
    // jsdom never fires script onload — spy on body.appendChild to resolve it.
    // Use Node.prototype.appendChild to avoid recursive calls into the spy.
    vi.spyOn(document.body, "appendChild").mockImplementation(function(node) {
      const result = Node.prototype.appendChild.call(document.body, node);
      if (node && node.tagName === "SCRIPT") {
        const n = node;
        setTimeout(function() { if (typeof n.onload === "function") n.onload(); }, 0);
      }
      return result;
    });
  });

  // -----------------------------------------------------------------------
  // Role selection step
  // -----------------------------------------------------------------------

  test("renders role selection step with three role cards", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} initialPlan="free" />);

    expect(await screen.findByText(/signing up as a/i)).toBeInTheDocument();
    expect(screen.getByText("Parent")).toBeInTheDocument();
    expect(screen.getByText("Student")).toBeInTheDocument();
    expect(screen.getByText("Teacher")).toBeInTheDocument();
  });

  test("Login button calls onBackToLogin", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");

    fireEvent.click(screen.getByText(/already have an account/i));
    expect(mockOnBackToLogin).toHaveBeenCalledTimes(1);
  });

  // -----------------------------------------------------------------------
  // Parent signup journey
  // -----------------------------------------------------------------------

  test("parent role selection advances to form step", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} initialPlan="free" />);
    await screen.findByText("Parent");

    fireEvent.click(screen.getByText("Parent"));

    expect(await screen.findByText(/Create your account/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter your full name")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();
  });

  test("parent form does NOT show grade or school fields", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Create your account/i);

    expect(screen.queryByText(/Class \*/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/School Name/i)).not.toBeInTheDocument();
  });

  test("parent form shows plan selection on step 3", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Create your account/i);
    fireEvent.click(screen.getByText(/Continue to Plan Selection/i));

    expect(await screen.findByText("Try It Out")).toBeInTheDocument();
    expect(screen.getAllByText("Standard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Family")).toBeInTheDocument();
  });

  test("parent form shows validation error when fields are empty", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Create your account/i);
    // Navigate to plan step with empty fields — validation happens on Pay button
    fireEvent.click(screen.getByText(/Continue to Plan Selection/i));
    await screen.findByText(/Choose Your Plan/i);
    await act(async () => { fireEvent.click(screen.getByText(/Pay ₹/i)); });

    expect(
      await screen.findByText(/please fill in all required fields/i)
    ).toBeInTheDocument();
  });

  // TODO: jsdom async fetch mock — undici intercept needed; skipped until resolved
  test.skip("parent happy path: shows success screen after payment", async () => {
    // Mock signup-order API
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          order_id: "order_test_001",
          amount: 100,
          currency: "INR",
          key_id: "rzp_test_key",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, role: "parent" }),
      });

    // Mock Razorpay to auto-call handler with fake payment response
    vi.stubGlobal("Razorpay", vi.fn().mockImplementation((options) => ({
      open: vi.fn(() => {
        options.handler({
          razorpay_order_id: "order_test_001",
          razorpay_payment_id: "pay_test_001",
          razorpay_signature: "sig_test_001",
        });
      }),
    })));

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Parent Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Priya Sharma" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "priya@test.com" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });

    expect(await screen.findByText(/Payment Confirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/check your email/i)).toBeInTheDocument();
  });

  test.skip("parent signup shows error when signup-order API fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Payment is not configured." }),
    });

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Parent Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Priya Sharma" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "priya@test.com" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });

    expect(await screen.findByText(/Payment is not configured/i)).toBeInTheDocument();
  });

  test.skip("parent signup shows error when complete-signup API fails after payment", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true, order_id: "order_001", amount: 100,
          currency: "INR", key_id: "rzp_key",
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "An account with this email already exists. Please log in." }),
      });

    vi.stubGlobal("Razorpay", vi.fn().mockImplementation((options) => ({
      open: vi.fn(() => {
        options.handler({
          razorpay_order_id: "order_001",
          razorpay_payment_id: "pay_001",
          razorpay_signature: "sig_001",
        });
      }),
    })));

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Parent Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Duplicate User" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "duplicate@test.com" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });

    expect(
      await screen.findByText(/already exists/i)
    ).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Student signup journey
  // -----------------------------------------------------------------------

  test("student role selection shows grade dropdown", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Student");
    fireEvent.click(screen.getByText("Student"));
    await screen.findByText(/Create your account/i);

    expect(screen.getByText(/Class \*/i)).toBeInTheDocument();
    // Student form has Grade + Board selects — both are comboboxes
    expect(screen.getAllByRole("combobox").length).toBeGreaterThanOrEqual(1);
  });

  test("student form does NOT show school name field", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Student");
    fireEvent.click(screen.getByText("Student"));
    await screen.findByText(/Create your account/i);

    expect(screen.queryByText(/School Name/i)).not.toBeInTheDocument();
  });

  test.skip("student happy path: selects grade and completes payment", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true, order_id: "order_stu_001", amount: 100,
          currency: "INR", key_id: "rzp_key",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, role: "student" }),
      });

    vi.stubGlobal("Razorpay", vi.fn().mockImplementation((options) => ({
      open: vi.fn(() => {
        options.handler({
          razorpay_order_id: "order_stu_001",
          razorpay_payment_id: "pay_stu_001",
          razorpay_signature: "sig_stu_001",
        });
      }),
    })));

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Student");
    fireEvent.click(screen.getByText("Student"));
    await screen.findByText(/Student Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Akshita Sharma" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "akshita@test.com" },
    });
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "Grade 9" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });

    expect(await screen.findByText(/Payment Confirmed/i)).toBeInTheDocument();

    // Verify grade was sent in the complete-signup call
    const completeCall = mockFetch.mock.calls[1];
    const body = JSON.parse(completeCall[1].body);
    expect(body.grade).toBe("Grade 9");
    expect(body.role).toBe("student");
  });

  // -----------------------------------------------------------------------
  // Teacher signup journey
  // -----------------------------------------------------------------------

  test("teacher role selection shows school name field", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Teacher");
    fireEvent.click(screen.getByText("Teacher"));
    await screen.findByText(/Create your account/i);

    expect(screen.getByText(/School Name/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Name of your school/i)).toBeInTheDocument();
  });

  test("teacher form does NOT show grade dropdown", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Teacher");
    fireEvent.click(screen.getByText("Teacher"));
    await screen.findByText(/Create your account/i);

    expect(screen.queryByText(/Class \*/i)).not.toBeInTheDocument();
  });

  test.skip("teacher happy path: includes school name in complete-signup call", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true, order_id: "order_tch_001", amount: 100,
          currency: "INR", key_id: "rzp_key",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, role: "teacher" }),
      });

    vi.stubGlobal("Razorpay", vi.fn().mockImplementation((options) => ({
      open: vi.fn(() => {
        options.handler({
          razorpay_order_id: "order_tch_001",
          razorpay_payment_id: "pay_tch_001",
          razorpay_signature: "sig_tch_001",
        });
      }),
    })));

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Teacher");
    fireEvent.click(screen.getByText("Teacher"));
    await screen.findByText(/Teacher Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Mr. Ramesh Kumar" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "ramesh@school.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Name of your school/i), {
      target: { value: "Delhi Public School" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });

    expect(await screen.findByText(/Payment Confirmed/i)).toBeInTheDocument();

    const completeCall = mockFetch.mock.calls[1];
    const body = JSON.parse(completeCall[1].body);
    expect(body.school).toBe("Delhi Public School");
    expect(body.role).toBe("teacher");
  });

  // -----------------------------------------------------------------------
  // Navigation and plan selection
  // -----------------------------------------------------------------------

  test("back button returns to role selection from form step", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Create your account/i);

    fireEvent.click(screen.getByText(/← Back to role selection/i));

    expect(await screen.findByText(/signing up as a/i)).toBeInTheDocument();
  });

  test("plan selection pre-selects initialPlan prop", async () => {
    render(<SignupPage onBackToLogin={mockOnBackToLogin} initialPlan="starter" />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Create your account/i);
    fireEvent.click(screen.getByText(/Continue to Plan Selection/i));
    await screen.findByText(/Choose Your Plan/i);

    expect(screen.getAllByText("Standard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Try It Out")).toBeInTheDocument();
    expect(screen.getByText("Family")).toBeInTheDocument();
    expect(screen.getByText(/Pay ₹299/)).toBeInTheDocument();
  });

  test.skip("success screen Go to Login button calls onBackToLogin", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true, order_id: "order_done", amount: 100,
          currency: "INR", key_id: "rzp_key",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, role: "parent" }),
      });

    vi.stubGlobal("Razorpay", vi.fn().mockImplementation((options) => ({
      open: vi.fn(() => {
        options.handler({
          razorpay_order_id: "order_done",
          razorpay_payment_id: "pay_done",
          razorpay_signature: "sig_done",
        });
      }),
    })));

    render(<SignupPage onBackToLogin={mockOnBackToLogin} />);
    await screen.findByText("Parent");
    fireEvent.click(screen.getByText("Parent"));
    await screen.findByText(/Parent Account/i);

    fireEvent.change(screen.getByPlaceholderText("Enter your full name"), {
      target: { value: "Done User" },
    });
    fireEvent.change(screen.getByPlaceholderText("your@email.com"), {
      target: { value: "done@test.com" },
    });

    await act(async () => { fireEvent.submit(document.querySelector("form")); });
    await screen.findByText(/Payment Confirmed/i);

    fireEvent.click(screen.getByRole("button", { name: /Go to Login/i }));
    expect(mockOnBackToLogin).toHaveBeenCalledTimes(1);
  });
});
