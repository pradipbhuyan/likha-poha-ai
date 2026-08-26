import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

// Mock supabaseClient so tests don't require real Supabase env vars
vi.mock("../api/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

import SubscriptionPlansPage from "../pages/SubscriptionPlansPage";
import {
  createPaymentOrder,
  getPaymentConfig,
  getStudentPaymentConfig,
  verifyPayment,
} from "../api/payments";
import { getParentChildren } from "../api/parentDashboard";

vi.mock("../api/parentDashboard", () => ({
  getParentChildren: vi.fn(async () => ({
    children: [
      {
        id: "child-1",
        username: "Student One",
        subscription_plan: "free",
        account_status: "active",
      },
    ],
  })),
  getParentSubscriptionPlans: vi.fn(async () => ({
    success: true,
    persisted: true,
    source: "database",
    plans: {
      free: {
        key: "free",
        label: "Free Trial",
        short_label: "Free",
        price: 0,
        billing_label: "14 days",
        is_public: true,
        display_order: 1,
        included: ["1 child profile"],
        not_included: [],
        comparison: {
          children: "1",
          aiUsage: "Limited",
          cbse: "Limited",
          parentDashboard: "Basic",
        },
      },
      starter: {
        key: "starter",
        label: "Standard",
        short_label: "Standard",
        price: 499,
        billing_label: "month",
        discount_percent: 10,
        discount_label: "Summer Special",
        is_public: true,
        display_order: 2,
        access_cbse: true,
        included: ["Everything in Free Trial"],
        not_included: [],
        comparison: {
          children: "1",
          aiUsage: "Higher limit",
          cbse: "Included",
          parentDashboard: "Full",
        },
      },
    },
    plan_order: ["free", "starter"],
    contact: {
      email: "help@likhapoha.test",
      phone: "",
      whatsapp: "",
      availability: "Replies within 24 hours.",
      message: "Need help choosing a plan? Contact support.",
    },
  })),
}));

vi.mock("../api/payments", () => ({
  getPaymentConfig: vi.fn(),
  getStudentPaymentConfig: vi.fn(),
  createPaymentOrder: vi.fn(),
  verifyPayment: vi.fn(),
}));

function renderPage() {
  /** Render the subscription page with a minimal mocked parent user. */
  return render(
    <SubscriptionPlansPage
      user={{
        role: "parent",
        email: "parent@example.com",
        username: "Parent User",
      }}
    />
  );
}

describe("SubscriptionPlansPage payments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete window.Razorpay;
    getPaymentConfig.mockResolvedValue({
      configured: false,
      provider: "razorpay",
      currency: "INR",
      key_id: null,
    });
  });

  test("shows safe payment pending state when Razorpay is not configured", async () => {
    /*
     * This validates the no-Razorpay setup path.
     *
     * Expected result:
     * - Parent selects a plan from the shared NoticeboardPricingTable (same
     *   comparison table + CTA row the student view uses, replacing the old
     *   per-plan card grid).
     * - The payment summary panel below reflects the real, DB-configured
     *   plan (discounted Standard price) once selected.
     * - Button says Payment Setup Pending.
     * - Clicking it does not call payment APIs and shows manual activation text.
     */
    renderPage();

    // "starter" is rendered as "Choose Premium" by the shared pricing table
    // (its CTA copy is fixed per plan key, independent of the admin-configured
    // display label) — selecting it still drives the real "starter" plan data.
    expect(
      await screen.findByRole("button", { name: /choose premium/i })
    ).toBeInTheDocument();
    expect(screen.getByText("help@likhapoha.test")).toBeInTheDocument();
    expect(screen.getByText("Replies within 24 hours.")).toBeInTheDocument();
    expect(
      screen.getByText("Support number will be added soon")
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /choose premium/i }));

    // Payment summary now shows the real DB-configured plan label + discounted price
    expect(screen.getByText("Standard")).toBeInTheDocument();
    expect(screen.getAllByText("₹449").length).toBeGreaterThan(0);

    const paymentButton = screen.getByRole("button", {
      name: /payment setup pending/i,
    });

    expect(paymentButton).toBeInTheDocument();
    fireEvent.click(paymentButton);

    expect(
      await screen.findByText(/admin can activate standard from admin control/i)
    ).toBeInTheDocument();
    expect(createPaymentOrder).not.toHaveBeenCalled();
    expect(verifyPayment).not.toHaveBeenCalled();
  });

  test("creates Razorpay order and verifies successful checkout callback", async () => {
    /*
     * This validates the configured-payment happy path using a mocked
     * Razorpay Checkout object.
     *
     * Expected result:
     * - Payment button changes to Pay with UPI.
     * - createPaymentOrder is called with child and plan.
     * - Razorpay checkout opens.
     * - handler calls verifyPayment with Razorpay ids/signature.
     */
    getPaymentConfig.mockResolvedValue({
      configured: true,
      provider: "razorpay",
      currency: "INR",
      key_id: "rzp_test_key",
    });
    createPaymentOrder.mockResolvedValue({
      key_id: "rzp_test_key",
      order: {
        id: "order_123",
        amount: 44900,
        currency: "INR",
      },
    });
    verifyPayment.mockResolvedValue({ success: true });

    const open = vi.fn();
    window.Razorpay = vi.fn(function Razorpay(options) {
      setTimeout(() => {
        options.handler({
          razorpay_order_id: "order_123",
          razorpay_payment_id: "pay_123",
          razorpay_signature: "signature_123",
        });
      }, 0);

      return { open };
    });

    renderPage();

    expect(
      await screen.findByRole("button", { name: /choose premium/i })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /choose premium/i }));
    fireEvent.click(screen.getByRole("button", { name: /pay with upi/i }));

    await waitFor(() => {
      expect(createPaymentOrder).toHaveBeenCalledWith({
        child_id: "child-1",
        plan_key: "starter",
      });
    });

    expect(window.Razorpay).toHaveBeenCalledWith(
      expect.objectContaining({
        key: "rzp_test_key",
        amount: 44900,
        currency: "INR",
        order_id: "order_123",
        method: {
          upi: true,
        },
      })
    );
    await waitFor(() => {
      expect(open).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(verifyPayment).toHaveBeenCalledWith({
        razorpay_order_id: "order_123",
        razorpay_payment_id: "pay_123",
        razorpay_signature: "signature_123",
      });
    });

    expect(
      await screen.findByText(/payment verified/i)
    ).toBeInTheDocument();
  });

  test("REGRESSION: refreshes the child's plan and notifies the app shell after successful payment", async () => {
    /*
     * Before this fix, the Razorpay success handler never refetched the
     * parent's children or called onSubscriptionComplete — the pay button
     * stayed enabled on the just-purchased plan (activePlan/isCurrentPlan
     * derive from `children`, which never updated), risking an accidental
     * second charge until a manual page reload.
     */
    getPaymentConfig.mockResolvedValue({
      configured: true,
      provider: "razorpay",
      currency: "INR",
      key_id: "rzp_test_key",
    });
    createPaymentOrder.mockResolvedValue({
      key_id: "rzp_test_key",
      order: { id: "order_123", amount: 44900, currency: "INR" },
    });
    verifyPayment.mockResolvedValue({ success: true });

    // Initial bootstrap load: child still on "free". Post-payment refetch:
    // child now shows "starter" — the newly-purchased plan.
    getParentChildren
      .mockResolvedValueOnce({
        children: [
          { id: "child-1", username: "Student One", subscription_plan: "free", account_status: "active" },
        ],
      })
      .mockResolvedValueOnce({
        children: [
          { id: "child-1", username: "Student One", subscription_plan: "starter", account_status: "active" },
        ],
      });

    const open = vi.fn();
    window.Razorpay = vi.fn(function Razorpay(options) {
      setTimeout(() => {
        options.handler({
          razorpay_order_id: "order_123",
          razorpay_payment_id: "pay_123",
          razorpay_signature: "signature_123",
        });
      }, 0);
      return { open };
    });

    const onSubscriptionComplete = vi.fn();
    render(
      <SubscriptionPlansPage
        user={{ role: "parent", email: "parent@example.com", username: "Parent User" }}
        onSubscriptionComplete={onSubscriptionComplete}
      />
    );

    expect(
      await screen.findByRole("button", { name: /choose premium/i })
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /choose premium/i }));
    fireEvent.click(screen.getByRole("button", { name: /pay with upi/i }));

    await waitFor(() => {
      expect(verifyPayment).toHaveBeenCalled();
    });

    // Children were refetched a second time (initial load + post-payment refresh)
    await waitFor(() => {
      expect(getParentChildren).toHaveBeenCalledTimes(2);
    });

    // Pay button must now reflect the new plan instead of staying purchasable
    expect(
      await screen.findByRole("button", { name: /current plan selected/i })
    ).toBeDisabled();

    // App shell notified so the parent's own profile refreshes too
    await waitFor(
      () => {
        expect(onSubscriptionComplete).toHaveBeenCalled();
      },
      { timeout: 2000 }
    );
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// REGRESSION: plan.included / notIncluded non-array crash
// Ticket: Student subscription page blank screen (2026-07-03)
// Root cause: DB sometimes returns included/notIncluded as a JSON string or null
// instead of an array. .map() on a non-array throws, crashing the component.
// ─────────────────────────────────────────────────────────────────────────────

describe("SubscriptionPlansPage — non-array included/notIncluded regression", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete window.Razorpay;
    getPaymentConfig.mockResolvedValue({
      configured: false,
      provider: "razorpay",
      currency: "INR",
      key_id: null,
    });
    // getStudentPaymentConfig is called when role=student
    getStudentPaymentConfig.mockResolvedValue({
      configured: false,
      provider: "razorpay",
      currency: "INR",
      key_id: null,
    });
  });

  test("does not crash when plan.included is a JSON string (DB regression)", async () => {
    /**
     * Reproduces the production blank-screen crash:
     * When subscription_plan_settings is saved via json.dumps(), the
     * included/notIncluded fields come back as strings, not arrays.
     * The component must render without throwing.
     */
    const { getParentSubscriptionPlans } = await import("../api/parentDashboard");
    getParentSubscriptionPlans.mockResolvedValueOnce({
      success: true,
      persisted: true,
      source: "database",
      plans: {
        starter: {
          key: "starter",
          label: "Premium",
          short_label: "Premium",
          price: 299,
          billing_label: "month",
          is_public: true,
          display_order: 1,
          access_cbse: true,
          // ← Non-array values that caused the crash
          included: "All CBSE subjects · All grades",
          not_included: null,
          comparison: {},
        },
      },
      plan_order: ["starter"],
      contact: {},
    });

    // Must not throw — page must render something
    render(
      <SubscriptionPlansPage
        user={{
          role: "parent",
          email: "parent@example.com",
          username: "Parent User",
        }}
      />
    );

    // The page should render — not crash to blank screen
    // (findAllByText used because "Premium" may appear in name + button)
    const matches = await screen.findAllByText(/Premium/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  test("does not crash when plan.included is null", async () => {
    const { getParentSubscriptionPlans } = await import("../api/parentDashboard");
    getParentSubscriptionPlans.mockResolvedValueOnce({
      success: true,
      persisted: true,
      source: "database",
      plans: {
        starter: {
          key: "starter",
          label: "Premium",
          short_label: "Premium",
          price: 299,
          billing_label: "month",
          is_public: true,
          display_order: 1,
          access_cbse: true,
          included: null,
          not_included: null,
          comparison: {},
        },
      },
      plan_order: ["starter"],
      contact: {},
    });

    render(
      <SubscriptionPlansPage
        user={{
          role: "parent",
          email: "parent@example.com",
          username: "Parent User",
        }}
      />
    );

    const matches2 = await screen.findAllByText(/Premium/i);
    expect(matches2.length).toBeGreaterThan(0);
  });

  test("does not crash when plan_order references a key missing from plans", async () => {
    /**
     * Reproduces a production crash: "Cannot read properties of undefined
     * (reading 'key')" at the plan grid's planOrder.map(). plan_order can
     * list a key that isn't (or is no longer) present in `plans` — the old
     * filter (`loadedPlans[planKey]?.isPublic !== false`) let missing keys
     * through because optional chaining on a missing entry evaluates to
     * `undefined`, which is `!== false`. The page must render the plans it
     * does have and simply skip the stray key, not crash to a blank screen.
     */
    const { getParentSubscriptionPlans } = await import("../api/parentDashboard");
    getParentSubscriptionPlans.mockResolvedValueOnce({
      success: true,
      persisted: true,
      source: "database",
      plans: {
        starter: {
          key: "starter",
          label: "Premium",
          short_label: "Premium",
          price: 299,
          billing_label: "month",
          is_public: true,
          display_order: 1,
          access_cbse: true,
          included: [],
          not_included: [],
          comparison: {},
        },
      },
      // "family_premium" has no matching entry in `plans` above
      plan_order: ["starter", "family_premium"],
      contact: {},
    });

    render(
      <SubscriptionPlansPage
        user={{
          role: "parent",
          email: "parent@example.com",
          username: "Parent User",
        }}
      />
    );

    const matches = await screen.findAllByText(/Premium/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  test("student role renders SubscriptionPlansPage without crash", async () => {
    /**
     * Student subscription view was never tested. This ensures the student
     * code path renders without crashing even with minimal plan data.
     */
    render(
      <SubscriptionPlansPage
        user={{
          role: "student",
          email: "student@example.com",
          username: "Test Student",
          subscriptionPlan: "free",
          accessCbse: false,
        }}
      />
    );

    // Should render loading or plan content — not crash to blank screen
    // (Either "Loading subscription plans..." or actual plan names appear)
    await waitFor(() => {
      const body = document.body.textContent;
      expect(body.length).toBeGreaterThan(0);
    });
  });

  test("standalone student can pick a plan via the Noticeboard comparison table", async () => {
    /**
     * The plan-selection cards were removed from the Subscription page; the
     * Noticeboard comparison table's CTA row is now the only plan picker for
     * a standalone student (no parentId). Clicking a real plan's button
     * there must update the selected plan reflected in the payment summary.
     */
    const { getParentSubscriptionPlans } = await import("../api/parentDashboard");
    getParentSubscriptionPlans.mockResolvedValueOnce({
      success: true,
      persisted: true,
      source: "database",
      plans: {
        starter: {
          key: "starter",
          label: "Premium",
          short_label: "Premium",
          price: 499,
          billing_label: "month",
          is_public: true,
          display_order: 1,
          access_cbse: true,
          included: ["Everything in Free Trial"],
          not_included: [],
          comparison: {},
        },
        family_premium: {
          key: "family_premium",
          label: "Family Premium",
          short_label: "Family",
          price: 799,
          billing_label: "month",
          is_public: true,
          display_order: 2,
          access_cbse: true,
          included: ["Everything in Premium"],
          not_included: [],
          comparison: {},
        },
      },
      plan_order: ["starter", "family_premium"],
      contact: {},
    });

    render(
      <SubscriptionPlansPage
        user={{
          role: "student",
          email: "student@example.com",
          username: "Test Student",
        }}
      />
    );

    // "Start Free" is a dead end for students (free_tier is never a real
    // fetched plan here), so it must not be offered in this view.
    await screen.findByRole("button", { name: /choose premium/i });
    expect(
      screen.queryByRole("button", { name: /start free/i })
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /get family premium/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/family premium/i).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText("₹799").length).toBeGreaterThan(0);
  });
});
